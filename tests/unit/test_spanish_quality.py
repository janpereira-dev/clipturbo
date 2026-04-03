from clipturbo_core.local_providers import RuleBasedSpanishLLMProvider
from clipturbo_core.spanish_quality import SpanishOrthographyGuard
from clipturbo_core.text_correction import CorrectionResult


class StubCorrector:
    def correct(self, text: str) -> CorrectionResult:
        return CorrectionResult(
            text="Texto corregido y limpio.",
            engine="hf",
            model="stub-model",
        )


def test_spanish_orthography_guard_corrects_common_errors() -> None:
    guard = SpanishOrthographyGuard()
    raw = "cada decision pequea define tu caracter y como respondes maana en una sensacion sin senal ni seal"
    corrected = guard.process(raw)

    assert "decisión" in corrected
    assert "pequeña" in corrected
    assert "carácter" in corrected
    assert "cómo respondes" in corrected
    assert "mañana" in corrected
    assert "sensación" in corrected
    assert "señal" in corrected


def test_spanish_orthography_guard_corrects_model_artifacts() -> None:
    guard = SpanishOrthographyGuard()
    raw = "Dominaras tu da. Cada decisión pequea construye tu identidad."
    corrected = guard.process(raw)

    assert "dominarás tu día." in corrected.lower()
    assert "pequeña" in corrected


def test_rule_based_provider_outputs_clean_spanish() -> None:
    provider = RuleBasedSpanishLLMProvider()
    script = provider.generate_text("Crea motivación estoica sobre hábitos")["script_text"]

    assert "caracter" not in script.lower()
    assert "reaccion" not in script.lower()
    assert "manana" not in script.lower()
    assert "enfocate" not in script.lower()


def test_rule_based_provider_reports_correction_source() -> None:
    provider = RuleBasedSpanishLLMProvider(text_corrector=StubCorrector())
    result = provider.generate_text("Crea motivación estoica sobre hábitos")

    assert result["script_text"] == "Texto corregido y limpio."
    assert provider.last_correction_engine == "hf"
    assert provider.last_correction_model == "stub-model"
    assert "correction:hf:stub-model" in result["trace"]["provider_model"]


def test_rule_based_provider_generates_topic_specific_script() -> None:
    provider = RuleBasedSpanishLLMProvider()
    script_a = provider.generate_text("Crea un guion sobre motivacion estoica")["script_text"]
    script_b = provider.generate_text("Crea un guion sobre soy un depresivo")["script_text"]

    assert script_a != script_b
    assert "motivación estoica" in script_a.lower() or "motivacion estoica" in script_a.lower()
    assert "tristeza profunda" in script_b.lower()
