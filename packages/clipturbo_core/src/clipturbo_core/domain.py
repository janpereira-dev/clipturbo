from __future__ import annotations

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
    READY_FOR_REVIEW = "ready_for_review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


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
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELED = "canceled"


class ActorType(str, Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class VoiceProvider(str, Enum):
    PIPER = "piper"
    MELO_TTS = "melo_tts"
    XTTS_V2 = "xtts_v2"
    AZURE_SPEECH = "azure_speech"
    ELEVENLABS = "elevenlabs"
    EDGE_TTS = "edge_tts"
    OPENAI_TTS = "openai_tts"


class VoiceGoal(str, Enum):
    SIMPLE_OFFLINE = "simple_offline"
    BETTER_SPANISH_LOCAL = "better_spanish_local"
    HIGH_QUALITY_CLONING = "high_quality_cloning"


class Project(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    title: str = Field(min_length=3, max_length=140)
    description: str | None = None
    locale: Locale = Locale.ES_ES
    status: ProjectStatus = ProjectStatus.DRAFT
    selected_format: RenderFormat = RenderFormat.VERTICAL_9_16
    niche: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("title")
    @classmethod
    def _clean_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("title cannot be empty")
        return normalized

    def touch(self) -> Project:
        return self.model_copy(update={"updated_at": utc_now()})


class ScriptVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    version_number: int = Field(default=1, ge=1)
    language: Locale = Locale.ES_ES
    tone: str = Field(default="neutral", min_length=2, max_length=40)
    hook_source: str = Field(min_length=2, max_length=240)
    script_text: str = Field(min_length=20)
    provider_name: str = Field(min_length=2, max_length=80)
    provider_model: str = Field(min_length=2, max_length=120)
    is_approved: bool = False
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("script_text")
    @classmethod
    def _clean_script_text(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 20:
            raise ValueError("script_text must have at least 20 chars")
        return normalized


class VoiceProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    provider_name: VoiceProvider
    voice_key: str = Field(min_length=2, max_length=120)
    locale: Locale
    style: str = Field(default="neutral", min_length=2, max_length=60)
    gender_hint: str | None = Field(default=None, max_length=20)
    quality_tier: str = Field(default="medium", min_length=2, max_length=20)
    is_active: bool = True
    is_local: bool = False
    docker_required: bool = False
    sample_rate_hz: int | None = Field(default=None, ge=8000, le=96000)
    notes: str | None = Field(default=None, max_length=400)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _derive_local_flags(self) -> VoiceProfile:
        if self.provider_name in {VoiceProvider.PIPER, VoiceProvider.MELO_TTS, VoiceProvider.XTTS_V2}:
            self.is_local = True
        return self


class PromptTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    stage: PipelineStage
    provider_name: str = Field(min_length=2, max_length=80)
    provider_model: str = Field(min_length=2, max_length=120)
    prompt_hash: str = Field(min_length=8, max_length=128)
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    output_snapshot: dict[str, Any] = Field(default_factory=dict)
    token_input: int | None = Field(default=None, ge=0)
    token_output: int | None = Field(default=None, ge=0)
    latency_ms: int | None = Field(default=None, ge=0)
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("prompt_hash")
    @classmethod
    def _clean_prompt_hash(cls, value: str) -> str:
        normalized = value.strip().lower()
        if " " in normalized:
            raise ValueError("prompt_hash cannot contain spaces")
        return normalized


class AuditLog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    actor_type: ActorType
    actor_id: str | None = Field(default=None, max_length=120)
    action: str = Field(min_length=2, max_length=120)
    target_type: str = Field(min_length=2, max_length=80)
    target_id: str | None = Field(default=None, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class RenderJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    script_version_id: UUID
    voice_profile_id: UUID
    stage: PipelineStage = PipelineStage.VIDEO_RENDER
    render_format: RenderFormat = RenderFormat.VERTICAL_9_16
    status: RenderJobStatus = RenderJobStatus.QUEUED
    attempts: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=3, ge=1)
    queued_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    output_asset_path: str | None = None
    error_code: str | None = Field(default=None, max_length=80)
    error_message: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _validate_timestamps(self) -> RenderJob:
        if self.finished_at and self.started_at and self.finished_at < self.started_at:
            raise ValueError("finished_at cannot be before started_at")
        if self.attempts > self.max_attempts:
            raise ValueError("attempts cannot exceed max_attempts")
        return self

    @property
    def can_retry(self) -> bool:
        return self.status == RenderJobStatus.FAILED and self.attempts < self.max_attempts


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
            provider_name=VoiceProvider.PIPER,
            voice_key="es_ES-davefx-medium",
            locale=Locale.ES_ES,
            style="neutral",
            quality_tier="medium",
            notes="Buena opcion base para espanol de Espana.",
        ),
        VoiceProfile(
            provider_name=VoiceProvider.PIPER,
            voice_key="es_ES-sharvard-medium",
            locale=Locale.ES_ES,
            style="neutral",
            quality_tier="medium",
            notes="Alternativa de timbre para espanol de Espana.",
        ),
        VoiceProfile(
            provider_name=VoiceProvider.PIPER,
            voice_key="es_MX-claude-high",
            locale=Locale.ES_MX,
            style="neutral",
            quality_tier="high",
            notes="Opcion para espanol de Mexico o neutral latino.",
        ),
        VoiceProfile(
            provider_name=VoiceProvider.PIPER,
            voice_key="es_AR-daniela-high",
            locale=Locale.ES_AR,
            style="neutral",
            quality_tier="high",
            notes="Opcion para rioplatense argentino.",
        ),
        VoiceProfile(
            provider_name=VoiceProvider.MELO_TTS,
            voice_key="ES",
            locale=Locale.ES_NEUTRAL,
            style="narracion",
            quality_tier="high",
            docker_required=True,
            notes="Suele dar mejor naturalidad local si aceptas setup mas pesado.",
        ),
    ]
