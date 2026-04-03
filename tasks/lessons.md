# Lessons

Usa este formato para registrar patrones repetidos.

## Plantilla

- fecha:
- contexto:
- error o friccion:
- correccion aplicada:
- regla aprendida:
- impacto:

## 2026-04-03 - correccion ortografica con modelo

- fecha: 2026-04-03
- contexto: ejecucion del pipeline `prompt -> script -> audio -> subtitulos -> render` en Windows/PowerShell.
- error o friccion: se intentaron ejecutar IDs de Hugging Face como comandos (`jorgeortizfuentes/...`) y el guion mantenia errores ortograficos.
- correccion aplicada: integrar corrector en el core con `--correction-engine guard|hf|auto` y `--correction-model`; `auto` cae a `guard` si faltan dependencias.
- regla aprendida: en PowerShell el modelo se pasa como argumento, nunca como comando; para `hf` instalar `transformers sentencepiece torch`.
- impacto: menos errores de espanol en guion y menor friccion operativa para activar correccion AI real.

## 2026-04-03 - compatibilidad transformers 5.x

- fecha: 2026-04-03
- contexto: modo `--correction-engine hf` con `transformers==5.5.0` en Windows.
- error o friccion: `KeyError: Unknown task text2text-generation` al usar `pipeline(task=...)`.
- correccion aplicada: reemplazar `pipeline(...)` por carga explicita `AutoTokenizer + AutoModelForSeq2SeqLM/AutoModelForCausalLM` y `model.generate(...)`.
- regla aprendida: evitar depender de nombres de task de `pipeline` para caminos criticos; preferir API de modelo/tokenizer directa y estable.
- impacto: correccion HF funcional y compatible con versiones recientes de transformers.

## 2026-04-03 - fuga de prompt en subtitulos/audio

- fecha: 2026-04-03
- contexto: salida HF incluia frases de instruccion dentro del texto final del guion.
- error o friccion: audio y subtitulos narraban "Corrige ortografia..." en lugar de solo contenido editorial.
- correccion aplicada: enviar solo texto plano al corrector HF y agregar limpieza de artefactos (`Corrige...`, `Texto:`) antes del guard de ortografia.
- regla aprendida: para modelos spellchecker, evitar prompts largos de instruccion en inferencia de produccion.
- impacto: el pipeline vuelve a generar audio/subtitulos sin contaminarse con metainstrucciones.

## 2026-04-03 - guion topic-driven con filtro de calidad

- fecha: 2026-04-03
- contexto: el topic cambiaba pero el guion salia casi igual o con eco de prompt.
- error o friccion: generacion HF devolvia texto pobre o metainstrucciones para temas sensibles.
- correccion aplicada: agregar `script-engine auto|hf|rule`, quality-gate de salida HF y fallback `topic_guided_v1` generado desde topic con normalizacion de temas sensibles.
- regla aprendida: en topics sensibles, rechazar autodefiniciones dañinas y reescribir hacia lenguaje operativo y accionable.
- impacto: el guion ahora depende del topic y el pipeline reporta si uso HF puro o fallback.
