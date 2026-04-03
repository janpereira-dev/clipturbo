from __future__ import annotations

import importlib
import re
from dataclasses import dataclass
from types import ModuleType
from typing import Protocol

from clipturbo_core.spanish_quality import SpanishOrthographyGuard


@dataclass(frozen=True)
class CorrectionResult:
    text: str
    engine: str
    model: str


class SpanishTextCorrector(Protocol):
    def correct(self, text: str) -> CorrectionResult: ...


class NoOpSpanishCorrector:
    def __init__(self, guard: SpanishOrthographyGuard | None = None) -> None:
        self._guard = guard or SpanishOrthographyGuard()

    def correct(self, text: str) -> CorrectionResult:
        corrected = self._guard.process(text)
        return CorrectionResult(
            text=corrected,
            engine="guard",
            model="spanish_quality_guard_v2",
        )


class HuggingFaceSpanishCorrector:
    def __init__(
        self,
        model_id: str,
        max_new_tokens: int = 256,
        guard: SpanishOrthographyGuard | None = None,
    ) -> None:
        self._model_id = model_id
        self._max_new_tokens = max_new_tokens
        self._guard = guard or SpanishOrthographyGuard()
        self._runtime: dict[str, object] | None = None

    @property
    def model_id(self) -> str:
        return self._model_id

    def correct(self, text: str) -> CorrectionResult:
        runtime = self._get_runtime()
        tokenizer = runtime["tokenizer"]
        model = runtime["model"]
        torch_module = runtime["torch_module"]
        mode = runtime["mode"]

        model_input = self._build_model_input(text)
        target_tokens = min(self._max_new_tokens, max(96, len(text.split()) * 4))

        encoded = tokenizer(  # type: ignore[operator]
            model_input,
            return_tensors="pt",
            truncation=True,
            max_length=1024,
        )
        with torch_module.no_grad():  # type: ignore[attr-defined]
            output_ids = model.generate(  # type: ignore[operator]
                **encoded,
                max_new_tokens=target_tokens,
                do_sample=False,
                num_beams=4 if mode == "seq2seq" else 1,
            )

        if mode == "causal":
            input_length = encoded["input_ids"].shape[1]
            output_ids = output_ids[:, input_length:]

        generated = tokenizer.decode(  # type: ignore[operator]
            output_ids[0],
            skip_special_tokens=True,
        )
        if not generated.strip():
            generated = text

        cleaned = _cleanup_generated_text(generated)
        corrected = self._guard.process(cleaned)
        return CorrectionResult(
            text=corrected,
            engine="hf",
            model=self._model_id,
        )

    def _get_runtime(self) -> dict[str, object]:
        if self._runtime is not None:
            return self._runtime
        transformers_module, torch_module = _load_transformers_runtime()
        auto_tokenizer = getattr(transformers_module, "AutoTokenizer")
        tokenizer = auto_tokenizer.from_pretrained(self._model_id)

        model: object
        mode: str
        try:
            auto_seq2seq = getattr(transformers_module, "AutoModelForSeq2SeqLM")
            model = auto_seq2seq.from_pretrained(self._model_id)
            mode = "seq2seq"
        except Exception:
            auto_causal = getattr(transformers_module, "AutoModelForCausalLM")
            model = auto_causal.from_pretrained(self._model_id)
            mode = "causal"

        model.eval()  # type: ignore[operator]
        self._runtime = {
            "tokenizer": tokenizer,
            "model": model,
            "torch_module": torch_module,
            "mode": mode,
        }
        return self._runtime

    @staticmethod
    def _build_model_input(text: str) -> str:
        # Los modelos spellchecker usados en ClipTurbo corrigen mejor
        # cuando reciben texto plano sin instrucciones.
        return text.strip()


def _load_transformers_runtime() -> tuple[ModuleType, ModuleType]:
    try:
        transformers_module = importlib.import_module("transformers")
        torch_module = importlib.import_module("torch")
    except Exception as exc:
        raise RuntimeError(
            "No se pudo importar transformers/torch para correccion HF. "
            "Instala dependencias: python -m pip install transformers sentencepiece torch"
        ) from exc
    return transformers_module, torch_module


class AutoSpanishCorrector:
    def __init__(
        self,
        model_id: str,
        max_new_tokens: int = 256,
        primary: SpanishTextCorrector | None = None,
        fallback: SpanishTextCorrector | None = None,
    ) -> None:
        self._primary = primary or HuggingFaceSpanishCorrector(
            model_id=model_id,
            max_new_tokens=max_new_tokens,
        )
        self._fallback = fallback or NoOpSpanishCorrector()

    def correct(self, text: str) -> CorrectionResult:
        try:
            return self._primary.correct(text)
        except Exception:
            return self._fallback.correct(text)


def huggingface_correction_available() -> bool:
    try:
        _load_transformers_runtime()
    except Exception:
        return False
    return True


def _cleanup_generated_text(text: str) -> str:
    cleaned = text.strip()
    # Limpia respuestas que incluyen instrucciones o encabezados.
    cleaned = re.sub(
        r"^(texto corregido|texto final|correccion)\s*:\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"^corrige ortografia y gramatica del siguiente texto en espanol\.?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"^conserva significado, tono y longitud aproximada\.?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"^devuelve solo el texto corregido\.?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"^texto:\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


# Backward compatibility alias. No lexicon corrections; only generic guard normalization.
RuleBasedSpanishCorrector = NoOpSpanishCorrector
