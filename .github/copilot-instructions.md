# GitHub Copilot Instructions

ClipTurbo es un producto nuevo y serio para crear, adaptar y programar videos cortos en espanol. No es un fork ni una copia de MoneyPrinter.

## Prioridades

- Python-first
- dominio antes que interfaz
- pipeline multimedia estable
- compliance y trazabilidad
- ahorro de tokens y contexto

## Reglas

- revisa primero `AGENTS.md`, `manifests/` y `tasks/`
- no inventes integraciones no verificadas
- no copies reglas largas en varios archivos
- usa providers por interfaz y adapters explicitos
- registra decisiones en `docs/lessons/` y Engram
- prefiere cambios pequenos, tipados y verificables

## Archivos clave

- `agents/`
- `agents/skills/`
- `manifests/`
- `docs/prompts/`
- `packages/clipturbo_core/`

## Salida esperada

- objetivo
- supuestos
- decision tecnica
- archivos afectados
- implementacion
- riesgos
- siguiente paso
