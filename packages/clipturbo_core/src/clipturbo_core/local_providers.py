from __future__ import annotations

import asyncio
import hashlib
import importlib
import json
import os
import random
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
from clipturbo_core.spanish_quality import SpanishOrthographyGuard
from clipturbo_core.text_correction import (
    CorrectionResult,
    RuleBasedSpanishCorrector,
    SpanishTextCorrector,
)


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True, capture_output=True, text=True)


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


class RuleBasedSpanishLLMProvider:
    def __init__(
        self,
        quality_guard: SpanishOrthographyGuard | None = None,
        text_corrector: SpanishTextCorrector | None = None,
    ) -> None:
        guard = quality_guard or SpanishOrthographyGuard()
        self._text_corrector = text_corrector or RuleBasedSpanishCorrector(guard=guard)
        self._last_correction = CorrectionResult(
            text="",
            engine="guard",
            model="spanish_orthography_guard_v1",
        )

    @property
    def last_correction_engine(self) -> str:
        return self._last_correction.engine

    @property
    def last_correction_model(self) -> str:
        return self._last_correction.model

    def generate_text(self, prompt: str) -> GeneratedScript:
        topic = self._extract_topic(prompt)
        lines = _build_topic_guided_lines(topic)
        correction = self._text_corrector.correct(" ".join(lines))
        self._last_correction = correction
        script_text = correction.text
        trace: ProviderTrace = {
            "provider_name": "rule_based_local",
            "provider_model": f"stoic-es-v1|correction:{correction.engine}:{correction.model}",
            "request_id": f"llm_{uuid4().hex}",
        }
        return {"script_text": script_text, "trace": trace}

    @staticmethod
    def _extract_topic(prompt: str) -> str:
        lower = prompt.lower()
        marker = "sobre "
        index = lower.find(marker)
        if index == -1:
            return "tu objetivo"
        topic = prompt[index + len(marker) :].strip().rstrip(".")
        return topic or "tu objetivo"


class HuggingFaceSpanishLLMProvider:
    def __init__(
        self,
        model_id: str,
        max_new_tokens: int = 220,
        text_corrector: SpanishTextCorrector | None = None,
        allow_fallback: bool = True,
    ) -> None:
        self._model_id = model_id
        self._max_new_tokens = max_new_tokens
        self._text_corrector = text_corrector or RuleBasedSpanishCorrector()
        self._allow_fallback = allow_fallback
        self._runtime: dict[str, object] | None = None

    def generate_text(self, prompt: str) -> GeneratedScript:
        topic = RuleBasedSpanishLLMProvider._extract_topic(prompt)
        model_prompt = _build_generation_prompt(topic)
        try:
            cleaned = self._generate_validated_script(model_prompt=model_prompt, topic=topic)
            correction = self._text_corrector.correct(cleaned)
            script_text = correction.text
            provider_name = "hf_local_generation"
            provider_model = f"{self._model_id}|correction:{correction.engine}:{correction.model}"
        except Exception:
            if not self._allow_fallback:
                raise
            fallback_lines = _build_topic_guided_lines(topic)
            correction = self._text_corrector.correct(" ".join(fallback_lines))
            script_text = correction.text
            provider_name = "hf_local_generation_fallback"
            provider_model = f"topic_guided_v1|correction:{correction.engine}:{correction.model}"

        trace: ProviderTrace = {
            "provider_name": provider_name,
            "provider_model": provider_model,
            "request_id": f"llm_{uuid4().hex}",
        }
        return {"script_text": script_text, "trace": trace}

    def _generate_validated_script(self, model_prompt: str, topic: str) -> str:
        first_raw = self._generate(model_prompt=model_prompt, topic=topic)
        first_clean = _clean_generated_script(first_raw, model_prompt)
        try:
            _validate_generated_script(first_clean, topic)
            return first_clean
        except Exception:
            retry_prompt = _build_generation_prompt_retry(topic)
            second_raw = self._generate(model_prompt=retry_prompt, topic=topic)
            second_clean = _clean_generated_script(second_raw, retry_prompt)
            _validate_generated_script(second_clean, topic)
            return second_clean

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
        transformers_module, torch_module = _load_transformers_runtime()
        auto_tokenizer = getattr(transformers_module, "AutoTokenizer")
        tokenizer = auto_tokenizer.from_pretrained(self._model_id)

        model: object
        mode: str
        try:
            auto_seq2seq = getattr(transformers_module, "AutoModelForSeq2SeqLM")
            model = auto_seq2seq.from_pretrained(self._model_id)
            mode = "seq2seq"
        except Exception:
            auto_causal = getattr(transformers_module, "AutoModelForCausalLM")
            model = auto_causal.from_pretrained(self._model_id)
            mode = "causal"

        model.eval()  # type: ignore[operator]
        self._runtime = {
            "tokenizer": tokenizer,
            "model": model,
            "torch_module": torch_module,
            "mode": mode,
        }
        return self._runtime


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


def _build_topic_guided_lines(topic: str) -> list[str]:
    clean_topic = topic.strip()
    normalized_topic = _normalize_topic_for_script(clean_topic)
    seed = int(hashlib.sha256(clean_topic.encode("utf-8")).hexdigest()[:8], 16)
    rng = random.Random(seed)

    openers = [
        "Hoy puedes mirar",
        "Ahora te toca observar",
        "En este momento conviene enfrentar",
        "Tu primer paso es reconocer",
    ]
    reframes = [
        "sin convertirlo en tu identidad.",
        "sin dejar que te defina por completo.",
        "como un estado temporal, no como destino.",
        "como una señal que puedes gestionar con método.",
    ]
    breath_actions = [
        "Respira cuatro segundos, exhala seis y baja el ritmo interno.",
        "Haz una pausa breve: inhala profundo, exhala lento y vuelve al presente.",
        "Detén la prisa mental con tres respiraciones largas y conscientes.",
    ]
    focus_actions = [
        "Elige una tarea de diez minutos y complétala antes de evaluar tu día.",
        "Define una acción mínima y termínala sin negociar contigo.",
        "Empieza por un bloque corto y deja que el impulso trabaje a tu favor.",
    ]
    discipline_lines = [
        "La disciplina no elimina el dolor, pero sí evita que mande sobre tu agenda.",
        "La constancia no exige perfección; exige volver a intentarlo hoy.",
        "El progreso nace cuando decides actuar incluso con incomodidad.",
    ]
    perspective_lines = [
        "No necesitas resolverlo todo ahora: necesitas sostener el siguiente paso.",
        "No busques aplausos rápidos; busca evidencia diaria de avance real.",
        "No esperes motivación perfecta; construye estabilidad con rutina simple.",
    ]
    closing_lines = [
        "Haz lo que depende de ti hoy y deja que mañana encuentre a alguien más fuerte.",
        "Suma una victoria pequeña hoy y tu narrativa empezará a cambiar.",
        "Acción sobria, foco diario y paciencia: así recuperas el control.",
    ]

    return [
        f"{rng.choice(openers)} {normalized_topic} {rng.choice(reframes)}",
        f"Cuando aparezca {normalized_topic}, {rng.choice(breath_actions)}",
        f"Convierte {normalized_topic} en dirección práctica: {rng.choice(focus_actions)}",
        rng.choice(discipline_lines),
        rng.choice(perspective_lines),
        f"Cada paso constante reduce el peso de {normalized_topic} sobre tus decisiones.",
        rng.choice(closing_lines),
    ]


def _build_generation_prompt(topic: str) -> str:
    return (
        "Escribe un guion breve en espanol para un video vertical de 30 a 45 segundos (90 a 130 palabras). "
        f"Tema: {topic}. "
        "Tono: motivacion estoica, claro y directo. "
        "Formato: 7 frases cortas en un solo parrafo. "
        "No incluyas encabezados, no listas, no hashtags, no emojis."
    )


def _build_generation_prompt_retry(topic: str) -> str:
    return (
        f"Genera un guion final en espanol sobre {topic}. "
        "Debe tener 7 frases completas, 90 a 130 palabras, tono estoico y lenguaje claro. "
        "No incluyas instrucciones, solo el guion final."
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
    cleaned = cleaned.strip("\"'`")
    cleaned = re.sub(r"^(guion|script)\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^[\-\*\d\.\)\s]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        raise RuntimeError("El modelo HF devolvio salida vacia")
    return cleaned


def _validate_generated_script(text: str, topic: str) -> None:
    lowered = text.lower()
    topic_lower = topic.lower().strip()
    if len(text.split()) < 20:
        raise RuntimeError("Salida HF demasiado corta para guion operativo")
    forbidden = (
        "escribe un guion",
        "tema:",
        "tono:",
        "formato:",
        "solo el guion",
    )
    if any(token in lowered for token in forbidden):
        raise RuntimeError("Salida HF contiene metainstrucciones")

    if "**" in text or "#" in text:
        raise RuntimeError("Salida HF contiene formato no editorial")

    sentence_candidates = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    if len(sentence_candidates) < 6:
        raise RuntimeError("Salida HF con pocas frases completas")

    if topic_lower.startswith("soy ") and topic_lower in lowered:
        raise RuntimeError("Salida HF repite autodefinicion sensible del topic")

    topic_terms = [t for t in re.findall(r"[a-záéíóúñü]{4,}", topic.lower()) if t not in {"sobre"}]
    if topic_terms and not any(term in lowered for term in topic_terms):
        raise RuntimeError("Salida HF sin relacion visible con el topic")


def _normalize_topic_for_script(topic: str) -> str:
    raw = topic.strip().lower()
    replacements = {
        "soy un depresivo": "la sensacion de tristeza profunda",
        "soy depresivo": "la sensacion de tristeza profunda",
        "depresion": "la depresion",
        "ansiedad": "la ansiedad",
    }
    for key, value in replacements.items():
        if raw == key:
            return value
    if raw.startswith("soy "):
        return f"ese estado de {topic.strip()[4:]}"
    return topic.strip()


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
        filter_chain = (
            "drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':"
            "text='ClipTurbo':fontcolor=white:fontsize=64:x=(w-text_w)/2:y=160,"
            "drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':"
            "text='Motivacion Estoica':fontcolor=0x93c5fd:fontsize=40:x=(w-text_w)/2:y=250,"
            f"subtitles={subtitle_path}:"
            "force_style='FontName=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00303030,"
            "BorderStyle=3,Outline=1,Shadow=0,Alignment=2,MarginV=120'"
        )

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
