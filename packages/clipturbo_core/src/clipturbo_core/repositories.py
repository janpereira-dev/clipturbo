from __future__ import annotations

from typing import Protocol
from uuid import UUID

from clipturbo_core.domain import (
    AuditLog,
    ComplianceReview,
    Project,
    PublishJob,
    RenderJob,
    ScriptVersion,
    VoiceProfile,
)


class ProjectRepository(Protocol):
    def save(self, project: Project) -> Project: ...

    def get(self, project_id: UUID) -> Project | None: ...

    def list_all(self) -> list[Project]: ...


class ScriptVersionRepository(Protocol):
    def save(self, script_version: ScriptVersion) -> ScriptVersion: ...

    def get(self, script_version_id: UUID) -> ScriptVersion | None: ...

    def list_by_project(self, project_id: UUID) -> list[ScriptVersion]: ...

    def next_version_number(self, project_id: UUID) -> int: ...


class VoiceProfileRepository(Protocol):
    def save(self, voice_profile: VoiceProfile) -> VoiceProfile: ...

    def get(self, voice_profile_id: UUID) -> VoiceProfile | None: ...

    def list_active(self) -> list[VoiceProfile]: ...


class RenderJobRepository(Protocol):
    def save(self, render_job: RenderJob) -> RenderJob: ...

    def get(self, render_job_id: UUID) -> RenderJob | None: ...

    def list_by_project(self, project_id: UUID) -> list[RenderJob]: ...


class PublishJobRepository(Protocol):
    def save(self, publish_job: PublishJob) -> PublishJob: ...

    def get(self, publish_job_id: UUID) -> PublishJob | None: ...

    def list_by_project(self, project_id: UUID) -> list[PublishJob]: ...


class PromptTraceRepository(Protocol):
    def append(self, trace: "PromptTrace") -> "PromptTrace": ...

    def list_by_project(self, project_id: UUID) -> list["PromptTrace"]: ...


class AuditLogRepository(Protocol):
    def append(self, event: AuditLog) -> AuditLog: ...

    def list_by_project(self, project_id: UUID) -> list[AuditLog]: ...


class ComplianceReviewRepository(Protocol):
    def save(self, review: ComplianceReview) -> ComplianceReview: ...

    def get(self, review_id: UUID) -> ComplianceReview | None: ...

    def list_by_project(self, project_id: UUID) -> list[ComplianceReview]: ...


from clipturbo_core.domain import PromptTrace  # noqa: E402  # avoid forward cyclical style warning
