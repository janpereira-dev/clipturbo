# Arquitectura de Orquestacion

ClipTurbo separa gobierno, dominio y ejecucion.

## Capas

- `agents/`: instrucciones operativas y subagentes
- `manifests/`: reglas comunes que no deben repetirse
- `docs/`: decisiones, prompts y runbooks
- `apps/`: servicios ejecutables
- `packages/clipturbo_core/`: contratos y modelos compartidos

## Regla

El orquestador decide contexto minimo, no implementa todo desde un prompt monolitico.
