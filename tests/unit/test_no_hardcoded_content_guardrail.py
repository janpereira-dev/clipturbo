from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_no_hardcoded_lexicon_in_spanish_quality() -> None:
    file_path = REPO_ROOT / "packages" / "clipturbo_core" / "src" / "clipturbo_core" / "spanish_quality.py"
    content = file_path.read_text(encoding="utf-8")

    banned_markers = (
        "_term_fixes",
        "_phrase_fixes",
        "_forbidden_tokens",
    )
    for marker in banned_markers:
        assert marker not in content


def test_no_topic_guided_static_script_fallback() -> None:
    file_path = REPO_ROOT / "packages" / "clipturbo_core" / "src" / "clipturbo_core" / "local_providers.py"
    content = file_path.read_text(encoding="utf-8")

    banned_markers = (
        "_build_topic_guided_lines",
        "_normalize_topic_for_script",
        "topic_guided_v1",
    )
    for marker in banned_markers:
        assert marker not in content
