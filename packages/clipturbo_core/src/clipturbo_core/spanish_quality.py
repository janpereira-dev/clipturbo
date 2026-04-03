from __future__ import annotations

import re
import unicodedata


class SpanishOrthographyGuard:
    """
    Guardrail liviano sin diccionarios quemados.

    Regla: no corrige vocabulario por tablas estáticas; solo normaliza formato
    y valida que la salida sea apta para pasar a modelos o render.
    """

    def process(self, text: str) -> str:
        normalized = self.correct(text)
        issues = self.validate(normalized)
        if issues:
            raise ValueError(f"Spanish quality gate failed: {', '.join(issues)}")
        return normalized

    def correct(self, text: str) -> str:
        cleaned = unicodedata.normalize("NFC", text.strip())
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
        if cleaned and cleaned[-1] not in ".!?":
            cleaned = f"{cleaned}."
        return cleaned

    def validate(self, text: str) -> list[str]:
        issues: list[str] = []
        if len(text.split()) < 4:
            issues.append("too_short")
        if "  " in text:
            issues.append("double_spaces")
        if re.search(r"[{}<>]", text):
            issues.append("template_tokens_detected")
        if re.search(r"(.)\1{4,}", text):
            issues.append("repeated_characters")
        if re.search(r"[^\S\r\n]{2,}", text):
            issues.append("irregular_spacing")
        return issues
