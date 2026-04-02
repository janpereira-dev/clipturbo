# Dominio Minimo

## Objetivo

Permitir a un usuario crear, revisar, exportar y publicar contenido corto con control editorial.

## Entidades iniciales

- `Workspace`
- `Project`
- `Template`
- `ContentIdea`
- `HookVariant`
- `ScriptVersion`
- `VoiceProfile`
- `Asset`
- `SubtitleTrack`
- `RenderJob`
- `VideoRender`
- `PublishTarget`
- `PublishJob`
- `PromptTrace`
- `ComplianceReview`
- `AuditLog`

## Campos clave por entidad

### `Project`

- `id`
- `workspace_id`
- `title`
- `locale`
- `status`
- `selected_format`
- `created_at`

### `ScriptVersion`

- `id`
- `project_id`
- `language`
- `tone`
- `hook_source`
- `script_text`
- `provider_name`
- `provider_model`

### `VoiceProfile`

- `id`
- `provider_name`
- `voice_key`
- `locale`
- `style`
- `gender_hint`
- `is_active`

### `PromptTrace`

- `id`
- `project_id`
- `stage`
- `provider_name`
- `provider_model`
- `prompt_hash`
- `input_snapshot`
- `output_snapshot`

### `AuditLog`

- `id`
- `project_id`
- `actor_type`
- `action`
- `target_type`
- `target_id`
- `metadata`
- `created_at`

## Localizacion prioritaria

- `es-ES`
- `es-MX`
- `es-AR`
- `es-VE`
- `es-neutral`

## Documento relacionado

Ver [docs/product/modelos-y-voces-espanol.md](modelos-y-voces-espanol.md).

## Regla

Mantener el dominio limpio y desacoplado de proveedores concretos.
