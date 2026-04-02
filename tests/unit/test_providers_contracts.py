from clipturbo_core.providers import GeneratedScript, GeneratedSubtitles, ProviderTrace, SynthesizedAudio


def test_provider_contract_shapes_are_available() -> None:
    trace: ProviderTrace = {
        "provider_name": "openai",
        "provider_model": "gpt-4.1-mini",
        "request_id": "req_123",
    }
    script: GeneratedScript = {
        "script_text": "Texto de prueba",
        "trace": trace,
    }
    audio: SynthesizedAudio = {
        "asset_path": "audio/output.mp3",
        "duration_ms": 12000,
        "trace": trace,
    }
    subtitles: GeneratedSubtitles = {
        "format": "srt",
        "segments": [{"start_ms": 0, "end_ms": 1000, "text": "Hola"}],
        "trace": trace,
    }

    assert script["trace"]["provider_name"] == "openai"
    assert audio["duration_ms"] == 12000
    assert subtitles["segments"][0]["text"] == "Hola"
