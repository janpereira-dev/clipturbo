from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from clipturbo_core.domain import (
    ActorType,
    AuditActor,
    AuditLog,
    ComplianceReview,
    ComplianceStatus,
    Locale,
    PipelineStage,
    Project,
    ProjectStatus,
    PromptTrace,
    PublishJob,
    PublishPlatform,
    RenderFormat,
    RenderJob,
    RenderJobStatus,
    ScriptSourceType,
    ScriptVersion,
    VersionNumber,
    VoiceProfile,
    utc_now,
)
from clipturbo_core.providers import (
    LLMProvider,
    PublisherProvider,
    StorageProvider,
    SubtitleProvider,
    TTSProvider,
    VideoRenderProvider,
)
from clipturbo_core.repositories import (
    AuditLogRepository,
    ComplianceReviewRepository,
    ProjectRepository,
    PromptTraceRepository,
    PublishJobRepository,
    RenderJobRepository,
    ScriptVersionRepository,
    VoiceProfileRepository,
)


class DomainServiceError(RuntimeError):
    pass


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class AuthoringService:
    def __init__(
        self,
        projects: ProjectRepository,
        script_versions: ScriptVersionRepository,
        audits: AuditLogRepository,
    ) -> None:
        self._projects = projects
        self._script_versions = script_versions
        self._audits = audits

    def create_project(
        self,
        owner_id: UUID,
        workspace_id: UUID,
        name: str,
        description: str | None,
    ) -> Project:
        project = Project(owner_id=owner_id, workspace_id=workspace_id, name=name, description=description)
        self._projects.save(project)
        self._audits.append(
            AuditLog(
                project_id=project.id,
                actor=AuditActor(actor_type=ActorType.USER, actor_id=str(owner_id)),
                action="project.create",
                entity_type="project",
                entity_id=str(project.id),
                after=project.model_dump(mode="json"),
            )
        )
        return project

    def create_script_version(
        self,
        project_id: UUID,
        title: str,
        content: str,
        created_by: str,
        source_type: ScriptSourceType,
        language: Locale = Locale.ES_ES,
        parent_version_id: UUID | None = None,
        change_summary: str | None = None,
        provider_name: str | None = None,
        provider_model: str | None = None,
    ) -> ScriptVersion:
        project = self._projects.get(project_id)
        if project is None:
            raise DomainServiceError(f"project {project_id} not found")
        if project.status == ProjectStatus.ARCHIVED:
            raise DomainServiceError("cannot create script version in archived project")

        next_number = self._script_versions.next_version_number(project_id)
        script_version = ScriptVersion(
            project_id=project_id,
            version_number=VersionNumber(value=next_number),
            title=title,
            content=content,
            source_type=source_type,
            created_by=created_by,
            language=language,
            parent_version_id=parent_version_id,
            change_summary=change_summary,
            provider_name=provider_name,
            provider_model=provider_model,
        )
        self._script_versions.save(script_version)

        updated_project = project.with_current_script(script_version.id)
        self._projects.save(updated_project)

        self._audits.append(
            AuditLog(
                project_id=project.id,
                actor=AuditActor(actor_type=ActorType.USER, actor_id=created_by),
                action="script_version.create",
                entity_type="script_version",
                entity_id=str(script_version.id),
                metadata={"version_number": next_number},
                after=script_version.model_dump(mode="json"),
            )
        )
        return script_version

    def set_current_script_version(self, project_id: UUID, script_version_id: UUID, actor_id: str) -> Project:
        project = self._projects.get(project_id)
        script_version = self._script_versions.get(script_version_id)
        if not project or not script_version:
            raise DomainServiceError("project or script version not found")
        if script_version.project_id != project.id:
            raise DomainServiceError("script version does not belong to project")

        previous = project.model_dump(mode="json")
        updated = project.with_current_script(script_version_id)
        self._projects.save(updated)
        self._audits.append(
            AuditLog(
                project_id=project.id,
                actor=AuditActor(actor_type=ActorType.USER, actor_id=actor_id),
                action="project.set_current_script_version",
                entity_type="project",
                entity_id=str(project.id),
                before=previous,
                after=updated.model_dump(mode="json"),
            )
        )
        return updated


class VoiceService:
    def __init__(self, voices: VoiceProfileRepository, audits: AuditLogRepository) -> None:
        self._voices = voices
        self._audits = audits

    def create_voice_profile(self, profile: VoiceProfile, actor_id: str) -> VoiceProfile:
        self._voices.save(profile)
        self._audits.append(
            AuditLog(
                project_id=None,
                actor=AuditActor(actor_type=ActorType.USER, actor_id=actor_id),
                action="voice_profile.create",
                entity_type="voice_profile",
                entity_id=str(profile.id),
                after=profile.model_dump(mode="json"),
            )
        )
        return profile

    def deactivate_voice_profile(self, voice_profile_id: UUID, actor_id: str) -> VoiceProfile:
        existing = self._voices.get(voice_profile_id)
        if not existing:
            raise DomainServiceError("voice profile not found")
        updated = existing.deactivate()
        self._voices.save(updated)
        self._audits.append(
            AuditLog(
                project_id=None,
                actor=AuditActor(actor_type=ActorType.USER, actor_id=actor_id),
                action="voice_profile.deactivate",
                entity_type="voice_profile",
                entity_id=str(updated.id),
            )
        )
        return updated


class RenderExecutionService:
    def __init__(
        self,
        projects: ProjectRepository,
        script_versions: ScriptVersionRepository,
        voice_profiles: VoiceProfileRepository,
        render_jobs: RenderJobRepository,
        audits: AuditLogRepository,
    ) -> None:
        self._projects = projects
        self._script_versions = script_versions
        self._voice_profiles = voice_profiles
        self._render_jobs = render_jobs
        self._audits = audits

    def queue_render_job(
        self,
        project_id: UUID,
        script_version_id: UUID,
        voice_profile_id: UUID | None,
        requested_by: str,
        output_format: RenderFormat = RenderFormat.VERTICAL_9_16,
        input_config: dict[str, Any] | None = None,
    ) -> RenderJob:
        project = self._projects.get(project_id)
        script = self._script_versions.get(script_version_id)
        if not project or not script:
            raise DomainServiceError("project or script version not found")
        if script.project_id != project_id:
            raise DomainServiceError("script version does not belong to project")
        if project.current_script_version_id is None:
            raise DomainServiceError("project has no current script version")

        voice_snapshot: dict[str, Any] = {}
        if voice_profile_id:
            voice = self._voice_profiles.get(voice_profile_id)
            if not voice:
                raise DomainServiceError("voice profile not found")
            if not voice.is_active:
                raise DomainServiceError("voice profile is inactive")
            voice_snapshot = voice.model_dump(mode="json")

        job = RenderJob(
            project_id=project_id,
            script_version_id=script_version_id,
            voice_profile_id=voice_profile_id,
            voice_snapshot=voice_snapshot,
            requested_by=requested_by,
            output_format=output_format,
            input_config=input_config or {},
        )
        self._render_jobs.save(job)
        self._audits.append(
            AuditLog(
                project_id=project_id,
                actor=AuditActor(actor_type=ActorType.USER, actor_id=requested_by),
                action="render_job.queue",
                entity_type="render_job",
                entity_id=str(job.id),
                metadata={"script_version_id": str(script_version_id)},
            )
        )
        return job

    def start_render_job(self, render_job_id: UUID, actor_id: str) -> RenderJob:
        job = self._require_job(render_job_id)
        updated = job.mark_preparing()
        self._render_jobs.save(updated)
        self._audit_render(updated, "render_job.start", actor_id)
        return updated

    def mark_rendering(self, render_job_id: UUID, actor_id: str) -> RenderJob:
        job = self._require_job(render_job_id)
        updated = job.mark_rendering()
        self._render_jobs.save(updated)
        self._audit_render(updated, "render_job.rendering", actor_id)
        return updated

    def mark_post_processing(self, render_job_id: UUID, actor_id: str) -> RenderJob:
        job = self._require_job(render_job_id)
        updated = job.mark_post_processing()
        self._render_jobs.save(updated)
        self._audit_render(updated, "render_job.post_processing", actor_id)
        return updated

    def complete_render_job(
        self,
        render_job_id: UUID,
        actor_id: str,
        output_url: str | None,
        artifact_id: str | None = None,
    ) -> RenderJob:
        job = self._require_job(render_job_id)
        updated = job.mark_completed(output_url=output_url, artifact_id=artifact_id)
        self._render_jobs.save(updated)
        self._audit_render(updated, "render_job.complete", actor_id)
        return updated

    def fail_render_job(self, render_job_id: UUID, actor_id: str, error_code: str, error_message: str) -> RenderJob:
        job = self._require_job(render_job_id)
        updated = job.mark_failed(error_code=error_code, error_message=error_message)
        self._render_jobs.save(updated)
        self._audit_render(updated, "render_job.fail", actor_id)
        return updated

    def retry_render_job(self, render_job_id: UUID, actor_id: str) -> RenderJob:
        job = self._require_job(render_job_id)
        scheduled = job.schedule_retry()
        self._render_jobs.save(scheduled)
        self._audit_render(scheduled, "render_job.retry_scheduled", actor_id)

        new_job = scheduled.model_copy(
            update={
                "id": uuid4(),
                "status": RenderJobStatus.QUEUED,
                "attempt_count": scheduled.attempt_count,
                "queued_at": utc_now(),
                "started_at": None,
                "finished_at": None,
            }
        )
        self._render_jobs.save(new_job)
        self._audit_render(new_job, "render_job.requeued", actor_id)
        return new_job

    def cancel_render_job(self, render_job_id: UUID, actor_id: str) -> RenderJob:
        job = self._require_job(render_job_id)
        updated = job.mark_canceled()
        self._render_jobs.save(updated)
        self._audit_render(updated, "render_job.cancel", actor_id)
        return updated

    def _require_job(self, render_job_id: UUID) -> RenderJob:
        job = self._render_jobs.get(render_job_id)
        if not job:
            raise DomainServiceError("render job not found")
        return job

    def _audit_render(self, job: RenderJob, action: str, actor_id: str) -> None:
        self._audits.append(
            AuditLog(
                project_id=job.project_id,
                actor=AuditActor(actor_type=ActorType.WORKER, actor_id=actor_id),
                action=action,
                entity_type="render_job",
                entity_id=str(job.id),
                metadata={"status": job.status.value},
            )
        )


class TraceabilityService:
    def __init__(
        self,
        prompt_traces: PromptTraceRepository,
        audits: AuditLogRepository,
        compliance_reviews: ComplianceReviewRepository,
    ) -> None:
        self._prompt_traces = prompt_traces
        self._audits = audits
        self._compliance_reviews = compliance_reviews

    def record_prompt_trace(self, trace: PromptTrace) -> PromptTrace:
        self._prompt_traces.append(trace)
        return trace

    def record_audit_event(self, event: AuditLog) -> AuditLog:
        self._audits.append(event)
        return event

    def create_compliance_review(self, review: ComplianceReview) -> ComplianceReview:
        self._compliance_reviews.save(review)
        return review

    def approve_compliance_review(
        self,
        review_id: UUID,
        reviewer_type: ActorType,
        reviewer_id: str | None,
    ) -> ComplianceReview:
        review = self._compliance_reviews.get(review_id)
        if not review:
            raise DomainServiceError("compliance review not found")
        updated = review.approve(reviewer_type=reviewer_type, reviewer_id=reviewer_id)
        self._compliance_reviews.save(updated)
        return updated

    def reject_compliance_review(
        self,
        review_id: UUID,
        reviewer_type: ActorType,
        issues: list[str],
        reviewer_id: str | None = None,
        notes: str | None = None,
    ) -> ComplianceReview:
        review = self._compliance_reviews.get(review_id)
        if not review:
            raise DomainServiceError("compliance review not found")
        updated = review.reject(
            issues=issues,
            reviewer_type=reviewer_type,
            reviewer_id=reviewer_id,
            notes=notes,
        )
        self._compliance_reviews.save(updated)
        return updated


class PublishService:
    def __init__(
        self,
        render_jobs: RenderJobRepository,
        publish_jobs: PublishJobRepository,
        audits: AuditLogRepository,
        providers: dict[PublishPlatform, PublisherProvider],
    ) -> None:
        self._render_jobs = render_jobs
        self._publish_jobs = publish_jobs
        self._audits = audits
        self._providers = providers

    def queue_publish_job(
        self,
        project_id: UUID,
        render_job_id: UUID,
        target_platform: PublishPlatform,
        requested_by: str,
        metadata: dict[str, Any] | None = None,
    ) -> PublishJob:
        render_job = self._render_jobs.get(render_job_id)
        if not render_job:
            raise DomainServiceError("render job not found")
        if render_job.project_id != project_id:
            raise DomainServiceError("render job does not belong to project")
        if render_job.status != RenderJobStatus.COMPLETED:
            raise DomainServiceError("render job must be completed before publish")
        if not render_job.output_url:
            raise DomainServiceError("render job has no output_url")

        job = PublishJob(
            project_id=project_id,
            render_job_id=render_job_id,
            target_platform=target_platform,
            requested_by=requested_by,
            metadata=metadata or {},
        )
        self._publish_jobs.save(job)
        self._audits.append(
            AuditLog(
                project_id=project_id,
                actor=AuditActor(actor_type=ActorType.USER, actor_id=requested_by),
                action="publish_job.queue",
                entity_type="publish_job",
                entity_id=str(job.id),
                metadata={"platform": target_platform.value},
            )
        )
        return job

    def execute_publish_job(self, publish_job_id: UUID, actor_id: str) -> PublishJob:
        job = self._publish_jobs.get(publish_job_id)
        if not job:
            raise DomainServiceError("publish job not found")
        provider = self._providers.get(job.target_platform)
        if provider is None:
            raise DomainServiceError(f"no publisher provider for {job.target_platform.value}")

        render_job = self._render_jobs.get(job.render_job_id)
        if not render_job or not render_job.output_url:
            raise DomainServiceError("render job output not available")

        uploading = job.mark_uploading()
        self._publish_jobs.save(uploading)
        self._audits.append(
            AuditLog(
                project_id=job.project_id,
                actor=AuditActor(actor_type=ActorType.WORKER, actor_id=actor_id),
                action="publish_job.uploading",
                entity_type="publish_job",
                entity_id=str(job.id),
            )
        )

        try:
            metadata = {key: str(value) for key, value in uploading.metadata.items()}
            publish_result = provider.publish_draft(
                platform=uploading.target_platform,
                asset_path=render_job.output_url,
                metadata=metadata,
            )
        except Exception as exc:
            failed = uploading.mark_failed(error_code="publish_error", error_message=str(exc))
            self._publish_jobs.save(failed)
            self._audits.append(
                AuditLog(
                    project_id=failed.project_id,
                    actor=AuditActor(actor_type=ActorType.WORKER, actor_id=actor_id),
                    action="publish_job.fail",
                    entity_type="publish_job",
                    entity_id=str(failed.id),
                    metadata={"error": str(exc)},
                )
            )
            return failed

        completed = uploading.mark_completed(
            external_post_id=publish_result["external_post_id"],
            external_url=publish_result["external_url"],
        )
        self._publish_jobs.save(completed)
        self._audits.append(
            AuditLog(
                project_id=completed.project_id,
                actor=AuditActor(actor_type=ActorType.WORKER, actor_id=actor_id),
                action="publish_job.complete",
                entity_type="publish_job",
                entity_id=str(completed.id),
                metadata={"external_post_id": completed.external_post_id},
            )
        )
        return completed


class PromptToVideoRequest(BaseModel):
    project_id: UUID
    prompt_template: str = Field(min_length=1)
    prompt_variables: dict[str, str] = Field(default_factory=dict)
    voice_profile_id: UUID | None = None
    requested_by: str = Field(min_length=2)
    render_format: RenderFormat = RenderFormat.VERTICAL_9_16
    publish_targets: list[PublishPlatform] = Field(default_factory=list)
    title: str = Field(default="Nuevo video", min_length=3, max_length=180)
    prompt_template_version: str = Field(default="v1", min_length=1, max_length=40)


class PromptToVideoResult(BaseModel):
    project_id: UUID
    script_version_id: UUID
    render_job_id: UUID
    compliance_review_id: UUID
    publish_job_ids: list[UUID] = Field(default_factory=list)


@dataclass
class PromptToVideoPipelineService:
    authoring: AuthoringService
    renders: RenderExecutionService
    traceability: TraceabilityService
    publish: PublishService
    projects: ProjectRepository
    voices: VoiceProfileRepository
    llm: LLMProvider
    tts: TTSProvider
    subtitles: SubtitleProvider
    video_renderer: VideoRenderProvider
    storage: StorageProvider

    def run(self, request: PromptToVideoRequest) -> PromptToVideoResult:
        project = self.projects.get(request.project_id)
        if project is None:
            raise DomainServiceError(f"project {request.project_id} not found")
        if project.status == ProjectStatus.ARCHIVED:
            raise DomainServiceError("cannot run pipeline for archived project")

        voice_profile = None
        if request.voice_profile_id:
            voice_profile = self.voices.get(request.voice_profile_id)
            if not voice_profile:
                raise DomainServiceError("voice profile not found")
            if not voice_profile.is_active:
                raise DomainServiceError("voice profile inactive")

        prompt_text = _render_prompt(request.prompt_template, request.prompt_variables)
        script_result = self.llm.generate_text(prompt_text)
        script_text = script_result["script_text"]

        script_version = self.authoring.create_script_version(
            project_id=request.project_id,
            title=request.title,
            content=script_text,
            created_by=request.requested_by,
            source_type=ScriptSourceType.GENERATED,
            parent_version_id=project.current_script_version_id,
            provider_name=script_result["trace"]["provider_name"],
            provider_model=script_result["trace"]["provider_model"],
            change_summary="Generado desde prompt base",
        )

        self.traceability.record_prompt_trace(
            PromptTrace(
                project_id=request.project_id,
                script_version_id=script_version.id,
                purpose="script_generate",
                provider=script_result["trace"]["provider_name"],
                model=script_result["trace"]["provider_model"],
                system_prompt="clipturbo.prompt.v1",
                user_prompt=prompt_text,
                input_variables=request.prompt_variables,
                output_text=script_text,
                prompt_template_version=request.prompt_template_version,
                usage=None,
                response_hash=_sha256_text(script_text),
            )
        )

        render_job = self.renders.queue_render_job(
            project_id=request.project_id,
            script_version_id=script_version.id,
            voice_profile_id=voice_profile.id if voice_profile else None,
            requested_by=request.requested_by,
            output_format=request.render_format,
            input_config={"prompt_template_version": request.prompt_template_version},
        )
        self.renders.start_render_job(render_job.id, actor_id="pipeline")
        self.renders.mark_rendering(render_job.id, actor_id="pipeline")
        try:
            # Empty voice key allows providers to use their configured default voice.
            voice_key = voice_profile.provider_voice_id if voice_profile else ""
            audio = self.tts.synthesize(script_text, voice_key)
            subtitle_track = self.subtitles.generate(script_text, audio["asset_path"])

            rendered = self.video_renderer.compose(
                script=script_text,
                audio_path=audio["asset_path"],
                subtitles=subtitle_track,
                render_format=request.render_format,
            )

            asset_key = f"renders/{request.project_id}/{render_job.id}.mp4"
            output_url = self.storage.put(key=asset_key, source_path=rendered["asset_path"])
            completed_render = self.renders.complete_render_job(
                render_job.id,
                actor_id="pipeline",
                output_url=output_url,
                artifact_id=asset_key,
            )
        except Exception as exc:
            self.renders.fail_render_job(
                render_job_id=render_job.id,
                actor_id="pipeline",
                error_code="pipeline_render_error",
                error_message=_truncate_error(str(exc)),
            )
            raise DomainServiceError(f"pipeline render failed: {exc}") from exc

        compliance_review = self.traceability.create_compliance_review(
            ComplianceReview(
                project_id=request.project_id,
                target_type="render_job",
                target_id=str(completed_render.id),
                status=ComplianceStatus.PENDING,
                reviewer_type=ActorType.SYSTEM,
                notes="Pendiente de revision humana antes de publicacion final.",
                requires_human_review=True,
            )
        )

        publish_job_ids: list[UUID] = []
        for target in request.publish_targets:
            queued = self.publish.queue_publish_job(
                project_id=request.project_id,
                render_job_id=completed_render.id,
                target_platform=target,
                requested_by=request.requested_by,
                metadata={"draft": True},
            )
            executed = self.publish.execute_publish_job(queued.id, actor_id="pipeline")
            publish_job_ids.append(executed.id)

        return PromptToVideoResult(
            project_id=request.project_id,
            script_version_id=script_version.id,
            render_job_id=completed_render.id,
            compliance_review_id=compliance_review.id,
            publish_job_ids=publish_job_ids,
        )


class _SafeDict(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _render_prompt(template: str, variables: dict[str, str]) -> str:
    return template.format_map(_SafeDict(variables))


def _truncate_error(message: str, limit: int = 500) -> str:
    cleaned = message.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."
