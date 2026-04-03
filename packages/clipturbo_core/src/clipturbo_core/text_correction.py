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
        fallback_model_ids: list[str] | None = None,
    ) -> None:
        self._model_id = model_id
        self._fallback_model_ids = fallback_model_ids or []
        self._max_new_tokens = max_new_tokens
        self._guard = guard or SpanishOrthographyGuard()
        self._runtime: dict[str, object] | None = None
        self._active_model_id = model_id

    @property
    def model_id(self) -> str:
        return self._active_model_id

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
        if _looks_like_instructional_output(cleaned):
            cleaned = text.strip()
        corrected = self._guard.process(cleaned)
        return CorrectionResult(
            text=corrected,
            engine="hf",
            model=self.model_id,
        )

    def _get_runtime(self) -> dict[str, object]:
        if self._runtime is not None:
            return self._runtime
        errors: list[Exception] = []
        for candidate_model in self._candidate_model_ids():
            try:
                runtime = self._load_runtime_for_model(candidate_model)
                self._active_model_id = candidate_model
                self._runtime = runtime
                return runtime
            except Exception as exc:
                errors.append(exc)
                continue
        if errors and any(_is_model_access_error(err) for err in errors):
            raise RuntimeError(_build_hf_model_access_message(self._candidate_model_ids())) from errors[-1]
        last_error = errors[-1] if errors else RuntimeError("runtime no disponible")
        raise RuntimeError("No fue posible cargar ningun modelo HF para correccion de texto.") from last_error

    def _load_runtime_for_model(self, model_id: str) -> dict[str, object]:
        transformers_module, torch_module = _load_transformers_runtime()
        auto_tokenizer = getattr(transformers_module, "AutoTokenizer")
        tokenizer = auto_tokenizer.from_pretrained(model_id)

        model: object
        mode: str
        try:
            auto_seq2seq = getattr(transformers_module, "AutoModelForSeq2SeqLM")
            model = auto_seq2seq.from_pretrained(model_id)
            mode = "seq2seq"
        except Exception:
            auto_causal = getattr(transformers_module, "AutoModelForCausalLM")
            model = auto_causal.from_pretrained(model_id)
            mode = "causal"

        model.eval()  # type: ignore[operator]
        return {
            "tokenizer": tokenizer,
            "model": model,
            "torch_module": torch_module,
            "mode": mode,
        }

    def _candidate_model_ids(self) -> list[str]:
        candidates = [self._model_id, *self._fallback_model_ids]
        unique: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            model_id = candidate.strip()
            if not model_id or model_id in seen:
                continue
            seen.add(model_id)
            unique.append(model_id)
        return unique

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


def _is_model_access_error(error: Exception) -> bool:
    text = str(error).lower()
    patterns = (
        "gated repo",
        "cannot access gated repo",
        "401",
        "unauthorized",
        "make sure to have access",
    )
    return any(pattern in text for pattern in patterns)


def _build_hf_model_access_message(candidate_model_ids: list[str]) -> str:
    candidates = ", ".join(candidate_model_ids)
    return (
        "No se pudo acceder a modelos HF para correccion (repo gated o credenciales faltantes). "
        f"Modelos intentados: {candidates}. "
        "Usa modelos abiertos en `manifests/model-routing.json` o autentica con `huggingface-cli login`."
    )


class AutoSpanishCorrector:
    def __init__(
        self,
        model_id: str,
        max_new_tokens: int = 256,
        fallback_model_ids: list[str] | None = None,
        primary: SpanishTextCorrector | None = None,
        fallback: SpanishTextCorrector | None = None,
    ) -> None:
        self._primary = primary or HuggingFaceSpanishCorrector(
            model_id=model_id,
            max_new_tokens=max_new_tokens,
            fallback_model_ids=fallback_model_ids,
        )
        self._fallback = fallback or NoOpSpanishCorrector()

    def correct(self, text: str) -> CorrectionResult:
        try:
            return self._primary.correct(text)
        except Exception as exc:
            if not _is_expected_correction_failure(exc):
                raise
            return self._fallback.correct(text)


def huggingface_correction_available() -> bool:
    try:
        _load_transformers_runtime()
    except Exception:
        return False
    return True


def _is_expected_correction_failure(error: Exception) -> bool:
    if isinstance(error, (RuntimeError, OSError, ImportError)):
        return True
    return _is_model_access_error(error)


def _cleanup_generated_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(
        r"\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"(?m)^\s*\d+\s*$", " ", cleaned)

    # Limpia respuestas que incluyen instrucciones o encabezados.
    instruction_patterns = (
        r"\b(texto corregido|texto final|correccion)\s*:\s*",
        r"\bcorrige ortografia y gramatica del siguiente texto en espanol\.?\s*",
        r"\bconserva significado,\s*tono y longitud aproximada\.?\s*",
        r"\bdevuelve solo el texto corregido\.?\s*",
        r"\btexto\s*:\s*",
    )
    for pattern in instruction_patterns:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"[#*_`]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _looks_like_instructional_output(text: str) -> bool:
    if not text:
        return True
    lowered = text.lower()
    markers = (
        "corrige ortografia",
        "conserva significado",
        "devuelve solo",
        "texto corregido",
        "texto final",
    )
    hits = sum(1 for marker in markers if marker in lowered)
    return hits >= 2


# Backward compatibility alias. No lexicon corrections; only generic guard normalization.
RuleBasedSpanishCorrector = NoOpSpanishCorrector
