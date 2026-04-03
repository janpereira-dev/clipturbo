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
