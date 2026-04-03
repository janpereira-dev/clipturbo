import pytest

from clipturbo_core.local_providers import (
    _build_topic_guided_lines,
    _clean_generated_script,
    _validate_generated_script,
)


def test_clean_generated_script_removes_prompt_echo() -> None:
    prompt = "Escribe un guion breve en espanol sobre motivacion estoica."
    raw = f"{prompt} Guion: Da un paso hoy y refuerza tu disciplina diaria."
    cleaned = _clean_generated_script(raw, prompt)

    assert "Escribe un guion" not in cleaned
    assert cleaned.startswith("Da un paso")


def test_validate_generated_script_rejects_meta_instructions() -> None:
    with pytest.raises(RuntimeError):
        _validate_generated_script(
            "Tema: motivacion estoica. Formato: 7 frases. Escribe un guion ahora.",
            "motivacion estoica",
        )


def test_validate_generated_script_rejects_sensitive_self_label_echo() -> None:
    with pytest.raises(RuntimeError):
        _validate_generated_script(
            "Soy un depresivo. Sigo igual cada dia y no hay salida.",
            "soy un depresivo",
        )


def test_topic_guided_lines_change_with_topic() -> None:
    lines_a = _build_topic_guided_lines("motivacion estoica")
    lines_b = _build_topic_guided_lines("soy un depresivo")

    assert lines_a != lines_b
    assert any("motivacion estoica" in line.lower() for line in lines_a)
    assert any("tristeza profunda" in line.lower() for line in lines_b)
