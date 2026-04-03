from clipturbo_core.text_correction import (
    AutoSpanishCorrector,
    CorrectionResult,
    RuleBasedSpanishCorrector,
    _cleanup_generated_text,
)


class BrokenCorrector:
    def correct(self, text: str) -> CorrectionResult:
        raise RuntimeError("model unavailable")


def test_rule_based_corrector_returns_clean_spanish() -> None:
    corrector = RuleBasedSpanishCorrector()
    result = corrector.correct("cada decision pequena define tu caracter")

    assert result.engine == "guard"
    assert "decisión" in result.text
    assert "pequeña" in result.text
    assert "carácter" in result.text


def test_auto_corrector_falls_back_when_primary_fails() -> None:
    fallback = RuleBasedSpanishCorrector()
    corrector = AutoSpanishCorrector(
        model_id="jorgeortizfuentes/spanish-spellchecker-t5-base-wiki200000",
        primary=BrokenCorrector(),
        fallback=fallback,
    )
    result = corrector.correct("la disciplina de hoy es la libertad de manana")

    assert result.engine == "guard"
    assert "mañana" in result.text


def test_cleanup_generated_text_removes_instruction_artifacts() -> None:
    raw = (
        "Corrige ortografia y gramatica del siguiente texto en espanol. "
        "Conserva significado, tono y longitud aproximada. "
        "Devuelve solo el texto corregido. "
        "Texto: No esperes el momento perfecto."
    )
    cleaned = _cleanup_generated_text(raw)
    assert cleaned == "No esperes el momento perfecto."
