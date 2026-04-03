import pytest

from clipturbo_core.local_providers import (
    HuggingFaceSpanishLLMProvider,
    _build_subtitle_filter_chain,
    _clean_generated_script,
    _escape_ffmpeg_filter_value,
    _soft_recover_script,
    _validate_generated_script,
)
from clipturbo_core.text_correction import CorrectionResult


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


def test_subtitle_filter_chain_has_no_hardcoded_title_text() -> None:
    filter_chain = _build_subtitle_filter_chain("tmp/demo.srt")
    assert "Motivacion Estoica" not in filter_chain
    assert "ClipTurbo" not in filter_chain


def test_subtitle_filter_chain_escapes_problematic_path_characters() -> None:
    raw_path = r"C:\media files\demo's:v1.srt"
    escaped = _escape_ffmpeg_filter_value(raw_path)
    filter_chain = _build_subtitle_filter_chain(raw_path)

    assert "\\\\" in escaped
    assert "\\:" in escaped
    assert "\\'" in escaped
    assert f"subtitles='{escaped}':" in filter_chain


def test_hf_provider_uses_user_prompt_as_primary_input(monkeypatch: pytest.MonkeyPatch) -> None:
    class EchoCorrector:
        def correct(self, text: str) -> CorrectionResult:
            return CorrectionResult(text=text, engine="guard", model="test")

    provider = HuggingFaceSpanishLLMProvider(
        model_id="test-model",
        text_corrector=EchoCorrector(),
        allow_fallback=False,
    )
    captured: dict[str, str] = {}

    def fake_generate_validated_script(model_prompt: str, topic: str) -> tuple[str, bool]:
        captured["model_prompt"] = model_prompt
        captured["topic"] = topic
        return ("Texto de salida suficientemente largo para validar el flujo sin runtime real.", False)

    monkeypatch.setattr(provider, "_generate_validated_script", fake_generate_validated_script)
    prompt = "Crea un guion corto en espanol (es-ES) con registro cercano sobre motivacion estoica."
    result = provider.generate_text(prompt)

    assert captured["model_prompt"] == prompt
    assert result["script_text"].startswith("Texto de salida")
