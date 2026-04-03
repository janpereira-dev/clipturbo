from __future__ import annotations

import importlib
import re
from dataclasses import dataclass
from typing import Protocol

from clipturbo_core.spanish_quality import SpanishOrthographyGuard


@dataclass(frozen=True)
class CorrectionResult:
    text: str
    engine: str
    model: str


class SpanishTextCorrector(Protocol):
    def correct(self, text: str) -> CorrectionResult: ...


class RuleBasedSpanishCorrector:
    def __init__(self, guard: SpanishOrthographyGuard | None = None) -> None:
        self._guard = guard or SpanishOrthographyGuard()

    def correct(self, text: str) -> CorrectionResult:
        corrected = self._guard.process(text)
        return CorrectionResult(
            text=corrected,
            engine="guard",
            model="spanish_orthography_guard_v1",
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
        self._generator: object | None = None

    @property
    def model_id(self) -> str:
        return self._model_id

    def correct(self, text: str) -> CorrectionResult:
        generator = self._get_generator()
        prompt = self._build_prompt(text)
        target_tokens = max(self._max_new_tokens, len(text.split()) * 3)
        output = generator(  # type: ignore[operator]
            prompt,
            max_new_tokens=target_tokens,
            do_sample=False,
        )
        generated = _extract_generated_text(output)
        cleaned = _cleanup_generated_text(generated)
        corrected = self._guard.process(cleaned)
        return CorrectionResult(
            text=corrected,
            engine="hf",
            model=self._model_id,
        )

    def _get_generator(self) -> object:
        if self._generator is not None:
            return self._generator
        try:
            transformers_module = importlib.import_module("transformers")
            pipeline_callable = getattr(transformers_module, "pipeline")
        except Exception as exc:
            raise RuntimeError(
                "No se pudo importar transformers para correccion HF. "
                "Instala dependencias: pip install transformers sentencepiece torch"
            ) from exc

        self._generator = pipeline_callable(
            task="text2text-generation",
            model=self._model_id,
            tokenizer=self._model_id,
            device=-1,
        )
        return self._generator

    @staticmethod
    def _build_prompt(text: str) -> str:
        return (
            "Corrige ortografia y gramatica del siguiente texto en espanol. "
            "Conserva significado, tono y longitud aproximada. "
            "Devuelve solo el texto corregido.\n\n"
            f"Texto:\n{text}"
        )


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
        self._fallback = fallback or RuleBasedSpanishCorrector()

    def correct(self, text: str) -> CorrectionResult:
        try:
            return self._primary.correct(text)
        except Exception:
            return self._fallback.correct(text)


def huggingface_correction_available() -> bool:
    try:
        importlib.import_module("transformers")
    except Exception:
        return False
    return True


def _extract_generated_text(output: object) -> str:
    if isinstance(output, list) and output:
        first_item = output[0]
        if isinstance(first_item, dict):
            maybe_text = first_item.get("generated_text")
            if isinstance(maybe_text, str):
                return maybe_text
    raise RuntimeError("Respuesta inesperada del corrector HF")


def _cleanup_generated_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(
        r"^(texto corregido|texto final|correccion)\s*:\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip()
