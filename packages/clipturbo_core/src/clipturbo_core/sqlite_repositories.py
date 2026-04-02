from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel

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

ModelT = TypeVar("ModelT", bound=BaseModel)


def _connect(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def _open_connection(db_path: str | Path) -> sqlite3.Connection:
    connection = _connect(db_path)
    try:
        yield connection
    finally:
        connection.close()


def _create_table(connection: sqlite3.Connection, table_name: str) -> None:
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id TEXT PRIMARY KEY,
            payload TEXT NOT NULL
        )
        """
    )
    connection.commit()


class _SqliteModelStore(Generic[ModelT]):
    def __init__(self, db_path: str | Path, table_name: str, loader: Callable[[dict], ModelT]) -> None:
        self._db_path = db_path
        self._table_name = table_name
        self._loader = loader
        with _open_connection(self._db_path) as connection:
            _create_table(connection, self._table_name)

    def upsert(self, model: ModelT) -> ModelT:
        payload = model.model_dump(mode="json")
        with _open_connection(self._db_path) as connection:
            connection.execute(
                f"""
                INSERT INTO {self._table_name} (id, payload)
                VALUES (?, ?)
                ON CONFLICT(id) DO UPDATE SET payload = excluded.payload
                """,
                (str(payload["id"]), json.dumps(payload)),
            )
            connection.commit()
        return model

    def get(self, item_id: UUID) -> ModelT | None:
        with _open_connection(self._db_path) as connection:
            row = connection.execute(
                f"SELECT payload FROM {self._table_name} WHERE id = ?", (str(item_id),)
            ).fetchone()
        if not row:
            return None
        return self._loader(json.loads(row["payload"]))

    def list_all(self) -> list[ModelT]:
        with _open_connection(self._db_path) as connection:
            rows = connection.execute(f"SELECT payload FROM {self._table_name}").fetchall()
        return [self._loader(json.loads(row["payload"])) for row in rows]


class SqliteProjectRepository:
    def __init__(self, db_path: str | Path) -> None:
        self._store = _SqliteModelStore(db_path, "projects", Project.model_validate)

    def save(self, project: Project) -> Project:
        return self._store.upsert(project)

    def get(self, project_id: UUID) -> Project | None:
        return self._store.get(project_id)

    def list_all(self) -> list[Project]:
        return self._store.list_all()


class SqliteScriptVersionRepository:
    def __init__(self, db_path: str | Path) -> None:
        self._store = _SqliteModelStore(db_path, "script_versions", ScriptVersion.model_validate)

    def save(self, script_version: ScriptVersion) -> ScriptVersion:
        return self._store.upsert(script_version)

    def get(self, script_version_id: UUID) -> ScriptVersion | None:
        return self._store.get(script_version_id)

    def list_by_project(self, project_id: UUID) -> list[ScriptVersion]:
        return [item for item in self._store.list_all() if item.project_id == project_id]

    def next_version_number(self, project_id: UUID) -> int:
        versions = self.list_by_project(project_id)
        if not versions:
            return 1
        return max(item.version_number.value for item in versions) + 1


class SqliteVoiceProfileRepository:
    def __init__(self, db_path: str | Path) -> None:
        self._store = _SqliteModelStore(db_path, "voice_profiles", VoiceProfile.model_validate)

    def save(self, voice_profile: VoiceProfile) -> VoiceProfile:
        return self._store.upsert(voice_profile)

    def get(self, voice_profile_id: UUID) -> VoiceProfile | None:
        return self._store.get(voice_profile_id)

    def list_active(self) -> list[VoiceProfile]:
        return [item for item in self._store.list_all() if item.is_active]


class SqliteRenderJobRepository:
    def __init__(self, db_path: str | Path) -> None:
        self._store = _SqliteModelStore(db_path, "render_jobs", RenderJob.model_validate)

    def save(self, render_job: RenderJob) -> RenderJob:
        return self._store.upsert(render_job)

    def get(self, render_job_id: UUID) -> RenderJob | None:
        return self._store.get(render_job_id)

    def list_by_project(self, project_id: UUID) -> list[RenderJob]:
        return [item for item in self._store.list_all() if item.project_id == project_id]


class SqlitePublishJobRepository:
    def __init__(self, db_path: str | Path) -> None:
        self._store = _SqliteModelStore(db_path, "publish_jobs", PublishJob.model_validate)

    def save(self, publish_job: PublishJob) -> PublishJob:
        return self._store.upsert(publish_job)

    def get(self, publish_job_id: UUID) -> PublishJob | None:
        return self._store.get(publish_job_id)

    def list_by_project(self, project_id: UUID) -> list[PublishJob]:
        return [item for item in self._store.list_all() if item.project_id == project_id]


class SqlitePromptTraceRepository:
    def __init__(self, db_path: str | Path) -> None:
        self._store = _SqliteModelStore(db_path, "prompt_traces", PromptTrace.model_validate)

    def append(self, trace: PromptTrace) -> PromptTrace:
        return self._store.upsert(trace)

    def list_by_project(self, project_id: UUID) -> list[PromptTrace]:
        return [item for item in self._store.list_all() if item.project_id == project_id]


class SqliteAuditLogRepository:
    def __init__(self, db_path: str | Path) -> None:
        self._store = _SqliteModelStore(db_path, "audit_logs", AuditLog.model_validate)

    def append(self, event: AuditLog) -> AuditLog:
        return self._store.upsert(event)

    def list_by_project(self, project_id: UUID) -> list[AuditLog]:
        return [item for item in self._store.list_all() if item.project_id == project_id]


class SqliteComplianceReviewRepository:
    def __init__(self, db_path: str | Path) -> None:
        self._store = _SqliteModelStore(db_path, "compliance_reviews", ComplianceReview.model_validate)

    def save(self, review: ComplianceReview) -> ComplianceReview:
        return self._store.upsert(review)

    def get(self, review_id: UUID) -> ComplianceReview | None:
        return self._store.get(review_id)

    def list_by_project(self, project_id: UUID) -> list[ComplianceReview]:
        return [item for item in self._store.list_all() if item.project_id == project_id]
