# Model Routing

## Objetivo

Usar el modelo correcto segun riesgo, no el mas grande por defecto.

## Recomendacion base

- `orquestador-clipturbo`: modelo fuerte para planificacion y decisiones de arquitectura
- `subagente-dominio-producto`: modelo fuerte o medio con buen razonamiento
- `subagente-backend-python`: modelo fuerte para refactors, medio para CRUD y contratos
- `subagente-pipeline-media`: modelo fuerte para FFmpeg, jobs y pipelines
- `subagente-publicacion-compliance`: modelo fuerte para cumplimiento y auditoria
- `subagente-observabilidad-calidad`: modelo medio para pruebas, fuerte para fallos complejos
- agentes de revision y formato: modelo medio o pequeno

## Regla

Subir de modelo solo si:
- hay riesgo alto
- hay ambiguedad real
- el cambio toca arquitectura o compliance

## Compatibilidad

- Codex: usa `AGENTS.md` y `agents/`
- Claude Code: usa `CLAUDE.md` y `agents/`
- GitHub Copilot: usa `.github/copilot-instructions.md` y `copilot/`
