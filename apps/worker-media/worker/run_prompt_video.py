from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
import re
import sys
from pathlib import Path
from uuid import uuid4

# Allow running this script directly from the repo without pip install.
REPO_ROOT = Path(__file__).resolve().parents[3]
CORE_SRC = REPO_ROOT / "packages" / "clipturbo_core" / "src"
if str(CORE_SRC) not in sys.path:
    sys.path.insert(0, str(CORE_SRC))

from clipturbo_core import (
    AuthoringService,
    Project,
    PromptToVideoPipelineService,
    PromptToVideoRequest,
    PublishPlatform,
    PublishService,
    RenderExecutionService,
    TraceabilityService,
    VoiceProfile,
    VoiceProvider,
)
from clipturbo_core.in_memory_repositories import InMemoryRepositoryBundle
from clipturbo_core.local_providers import (
    EdgeNeuralTTSProvider,
    FFmpegVideoRenderProvider,
    HuggingFaceSpanishLLMProvider,
    LocalDraftPublisherProvider,
    LocalStorageProvider,
    LocalSubtitleProvider,
    RuleBasedSpanishLLMProvider,
    WindowsSpeechTTSProvider,
    edge_tts_available,
    huggingface_generation_available,
)
from clipturbo_core.providers import LLMProvider, TTSProvider
from clipturbo_core.text_correction import (
    AutoSpanishCorrector,
    HuggingFaceSpanishCorrector,
    RuleBasedSpanishCorrector,
    SpanishTextCorrector,
    huggingface_correction_available,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera video vertical desde prompt base usando el core.")
    parser.add_argument("--topic", default="motivacion estoica", help="Tema principal del video.")
    parser.add_argument(
        "--script-engine",
        default="auto",
        choices=["auto", "hf", "rule"],
        help="auto: intenta generacion HF y cae a generacion local por reglas.",
    )
    parser.add_argument(
        "--script-model",
        default="Qwen/Qwen2.5-0.5B-Instruct",
        help="Modelo Hugging Face para generar guion desde el topic.",
    )
    parser.add_argument(
        "--tts-engine",
        default="auto",
        choices=["auto", "fluido", "loquendo"],
        help="auto: intenta voz neural y cae a loquendo; fluido: fuerza neural; loquendo: fuerza Windows Speech.",
    )
    parser.add_argument("--voice", default="", help="Voice ID especifico del motor seleccionado.")
    parser.add_argument(
        "--output-root",
        default="media/generated",
        help="Directorio base para artefactos generados.",
    )
    parser.add_argument(
        "--publish-drafts",
        action="store_true",
        help="Si se activa, genera borradores locales para YouTube, Instagram y TikTok.",
    )
    parser.add_argument(
        "--correction-engine",
        default="auto",
        choices=["auto", "guard", "hf"],
        help="guard: reglas locales; hf: modelo Hugging Face; auto: usa HF y cae a reglas.",
    )
    parser.add_argument(
        "--correction-model",
        default="jorgeortizfuentes/spanish-spellchecker-t5-base-wiki200000",
        help="Modelo Hugging Face para correccion ortografica/gramatical.",
    )
    parser.add_argument(
        "--record-lesson",
        dest="record_lesson",
        action="store_true",
        default=True,
        help="Guarda bitacora local en docs/lessons/pipeline-runs.md.",
    )
    parser.add_argument(
        "--no-record-lesson",
        dest="record_lesson",
        action="store_false",
        help="No escribir bitacora local en docs/lessons.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    repos = InMemoryRepositoryBundle()
    project = Project(owner_id=uuid4(), workspace_id=uuid4(), name=f"Demo {args.topic.title()}")
    repos.projects.save(project)

    tts_provider, voice_provider, voice_name = _build_tts_provider(
        engine=args.tts_engine,
        voice=args.voice,
        audio_dir=output_root / "audio",
    )
    correction_provider = _build_correction_provider(
        engine=args.correction_engine,
        model=args.correction_model,
    )
    llm_provider = _build_llm_provider(
        engine=args.script_engine,
        model=args.script_model,
        text_corrector=correction_provider,
    )
    voice_profile = VoiceProfile(
        name=voice_name,
        provider=voice_provider,
        provider_voice_id=voice_name,
    )
    repos.voice_profiles.save(voice_profile)

    authoring = AuthoringService(repos.projects, repos.script_versions, repos.audit_logs)
    render_service = RenderExecutionService(
        repos.projects, repos.script_versions, repos.voice_profiles, repos.render_jobs, repos.audit_logs
    )
    traceability = TraceabilityService(repos.prompt_traces, repos.audit_logs, repos.compliance_reviews)
    publish_service = PublishService(
        repos.render_jobs,
        repos.publish_jobs,
        repos.audit_logs,
        {
            PublishPlatform.YOUTUBE_SHORTS: LocalDraftPublisherProvider(output_root / "drafts"),
            PublishPlatform.INSTAGRAM_REELS: LocalDraftPublisherProvider(output_root / "drafts"),
            PublishPlatform.TIKTOK: LocalDraftPublisherProvider(output_root / "drafts"),
        },
    )

    subtitle_provider = LocalSubtitleProvider(output_root / "subtitles")
    pipeline = PromptToVideoPipelineService(
        authoring=authoring,
        renders=render_service,
        traceability=traceability,
        publish=publish_service,
        projects=repos.projects,
        voices=repos.voice_profiles,
        llm=llm_provider,
        tts=tts_provider,
        subtitles=subtitle_provider,
        video_renderer=FFmpegVideoRenderProvider(output_root / "videos", subtitle_provider),
        storage=LocalStorageProvider(output_root / "storage"),
    )

    publish_targets: list[PublishPlatform] = []
    if args.publish_drafts:
        publish_targets = [
            PublishPlatform.YOUTUBE_SHORTS,
            PublishPlatform.INSTAGRAM_REELS,
            PublishPlatform.TIKTOK,
        ]

    result = pipeline.run(
        PromptToVideoRequest(
            project_id=project.id,
            prompt_template="Crea un guion corto de motivacion estoica en espanol sobre {topic}.",
            prompt_variables={"topic": args.topic},
            voice_profile_id=voice_profile.id,
            requested_by="demo-worker",
            publish_targets=publish_targets,
            title=f"Motivacion Estoica: {args.topic.title()}",
        )
    )

    render_job = repos.render_jobs.get(result.render_job_id)
    script_version = repos.script_versions.get(result.script_version_id)
    llm_provider = pipeline.llm
    script_provider_name = script_version.provider_name if script_version else "n/a"
    script_engine_resolved = "n/a"
    script_model_resolved = "n/a"
    correction_engine_resolved = "n/a"
    correction_model_resolved = "n/a"
    if isinstance(llm_provider, RuleBasedSpanishLLMProvider):
        script_engine_resolved = "rule"
        script_model_resolved = "topic_guided_v1"
        correction_engine_resolved = llm_provider.last_correction_engine
        correction_model_resolved = llm_provider.last_correction_model
    elif isinstance(llm_provider, HuggingFaceSpanishLLMProvider):
        script_engine_resolved = "hf"
        script_model_resolved = args.script_model

    if script_version and script_version.provider_model:
        match = re.search(r"\|correction:([^:]+):(.+)$", script_version.provider_model)
        if match:
            correction_engine_resolved = match.group(1)
            correction_model_resolved = match.group(2)
    if script_provider_name == "hf_local_generation_fallback":
        script_engine_resolved = "rule_fallback"
        script_model_resolved = "topic_guided_v1"
    summary = {
        "script_engine": args.script_engine,
        "resolved_script_provider": script_provider_name,
        "resolved_script_engine": script_engine_resolved,
        "resolved_script_model": script_model_resolved,
        "tts_engine": args.tts_engine,
        "resolved_tts_provider": voice_provider.value,
        "voice_name": voice_name,
        "correction_engine": args.correction_engine,
        "resolved_correction_engine": correction_engine_resolved,
        "resolved_correction_model": correction_model_resolved,
        "project_id": str(result.project_id),
        "script_version_id": str(result.script_version_id),
        "render_job_id": str(result.render_job_id),
        "output_video": render_job.output_url if render_job else None,
        "publish_jobs": [str(job_id) for job_id in result.publish_job_ids],
        "publish_jobs_count": len(result.publish_job_ids),
        "compliance_review_id": str(result.compliance_review_id),
    }
    summary_path = output_root / "last_run.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=True, indent=2), encoding="utf-8")
    if args.record_lesson:
        _append_run_lesson(summary=summary, args=args)
    print(json.dumps(summary, ensure_ascii=True, indent=2))


def _build_tts_provider(
    engine: str,
    voice: str,
    audio_dir: Path,
) -> tuple[TTSProvider, VoiceProvider, str]:
    loquendo_default = "Microsoft Laura"
    fluido_default = "es-ES-AlvaroNeural"

    if engine == "loquendo":
        selected_voice = voice or loquendo_default
        return (
            WindowsSpeechTTSProvider(audio_dir, default_voice=selected_voice),
            VoiceProvider.WINDOWS_SPEECH,
            selected_voice,
        )

    if engine == "fluido":
        selected_voice = voice or fluido_default
        return (
            EdgeNeuralTTSProvider(audio_dir, default_voice=selected_voice),
            VoiceProvider.EDGE_TTS,
            selected_voice,
        )

    if edge_tts_available():
        selected_voice = voice or fluido_default
        return (
            EdgeNeuralTTSProvider(audio_dir, default_voice=selected_voice),
            VoiceProvider.EDGE_TTS,
            selected_voice,
        )
    selected_voice = loquendo_default
    return (
        WindowsSpeechTTSProvider(audio_dir, default_voice=selected_voice),
        VoiceProvider.WINDOWS_SPEECH,
        selected_voice,
    )


def _build_correction_provider(engine: str, model: str) -> SpanishTextCorrector:
    if engine == "guard":
        return RuleBasedSpanishCorrector()

    if engine == "hf":
        if not huggingface_correction_available():
            raise RuntimeError(
                "Modo hf requiere dependencias. Instala: "
                "python -m pip install transformers sentencepiece torch"
            )
        return HuggingFaceSpanishCorrector(model_id=model)

    if huggingface_correction_available():
        return AutoSpanishCorrector(model_id=model)
    return RuleBasedSpanishCorrector()


def _build_llm_provider(
    engine: str,
    model: str,
    text_corrector: SpanishTextCorrector,
) -> LLMProvider:
    if engine == "rule":
        return RuleBasedSpanishLLMProvider(text_corrector=text_corrector)

    if engine == "hf":
        if not huggingface_generation_available():
            raise RuntimeError(
                "Modo script hf requiere dependencias. Instala: "
                "python -m pip install transformers sentencepiece torch"
            )
        return HuggingFaceSpanishLLMProvider(
            model_id=model,
            text_corrector=text_corrector,
            allow_fallback=True,
        )

    if huggingface_generation_available():
        return HuggingFaceSpanishLLMProvider(
            model_id=model,
            text_corrector=text_corrector,
            allow_fallback=True,
        )
    return RuleBasedSpanishLLMProvider(text_corrector=text_corrector)


def _append_run_lesson(summary: dict[str, object], args: argparse.Namespace) -> None:
    lessons_path = REPO_ROOT / "docs" / "lessons" / "pipeline-runs.md"
    lessons_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).isoformat()
    lines = [
        f"## Run {timestamp}",
        f"- topic: {args.topic}",
        f"- script_provider: {summary['resolved_script_provider']}",
        f"- script_engine: {summary['resolved_script_engine']}",
        f"- script_model: {summary['resolved_script_model']}",
        f"- tts_engine: {summary['tts_engine']}",
        f"- voice_name: {summary['voice_name']}",
        f"- correction_engine: {summary['resolved_correction_engine']}",
        f"- correction_model: {summary['resolved_correction_model']}",
        f"- output_video: {summary['output_video']}",
        f"- publish_jobs: {summary['publish_jobs_count']}",
        f"- compliance_review_id: {summary['compliance_review_id']}",
        "- nota: registrar tambien en Engram para memoria transversal.",
        "",
    ]
    with lessons_path.open("a", encoding="utf-8") as file:
        file.write("\n".join(lines))


if __name__ == "__main__":
    main()
