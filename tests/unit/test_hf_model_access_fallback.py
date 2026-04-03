import pytest

from clipturbo_core.local_providers import HuggingFaceSpanishLLMProvider
from clipturbo_core.text_correction import HuggingFaceSpanishCorrector


def test_llm_provider_uses_fallback_model_when_primary_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = HuggingFaceSpanishLLMProvider(
        model_id="modelo-primario",
        fallback_model_ids=["modelo-fallback"],
    )

    calls: list[str] = []

    def fake_load_runtime(model_id: str) -> dict[str, object]:
        calls.append(model_id)
        if model_id == "modelo-primario":
            raise RuntimeError("401 Unauthorized - gated repo")
        return {"tokenizer": object(), "model": object(), "torch_module": object(), "mode": "causal"}

    monkeypatch.setattr(provider, "_load_runtime_for_model", fake_load_runtime)
    runtime = provider._get_runtime()

    assert provider.active_model_id == "modelo-fallback"
    assert calls == ["modelo-primario", "modelo-fallback"]
    assert runtime["mode"] == "causal"


def test_llm_provider_raises_actionable_error_when_all_models_are_gated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = HuggingFaceSpanishLLMProvider(
        model_id="modelo-primario",
        fallback_model_ids=["modelo-fallback"],
    )

    def fake_load_runtime(model_id: str) -> dict[str, object]:
        raise RuntimeError(f"Cannot access gated repo for {model_id}. 401 Unauthorized")

    monkeypatch.setattr(provider, "_load_runtime_for_model", fake_load_runtime)

    with pytest.raises(RuntimeError, match="Modelos intentados"):
        provider._get_runtime()


def test_corrector_uses_fallback_model_when_primary_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    corrector = HuggingFaceSpanishCorrector(
        model_id="modelo-primario",
        fallback_model_ids=["modelo-fallback"],
    )

    calls: list[str] = []

    def fake_load_runtime(model_id: str) -> dict[str, object]:
        calls.append(model_id)
        if model_id == "modelo-primario":
            raise RuntimeError("gated repo 401")
        return {"tokenizer": object(), "model": object(), "torch_module": object(), "mode": "seq2seq"}

    monkeypatch.setattr(corrector, "_load_runtime_for_model", fake_load_runtime)
    runtime = corrector._get_runtime()

    assert corrector.model_id == "modelo-fallback"
    assert calls == ["modelo-primario", "modelo-fallback"]
    assert runtime["mode"] == "seq2seq"
