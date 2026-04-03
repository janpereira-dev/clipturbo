from clipturbo_core.text_correction import (
    AutoSpanishCorrector,
    CorrectionResult,
    RuleBasedSpanishCorrector,
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
