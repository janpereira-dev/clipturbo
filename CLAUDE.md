# CLAUDE

Usa este repositorio como sistema de orquestacion para ClipTurbo, no como demo ni como clon de un proyecto tercero.

## Reglas rapidas

- piensa en Python, dominio, pipeline y compliance antes que en UI
- usa [AGENTS.md](AGENTS.md) como indice principal
- consulta primero `docs/lessons/` y Engram antes de abrir mas contexto
- no repitas normas extensas si ya existen en `manifests/`
- documenta toda decision durable en `docs/lessons/` y en Engram
- valida cambios con tests, lint o evidencia tecnica proporcional al riesgo

## Flujo recomendado

1. leer [manifests/clipturbo-context.md](manifests/clipturbo-context.md)
2. leer [tasks/todo.md](tasks/todo.md)
3. elegir un agente en `agents/`
4. usar una sola skill en `agents/skills/` salvo necesidad clara
5. cerrar con evidencia concreta y siguiente paso

## Modelos por tipo de trabajo

Consulta [docs/prompts/model-routing.md](docs/prompts/model-routing.md).
