from uuid import uuid4

import pytest
from pydantic import ValidationError

from clipturbo_core.domain import (
    ActorType,
    AuditActor,
    AuditLog,
    ComplianceReview,
    Locale,
    Project,
    ProjectStatus,
    PublishJob,
    PublishJobStatus,
    PublishPlatform,
    RenderJob,
    RenderJobStatus,
    ScriptSourceType,
    ScriptVersion,
    VersionNumber,
    VoiceGoal,
    VoiceProvider,
    default_voice_profiles,
    recommend_voice_stack,
)


def test_project_activate_and_archive_flow() -> None:
    project = Project(
        owner_id=uuid4(),
        workspace_id=uuid4(),
        name="Proyecto Clips",
    )
    active = project.activate()
    archived = active.archive()

    assert active.status == ProjectStatus.ACTIVE
    assert archived.status == ProjectStatus.ARCHIVED


def test_script_version_generates_content_hash() -> None:
    script = ScriptVersion(
        project_id=uuid4(),
        version_number=VersionNumber(value=1),
        title="Guion inicial",
        content="Este es un contenido suficientemente largo para una version valida.",
        source_type=ScriptSourceType.GENERATED,
        created_by="agent",
    )

    assert len(script.content_hash or "") == 64


def test_render_job_completion_requires_output() -> None:
    with pytest.raises(ValidationError):
        RenderJob(
            project_id=uuid4(),
            script_version_id=uuid4(),
            requested_by="user-1",
            status=RenderJobStatus.COMPLETED,
        )


def test_publish_job_retry_path() -> None:
    publish_job = PublishJob(
        project_id=uuid4(),
        render_job_id=uuid4(),
        target_platform=PublishPlatform.TIKTOK,
        requested_by="user-1",
        status=PublishJobStatus.FAILED,
    )
    failed = publish_job.mark_failed("upload_error", "network")
    scheduled = failed.schedule_retry()

    assert failed.can_retry is True
    assert scheduled.status.value == "retry_scheduled"


def test_audit_log_append_only_shape() -> None:
    event = AuditLog(
        project_id=uuid4(),
        actor=AuditActor(actor_type=ActorType.AGENT, actor_id="agent-1"),
        action="render.retry",
        entity_type="render_job",
        entity_id="job-123",
        metadata={"reason": "timeout"},
    )
    assert event.metadata["reason"] == "timeout"


def test_compliance_review_reject_requires_issues() -> None:
    review = ComplianceReview(project_id=uuid4(), target_type="render_job", target_id="job-1")
    with pytest.raises(ValueError):
        review.reject(issues=[], reviewer_type=ActorType.ADMIN)


def test_voice_recommendation_for_windows_quality_goal() -> None:
    recommendation = recommend_voice_stack(
        goal=VoiceGoal.BETTER_SPANISH_LOCAL,
        target_locale=Locale.ES_ES,
        windows_host=True,
    )

    assert recommendation.primary_provider == VoiceProvider.MELO_TTS
    assert recommendation.backup_provider == VoiceProvider.PIPER
    assert any("Docker" in note for note in recommendation.notes)


def test_voice_recommendation_for_colombia_uses_latam_piper_voice() -> None:
    recommendation = recommend_voice_stack(
        goal=VoiceGoal.SIMPLE_OFFLINE,
        target_locale=Locale.ES_CO,
        windows_host=False,
    )

    assert recommendation.suggested_voice_keys == ["es_MX-claude-high"]


def test_default_voice_profiles_include_spanish_piper_voices() -> None:
    voices = default_voice_profiles()
    keys = {voice.provider_voice_id for voice in voices if voice.provider == VoiceProvider.PIPER}

    assert "es_ES-davefx-medium" in keys
    assert "es_ES-sharvard-medium" in keys
    assert "es_MX-claude-high" in keys
    assert "es_AR-daniela-high" in keys
