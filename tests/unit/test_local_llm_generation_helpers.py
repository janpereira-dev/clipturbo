import pytest

from clipturbo_core.local_providers import (
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


def test_validate_generated_script_rejects_too_short_output() -> None:
    with pytest.raises(RuntimeError):
        _validate_generated_script("Texto corto.", "motivacion estoica")


def test_validate_generated_script_rejects_screenplay_format() -> None:
    with pytest.raises(RuntimeError):
        _validate_generated_script(
            "[Background music] INT. STREET NIGHT. Texto con formato de escena no editorial.",
            "motivacion estoica",
        )
