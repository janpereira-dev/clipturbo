from __future__ import annotations

from typing import TypeVar
from uuid import UUID

from clipturbo_core.domain import (
    AuditLog,
    ComplianceReview,
    Project,
    PromptTrace,
    PublishJob,
    RenderJob,
    ScriptVersion,
    VoiceProfile,
)

T = TypeVar("T")


class InMemoryProjectRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, Project] = {}

    def save(self, project: Project) -> Project:
        self._items[project.id] = project
        return project

    def get(self, project_id: UUID) -> Project | None:
        return self._items.get(project_id)

    def list_all(self) -> list[Project]:
        return list(self._items.values())


class InMemoryScriptVersionRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, ScriptVersion] = {}

    def save(self, script_version: ScriptVersion) -> ScriptVersion:
        self._items[script_version.id] = script_version
        return script_version

    def get(self, script_version_id: UUID) -> ScriptVersion | None:
        return self._items.get(script_version_id)

    def list_by_project(self, project_id: UUID) -> list[ScriptVersion]:
        return [item for item in self._items.values() if item.project_id == project_id]

    def next_version_number(self, project_id: UUID) -> int:
        versions = self.list_by_project(project_id)
        if not versions:
            return 1
        return max(item.version_number.value for item in versions) + 1


class InMemoryVoiceProfileRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, VoiceProfile] = {}

    def save(self, voice_profile: VoiceProfile) -> VoiceProfile:
        self._items[voice_profile.id] = voice_profile
        return voice_profile

    def get(self, voice_profile_id: UUID) -> VoiceProfile | None:
        return self._items.get(voice_profile_id)

    def list_active(self) -> list[VoiceProfile]:
        return [item for item in self._items.values() if item.is_active]


class InMemoryRenderJobRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, RenderJob] = {}

    def save(self, render_job: RenderJob) -> RenderJob:
        self._items[render_job.id] = render_job
        return render_job

    def get(self, render_job_id: UUID) -> RenderJob | None:
        return self._items.get(render_job_id)

    def list_by_project(self, project_id: UUID) -> list[RenderJob]:
        return [item for item in self._items.values() if item.project_id == project_id]


class InMemoryPublishJobRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, PublishJob] = {}

    def save(self, publish_job: PublishJob) -> PublishJob:
        self._items[publish_job.id] = publish_job
        return publish_job

    def get(self, publish_job_id: UUID) -> PublishJob | None:
        return self._items.get(publish_job_id)

    def list_by_project(self, project_id: UUID) -> list[PublishJob]:
        return [item for item in self._items.values() if item.project_id == project_id]


class InMemoryPromptTraceRepository:
    def __init__(self) -> None:
        self._items: list[PromptTrace] = []

    def append(self, trace: PromptTrace) -> PromptTrace:
        self._items.append(trace)
        return trace

    def list_by_project(self, project_id: UUID) -> list[PromptTrace]:
        return [item for item in self._items if item.project_id == project_id]


class InMemoryAuditLogRepository:
    def __init__(self) -> None:
        self._items: list[AuditLog] = []

    def append(self, event: AuditLog) -> AuditLog:
        self._items.append(event)
        return event

    def list_by_project(self, project_id: UUID) -> list[AuditLog]:
        return [item for item in self._items if item.project_id == project_id]


class InMemoryComplianceReviewRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, ComplianceReview] = {}

    def save(self, review: ComplianceReview) -> ComplianceReview:
        self._items[review.id] = review
        return review

    def get(self, review_id: UUID) -> ComplianceReview | None:
        return self._items.get(review_id)

    def list_by_project(self, project_id: UUID) -> list[ComplianceReview]:
        return [item for item in self._items.values() if item.project_id == project_id]


class InMemoryRepositoryBundle:
    def __init__(self) -> None:
        self.projects = InMemoryProjectRepository()
        self.script_versions = InMemoryScriptVersionRepository()
        self.voice_profiles = InMemoryVoiceProfileRepository()
        self.render_jobs = InMemoryRenderJobRepository()
        self.publish_jobs = InMemoryPublishJobRepository()
        self.prompt_traces = InMemoryPromptTraceRepository()
        self.audit_logs = InMemoryAuditLogRepository()
        self.compliance_reviews = InMemoryComplianceReviewRepository()
