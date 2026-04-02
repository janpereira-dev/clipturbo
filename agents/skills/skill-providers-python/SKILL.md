# skill-providers-python

## Interfaces minimas

- `LLMProvider`
- `TTSProvider`
- `STTProvider`
- `AssetProvider`
- `SubtitleProvider`
- `ThumbnailProvider`
- `PublisherProvider`
- `StorageProvider`

## Regla

El core no depende de SDKs concretos. Cada proveedor entra por adapter.
