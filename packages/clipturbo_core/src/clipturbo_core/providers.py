from typing import Protocol


class LLMProvider(Protocol):
    def generate_text(self, prompt: str) -> str: ...


class TTSProvider(Protocol):
    def synthesize(self, script: str, voice_id: str) -> str: ...


class STTProvider(Protocol):
    def transcribe(self, asset_path: str) -> str: ...


class AssetProvider(Protocol):
    def resolve(self, query: str) -> list[str]: ...


class SubtitleProvider(Protocol):
    def generate(self, script: str, audio_path: str) -> str: ...


class ThumbnailProvider(Protocol):
    def render(self, title: str) -> str: ...


class PublisherProvider(Protocol):
    def publish_draft(self, asset_path: str, metadata: dict[str, str]) -> str: ...


class StorageProvider(Protocol):
    def put(self, key: str, source_path: str) -> str: ...
