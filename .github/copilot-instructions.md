# GitHub Copilot Instructions (ClipTurbo)

Estas instrucciones son obligatorias para todo aporte de codigo, documentacion o review en este repositorio.

## 1) Contexto del producto

- ClipTurbo es un producto nuevo para crear, adaptar, renderizar y publicar video corto en espanol.
- Foco operativo: Python-first, backend + dominio + pipeline media + compliance.
- No frontend-first.
- No usar narrativa de dinero facil, growth magico o automatizacion sin supervision.
- Publicacion siempre en borrador por defecto (`draft by default`) y con posibilidad de revision humana.

## 2) Regla de memoria primero

Antes de proponer cambios o revisar codigo:

1. Leer `AGENTS.md`.
2. Leer `manifests/clipturbo-context.md`.
3. Leer `manifests/architecture-rules.md`.
4. Leer `manifests/token-policy.md`.
5. Leer `tasks/todo.md` y `tasks/lessons.md`.
6. Revisar lecciones aplicables en `docs/lessons/`.
7. Consultar Engram para no repetir errores ya resueltos.

No repetir investigacion ya documentada.

## 3) Prioridades tecnicas

Orden de prioridad:

1. Coherencia de dominio.
2. Correctitud funcional.
3. Trazabilidad y compliance.
4. Estabilidad operativa del pipeline.
5. Claridad de codigo y mantenibilidad.
6. Performance razonable.
7. Estilo/estetica.

## 4) Reglas de arquitectura (no negociables)

- Python-first.
- Dominio separado de infraestructura.
- Providers por interfaz + adapters explicitos.
- No acoplar el core a un proveedor unico.
- Diseñar para evolucion SaaS futura, sin meter multi-tenant completo en fase inicial.
- Evitar dependencias opacas y “magia” no trazable.
- Errores de pipeline deben terminar en estado terminal correcto (`failed` o `completed`).
- Idempotencia y reintentos donde aplique.

## 5) Reglas de contenido y modelos

- Nada editorial quemado en codigo.
- No hardcodear guiones, hooks, copies, temas, dialectos, listas de vocabulario o “frases de ejemplo” como logica productiva.
- El contenido debe generarse en runtime desde `topic` + contexto + modelo.
- Si falta informacion, completar con modelo o heuristica explicita, nunca con texto fijo oculto.
- Todo fallback debe ser visible y trazable.
- Evitar modelos gated como default sin control de autenticacion.
- Si un modelo requiere acceso/autenticacion, proveer fallback abierto funcional.

## 6) Localizacion espanola y variantes

- Espanol correcto obligatorio (ortografia y gramatica).
- Soportar locales y registro editorial de forma parametrica (ej. es-ES, es-VE, es-CO, es-EC, es-PR).
- No codificar dialecto con listas fijas en el core.
- Mantener neutralidad si no hay suficiente contexto regional.

## 7) Reglas de comandos y ejecucion

- Recomendar solo comandos validos y ejecutables.
- Preferir `python -m <tool>` sobre binarios sueltos.
- Si hay duda, validar sintaxis con `--help`.
- Nunca inventar comandos.
- Al documentar comandos, indicar objetivo y prerequisitos.

## 8) Calidad y validacion minima

Para cambios de codigo:

- Tipado fuerte y validaciones de entrada.
- Tests unitarios para invariantes y bugs corregidos.
- Tests de integracion en flujos criticos cuando aplique.
- Evitar `except Exception` silencioso sin criterio.
- No introducir bypasses de error sin trazabilidad.

Checklist previo a cerrar un cambio:

1. ¿Compila/ejecuta en el entorno objetivo?
2. ¿Tiene test del comportamiento nuevo o del bug corregido?
3. ¿No rompe trazabilidad ni compliance?
4. ¿No deja estados intermedios inconsistentes?
5. ¿No mete contenido hardcodeado?

## 9) Reglas de review (cuando Copilot comenta PRs)

En review, priorizar:

- Bugs funcionales reales.
- Riesgos de regresion.
- Integridad de datos.
- Estados de jobs y manejo de errores.
- Seguridad/compliance.
- Tests faltantes en rutas criticas.

Evitar ruido:

- No pedir refactors cosmeticos sin impacto.
- No pedir cambios de estilo si no hay riesgo real.
- No duplicar comentarios ya cubiertos.

Cada hallazgo debe incluir:

- Severidad (`P1`, `P2`, `P3`).
- Evidencia concreta (archivo + comportamiento).
- Riesgo real si no se corrige.
- Sugerencia implementable.

## 10) Reglas de documentacion

- Enlaces siempre relativos al repo (nunca rutas absolutas locales).
- Documentacion portable (GitHub web, Codespaces, Linux/macOS/Windows).
- Mantener README y runbooks sincronizados con el estado real del codigo.
- No documentar features no verificadas.

## 11) Estructura y alcance de cambios

- Cambios pequeños, cohesionados y reversibles.
- No mezclar tareas no relacionadas en el mismo commit.
- No tocar archivos fuera de alcance sin justificacion.
- No borrar ni reescribir artefactos del usuario sin autorizacion explicita.

## 12) Fuentes de verdad del repo

- `AGENTS.md`
- `manifests/clipturbo-context.md`
- `manifests/architecture-rules.md`
- `manifests/token-policy.md`
- `tasks/todo.md`
- `tasks/lessons.md`
- `docs/lessons/`
- `docs/runbooks/`
- `packages/clipturbo_core/`
- `apps/api-fastapi/`
- `apps/worker-media/`

## 13) Formato esperado de respuesta tecnica

Cuando propongas o resumas trabajo, usa esta estructura:

1. objetivo
2. supuestos
3. decision tecnica
4. archivos afectados
5. implementacion
6. riesgos/trade-offs
7. siguiente paso

Mantener respuestas directas, sin relleno, y con foco operativo.
