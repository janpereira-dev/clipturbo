from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from clipturbo_core.domain import Project, ScriptSourceType, ScriptVersion, VersionNumber, VoiceProfile, VoiceProvider
from clipturbo_core.in_memory_repositories import InMemoryRepositoryBundle
from clipturbo_core.sqlite_repositories import SqliteProjectRepository, SqliteScriptVersionRepository


def test_in_memory_script_version_sequence() -> None:
    repos = InMemoryRepositoryBundle()
    project = Project(owner_id=uuid4(), workspace_id=uuid4(), name="Proyecto")
    repos.projects.save(project)

    assert repos.script_versions.next_version_number(project.id) == 1
    repos.script_versions.save(
        ScriptVersion(
            project_id=project.id,
            version_number=VersionNumber(value=1),
            title="v01",
            content="Contenido suficientemente largo para validar una version uno.",
            source_type=ScriptSourceType.MANUAL,
            created_by="user-1",
        )
    )
    assert repos.script_versions.next_version_number(project.id) == 2


def test_sqlite_repositories_roundtrip() -> None:
    with TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "clipturbo.db"
        projects = SqliteProjectRepository(db_path)
        scripts = SqliteScriptVersionRepository(db_path)

        project = Project(owner_id=uuid4(), workspace_id=uuid4(), name="Proyecto sqlite")
        projects.save(project)

        loaded_project = projects.get(project.id)
        assert loaded_project is not None
        assert loaded_project.name == "Proyecto sqlite"

        script = ScriptVersion(
            project_id=project.id,
            version_number=VersionNumber(value=1),
            title="v01",
            content="Contenido suficientemente largo para validar sqlite repository.",
            source_type=ScriptSourceType.GENERATED,
            created_by="agent",
        )
        scripts.save(script)
        loaded = scripts.get(script.id)
        assert loaded is not None
        assert loaded.version_number.value == 1


def test_in_memory_active_voice_listing() -> None:
    repos = InMemoryRepositoryBundle()
    active = VoiceProfile(
        name="voice-a",
        provider=VoiceProvider.PIPER,
        provider_voice_id="es_ES-davefx-medium",
    )
    inactive = active.deactivate().model_copy(update={"id": uuid4()})

    repos.voice_profiles.save(active)
    repos.voice_profiles.save(inactive)

    active_ids = {voice.id for voice in repos.voice_profiles.list_active()}
    assert active.id in active_ids
    assert inactive.id not in active_ids
