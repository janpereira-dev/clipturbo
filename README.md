# ClipTurbo

ClipTurbo es una base inicial Python-first para construir una plataforma de creacion, adaptacion y programacion de videos cortos en espanol para YouTube, Instagram y TikTok. Este repositorio prioriza orquestacion de agentes, arquitectura, memoria operativa y una base tecnica sobria para evolucionar a SaaS sin empezar con complejidad innecesaria.

## Estado actual

Fase 1 implementada en este repo:
- gobierno para `Codex`, `Claude Code` y `GitHub Copilot`
- prompt maestro optimizado para bajo consumo de tokens
- subagentes especializados por dominio y control
- skills reutilizables con foco operativo
- manifiestos de arquitectura, tokens y comandos
- memoria dual: `docs/lessons/` y Engram
- esqueleto Python para `api`, `worker` y `core`

## Inventario

- agentes: 9
- skills: 8
- manifiestos: 5
- apps Python base: 2
- paquete compartido Python: 1

## Flujo de trabajo

1. Leer [AGENTS.md](/C:/Users/cowbo/Repositorios/clipturbo/AGENTS.md).
2. Consultar [manifests/clipturbo-context.md](/C:/Users/cowbo/Repositorios/clipturbo/manifests/clipturbo-context.md).
3. Revisar [tasks/todo.md](/C:/Users/cowbo/Repositorios/clipturbo/tasks/todo.md) y [tasks/lessons.md](/C:/Users/cowbo/Repositorios/clipturbo/tasks/lessons.md).
4. Elegir el subagente correcto.
5. Cargar solo la skill minima necesaria.
6. Ejecutar con validacion proporcional al riesgo.
7. Registrar decision o leccion en `docs/lessons/` y en Engram.

## Politica de tokens

- memoria primero, contexto despues
- un solo subagente por defecto
- abrir solo archivos criticos
- resumir antes de expandir
- reutilizar skills y manifiestos
- evitar repetir reglas largas en varios archivos

Ver [manifests/token-policy.md](/C:/Users/cowbo/Repositorios/clipturbo/manifests/token-policy.md).

## Memoria operativa

Toda decision relevante debe persistirse en dos capas:
- repo local: [docs/lessons/README.md](/C:/Users/cowbo/Repositorios/clipturbo/docs/lessons/README.md)
- memoria externa: Engram, basado en `https://github.com/Gentleman-Programming/engram`

## Estructura

```text
.
├─ agents/
├─ apps/
├─ copilot/
├─ docs/
├─ manifests/
├─ media/
├─ packages/
├─ public/
├─ tasks/
└─ tests/
```

## Compatibilidad de agentes

- `Codex`: [AGENTS.md](/C:/Users/cowbo/Repositorios/clipturbo/AGENTS.md)
- `Claude Code`: [CLAUDE.md](/C:/Users/cowbo/Repositorios/clipturbo/CLAUDE.md)
- `GitHub Copilot`: [.github/copilot-instructions.md](/C:/Users/cowbo/Repositorios/clipturbo/.github/copilot-instructions.md)

## Uso de modelos por rol

La estrategia de modelos esta separada del prompt maestro para no contaminar cada interaccion:
- [docs/prompts/model-routing.md](/C:/Users/cowbo/Repositorios/clipturbo/docs/prompts/model-routing.md)
- [copilot/model-routing.md](/C:/Users/cowbo/Repositorios/clipturbo/copilot/model-routing.md)

## Validacion minima

- `python -m pytest`
- `ruff check .`
- `mypy apps packages`

## Backlog inicial

1. Completar entidades y contratos del dominio.
2. Definir proveedores reales de LLM, TTS, storage y publicacion.
3. Añadir persistencia y cola de trabajos.
4. Implementar trazabilidad y cumplimiento Spain-first.
5. Expandir pipeline multimedia con FFmpeg.
