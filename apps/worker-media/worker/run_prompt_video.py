from __future__ import annotations

import argparse
import json
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
    FFmpegVideoRenderProvider,
    LocalDraftPublisherProvider,
    LocalStorageProvider,
    LocalSubtitleProvider,
    RuleBasedSpanishLLMProvider,
    WindowsSpeechTTSProvider,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera video vertical desde prompt base usando el core.")
    parser.add_argument("--topic", default="motivacion estoica", help="Tema principal del video.")
    parser.add_argument("--voice", default="Microsoft Laura", help="Voz TTS instalada en Windows.")
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    repos = InMemoryRepositoryBundle()
    project = Project(owner_id=uuid4(), workspace_id=uuid4(), name=f"Demo {args.topic.title()}")
    repos.projects.save(project)

    voice_profile = VoiceProfile(
        name=f"Windows {args.voice}",
        provider=VoiceProvider.WINDOWS_SPEECH,
        provider_voice_id=args.voice,
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
        llm=RuleBasedSpanishLLMProvider(),
        tts=WindowsSpeechTTSProvider(output_root / "audio", default_voice=args.voice),
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
    summary = {
        "project_id": str(result.project_id),
        "script_version_id": str(result.script_version_id),
        "render_job_id": str(result.render_job_id),
        "output_video": render_job.output_url if render_job else None,
        "publish_jobs": [str(job_id) for job_id in result.publish_job_ids],
        "compliance_review_id": str(result.compliance_review_id),
    }
    summary_path = output_root / "last_run.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=True, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
