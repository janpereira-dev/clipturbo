# Contrato Inicial del Pipeline

## Objetivo

Fijar la forma minima del pipeline `guion -> voz -> subtitulos -> render` para evitar acoplamiento accidental entre pasos.

## Etapas base

1. `script_generation`
2. `voice_selection`
3. `audio_synthesis`
4. `subtitle_generation`
5. `asset_selection`
6. `video_render`
7. `review`
8. `publish_draft`

## Regla de independencia

Un cambio pequeño debe rehacer solo la etapa afectada y las dependencias directas:

- cambiar titulo: no rehace audio ni render
- cambiar voz: rehace audio, subtitulos sincronizados y render
- cambiar hook: rehace guion y etapas derivadas
- cambiar subtitulos de estilo: no rehace guion ni audio

## Entradas y salidas minimas

### `script_generation`

- entrada: `project_id`, `language`, `tone`, `idea`, `hook`
- salida: `script_id`, `script_text`, `provider_trace`

### `audio_synthesis`

- entrada: `script_id`, `voice_profile_id`
- salida: `audio_asset_id`, `duration_ms`, `provider_trace`

### `subtitle_generation`

- entrada: `script_id`, `audio_asset_id`, `language`
- salida: `subtitle_track_id`, `segments`, `provider_trace`

### `video_render`

- entrada: `audio_asset_id`, `subtitle_track_id`, `asset_bundle_id`, `render_format`
- salida: `render_id`, `video_asset_id`, `render_log`

## Trazabilidad minima

Cada etapa debe registrar:
- `job_id`
- `provider_name`
- `provider_model`
- `input_ref`
- `output_ref`
- `started_at`
- `finished_at`
- `status`
- `error_code` cuando aplique

## Formatos iniciales

- vertical `9:16` `1080x1920`
- horizontal `16:9` `1920x1080`

El foco inicial debe estar en vertical.
