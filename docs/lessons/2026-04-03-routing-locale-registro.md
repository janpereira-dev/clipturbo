# Routing Locale + Registro

- contexto: se pidio controlar naturalidad por pais/registro en espanol sin quemar vocabulario en codigo.
- decision: implementar routing de modelos y voz via `manifests/model-routing.json` y resolverlo en runtime desde el runner.
- motivo: separar configuracion dialectal del core para evitar listas lexicas estaticas y permitir ajustes sin tocar logica.
- validacion: `python -m pytest` -> `33 passed, 1 skipped`; CLI expone `--locale`, `--registro` y `--routing-manifest`.
- siguiente paso: validar en entorno real la disponibilidad de voces Edge por locale y ajustar el manifiesto segun resultados.
