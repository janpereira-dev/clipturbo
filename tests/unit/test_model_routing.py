from pathlib import Path

from clipturbo_core.domain import Locale
from clipturbo_core.model_routing import (
    list_registers_for_locale,
    load_model_routing_manifest,
    resolve_dialect_route,
)


def _manifest_path() -> Path:
    return Path(__file__).resolve().parents[2] / "manifests" / "model-routing.json"


def test_model_routing_manifest_contains_requested_locales() -> None:
    manifest = load_model_routing_manifest(_manifest_path())

    assert Locale.ES_ES in manifest.routes
    assert Locale.ES_VE in manifest.routes
    assert Locale.ES_CO in manifest.routes
    assert Locale.ES_EC in manifest.routes
    assert Locale.ES_PR in manifest.routes


def test_resolve_route_returns_country_specific_models() -> None:
    manifest = load_model_routing_manifest(_manifest_path())
    route = resolve_dialect_route(manifest, locale=Locale.ES_CO, register="profesional")

    assert route.register_id == "profesional"
    assert route.script_model == "meta-llama/Llama-3.2-3B-Instruct"
    assert route.correction_model == "jorgeortizfuentes/spanish-spellchecker-mt5-large_3e"


def test_resolve_route_falls_back_to_neutral_register() -> None:
    manifest = load_model_routing_manifest(_manifest_path())
    route = resolve_dialect_route(manifest, locale=Locale.ES_EC, register="no-existe")

    assert route.register_id == "neutral"
    assert route.script_model == "Qwen/Qwen2.5-0.5B-Instruct"


def test_resolve_route_falls_back_to_default_locale_when_missing() -> None:
    manifest = load_model_routing_manifest(_manifest_path())
    route = resolve_dialect_route(manifest, locale=Locale.ES_MX, register="cercano")

    assert route.register_id == "cercano"
    assert route.script_model == "google/gemma-3-4b-it"


def test_list_registers_uses_default_locale_when_locale_missing() -> None:
    manifest = load_model_routing_manifest(_manifest_path())
    registers = list_registers_for_locale(manifest, Locale.ES_MX)

    assert registers == ["cercano", "neutral", "profesional"]
