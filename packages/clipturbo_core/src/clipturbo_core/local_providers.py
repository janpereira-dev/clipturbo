from __future__ import annotations

import asyncio
import hashlib
import importlib
import json
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from uuid import uuid4

from clipturbo_core.domain import PublishPlatform, RenderFormat
from clipturbo_core.providers import (
    GeneratedScript,
    GeneratedSubtitles,
    ProviderTrace,
    PublishResult,
    RenderedVideo,
    SubtitleSegment,
    SynthesizedAudio,
)
from clipturbo_core.text_correction import (
    NoOpSpanishCorrector,
    SpanishTextCorrector,
)


_MAX_SUBPROCESS_ERROR_OUTPUT_CHARS = 1000


def _truncate_subprocess_output(output: str | None) -> str:
    if not output:
        return ""
    normalized = output.strip()
    if len(normalized) <= _MAX_SUBPROCESS_ERROR_OUTPUT_CHARS:
        return normalized
    return normalized[:_MAX_SUBPROCESS_ERROR_OUTPUT_CHARS] + "... [truncated]"


def _run(command: list[str]) -> None:
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        output = _truncate_subprocess_output(error.stderr) or _truncate_subprocess_output(error.stdout)
        details = f": {output}" if output else ""
        raise RuntimeError(f"Command failed ({' '.join(command)}){details}") from error


def _ffprobe_duration_seconds(asset_path: str) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            asset_path,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def _split_sentences(text: str) -> list[str]:
    parts = [segment.strip() for segment in re.split(r"[.!?]+", text) if segment.strip()]
    return parts or [text.strip()]


def _extract_topic_from_prompt(prompt: str) -> str:
    lower = prompt.lower()
    marker = "sobre "
    index = lower.find(marker)
    if index == -1:
        return ""
    topic = prompt[index + len(marker) :].strip().rstrip(".")
    return topic


class HuggingFaceSpanishLLMProvider:
    def __init__(
        self,
        model_id: str,
        max_new_tokens: int = 220,
        text_corrector: SpanishTextCorrector | None = None,
        allow_fallback: bool = True,
        fallback_model_ids: list[str] | None = None,
    ) -> None:
        self._model_id = model_id
        self._fallback_model_ids = fallback_model_ids or []
        self._max_new_tokens = max_new_tokens
        self._text_corrector = text_corrector or NoOpSpanishCorrector()
        self._allow_fallback = allow_fallback
        self._runtime: dict[str, object] | None = None
        self._active_model_id = model_id

    @property
    def active_model_id(self) -> str:
        return self._active_model_id

    def generate_text(self, prompt: str) -> GeneratedScript:
        topic = _extract_topic_from_prompt(prompt)
        model_prompt = prompt.strip() or _build_generation_prompt(topic)
        try:
            cleaned, degraded = self._generate_validated_script(model_prompt=model_prompt, topic=topic)
            correction = self._text_corrector.correct(cleaned)
            script_text = correction.text
            provider_name = "hf_local_generation_degraded" if degraded else "hf_local_generation"
            provider_model = _compact_provider_model(
                model_id=self.active_model_id,
                correction_engine=correction.engine,
                correction_model=correction.model,
                retry=degraded,
            )
        except Exception as exc:
            if _is_model_access_error(exc):
                raise RuntimeError(_build_hf_model_access_message(self._candidate_model_ids())) from exc
            if not self._allow_fallback:
                raise
            cleaned_retry, degraded_retry = self._generate_validated_script(
                model_prompt=_build_generation_prompt_recovery(topic),
                topic=topic,
            )
            correction = self._text_corrector.correct(cleaned_retry)
            script_text = correction.text
            provider_name = "hf_local_generation_recovery_degraded" if degraded_retry else "hf_local_generation_recovery"
            provider_model = _compact_provider_model(
                model_id=self.active_model_id,
                correction_engine=correction.engine,
                correction_model=correction.model,
                retry=True,
            )

        trace: ProviderTrace = {
            "provider_name": provider_name,
            "provider_model": _truncate_provider_model(provider_model),
            "request_id": f"llm_{uuid4().hex}",
        }
        return {"script_text": script_text, "trace": trace}

    def _generate_validated_script(self, model_prompt: str, topic: str) -> tuple[str, bool]:
        prompts: list[str] = [model_prompt, _build_generation_prompt_retry(topic)]
        last_candidate = ""

        for prompt_item in prompts:
            raw = self._generate(model_prompt=prompt_item, topic=topic)
            cleaned = _clean_generated_script(raw, prompt_item)
            last_candidate = cleaned
            try:
                _validate_generated_script(cleaned, topic)
                return cleaned, False
            except Exception:
                continue

        repair_prompt = _build_generation_prompt_repair(topic=topic, previous_output=last_candidate)
        repaired_raw = self._generate(model_prompt=repair_prompt, topic=topic)
        repaired_clean = _clean_generated_script(repaired_raw, repair_prompt)
        try:
            _validate_generated_script(repaired_clean, topic)
            return repaired_clean, False
        except Exception:
            return _soft_recover_script(repaired_clean, topic), True

    def _generate(self, model_prompt: str, topic: str) -> str:
        runtime = self._get_runtime()
        tokenizer = runtime["tokenizer"]
        model = runtime["model"]
        torch_module = runtime["torch_module"]
        mode = runtime["mode"]

        if mode == "causal":
            encoded = _encode_causal_prompt(tokenizer=tokenizer, topic=topic, user_prompt=model_prompt)
        else:
            encoded = tokenizer(  # type: ignore[operator]
                model_prompt,
                return_tensors="pt",
                truncation=True,
                max_length=1024,
            )
        with torch_module.no_grad():  # type: ignore[attr-defined]
            output_ids = model.generate(  # type: ignore[operator]
                **encoded,
                max_new_tokens=self._max_new_tokens,
                do_sample=True,
                temperature=0.8,
                top_p=0.9,
                repetition_penalty=1.1,
                num_beams=1 if mode == "causal" else 3,
            )

        if mode == "causal":
            input_length = encoded["input_ids"].shape[1]
            output_ids = output_ids[:, input_length:]

        decoded = tokenizer.decode(output_ids[0], skip_special_tokens=True)  # type: ignore[operator]
        return decoded.strip()

    def _get_runtime(self) -> dict[str, object]:
        if self._runtime is not None:
            return self._runtime
        errors: list[Exception] = []
        for candidate_model in self._candidate_model_ids():
            try:
                runtime = self._load_runtime_for_model(candidate_model)
                self._active_model_id = candidate_model
                self._runtime = runtime
                return runtime
            except Exception as exc:
                errors.append(exc)
                continue
        if errors and any(_is_model_access_error(err) for err in errors):
            raise RuntimeError(_build_hf_model_access_message(self._candidate_model_ids())) from errors[-1]
        last_error = errors[-1] if errors else RuntimeError("runtime no disponible")
        raise RuntimeError("No fue posible cargar ningun modelo HF para generacion de guion.") from last_error

    def _load_runtime_for_model(self, model_id: str) -> dict[str, object]:
        transformers_module, torch_module = _load_transformers_runtime()
        auto_tokenizer = getattr(transformers_module, "AutoTokenizer")
        tokenizer = auto_tokenizer.from_pretrained(model_id)

        model: object
        mode: str
        try:
            auto_seq2seq = getattr(transformers_module, "AutoModelForSeq2SeqLM")
            model = auto_seq2seq.from_pretrained(model_id)
            mode = "seq2seq"
        except Exception:
            auto_causal = getattr(transformers_module, "AutoModelForCausalLM")
            model = auto_causal.from_pretrained(model_id)
            mode = "causal"

        model.eval()  # type: ignore[operator]
        return {
            "tokenizer": tokenizer,
            "model": model,
            "torch_module": torch_module,
            "mode": mode,
        }

    def _candidate_model_ids(self) -> list[str]:
        candidates = [self._model_id, *self._fallback_model_ids]
        unique: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            model_id = candidate.strip()
            if not model_id or model_id in seen:
                continue
            seen.add(model_id)
            unique.append(model_id)
        return unique


def huggingface_generation_available() -> bool:
    try:
        _load_transformers_runtime()
    except Exception:
        return False
    return True


def _load_transformers_runtime() -> tuple[ModuleType, ModuleType]:
    try:
        transformers_module = importlib.import_module("transformers")
        torch_module = importlib.import_module("torch")
    except Exception as exc:
        raise RuntimeError(
            "No se pudo importar transformers/torch para generacion HF. "
            "Instala dependencias: python -m pip install transformers sentencepiece torch"
        ) from exc
    return transformers_module, torch_module


def _is_model_access_error(error: Exception) -> bool:
    text = str(error).lower()
    patterns = (
        "gated repo",
        "cannot access gated repo",
        "401",
        "unauthorized",
        "make sure to have access",
    )
    return any(pattern in text for pattern in patterns)


def _build_hf_model_access_message(candidate_model_ids: list[str]) -> str:
    candidates = ", ".join(candidate_model_ids)
    return (
        "No se pudo acceder a modelos HF (repo gated o credenciales faltantes). "
        f"Modelos intentados: {candidates}. "
        "Usa modelos abiertos en `manifests/model-routing.json` o autentica con `huggingface-cli login`."
    )


def _build_generation_prompt(topic: str) -> str:
    return (
        "Genera un guion en espanol para video vertical de 30 a 45 segundos (90 a 130 palabras). "
        f"Tema: {topic}. "
        "Escribe 6 a 8 frases claras, naturales y publicables. "
        "No incluyas encabezados, bullets, hashtags ni emojis. "
        "No repitas el prompt ni metainstrucciones."
    )


def _build_generation_prompt_retry(topic: str) -> str:
    return (
        "Reescribe desde cero un guion final limpio en espanol. "
        f"Tema real: {topic}. "
        "Debe ser util para narracion TTS, 6 a 8 frases, sin formato markdown, sin comillas envolventes. "
        "Devuelve solo el guion."
    )


def _build_generation_prompt_recovery(topic: str) -> str:
    return (
        "Recuperacion de salida: produce una version alternativa y mas simple del guion. "
        f"Tema: {topic}. "
        "Mantener neutralidad regional (espanol internacional), claridad y tono sobrio. "
        "Devuelve solo texto final, sin metaexplicaciones."
    )


def _build_generation_prompt_repair(topic: str, previous_output: str) -> str:
    clipped = previous_output[:450]
    return (
        "Corrige y reescribe el siguiente borrador para que sea un guion final limpio en espanol. "
        f"Tema obligatorio: {topic}. "
        "Reglas: 6 a 8 frases, texto continuo, sin markdown, sin bullets, sin etiquetas de escena, sin ingles. "
        "Devuelve solo el guion final.\n\n"
        f"Borrador:\n{clipped}"
    )


def _encode_causal_prompt(tokenizer: object, topic: str, user_prompt: str) -> dict[str, object]:
    if hasattr(tokenizer, "apply_chat_template"):
        messages = [
            {
                "role": "system",
                "content": (
                    "Eres un redactor experto en guiones cortos en espanol para redes sociales. "
                    "Responde siempre con texto final publicable."
                ),
            },
            {"role": "user", "content": user_prompt},
        ]
        rendered = tokenizer.apply_chat_template(  # type: ignore[operator]
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        return tokenizer(  # type: ignore[operator]
            rendered,
            return_tensors="pt",
            truncation=True,
            max_length=1024,
        )
    return tokenizer(  # type: ignore[operator]
        f"{user_prompt}\nTema real: {topic}\nGuion final:",
        return_tensors="pt",
        truncation=True,
        max_length=1024,
    )


def _clean_generated_script(text: str, model_prompt: str) -> str:
    cleaned = text.strip()
    if cleaned.lower().startswith(model_prompt.lower()):
        cleaned = cleaned[len(model_prompt) :].strip()
    cleaned = _sanitize_editorial_artifacts(cleaned)
    cleaned = cleaned.strip("\"'`")
    cleaned = re.sub(r"^(guion|script)\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^[\-\*\d\.\)\s]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        raise RuntimeError("El modelo HF devolvio salida vacia")
    return cleaned


def _validate_generated_script(text: str, topic: str) -> None:
    lowered = text.lower()
    if len(text.split()) < 8:
        raise RuntimeError("Salida HF demasiado corta para guion operativo")
    forbidden = (
        "escribe un guion",
        "tema:",
        "tono:",
        "formato:",
        "solo el guion",
        "corrige ortografia",
        "conserva significado",
        "devuelve solo el texto corregido",
        "texto corregido",
        "guion final",
        "script final",
    )
    if any(token in lowered for token in forbidden):
        raise RuntimeError("Salida HF contiene metainstrucciones")

    if "**" in text or "#" in text:
        raise RuntimeError("Salida HF contiene formato no editorial")
    if any(marker in text for marker in ("[", "]", "•")):
        raise RuntimeError("Salida HF contiene marcadores no editoriales")
    if re.search(r"\b(INT|EXT)\b", text, flags=re.IGNORECASE):
        raise RuntimeError("Salida HF con formato tipo screenplay")

    sentence_candidates = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    if len(sentence_candidates) < 2:
        raise RuntimeError("Salida HF con pocas frases completas")

    tokens = [tok.strip(".,;:!?()[]\"'") for tok in text.split()]
    significant = [tok for tok in tokens if len(tok) >= 3]
    if significant:
        uppercase_ratio = sum(1 for tok in significant if tok.isupper()) / len(significant)
        if uppercase_ratio > 0.25:
            raise RuntimeError("Salida HF con exceso de tokens en mayusculas")

    topic_terms = [t for t in re.findall(r"[a-záéíóúñü]{4,}", topic.lower()) if t not in {"sobre"}]
    if topic_terms and not any(term in lowered for term in topic_terms[:2]):
        raise RuntimeError("Salida HF sin relacion visible con el topic")


def _compact_provider_model(
    model_id: str,
    correction_engine: str,
    correction_model: str,
    retry: bool,
) -> str:
    mode = "retry" if retry else "direct"
    return f"{model_id}|{mode}|corr:{correction_engine}:{correction_model}"


def _truncate_provider_model(value: str, max_len: int = 120) -> str:
    if len(value) <= max_len:
        return value
    short_hash = hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]
    keep = max_len - 9
    return f"{value[:keep]}#{short_hash}"


def _soft_recover_script(text: str, topic: str) -> str:
    cleaned = _sanitize_editorial_artifacts(text)
    cleaned = re.sub(r"\[.*?\]", " ", cleaned)
    cleaned = cleaned.replace("•", " ")
    cleaned = re.sub(r"(?m)^\s*\d+\s*$", " ", cleaned)
    cleaned = re.sub(r"\b(INT|EXT)\b\.?", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[#*_`]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        cleaned = topic.strip()
    if cleaned and cleaned[-1] not in ".!?":
        cleaned = f"{cleaned}."
    return cleaned


def _sanitize_editorial_artifacts(text: str) -> str:
    cleaned = text
    cleaned = re.sub(
        r"\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"(?m)^\s*\d+\s*$", " ", cleaned)
    cleaned = re.sub(r"(?i)\b(guion|script)\s*final\b[\s:\-\*]*", " ", cleaned)
    cleaned = re.sub(r"(?i)\btexto\s*:\s*", " ", cleaned)
    cleaned = re.sub(r"(?i)\beste guion\b[^.:]{0,120}[:\-]\s*", " ", cleaned)
    cleaned = re.sub(r"[#*_`]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


class WindowsSpeechTTSProvider:
    def __init__(self, output_dir: str | Path, default_voice: str = "Microsoft Laura") -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._default_voice = default_voice

    def synthesize(self, script: str, voice_id: str) -> SynthesizedAudio:
        voice = (voice_id or self._default_voice).strip()
        wav_path = self._output_dir / f"voice_{uuid4().hex}.wav"
        escaped_voice = voice.replace("'", "''")
        escaped_text = script.replace("'", "''")
        escaped_path = str(wav_path).replace("'", "''")
        command = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.SelectVoice('{escaped_voice}'); "
            "$s.Rate = 0; $s.Volume = 100; "
            f"$s.SetOutputToWaveFile('{escaped_path}'); "
            f"$s.Speak('{escaped_text}'); "
            "$s.Dispose();"
        )
        _run(["powershell", "-NoProfile", "-Command", command])
        duration_seconds = _ffprobe_duration_seconds(str(wav_path))
        trace: ProviderTrace = {
            "provider_name": "windows_speech",
            "provider_model": voice,
            "request_id": f"tts_{uuid4().hex}",
        }
        return {
            "asset_path": str(wav_path),
            "duration_ms": int(duration_seconds * 1000),
            "trace": trace,
        }


class EdgeNeuralTTSProvider:
    def __init__(self, output_dir: str | Path, default_voice: str = "es-ES-AlvaroNeural") -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._default_voice = default_voice

    def synthesize(self, script: str, voice_id: str) -> SynthesizedAudio:
        voice = (voice_id or self._default_voice).strip()
        output_path = self._output_dir / f"voice_{uuid4().hex}.mp3"

        if edge_tts_available(python_only=True):
            _synthesize_with_edge_python(script=script, voice=voice, output_path=output_path)
        elif edge_tts_available(cli_only=True):
            _run(
                [
                    "edge-tts",
                    "--text",
                    script,
                    "--voice",
                    voice,
                    "--write-media",
                    str(output_path),
                ]
            )
        else:
            raise RuntimeError(
                "No se encontro edge-tts. Instala con `pip install edge-tts` para usar modo fluido."
            )

        duration_seconds = _ffprobe_duration_seconds(str(output_path))
        trace: ProviderTrace = {
            "provider_name": "edge_tts",
            "provider_model": voice,
            "request_id": f"tts_{uuid4().hex}",
        }
        return {
            "asset_path": str(output_path),
            "duration_ms": int(duration_seconds * 1000),
            "trace": trace,
        }


def _has_edge_tts_python() -> bool:
    try:
        import edge_tts  # noqa: F401
    except Exception:
        return False
    return True


def edge_tts_available(*, python_only: bool = False, cli_only: bool = False) -> bool:
    python_available = _has_edge_tts_python()
    cli_available = bool(shutil.which("edge-tts"))
    if python_only:
        return python_available
    if cli_only:
        return cli_available
    return python_available or cli_available


def _synthesize_with_edge_python(script: str, voice: str, output_path: Path) -> None:
    import edge_tts

    async def _run_async() -> None:
        communicate = edge_tts.Communicate(text=script, voice=voice)
        await communicate.save(str(output_path))

    asyncio.run(_run_async())


class LocalSubtitleProvider:
    def __init__(self, output_dir: str | Path) -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, script: str, audio_path: str) -> GeneratedSubtitles:
        sentences = _split_sentences(script)
        total_duration = max(_ffprobe_duration_seconds(audio_path), float(len(sentences) * 2))
        total_chars = sum(max(len(sentence), 1) for sentence in sentences)
        cursor = 0.0
        segments: list[SubtitleSegment] = []
        for sentence in sentences:
            ratio = max(len(sentence), 1) / total_chars
            duration = max(2.0, total_duration * ratio)
            start = int(cursor * 1000)
            end = int((cursor + duration) * 1000)
            segments.append({"start_ms": start, "end_ms": end, "text": sentence})
            cursor += duration

        trace: ProviderTrace = {
            "provider_name": "local_subtitles",
            "provider_model": "timed_segments_v1",
            "request_id": f"subs_{uuid4().hex}",
        }
        return {"format": "srt", "segments": segments, "trace": trace}

    def write_srt(self, subtitles: GeneratedSubtitles, target_path: str | Path) -> Path:
        srt_path = Path(target_path)
        srt_path.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        for index, segment in enumerate(subtitles["segments"], start=1):
            lines.append(str(index))
            lines.append(f"{_ms_to_srt_time(segment['start_ms'])} --> {_ms_to_srt_time(segment['end_ms'])}")
            lines.append(segment["text"])
            lines.append("")
        srt_path.write_text("\n".join(lines), encoding="utf-8")
        return srt_path


def _ms_to_srt_time(value: int) -> str:
    total_ms = max(value, 0)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


class FFmpegVideoRenderProvider:
    def __init__(self, output_dir: str | Path, subtitle_provider: LocalSubtitleProvider) -> None:
        self._output_dir = Path(output_dir)
        self._subtitle_provider = subtitle_provider
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def compose(
        self,
        script: str,
        audio_path: str,
        subtitles: GeneratedSubtitles,
        render_format: RenderFormat,
    ) -> RenderedVideo:
        width, height = (1080, 1920) if render_format == RenderFormat.VERTICAL_9_16 else (1920, 1080)
        duration = max(_ffprobe_duration_seconds(audio_path) + 1.0, 8.0)
        job_id = uuid4().hex
        srt_path = self._subtitle_provider.write_srt(subtitles, self._output_dir / f"{job_id}.srt")
        output_path = self._output_dir / f"{job_id}.mp4"

        subtitle_path = os.path.relpath(srt_path, Path.cwd()).replace("\\", "/")
        filter_chain = _build_subtitle_filter_chain(subtitle_path)

        _run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c=0x0f172a:s={width}x{height}:r=30:d={duration:.2f}",
                "-i",
                audio_path,
                "-vf",
                filter_chain,
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                str(output_path),
            ]
        )

        trace: ProviderTrace = {
            "provider_name": "ffmpeg",
            "provider_model": "ffmpeg_template_v1",
            "request_id": f"render_{job_id}",
        }
        return {
            "asset_path": str(output_path),
            "duration_ms": int(duration * 1000),
            "trace": trace,
        }


def _build_subtitle_filter_chain(subtitle_path: str) -> str:
    escaped_path = _escape_ffmpeg_filter_value(subtitle_path)
    return (
        f"subtitles='{escaped_path}':"
        "force_style='FontName=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00303030,"
        "BorderStyle=3,Outline=1,Shadow=0,Alignment=2,MarginV=120'"
    )


def _escape_ffmpeg_filter_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace(":", r"\:").replace("'", r"\'")


class LocalStorageProvider:
    def __init__(self, root_dir: str | Path) -> None:
        self._root_dir = Path(root_dir)
        self._root_dir.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, source_path: str) -> str:
        destination = self._root_dir / key
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)
        return str(destination)


class LocalDraftPublisherProvider:
    def __init__(self, root_dir: str | Path) -> None:
        self._root_dir = Path(root_dir)
        self._root_dir.mkdir(parents=True, exist_ok=True)

    def publish_draft(
        self,
        platform: PublishPlatform,
        asset_path: str,
        metadata: dict[str, str],
    ) -> PublishResult:
        post_id = f"{platform.value}_{uuid4().hex[:8]}"
        payload = {
            "post_id": post_id,
            "platform": platform.value,
            "asset_path": asset_path,
            "metadata": metadata,
            "created_at": datetime.now(UTC).isoformat(),
            "status": "draft",
        }
        output_dir = self._root_dir / platform.value
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{post_id}.json"
        output_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        trace: ProviderTrace = {
            "provider_name": "local_draft_publisher",
            "provider_model": platform.value,
            "request_id": f"publish_{uuid4().hex}",
        }
        return {
            "external_post_id": post_id,
            "external_url": str(output_file),
            "trace": trace,
        }
