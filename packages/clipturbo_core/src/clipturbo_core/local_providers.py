from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
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
    def generate_text(self, prompt: str) -> GeneratedScript:
        topic = self._extract_topic(prompt)
        lines = [
            f"No esperes el momento perfecto para {topic}. Empieza con lo que tienes.",
            "La dificultad no es una excusa. Es la escuela del caracter.",
            "Domina tu reaccion y dominaras tu dia.",
            "Cada decision pequena construye tu identidad.",
            "La disciplina de hoy es la libertad de manana.",
            "No busques aplausos. Busca coherencia.",
            "Respira, enfocate y da el siguiente paso.",
        ]
        script_text = " ".join(lines)
        trace: ProviderTrace = {
            "provider_name": "rule_based_local",
            "provider_model": "stoic-es-v1",
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
