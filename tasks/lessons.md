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
- correccion aplicada: agregar `script-engine auto|hf`, quality-gate de salida HF y recovery por modelo.
- regla aprendida: en topics sensibles, rechazar autodefiniciones dañinas y reescribir hacia lenguaje operativo y accionable.
- impacto: el guion ahora depende del topic y el pipeline reporta si uso HF puro o fallback.

## 2026-04-03 - regla no hardcode

- fecha: 2026-04-03
- contexto: requerimiento explicito de producto para no quemar vocabulario, dialectos ni guiones en codigo.
- error o friccion: existian tablas estaticas de correccion y fallback de guion con frases predefinidas.
- correccion aplicada: eliminar diccionarios de reemplazo y fallback estatico; dejar guion/correccion en tiempo de ejecucion por modelo con guardrails genericos.
- regla aprendida: NADA QUEMADO EN CODIGO para contenido editorial; si falta informacion, resolver con modelo y reintentos.
- impacto: arquitectura mas adaptable a variaciones regionales (LatAm/Espana) sin crecer listas manuales.

## 2026-04-03 - routing por pais/registro sin vocabulario quemado

- fecha: 2026-04-03
- contexto: necesidad de mejorar naturalidad por dialecto (`es-ES`, `es-VE`, `es-CO`, `es-EC`, `es-PR`) sin crear listas manuales de palabras.
- error o friccion: los modelos/voz se configuraban por flags aislados y no habia capa unica de enrutado.
- correccion aplicada: crear `manifests/model-routing.json` + modulo `model_routing.py` para resolver `script_model`, `correction_model`, `tts_engine` y voz por `locale+registro`.
- regla aprendida: el dialecto se controla por routing de modelos y prompts de contexto, no por reemplazos lexicos quemados en codigo.
- impacto: configuracion centralizada, editable sin tocar logica del core y lista para escalar a mas paises/registros.

## 2026-04-03 - bloqueo de fuga de metainstrucciones al audio/subtitulos

- fecha: 2026-04-03
- contexto: algunos outputs HF llegaban con artefactos de prompt (ej. "Guion final", "Corrige ortografia...", numeracion y bloques estilo SRT).
- error o friccion: el pipeline los trataba como guion real y terminaban narrados en TTS/subtitulos.
- correccion aplicada: reforzar limpieza en `text_correction.py` y `local_providers.py`, anadir sanitizacion de markdown/numeracion/timestamps e instrucciones meta, y tests de regresion.
- regla aprendida: cualquier salida de modelo debe pasar un filtro anti-metainstruccion antes de persistirla o narrarla.
- impacto: el guion final ahora descarta ruido de prompt y prioriza texto editorial util.

## 2026-04-03 - gated repo HF y fallback de modelos

- fecha: 2026-04-03
- contexto: ejecucion real del runner con `es-ES/cercano` devolvio `401 Unauthorized` al intentar `google/gemma-3-4b-it`.
- error o friccion: el pipeline caia con traceback largo sin intentar otro modelo.
- correccion aplicada: agregar fallback de carga de modelo HF (guion y correccion), actualizar manifiesto a modelos abiertos por defecto y devolver error accionable corto cuando todos los candidatos fallan.
- regla aprendida: nunca dejar un modelo potencialmente gated como unica ruta operativa; toda ruta HF debe incluir fallback verificable.
- impacto: menor probabilidad de parada total por permisos HF y mejor DX de debugging.
