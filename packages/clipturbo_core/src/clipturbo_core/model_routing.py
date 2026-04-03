from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from clipturbo_core.domain import Locale

TtsEngine = Literal["auto", "fluido", "loquendo"]


def _normalize_register(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError("register cannot be empty")
    return normalized


class DialectRoute(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    register_id: str = Field(default="neutral", alias="register", min_length=2, max_length=32)
    script_model: str = Field(min_length=3, max_length=200)
    correction_model: str = Field(min_length=3, max_length=200)
    tts_engine: TtsEngine = "auto"
    fluido_voice: str = Field(default="es-ES-AlvaroNeural", min_length=2, max_length=120)
    loquendo_voice: str = Field(default="Microsoft Laura", min_length=2, max_length=120)

    @field_validator("register_id")
    @classmethod
    def _clean_register(cls, value: str) -> str:
        return _normalize_register(value)


class ModelRoutingManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(default="1.0", min_length=1, max_length=20)
    default_locale: Locale = Locale.ES_ES
    default_register: str = Field(default="neutral", min_length=2, max_length=32)
    routes: dict[Locale, dict[str, DialectRoute]] = Field(default_factory=dict)

    @field_validator("default_register")
    @classmethod
    def _clean_default_register(cls, value: str) -> str:
        return _normalize_register(value)

    @model_validator(mode="after")
    def _normalize_routes(self) -> ModelRoutingManifest:
        normalized_routes: dict[Locale, dict[str, DialectRoute]] = {}
        for locale, per_register in self.routes.items():
            normalized_per_register: dict[str, DialectRoute] = {}
            for register, route in per_register.items():
                normalized_register = _normalize_register(register)
                normalized_per_register[normalized_register] = route.model_copy(
                    update={"register_id": normalized_register}
                )
            normalized_routes[locale] = normalized_per_register
        self.routes = normalized_routes

        default_routes = self.routes.get(self.default_locale, {})
        if self.default_register not in default_routes:
            raise ValueError(
                "default_register must exist for default_locale in model routing manifest"
            )
        return self


def load_model_routing_manifest(path: str | Path) -> ModelRoutingManifest:
    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    return ModelRoutingManifest.model_validate(payload)


def resolve_dialect_route(
    manifest: ModelRoutingManifest,
    locale: Locale,
    register: str,
) -> DialectRoute:
    normalized_register = _normalize_register(register or manifest.default_register)
    locale_routes = manifest.routes.get(locale, {})

    if normalized_register in locale_routes:
        return locale_routes[normalized_register]
    if manifest.default_register in locale_routes:
        return locale_routes[manifest.default_register]

    default_locale_routes = manifest.routes.get(manifest.default_locale, {})
    if normalized_register in default_locale_routes:
        return default_locale_routes[normalized_register]
    if manifest.default_register in default_locale_routes:
        return default_locale_routes[manifest.default_register]

    raise ValueError("model routing manifest has no resolvable route for locale/register")


def list_registers_for_locale(manifest: ModelRoutingManifest, locale: Locale) -> list[str]:
    locale_routes = manifest.routes.get(locale)
    if locale_routes:
        return sorted(locale_routes.keys())
    default_routes = manifest.routes.get(manifest.default_locale, {})
    return sorted(default_routes.keys())
