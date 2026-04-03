from clipturbo_core.domain import PublishPlatform
from clipturbo_core.providers import (
    GeneratedScript,
    GeneratedSubtitles,
    ProviderTrace,
    PublishResult,
    RenderedVideo,
    SynthesizedAudio,
)


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
    video: RenderedVideo = {
        "asset_path": "renders/out.mp4",
        "duration_ms": 12000,
        "trace": trace,
    }
    publish: PublishResult = {
        "external_post_id": "yt_123",
        "external_url": "https://youtube.com/shorts/abc",
        "trace": trace,
    }

    assert script["trace"]["provider_name"] == "openai"
    assert audio["duration_ms"] == 12000
    assert subtitles["segments"][0]["text"] == "Hola"
    assert video["asset_path"].endswith(".mp4")
    assert publish["external_post_id"].startswith("yt_")
    assert PublishPlatform.YOUTUBE_SHORTS.value == "youtube_shorts"
