import pytest

from clipturbo_core.local_providers import (
    _clean_generated_script,
    _soft_recover_script,
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


def test_clean_generated_script_removes_markdown_heading_noise() -> None:
    prompt = "Genera un guion corto."
    raw = (
        "Guion Final** --- Este guion es para guiar al lector: "
        "### En cada esfuerzo hay oportunidades para crecer."
    )
    cleaned = _clean_generated_script(raw, prompt)
    assert "Guion Final" not in cleaned
    assert "###" not in cleaned


def test_soft_recover_script_removes_numbered_artifacts() -> None:
    raw = "2\n### **Planifique** tus acciones\n3\n### **Aplica** tus habilidades"
    recovered = _soft_recover_script(raw, "determinacion")
    assert "###" not in recovered
    assert "\n2\n" not in recovered
