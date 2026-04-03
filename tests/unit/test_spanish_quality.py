import pytest

from clipturbo_core.spanish_quality import SpanishOrthographyGuard


def test_spanish_quality_guard_normalizes_spacing_and_punctuation() -> None:
    guard = SpanishOrthographyGuard()
    raw = "  Texto   con   espacios    y coma  , final "
    corrected = guard.process(raw)

    assert "  " not in corrected
    assert ", final." in corrected


def test_spanish_quality_guard_rejects_too_short_text() -> None:
    guard = SpanishOrthographyGuard()
    with pytest.raises(ValueError):
        guard.process("hola")


def test_spanish_quality_guard_rejects_template_tokens() -> None:
    guard = SpanishOrthographyGuard()
    with pytest.raises(ValueError):
        guard.process("Genera contenido para {topic} en espanol correcto")
