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
    Locale,
    Project,
    PromptToVideoPipelineService,
    PromptToVideoRequest,
    PublishPlatform,
    PublishService,
    RenderExecutionService,
    TraceabilityService,
    VoiceProfile,
    VoiceProvider,
    list_registers_for_locale,
    load_model_routing_manifest,
    resolve_dialect_route,
)
from clipturbo_core.in_memory_repositories import InMemoryRepositoryBundle
from clipturbo_core.local_providers import (
    EdgeNeuralTTSProvider,
    FFmpegVideoRenderProvider,
    HuggingFaceSpanishLLMProvider,
    LocalDraftPublisherProvider,
    LocalStorageProvider,
    LocalSubtitleProvider,
    WindowsSpeechTTSProvider,
    edge_tts_available,
    huggingface_generation_available,
)
from clipturbo_core.providers import LLMProvider, TTSProvider
from clipturbo_core.text_correction import (
    AutoSpanishCorrector,
    HuggingFaceSpanishCorrector,
    NoOpSpanishCorrector,
    SpanishTextCorrector,
    huggingface_correction_available,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera video vertical desde prompt base usando el core.")
    parser.add_argument("--topic", default="motivacion estoica", help="Tema principal del video.")
    parser.add_argument(
        "--locale",
        default="es-ES",
        help="Locale de escritura/voz (es-ES, es-VE, es-CO, es-EC, es-PR).",
    )
    parser.add_argument(
        "--registro",
        default="neutral",
        help="Registro editorial (neutral, cercano, profesional).",
    )
    parser.add_argument(
        "--routing-manifest",
        default="manifests/model-routing.json",
        help="Ruta al manifiesto JSON de routing por locale/registro.",
    )
    parser.add_argument(
        "--script-engine",
        default="auto",
        choices=["auto", "hf"],
        help="auto: generacion HF con reintentos y recovery; hf: fuerza HF.",
    )
    parser.add_argument(
        "--script-model",
        default="",
        help="Modelo HF para guion. Si queda vacio, se resuelve por routing locale/registro.",
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
        help="guard: normalizacion basica sin IA; hf: modelo Hugging Face; auto: usa HF y cae a normalizacion.",
    )
    parser.add_argument(
        "--correction-model",
        default="",
        help="Modelo HF para correccion. Si queda vacio, se resuelve por routing locale/registro.",
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

    locale = _parse_locale(args.locale)
    routing_manifest = load_model_routing_manifest(REPO_ROOT / args.routing_manifest)
    route = resolve_dialect_route(routing_manifest, locale=locale, register=args.registro)
    available_registers = list_registers_for_locale(routing_manifest, locale)

    resolved_script_model = args.script_model.strip() or route.script_model
    resolved_script_model_fallbacks = route.script_model_fallbacks
    resolved_correction_model = args.correction_model.strip() or route.correction_model
    resolved_correction_model_fallbacks = route.correction_model_fallbacks
    resolved_tts_engine = args.tts_engine if args.tts_engine != "auto" else route.tts_engine
    resolved_voice = args.voice.strip()
    if not resolved_voice:
        if resolved_tts_engine == "loquendo":
            resolved_voice = route.loquendo_voice
        elif resolved_tts_engine == "fluido":
            resolved_voice = route.fluido_voice
        else:
            # En auto dejamos vacio para que el proveedor real (edge/windows) decida el default correcto.
            resolved_voice = ""

    repos = InMemoryRepositoryBundle()
    project = Project(
        owner_id=uuid4(),
        workspace_id=uuid4(),
        name=f"Demo {args.topic.title()}",
        default_language=locale,
    )
    repos.projects.save(project)

    tts_provider, voice_provider, voice_name = _build_tts_provider(
        engine=resolved_tts_engine,
        voice=resolved_voice,
        audio_dir=output_root / "audio",
        fluido_default=route.fluido_voice,
        loquendo_default=route.loquendo_voice,
    )
    correction_provider = _build_correction_provider(
        engine=args.correction_engine,
        model=resolved_correction_model,
        fallback_models=resolved_correction_model_fallbacks,
    )
    llm_provider = _build_llm_provider(
        engine=args.script_engine,
        model=resolved_script_model,
        fallback_models=resolved_script_model_fallbacks,
        text_corrector=correction_provider,
    )
    voice_profile = VoiceProfile(
        name=voice_name,
        provider=voice_provider,
        provider_voice_id=voice_name,
        language=locale,
        locale=locale,
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
            prompt_template=(
                "Crea un guion corto en espanol ({locale}) "
                "con registro {registro} sobre {topic}."
            ),
            prompt_variables={
                "topic": args.topic,
                "locale": locale.value,
                "registro": route.register_id,
            },
            voice_profile_id=voice_profile.id,
            requested_by="demo-worker",
            publish_targets=publish_targets,
            title=f"{args.topic.title()} ({locale.value}, {route.register_id})",
        )
    )

    render_job = repos.render_jobs.get(result.render_job_id)
    script_version = repos.script_versions.get(result.script_version_id)
    llm_provider = pipeline.llm
    script_provider_name = (script_version.provider_name if script_version else "n/a") or "n/a"
    script_engine_resolved = "n/a"
    script_model_resolved = "n/a"
    correction_engine_resolved = "n/a"
    correction_model_resolved = "n/a"
    active_script_model = (
        llm_provider.active_model_id if isinstance(llm_provider, HuggingFaceSpanishLLMProvider) else resolved_script_model
    )
    if isinstance(llm_provider, HuggingFaceSpanishLLMProvider):
        script_engine_resolved = "hf"
        script_model_resolved = active_script_model

    if script_version and script_version.provider_model:
        parts = script_version.provider_model.split("|", maxsplit=1)
        if parts and parts[0].strip():
            script_model_resolved = parts[0].strip()
        match = re.search(r"\|(?:correction|corr):([^:]+):(.+)$", script_version.provider_model)
        if match:
            correction_engine_resolved = match.group(1)
            correction_model_resolved = match.group(2)
    if "recovery" in script_provider_name:
        script_engine_resolved = "hf_recovery"
        script_model_resolved = active_script_model
    elif "degraded" in script_provider_name:
        script_engine_resolved = "hf_degraded"
        script_model_resolved = active_script_model
    if correction_engine_resolved == "n/a":
        correction_engine_resolved = _resolve_correction_engine_label(
            requested_engine=args.correction_engine,
            correction_provider=correction_provider,
        )
        correction_model_resolved = resolved_correction_model
    summary = {
        "locale": locale.value,
        "requested_registro": args.registro.strip().lower(),
        "registro": route.register_id,
        "routing_manifest": args.routing_manifest,
        "routing_registers_locale": available_registers,
        "routing_script_model": resolved_script_model,
        "routing_script_fallbacks": resolved_script_model_fallbacks,
        "routing_correction_model": resolved_correction_model,
        "routing_correction_fallbacks": resolved_correction_model_fallbacks,
        "script_engine": args.script_engine,
        "resolved_script_provider": script_provider_name,
        "resolved_script_engine": script_engine_resolved,
        "resolved_script_model": script_model_resolved,
        "tts_engine": resolved_tts_engine,
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


def _parse_locale(raw_locale: str) -> Locale:
    value = raw_locale.strip()
    try:
        return Locale(value)
    except ValueError as exc:
        supported = ", ".join(locale.value for locale in Locale)
        raise RuntimeError(f"Locale no soportado: {raw_locale}. Valores validos: {supported}") from exc


def _build_tts_provider(
    engine: str,
    voice: str,
    audio_dir: Path,
    fluido_default: str,
    loquendo_default: str,
) -> tuple[TTSProvider, VoiceProvider, str]:
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
    selected_voice = voice or loquendo_default
    return (
        WindowsSpeechTTSProvider(audio_dir, default_voice=selected_voice),
        VoiceProvider.WINDOWS_SPEECH,
        selected_voice,
    )


def _build_correction_provider(
    engine: str,
    model: str,
    fallback_models: list[str],
) -> SpanishTextCorrector:
    if engine == "guard":
        return NoOpSpanishCorrector()

    if engine == "hf":
        if not huggingface_correction_available():
            raise RuntimeError(
                "Modo hf requiere dependencias. Instala: "
                "python -m pip install transformers sentencepiece torch"
            )
        return HuggingFaceSpanishCorrector(
            model_id=model,
            fallback_model_ids=fallback_models,
        )

    if huggingface_correction_available():
        return AutoSpanishCorrector(
            model_id=model,
            fallback_model_ids=fallback_models,
        )
    return NoOpSpanishCorrector()


def _build_llm_provider(
    engine: str,
    model: str,
    fallback_models: list[str],
    text_corrector: SpanishTextCorrector,
) -> LLMProvider:
    if engine == "hf":
        if not huggingface_generation_available():
            raise RuntimeError(
                "Modo script hf requiere dependencias. Instala: "
                "python -m pip install transformers sentencepiece torch"
            )
        return HuggingFaceSpanishLLMProvider(
            model_id=model,
            fallback_model_ids=fallback_models,
            text_corrector=text_corrector,
            allow_fallback=True,
        )

    if huggingface_generation_available():
        return HuggingFaceSpanishLLMProvider(
            model_id=model,
            fallback_model_ids=fallback_models,
            text_corrector=text_corrector,
            allow_fallback=True,
        )
    raise RuntimeError(
        "No hay runtime de generacion disponible. Instala: "
        "python -m pip install transformers sentencepiece torch"
    )


def _append_run_lesson(summary: dict[str, object], args: argparse.Namespace) -> None:
    lessons_path = REPO_ROOT / "docs" / "lessons" / "pipeline-runs.md"
    lessons_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).isoformat()
    lines = [
        f"## Run {timestamp}",
        f"- topic: {args.topic}",
        f"- locale: {summary['locale']}",
        f"- registro: {summary['registro']}",
        f"- routing_script_model: {summary['routing_script_model']}",
        f"- routing_script_fallbacks: {summary['routing_script_fallbacks']}",
        f"- routing_correction_model: {summary['routing_correction_model']}",
        f"- routing_correction_fallbacks: {summary['routing_correction_fallbacks']}",
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


def _resolve_correction_engine_label(requested_engine: str, correction_provider: SpanishTextCorrector) -> str:
    normalized = requested_engine.strip().lower()
    if isinstance(correction_provider, HuggingFaceSpanishCorrector):
        return "hf"
    if isinstance(correction_provider, NoOpSpanishCorrector):
        return "guard"
    if isinstance(correction_provider, AutoSpanishCorrector):
        return "auto"
    return normalized or "n/a"


if __name__ == "__main__":
    main()
