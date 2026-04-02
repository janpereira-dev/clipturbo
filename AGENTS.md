# AGENTS

## Proposito

Gobernar ClipTurbo con enfoque Python-first, bajo consumo de tokens, trazabilidad y validacion real antes de cerrar tareas.

## Prioridades

1. coherencia de producto
2. dominio y backend Python
3. pipeline multimedia estable
4. compliance y trazabilidad
5. uso eficiente de contexto

## Regla de memoria primero

Antes de abrir contexto nuevo:
1. revisar [manifests/clipturbo-context.md](/C:/Users/cowbo/Repositorios/clipturbo/manifests/clipturbo-context.md)
2. revisar [tasks/todo.md](/C:/Users/cowbo/Repositorios/clipturbo/tasks/todo.md)
3. revisar [tasks/lessons.md](/C:/Users/cowbo/Repositorios/clipturbo/tasks/lessons.md)
4. leer la leccion repo-local aplicable en `docs/lessons/`
5. consultar Engram para decisiones previas

## Agentes disponibles

- [agents/orquestador-clipturbo.md](/C:/Users/cowbo/Repositorios/clipturbo/agents/orquestador-clipturbo.md): coordinacion general
- [agents/subagente-dominio-producto.md](/C:/Users/cowbo/Repositorios/clipturbo/agents/subagente-dominio-producto.md): alcance, dominio y producto
- [agents/subagente-backend-python.md](/C:/Users/cowbo/Repositorios/clipturbo/agents/subagente-backend-python.md): FastAPI, contratos y persistencia
- [agents/subagente-pipeline-media.md](/C:/Users/cowbo/Repositorios/clipturbo/agents/subagente-pipeline-media.md): FFmpeg, TTS, subtitulos y render
- [agents/subagente-publicacion-compliance.md](/C:/Users/cowbo/Repositorios/clipturbo/agents/subagente-publicacion-compliance.md): publicacion, auditoria y cumplimiento
- [agents/subagente-observabilidad-calidad.md](/C:/Users/cowbo/Repositorios/clipturbo/agents/subagente-observabilidad-calidad.md): tests, lint, typing y runbooks
- [agents/subagente-revision-codigo.md](/C:/Users/cowbo/Repositorios/clipturbo/agents/subagente-revision-codigo.md): revision tecnica
- [agents/subagente-revision-procesos.md](/C:/Users/cowbo/Repositorios/clipturbo/agents/subagente-revision-procesos.md): revision de flujo y operacion
- [agents/subagente-orquestador-documentacion.md](/C:/Users/cowbo/Repositorios/clipturbo/agents/subagente-orquestador-documentacion.md): consistencia documental
- [agents/subagente-guardarrailes-formato.md](/C:/Users/cowbo/Repositorios/clipturbo/agents/subagente-guardarrailes-formato.md): formato, tono y plantillas

## Cuando usar cada uno

- usa un solo subagente salvo trabajo realmente cruzado
- prioriza `subagente-backend-python` para cambios tecnicos
- usa `subagente-dominio-producto` para alcance, entidades y roadmap
- usa `subagente-pipeline-media` para audio, video o jobs
- usa `subagente-publicacion-compliance` para canales, retencion o auditoria
- usa `subagente-observabilidad-calidad` para validacion o endurecimiento
- usa los agentes de revision solo para control, no como via primaria de implementacion

## Reglas obligatorias

- Python-first
- no frontend-first
- no copiar codigo de MoneyPrinter
- draft by default
- human review first
- providers desacoplados por interfaz
- validacion proporcional al riesgo
- no mezclar dominios no relacionados en la misma tarea

## Tokens

Aplicar [manifests/token-policy.md](/C:/Users/cowbo/Repositorios/clipturbo/manifests/token-policy.md) y cargar solo la skill minima necesaria desde `agents/skills/`.
