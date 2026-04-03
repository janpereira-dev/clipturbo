from __future__ import annotations

import re
import unicodedata


class SpanishOrthographyGuard:
    """Corrects and validates common Spanish orthography issues for generated scripts."""

    _term_fixes: tuple[tuple[str, str], ...] = (
        ("caracter", "carácter"),
        ("reaccion", "reacción"),
        ("decision", "decisión"),
        ("pequena", "pequeña"),
        ("manana", "mañana"),
        ("dificil", "difícil"),
        ("aprobacion", "aprobación"),
        ("enfocate", "enfócate"),
        ("accion", "acción"),
        ("mas", "más"),
    )

    _phrase_fixes: tuple[tuple[str, str], ...] = (
        ("como respondes", "cómo respondes"),
        ("cada decision pequena", "cada decisión pequeña"),
        ("haz hoy lo dificil", "haz hoy lo difícil"),
        ("no busques aprobacion", "no busques aprobación"),
        ("respira, enfocate y actua", "respira, enfócate y actúa"),
        ("la disciplina de hoy es la libertad de manana", "la disciplina de hoy es la libertad de mañana"),
    )

    _forbidden_tokens: tuple[str, ...] = (
        "caracter",
        "reaccion",
        "decision",
        "pequena",
        "manana",
        "dificil",
        "aprobacion",
        "enfocate",
    )

    def process(self, text: str) -> str:
        corrected = self.correct(text)
        issues = self.validate(corrected)
        if issues:
            raise ValueError(f"Spanish orthography quality gate failed: {', '.join(issues)}")
        return corrected

    def correct(self, text: str) -> str:
        cleaned = unicodedata.normalize("NFC", text.strip())
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)

        for wrong, right in self._phrase_fixes:
            pattern = re.compile(re.escape(wrong), flags=re.IGNORECASE)
            cleaned = pattern.sub(right, cleaned)

        for wrong, right in self._term_fixes:
            pattern = re.compile(rf"\b{re.escape(wrong)}\b", flags=re.IGNORECASE)
            cleaned = pattern.sub(right, cleaned)

        if cleaned and cleaned[-1] not in ".!?":
            cleaned = f"{cleaned}."
        return cleaned

    def validate(self, text: str) -> list[str]:
        issues: list[str] = []
        lowered = text.lower()
        for token in self._forbidden_tokens:
            if re.search(rf"\b{re.escape(token)}\b", lowered):
                issues.append(f"contains '{token}'")
        if "  " in text:
            issues.append("contains double spaces")
        return issues
