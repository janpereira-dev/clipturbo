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
    result = corrector.correct("texto   con  espacios   de  prueba")

    assert result.engine == "guard"
    assert "  " not in result.text


def test_auto_corrector_falls_back_when_primary_fails() -> None:
    fallback = RuleBasedSpanishCorrector()
    corrector = AutoSpanishCorrector(
        model_id="jorgeortizfuentes/spanish-spellchecker-t5-base-wiki200000",
        primary=BrokenCorrector(),
        fallback=fallback,
    )
    result = corrector.correct("texto  de fallback para validacion")

    assert result.engine == "guard"
    assert "  " not in result.text


def test_cleanup_generated_text_removes_instruction_artifacts() -> None:
    raw = (
        "Corrige ortografia y gramatica del siguiente texto en espanol. "
        "Conserva significado, tono y longitud aproximada. "
        "Devuelve solo el texto corregido. "
        "Texto: No esperes el momento perfecto."
    )
    cleaned = _cleanup_generated_text(raw)
    assert cleaned == "No esperes el momento perfecto."


def test_cleanup_generated_text_removes_srt_like_instruction_noise() -> None:
    raw = (
        "1\n00:00:00,000 --> 00:00:04,000\n"
        "Corrige ortografia y gramatica del siguiente texto en espanol\n"
        "2\n00:00:04,000 --> 00:00:08,000\n"
        "Conserva significado, tono y longitud aproximada\n"
        "3\n00:00:08,000 --> 00:00:12,000\n"
        "Devuelve solo el texto corregido\n"
        "4\n00:00:12,000 --> 00:00:16,000\n"
        "Texto: Respira, enfocate y da el siguiente paso."
    )
    cleaned = _cleanup_generated_text(raw)
    assert cleaned == "Respira, enfocate y da el siguiente paso."
