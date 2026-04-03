# Bloqueo de Fuga de Metainstrucciones

- contexto: el guion generado por modelos HF podia incluir cabeceras tipo "Guion Final", instrucciones de correccion y ruido numerado/SRT.
- decision: aplicar limpieza anti-metainstruccion en dos capas del core (`text_correction` y `local_providers`) antes de TTS/subtitulos.
- motivo: evitar que el audio/subtitulo narre prompts o formato tecnico en lugar de contenido editorial.
- validacion: `python -m pytest` -> `36 passed, 1 skipped`; tests nuevos de regresion para limpieza de artefactos.
- siguiente paso: ejecutar 5 corridas reales con topics distintos y validar que `script_text` no contenga `Guion Final`, `Texto:` ni timestamps.
