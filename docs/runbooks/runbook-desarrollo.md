# Runbook de Desarrollo

## Inicio rapido

1. crear entorno virtual
2. instalar `.[dev]`
3. ejecutar `python -m pytest`
4. ejecutar `python -m ruff check .`
5. ejecutar `python -m mypy apps packages`

## Ejecucion local

### API FastAPI

Ejecutar desde `apps/api-fastapi`:

```bash
uvicorn app.main:app --reload
```

La carpeta tiene guiones en su nombre, asi que no debe asumirse import directo desde la raiz con notacion de paquete.

### Worker media

Ejecutar desde `apps/worker-media`:

```bash
python -m worker
```

Este comando ya ejecuta el pipeline Python del core para `prompt -> script -> audio -> subtitulos -> render -> publish`.

Tambien puedes lanzarlo desde raiz:

```bash
python apps/worker-media/worker/run_prompt_video.py --topic "motivacion estoica" --locale es-ES --registro neutral --script-engine auto --tts-engine auto --correction-engine auto --publish-drafts
```

Generacion de guion desde topic:

- `--script-engine hf`: fuerza generacion con modelo Hugging Face.
- `--script-engine auto`: usa HF con reintentos y recovery por modelo.
- revisa `resolved_script_provider` en el JSON final: `hf_local_generation`, `hf_local_generation_recovery` o variantes `*_degraded`.

Routing por pais/registro:

- `--locale`: `es-ES`, `es-VE`, `es-CO`, `es-EC`, `es-PR`.
- `--registro`: `neutral`, `cercano`, `profesional`.
- `--routing-manifest`: manifiesto JSON con modelos y voces por locale/registro.
- `--script-model` y `--correction-model` sobreescriben el routing cuando se pasan explicitamente.

Modos de voz:

- `--tts-engine loquendo`: Windows Speech (compatible, menos natural).
- `--tts-engine fluido`: Edge Neural TTS (mas natural, requiere `edge-tts`).
- `--tts-engine auto`: intenta fluido y cae a loquendo si falta dependencia.

Correccion de ortografia/gramatica:

- `--correction-engine guard`: normalizacion/validacion local sin modelo AI.
- `--correction-engine hf`: fuerza modelo Hugging Face (falla si no estan instaladas dependencias).
- `--correction-engine auto`: intenta modelo HF y cae a `guard` si no esta disponible.

Dependencias para modo HF:

```bash
python -m pip install transformers sentencepiece torch
```

Ejemplo con modelo en espanol:

```bash
python apps/worker-media/worker/run_prompt_video.py --topic "motivacion estoica" --locale es-ES --registro cercano --tts-engine fluido --voice "es-ES-AlvaroNeural" --correction-engine hf --correction-model "jorgeortizfuentes/spanish-spellchecker-t5-base-wiki200000" --publish-drafts
```

Ejemplo full HF (guion + correccion):

```bash
python apps/worker-media/worker/run_prompt_video.py --topic "habitos estoicos para entrenar disciplina" --locale es-CO --registro profesional --script-engine hf --script-model "meta-llama/Llama-3.2-3B-Instruct" --tts-engine fluido --voice "es-MX-DaliaNeural" --correction-engine hf --correction-model "jorgeortizfuentes/spanish-spellchecker-mt5-large_3e" --publish-drafts
```

Modelos sugeridos para `--correction-model`:

- `jorgeortizfuentes/spanish-spellchecker-t5-base-wiki200000`
- `jorgeortizfuentes/spanish-spellchecker-mt5-large_3e`
- `jorgeortizfuentes/spanish-spellchecker-flan-t5-large_3e`

Nota de PowerShell:

- el identificador del modelo (`jorgeortizfuentes/...`) no se ejecuta como comando.
- siempre debe pasarse como valor de `--correction-model`.
- si un comando falla por entorno, validar primero `python -m <herramienta> --help` antes de documentarlo.

Memoria de ejecucion:

- por defecto guarda bitacora en `docs/lessons/pipeline-runs.md`
- puedes desactivar con `--no-record-lesson`
- despues de una ejecucion relevante, guardar tambien resumen en Engram

## Antes de cerrar una tarea

1. revisar `tasks/todo.md`
2. ejecutar validacion proporcional
3. actualizar `tasks/lessons.md`
4. guardar leccion en `docs/lessons/`
5. registrar en Engram
