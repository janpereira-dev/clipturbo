from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class Locale(str, Enum):
    ES_ES = "es-ES"
    ES_MX = "es-MX"
    ES_AR = "es-AR"
    ES_VE = "es-VE"
    ES_NEUTRAL = "es-neutral"


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ScriptSourceType(str, Enum):
    MANUAL = "manual"
    GENERATED = "generated"
    IMPORTED = "imported"
    TRANSLATED = "translated"
    REFINED = "refined"


class PipelineStage(str, Enum):
    SCRIPT_GENERATION = "script_generation"
    VOICE_SELECTION = "voice_selection"
    AUDIO_SYNTHESIS = "audio_synthesis"
    SUBTITLE_GENERATION = "subtitle_generation"
    ASSET_SELECTION = "asset_selection"
    VIDEO_RENDER = "video_render"
    REVIEW = "review"
    PUBLISH_DRAFT = "publish_draft"


class RenderFormat(str, Enum):
    VERTICAL_9_16 = "9:16"
    LANDSCAPE_16_9 = "16:9"


class RenderJobStatus(str, Enum):
    QUEUED = "queued"
    PREPARING = "preparing"
    RENDERING = "rendering"
    POST_PROCESSING = "post_processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    RETRY_SCHEDULED = "retry_scheduled"


class PublishPlatform(str, Enum):
    YOUTUBE_SHORTS = "youtube_shorts"
    INSTAGRAM_REELS = "instagram_reels"
    TIKTOK = "tiktok"


class PublishJobStatus(str, Enum):
    QUEUED = "queued"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    RETRY_SCHEDULED = "retry_scheduled"


class ActorType(str, Enum):
    USER = "user"
    AGENT = "agent"
    WORKER = "worker"
    SYSTEM = "system"
    ADMIN = "admin"


class VoiceProvider(str, Enum):
    PIPER = "piper"
    MELO_TTS = "melo_tts"
    XTTS_V2 = "xtts_v2"
    WINDOWS_SPEECH = "windows_speech"
    AZURE_SPEECH = "azure_speech"
    ELEVENLABS = "elevenlabs"
    EDGE_TTS = "edge_tts"
    OPENAI_TTS = "openai_tts"


class VoiceGoal(str, Enum):
    SIMPLE_OFFLINE = "simple_offline"
    BETTER_SPANISH_LOCAL = "better_spanish_local"
    HIGH_QUALITY_CLONING = "high_quality_cloning"


class ComplianceStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


class VersionNumber(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    value: int = Field(ge=1)

    def next(self) -> VersionNumber:
        return VersionNumber(value=self.value + 1)


class PromptUsage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class VoiceSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    pitch: float = Field(default=0.0, ge=-20.0, le=20.0)
    stability: float = Field(default=0.5, ge=0.0, le=1.0)
    similarity: float = Field(default=0.5, ge=0.0, le=1.0)
    sample_rate_hz: int | None = Field(default=None, ge=8000, le=96000)
    provider_config: dict[str, Any] = Field(default_factory=dict)


class AuditActor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    actor_type: ActorType
    actor_id: str | None = Field(default=None, max_length=120)


class Project(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    workspace_id: UUID
    name: str = Field(min_length=3, max_length=140)
    description: str | None = None
    default_language: Locale = Locale.ES_ES
    status: ProjectStatus = ProjectStatus.DRAFT
    default_voice_profile_id: UUID | None = None
    current_script_version_id: UUID | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name cannot be empty")
        return normalized

    def touch(self) -> Project:
        return self.model_copy(update={"updated_at": utc_now()})

    def activate(self) -> Project:
        return self.model_copy(update={"status": ProjectStatus.ACTIVE, "updated_at": utc_now()})

    def archive(self) -> Project:
        return self.model_copy(update={"status": ProjectStatus.ARCHIVED, "updated_at": utc_now()})

    def with_current_script(self, script_version_id: UUID) -> Project:
        status = self.status
        if status == ProjectStatus.DRAFT:
            status = ProjectStatus.ACTIVE
        return self.model_copy(
            update={
                "current_script_version_id": script_version_id,
                "status": status,
                "updated_at": utc_now(),
            }
        )


class ScriptVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    version_number: VersionNumber
    title: str = Field(min_length=3, max_length=180)
    content: str = Field(min_length=20)
    language: Locale = Locale.ES_ES
    source_type: ScriptSourceType = ScriptSourceType.GENERATED
    created_by: str = Field(min_length=2, max_length=120)
    parent_version_id: UUID | None = None
    change_summary: str | None = Field(default=None, max_length=300)
    content_hash: str | None = Field(default=None, min_length=64, max_length=64)
    provider_name: str | None = Field(default=None, min_length=2, max_length=80)
    provider_model: str | None = Field(default=None, min_length=2, max_length=120)
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("title")
    @classmethod
    def _clean_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("title cannot be empty")
        return normalized

    @field_validator("content")
    @classmethod
    def _clean_content(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 20:
            raise ValueError("content must have at least 20 chars")
        return normalized

    @model_validator(mode="after")
    def _ensure_hash(self) -> ScriptVersion:
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.content.encode("utf-8")).hexdigest()
        return self


class VoiceProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID | None = None
    name: str = Field(min_length=2, max_length=120)
    provider: VoiceProvider
    provider_voice_id: str = Field(min_length=2, max_length=120)
    language: Locale = Locale.ES_ES
    locale: Locale = Locale.ES_ES
    tone_tags: list[str] = Field(default_factory=list)
    settings: VoiceSettings = Field(default_factory=VoiceSettings)
    is_active: bool = True
    is_system: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _normalize_tags(self) -> VoiceProfile:
        self.tone_tags = sorted({tag.strip().lower() for tag in self.tone_tags if tag.strip()})
        return self

    def deactivate(self) -> VoiceProfile:
        return self.model_copy(update={"is_active": False, "updated_at": utc_now()})


class PromptTrace(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    script_version_id: UUID | None = None
    render_job_id: UUID | None = None
    purpose: str = Field(min_length=2, max_length=120)
    provider: str = Field(min_length=2, max_length=80)
    model: str = Field(min_length=2, max_length=120)
    system_prompt: str = Field(min_length=1)
    user_prompt: str = Field(min_length=1)
    input_variables: dict[str, Any] = Field(default_factory=dict)
    output_text: str = Field(min_length=1)
    prompt_template_version: str = Field(min_length=1, max_length=40)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    max_tokens: int | None = Field(default=None, ge=1)
    usage: PromptUsage | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    status: str = Field(default="success", min_length=2, max_length=40)
    response_hash: str = Field(min_length=64, max_length=64)
    created_at: datetime = Field(default_factory=utc_now)


class AuditLog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    actor: AuditActor
    action: str = Field(min_length=2, max_length=120)
    entity_type: str = Field(min_length=2, max_length=80)
    entity_id: str | None = Field(default=None, max_length=120)
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    ip_address: str | None = Field(default=None, max_length=80)
    user_agent: str | None = Field(default=None, max_length=300)
    created_at: datetime = Field(default_factory=utc_now)


class RenderJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    script_version_id: UUID
    voice_profile_id: UUID | None = None
    voice_snapshot: dict[str, Any] = Field(default_factory=dict)
    status: RenderJobStatus = RenderJobStatus.QUEUED
    priority: int = Field(default=5, ge=1, le=10)
    requested_by: str = Field(min_length=2, max_length=120)
    engine: str = Field(default="ffmpeg", min_length=2, max_length=80)
    input_config: dict[str, Any] = Field(default_factory=dict)
    output_format: RenderFormat = RenderFormat.VERTICAL_9_16
    output_url: str | None = None
    artifact_id: str | None = None
    error_code: str | None = Field(default=None, max_length=80)
    error_message: str | None = Field(default=None, max_length=500)
    attempt_count: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=3, ge=1)
    queued_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @model_validator(mode="after")
    def _validate_invariants(self) -> RenderJob:
        if self.attempt_count > self.max_attempts:
            raise ValueError("attempt_count cannot exceed max_attempts")
        if self.status == RenderJobStatus.COMPLETED and not (self.output_url or self.artifact_id):
            raise ValueError("completed render requires output_url or artifact_id")
        if self.finished_at and self.started_at and self.finished_at < self.started_at:
            raise ValueError("finished_at cannot be before started_at")
        return self

    @property
    def can_retry(self) -> bool:
        return self.status in {RenderJobStatus.FAILED, RenderJobStatus.RETRY_SCHEDULED} and (
            self.attempt_count < self.max_attempts
        )

    def mark_preparing(self) -> RenderJob:
        return self.model_copy(update={"status": RenderJobStatus.PREPARING, "started_at": utc_now()})

    def mark_rendering(self) -> RenderJob:
        return self.model_copy(update={"status": RenderJobStatus.RENDERING})

    def mark_post_processing(self) -> RenderJob:
        return self.model_copy(update={"status": RenderJobStatus.POST_PROCESSING})

    def mark_completed(self, output_url: str | None, artifact_id: str | None = None) -> RenderJob:
        return self.model_copy(
            update={
                "status": RenderJobStatus.COMPLETED,
                "output_url": output_url,
                "artifact_id": artifact_id,
                "finished_at": utc_now(),
                "error_code": None,
                "error_message": None,
            }
        )

    def mark_failed(self, error_code: str, error_message: str) -> RenderJob:
        return self.model_copy(
            update={
                "status": RenderJobStatus.FAILED,
                "error_code": error_code,
                "error_message": error_message,
                "finished_at": utc_now(),
            }
        )

    def schedule_retry(self) -> RenderJob:
        if not self.can_retry:
            raise ValueError("job cannot be retried")
        return self.model_copy(
            update={
                "status": RenderJobStatus.RETRY_SCHEDULED,
                "attempt_count": self.attempt_count + 1,
                "error_code": None,
                "error_message": None,
                "finished_at": None,
                "started_at": None,
            }
        )

    def mark_canceled(self) -> RenderJob:
        return self.model_copy(update={"status": RenderJobStatus.CANCELED, "finished_at": utc_now()})


class PublishJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    render_job_id: UUID
    target_platform: PublishPlatform
    status: PublishJobStatus = PublishJobStatus.QUEUED
    requested_by: str = Field(min_length=2, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)
    external_post_id: str | None = Field(default=None, max_length=200)
    external_url: str | None = Field(default=None, max_length=300)
    error_code: str | None = Field(default=None, max_length=80)
    error_message: str | None = Field(default=None, max_length=500)
    attempt_count: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=3, ge=1)
    queued_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @property
    def can_retry(self) -> bool:
        return self.status in {PublishJobStatus.FAILED, PublishJobStatus.RETRY_SCHEDULED} and (
            self.attempt_count < self.max_attempts
        )

    def mark_uploading(self) -> PublishJob:
        return self.model_copy(update={"status": PublishJobStatus.UPLOADING, "started_at": utc_now()})

    def mark_completed(self, external_post_id: str, external_url: str | None = None) -> PublishJob:
        return self.model_copy(
            update={
                "status": PublishJobStatus.COMPLETED,
                "external_post_id": external_post_id,
                "external_url": external_url,
                "finished_at": utc_now(),
                "error_code": None,
                "error_message": None,
            }
        )

    def mark_failed(self, error_code: str, error_message: str) -> PublishJob:
        return self.model_copy(
            update={
                "status": PublishJobStatus.FAILED,
                "error_code": error_code,
                "error_message": error_message,
                "finished_at": utc_now(),
            }
        )

    def schedule_retry(self) -> PublishJob:
        if not self.can_retry:
            raise ValueError("publish job cannot be retried")
        return self.model_copy(
            update={
                "status": PublishJobStatus.RETRY_SCHEDULED,
                "attempt_count": self.attempt_count + 1,
                "error_code": None,
                "error_message": None,
                "started_at": None,
                "finished_at": None,
            }
        )

    def mark_canceled(self) -> PublishJob:
        return self.model_copy(update={"status": PublishJobStatus.CANCELED, "finished_at": utc_now()})


class ComplianceReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    target_type: str = Field(min_length=2, max_length=80)
    target_id: str = Field(min_length=2, max_length=120)
    status: ComplianceStatus = ComplianceStatus.PENDING
    reviewer_type: ActorType = ActorType.SYSTEM
    reviewer_id: str | None = Field(default=None, max_length=120)
    requires_human_review: bool = True
    issues: list[str] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=utc_now)
    decided_at: datetime | None = None

    def approve(self, reviewer_type: ActorType, reviewer_id: str | None = None) -> ComplianceReview:
        return self.model_copy(
            update={
                "status": ComplianceStatus.APPROVED,
                "reviewer_type": reviewer_type,
                "reviewer_id": reviewer_id,
                "decided_at": utc_now(),
            }
        )

    def reject(
        self,
        issues: list[str],
        reviewer_type: ActorType,
        reviewer_id: str | None = None,
        notes: str | None = None,
    ) -> ComplianceReview:
        if not issues:
            raise ValueError("rejected compliance review must include issues")
        return self.model_copy(
            update={
                "status": ComplianceStatus.REJECTED,
                "issues": issues,
                "reviewer_type": reviewer_type,
                "reviewer_id": reviewer_id,
                "notes": notes,
                "decided_at": utc_now(),
            }
        )


class VoiceStackRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_provider: VoiceProvider
    backup_provider: VoiceProvider
    rationale: str
    suggested_voice_keys: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def _piper_voice_keys(locale: Locale) -> list[str]:
    if locale == Locale.ES_AR:
        return ["es_AR-daniela-high"]
    if locale == Locale.ES_MX:
        return ["es_MX-claude-high"]
    return ["es_ES-davefx-medium", "es_ES-sharvard-medium"]


def recommend_voice_stack(
    goal: VoiceGoal,
    target_locale: Locale = Locale.ES_ES,
    windows_host: bool = False,
) -> VoiceStackRecommendation:
    if goal == VoiceGoal.SIMPLE_OFFLINE:
        return VoiceStackRecommendation(
            primary_provider=VoiceProvider.PIPER,
            backup_provider=VoiceProvider.EDGE_TTS,
            rationale="Piper es el camino mas simple para offline real en espanol.",
            suggested_voice_keys=_piper_voice_keys(target_locale),
            notes=["En Windows la instalacion es directa y ligera."],
        )
    if goal == VoiceGoal.BETTER_SPANISH_LOCAL:
        notes = ["MeloTTS suele sonar mejor en espanol que motores pequenos."]
        if windows_host:
            notes.append("En Windows conviene usar Docker para un setup estable de MeloTTS.")
        return VoiceStackRecommendation(
            primary_provider=VoiceProvider.MELO_TTS,
            backup_provider=VoiceProvider.PIPER,
            rationale="Mejor balance entre naturalidad y ejecucion local.",
            suggested_voice_keys=["ES", *_piper_voice_keys(target_locale)],
            notes=notes,
        )
    return VoiceStackRecommendation(
        primary_provider=VoiceProvider.XTTS_V2,
        backup_provider=VoiceProvider.MELO_TTS,
        rationale="XTTS-v2 prioriza calidad y clonacion de voz en local.",
        suggested_voice_keys=["xtts-reference-voice", "ES"],
        notes=["Requiere mas recursos y setup mas pesado que Piper/MeloTTS."],
    )


def default_voice_profiles() -> list[VoiceProfile]:
    return [
        VoiceProfile(
            name="es-ES davefx",
            provider=VoiceProvider.PIPER,
            provider_voice_id="es_ES-davefx-medium",
            language=Locale.ES_ES,
            locale=Locale.ES_ES,
            tone_tags=["neutral", "informativo"],
        ),
        VoiceProfile(
            name="es-ES sharvard",
            provider=VoiceProvider.PIPER,
            provider_voice_id="es_ES-sharvard-medium",
            language=Locale.ES_ES,
            locale=Locale.ES_ES,
            tone_tags=["neutral", "storytelling"],
        ),
        VoiceProfile(
            name="es-MX claude",
            provider=VoiceProvider.PIPER,
            provider_voice_id="es_MX-claude-high",
            language=Locale.ES_MX,
            locale=Locale.ES_MX,
            tone_tags=["neutral", "latam"],
        ),
        VoiceProfile(
            name="es-AR daniela",
            provider=VoiceProvider.PIPER,
            provider_voice_id="es_AR-daniela-high",
            language=Locale.ES_AR,
            locale=Locale.ES_AR,
            tone_tags=["neutral", "rioplatense"],
        ),
        VoiceProfile(
            name="MeloTTS ES",
            provider=VoiceProvider.MELO_TTS,
            provider_voice_id="ES",
            language=Locale.ES_NEUTRAL,
            locale=Locale.ES_NEUTRAL,
            tone_tags=["natural", "narracion"],
            settings=VoiceSettings(provider_config={"docker_recommended_on_windows": True}),
        ),
    ]
