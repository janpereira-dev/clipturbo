from clipturbo_core.local_providers import RuleBasedSpanishLLMProvider
from clipturbo_core.spanish_quality import SpanishOrthographyGuard


def test_spanish_orthography_guard_corrects_common_errors() -> None:
    guard = SpanishOrthographyGuard()
    raw = "cada decision pequena define tu caracter y como respondes manana"
    corrected = guard.process(raw)

    assert "decisión" in corrected
    assert "pequeña" in corrected
    assert "carácter" in corrected
    assert "cómo respondes" in corrected
    assert "mañana" in corrected


def test_rule_based_provider_outputs_clean_spanish() -> None:
    provider = RuleBasedSpanishLLMProvider()
    script = provider.generate_text("Crea motivación estoica sobre hábitos")["script_text"]

    assert "caracter" not in script.lower()
    assert "reaccion" not in script.lower()
    assert "manana" not in script.lower()
    assert "enfocate" not in script.lower()
