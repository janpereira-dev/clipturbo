# Service Hardening de Code Review

- contexto: la revisión automática reportó riesgos P1/P2 en servicios del pipeline y persistencia.
- decision: cerrar todos los hallazgos en una sola iteración con tests de regresión.
- motivo: evitar repetición de bugs operativos (jobs colgados, publish cruzado, defaults de voz inválidos).
- validacion: `python -m pytest` -> `44 passed, 1 skipped`; casos nuevos para fallback de voz en runner, render failed path y cross-project publish.
- siguiente paso: responder los comentarios de PR con referencia a los commits y mantener esta suite como guardrail permanente.
