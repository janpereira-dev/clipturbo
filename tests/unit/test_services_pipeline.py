from uuid import uuid4

import pytest

from clipturbo_core.domain import (
    ComplianceStatus,
    Project,
    PublishPlatform,
    RenderFormat,
    RenderJob,
    RenderJobStatus,
    VoiceProfile,
    VoiceProvider,
)
from clipturbo_core.in_memory_repositories import InMemoryRepositoryBundle
from clipturbo_core.providers import (
    GeneratedScript,
    GeneratedSubtitles,
    ProviderTrace,
    PublishResult,
    RenderedVideo,
    SynthesizedAudio,
)
from clipturbo_core.services import (
    AuthoringService,
    DomainServiceError,
    PromptToVideoPipelineService,
    PromptToVideoRequest,
    PublishService,
    RenderExecutionService,
    TraceabilityService,
)


class FakeLLMProvider:
    def generate_text(self, prompt: str) -> GeneratedScript:
        trace: ProviderTrace = {
            "provider_name": "fake-llm",
            "provider_model": "fake-es-1",
            "request_id": "req-llm-1",
        }
        return {"script_text": f"{prompt} con cierre y llamada a la accion.", "trace": trace}


class FakeTTSProvider:
    def synthesize(self, script: str, voice_id: str) -> SynthesizedAudio:
        trace: ProviderTrace = {
            "provider_name": "fake-tts",
            "provider_model": "fake-voice",
            "request_id": "req-tts-1",
        }
        return {"asset_path": f"audio/{voice_id}.wav", "duration_ms": 45000, "trace": trace}


class RecordingTTSProvider:
    def __init__(self) -> None:
        self.last_voice_id: str | None = None

    def synthesize(self, script: str, voice_id: str) -> SynthesizedAudio:
        self.last_voice_id = voice_id
        trace: ProviderTrace = {
            "provider_name": "fake-tts",
            "provider_model": "fake-voice",
            "request_id": "req-tts-recording",
        }
        return {"asset_path": "audio/default.wav", "duration_ms": 30000, "trace": trace}


class FailingTTSProvider:
    def synthesize(self, script: str, voice_id: str) -> SynthesizedAudio:
        raise RuntimeError("tts backend unavailable")


class FakeSubtitleProvider:
    def generate(self, script: str, audio_path: str) -> GeneratedSubtitles:
        trace: ProviderTrace = {
            "provider_name": "fake-subs",
            "provider_model": "fake-whisper",
            "request_id": "req-subs-1",
        }
        return {
            "format": "srt",
            "segments": [{"start_ms": 0, "end_ms": 1000, "text": "Hola mundo"}],
            "trace": trace,
        }


class FakeVideoRenderProvider:
    def compose(
        self,
        script: str,
        audio_path: str,
        subtitles: GeneratedSubtitles,
        render_format: RenderFormat,
    ) -> RenderedVideo:
        trace: ProviderTrace = {
            "provider_name": "fake-render",
            "provider_model": "ffmpeg-template",
            "request_id": "req-render-1",
        }
        return {"asset_path": "renders/output.mp4", "duration_ms": 45000, "trace": trace}


class FakeStorageProvider:
    def put(self, key: str, source_path: str) -> str:
        return f"storage://{key}"


class FakePublisherProvider:
    def publish_draft(
        self, platform: PublishPlatform, asset_path: str, metadata: dict[str, str]
    ) -> PublishResult:
        trace: ProviderTrace = {
            "provider_name": f"fake-{platform.value}",
            "provider_model": "v1",
            "request_id": f"req-{platform.value}",
        }
        return {
            "external_post_id": f"{platform.value}-123",
            "external_url": f"https://example.com/{platform.value}/123",
            "trace": trace,
        }


def test_prompt_to_video_pipeline_end_to_end() -> None:
    repos = InMemoryRepositoryBundle()
    project = Project(owner_id=uuid4(), workspace_id=uuid4(), name="Proyecto pipeline")
    repos.projects.save(project)
    voice = VoiceProfile(
        name="es-ES piper",
        provider=VoiceProvider.PIPER,
        provider_voice_id="es_ES-davefx-medium",
    )
    repos.voice_profiles.save(voice)

    authoring = AuthoringService(repos.projects, repos.script_versions, repos.audit_logs)
    renders = RenderExecutionService(
        repos.projects, repos.script_versions, repos.voice_profiles, repos.render_jobs, repos.audit_logs
    )
    traceability = TraceabilityService(repos.prompt_traces, repos.audit_logs, repos.compliance_reviews)
    publish = PublishService(
        repos.render_jobs,
        repos.publish_jobs,
        repos.audit_logs,
        {
            PublishPlatform.YOUTUBE_SHORTS: FakePublisherProvider(),
            PublishPlatform.INSTAGRAM_REELS: FakePublisherProvider(),
            PublishPlatform.TIKTOK: FakePublisherProvider(),
        },
    )

    pipeline = PromptToVideoPipelineService(
        authoring=authoring,
        renders=renders,
        traceability=traceability,
        publish=publish,
        projects=repos.projects,
        voices=repos.voice_profiles,
        llm=FakeLLMProvider(),
        tts=FakeTTSProvider(),
        subtitles=FakeSubtitleProvider(),
        video_renderer=FakeVideoRenderProvider(),
        storage=FakeStorageProvider(),
    )

    result = pipeline.run(
        PromptToVideoRequest(
            project_id=project.id,
            prompt_template="Crea un short sobre {tema}",
            prompt_variables={"tema": "productividad"},
            voice_profile_id=voice.id,
            requested_by="user-1",
            publish_targets=[
                PublishPlatform.YOUTUBE_SHORTS,
                PublishPlatform.INSTAGRAM_REELS,
                PublishPlatform.TIKTOK,
            ],
            title="Productividad en 45 segundos",
        )
    )

    assert result.project_id == project.id
    assert len(result.publish_job_ids) == 3

    render_job = repos.render_jobs.get(result.render_job_id)
    assert render_job is not None
    assert render_job.status.value == "completed"
    assert render_job.output_url is not None

    compliance = repos.compliance_reviews.get(result.compliance_review_id)
    assert compliance is not None
    assert compliance.status == ComplianceStatus.PENDING


def test_pipeline_without_voice_profile_uses_provider_default_voice() -> None:
    repos = InMemoryRepositoryBundle()
    project = Project(owner_id=uuid4(), workspace_id=uuid4(), name="Proyecto sin voz")
    repos.projects.save(project)

    authoring = AuthoringService(repos.projects, repos.script_versions, repos.audit_logs)
    renders = RenderExecutionService(
        repos.projects, repos.script_versions, repos.voice_profiles, repos.render_jobs, repos.audit_logs
    )
    traceability = TraceabilityService(repos.prompt_traces, repos.audit_logs, repos.compliance_reviews)
    publish = PublishService(
        repos.render_jobs,
        repos.publish_jobs,
        repos.audit_logs,
        {},
    )
    tts = RecordingTTSProvider()
    pipeline = PromptToVideoPipelineService(
        authoring=authoring,
        renders=renders,
        traceability=traceability,
        publish=publish,
        projects=repos.projects,
        voices=repos.voice_profiles,
        llm=FakeLLMProvider(),
        tts=tts,
        subtitles=FakeSubtitleProvider(),
        video_renderer=FakeVideoRenderProvider(),
        storage=FakeStorageProvider(),
    )

    pipeline.run(
        PromptToVideoRequest(
            project_id=project.id,
            prompt_template="Tema {tema}",
            prompt_variables={"tema": "disciplina"},
            requested_by="user-1",
            title="Video sin voice profile",
        )
    )

    assert tts.last_voice_id == ""


def test_pipeline_marks_render_failed_when_provider_throws() -> None:
    repos = InMemoryRepositoryBundle()
    project = Project(owner_id=uuid4(), workspace_id=uuid4(), name="Proyecto fallo render")
    repos.projects.save(project)

    authoring = AuthoringService(repos.projects, repos.script_versions, repos.audit_logs)
    renders = RenderExecutionService(
        repos.projects, repos.script_versions, repos.voice_profiles, repos.render_jobs, repos.audit_logs
    )
    traceability = TraceabilityService(repos.prompt_traces, repos.audit_logs, repos.compliance_reviews)
    publish = PublishService(
        repos.render_jobs,
        repos.publish_jobs,
        repos.audit_logs,
        {},
    )
    pipeline = PromptToVideoPipelineService(
        authoring=authoring,
        renders=renders,
        traceability=traceability,
        publish=publish,
        projects=repos.projects,
        voices=repos.voice_profiles,
        llm=FakeLLMProvider(),
        tts=FailingTTSProvider(),
        subtitles=FakeSubtitleProvider(),
        video_renderer=FakeVideoRenderProvider(),
        storage=FakeStorageProvider(),
    )

    with pytest.raises(DomainServiceError, match="pipeline render failed"):
        pipeline.run(
            PromptToVideoRequest(
                project_id=project.id,
                prompt_template="Tema {tema}",
                prompt_variables={"tema": "disciplina"},
                requested_by="user-1",
                title="Video con fallo",
            )
        )

    render_jobs = repos.render_jobs.list_by_project(project.id)
    assert len(render_jobs) == 1
    assert render_jobs[0].status.value == "failed"
    assert render_jobs[0].error_code == "pipeline_render_error"


def test_publish_queue_rejects_cross_project_render() -> None:
    repos = InMemoryRepositoryBundle()
    project_a = Project(owner_id=uuid4(), workspace_id=uuid4(), name="Proyecto A")
    project_b = Project(owner_id=uuid4(), workspace_id=uuid4(), name="Proyecto B")
    repos.projects.save(project_a)
    repos.projects.save(project_b)

    render_job = RenderJob(
        project_id=project_a.id,
        script_version_id=uuid4(),
        requested_by="user-a",
        status=RenderJobStatus.COMPLETED,
        output_url="storage://renders/a.mp4",
    )
    repos.render_jobs.save(render_job)

    publish = PublishService(
        repos.render_jobs,
        repos.publish_jobs,
        repos.audit_logs,
        {PublishPlatform.YOUTUBE_SHORTS: FakePublisherProvider()},
    )

    with pytest.raises(DomainServiceError, match="does not belong"):
        publish.queue_publish_job(
            project_id=project_b.id,
            render_job_id=render_job.id,
            target_platform=PublishPlatform.YOUTUBE_SHORTS,
            requested_by="user-b",
            metadata={"draft": True},
        )
