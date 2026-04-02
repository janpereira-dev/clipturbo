from typing import Protocol, TypedDict


class ProviderTrace(TypedDict):
    provider_name: str
    provider_model: str
    request_id: str


class GeneratedScript(TypedDict):
    script_text: str
    trace: ProviderTrace


class SynthesizedAudio(TypedDict):
    asset_path: str
    duration_ms: int
    trace: ProviderTrace


class SubtitleSegment(TypedDict):
    start_ms: int
    end_ms: int
    text: str


class GeneratedSubtitles(TypedDict):
    format: str
    segments: list[SubtitleSegment]
    trace: ProviderTrace


class LLMProvider(Protocol):
    def generate_text(self, prompt: str) -> GeneratedScript: ...


class TTSProvider(Protocol):
    def synthesize(self, script: str, voice_id: str) -> SynthesizedAudio: ...


class STTProvider(Protocol):
    def transcribe(self, asset_path: str) -> str: ...


class AssetProvider(Protocol):
    def resolve(self, query: str) -> list[str]: ...


class SubtitleProvider(Protocol):
    def generate(self, script: str, audio_path: str) -> GeneratedSubtitles: ...


class ThumbnailProvider(Protocol):
    def render(self, title: str) -> str: ...


class PublisherProvider(Protocol):
    def publish_draft(self, asset_path: str, metadata: dict[str, str]) -> str: ...


class StorageProvider(Protocol):
    def put(self, key: str, source_path: str) -> str: ...
