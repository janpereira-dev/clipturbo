from uuid import uuid4

import pytest
from pydantic import ValidationError

from clipturbo_core.domain import (
    ActorType,
    AuditLog,
    Locale,
    PipelineStage,
    Project,
    PromptTrace,
    RenderFormat,
    RenderJob,
    RenderJobStatus,
    ScriptVersion,
    VoiceGoal,
    VoiceProvider,
    default_voice_profiles,
    recommend_voice_stack,
)


def test_project_defaults_and_touch() -> None:
    project = Project(workspace_id=uuid4(), title="  Proyecto inicial  ")
    touched = project.touch()

    assert project.title == "Proyecto inicial"
    assert project.status.value == "draft"
    assert touched.updated_at >= project.updated_at


def test_script_version_rejects_short_script() -> None:
    with pytest.raises(ValidationError):
        ScriptVersion(
            project_id=uuid4(),
            hook_source="hook 1",
            script_text="demasiado corto",
            provider_name="openai",
            provider_model="gpt-4.1-mini",
        )


def test_prompt_trace_rejects_hash_with_spaces() -> None:
    with pytest.raises(ValidationError):
        PromptTrace(
            project_id=uuid4(),
            stage=PipelineStage.SCRIPT_GENERATION,
            provider_name="openai",
            provider_model="gpt-4.1-mini",
            prompt_hash="hash invalido",
        )


def test_render_job_retry_logic() -> None:
    job = RenderJob(
        project_id=uuid4(),
        script_version_id=uuid4(),
        voice_profile_id=uuid4(),
        render_format=RenderFormat.VERTICAL_9_16,
        status=RenderJobStatus.FAILED,
        attempts=1,
        max_attempts=3,
    )

    assert job.can_retry is True


def test_audit_log_minimum_shape() -> None:
    entry = AuditLog(
        project_id=uuid4(),
        actor_type=ActorType.AGENT,
        action="render.retry",
        target_type="render_job",
        target_id="job-123",
        metadata={"reason": "timeout"},
    )

    assert entry.actor_type == ActorType.AGENT
    assert entry.metadata["reason"] == "timeout"


def test_voice_recommendation_for_windows_quality_goal() -> None:
    recommendation = recommend_voice_stack(
        goal=VoiceGoal.BETTER_SPANISH_LOCAL,
        target_locale=Locale.ES_ES,
        windows_host=True,
    )

    assert recommendation.primary_provider == VoiceProvider.MELO_TTS
    assert recommendation.backup_provider == VoiceProvider.PIPER
    assert any("Docker" in note for note in recommendation.notes)


def test_default_voice_profiles_include_spanish_piper_voices() -> None:
    voices = default_voice_profiles()
    keys = {voice.voice_key for voice in voices if voice.provider_name == VoiceProvider.PIPER}

    assert "es_ES-davefx-medium" in keys
    assert "es_ES-sharvard-medium" in keys
    assert "es_MX-claude-high" in keys
    assert "es_AR-daniela-high" in keys
