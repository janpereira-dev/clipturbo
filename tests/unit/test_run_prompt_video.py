from __future__ import annotations

import importlib.util
from pathlib import Path

from clipturbo_core.domain import VoiceProvider


def _load_runner_module():
    module_path = Path(__file__).resolve().parents[2] / "apps" / "worker-media" / "worker" / "run_prompt_video.py"
    spec = importlib.util.spec_from_file_location("run_prompt_video_module", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar run_prompt_video.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_auto_tts_fallback_respects_voice_override_when_edge_missing(tmp_path, monkeypatch) -> None:
    module = _load_runner_module()
    monkeypatch.setattr(module, "edge_tts_available", lambda: False)

    _, provider, voice_name = module._build_tts_provider(
        engine="auto",
        voice="Microsoft Helena",
        audio_dir=tmp_path / "audio",
        fluido_default="es-ES-AlvaroNeural",
        loquendo_default="Microsoft Laura",
    )

    assert provider == VoiceProvider.WINDOWS_SPEECH
    assert voice_name == "Microsoft Helena"
