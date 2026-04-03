<div align="center">
  <h1 align="center">ClipTurbo</h1>
  <p align="center">
    Plataforma Spain-first para crear, adaptar y programar videos cortos en espanol.
  </p>
  <p align="center">
    <a href="https://github.com/janpereira-dev/clipturbo/stargazers"><img src="https://img.shields.io/github/stars/janpereira-dev/clipturbo.svg?style=for-the-badge" alt="Stargazers"></a>
    <a href="https://github.com/janpereira-dev/clipturbo/issues"><img src="https://img.shields.io/github/issues/janpereira-dev/clipturbo.svg?style=for-the-badge" alt="Issues"></a>
    <a href="https://github.com/janpereira-dev/clipturbo/network/members"><img src="https://img.shields.io/github/forks/janpereira-dev/clipturbo.svg?style=for-the-badge" alt="Forks"></a>
    <a href="https://github.com/janpereira-dev/clipturbo/blob/main/LICENSE"><img src="https://img.shields.io/github/license/janpereira-dev/clipturbo.svg?style=for-the-badge" alt="License"></a>
  </p>
  <p align="center">
    Espanol
  </p>
</div>

## Vision

ClipTurbo es un producto nuevo para equipos pequenos, creadores y negocios que necesitan producir mas video corto en espanol con menos friccion tecnica y mas control editorial.

La promesa del producto es concreta:
- mas flujo
- mas velocidad
- mas reutilizacion
- mas control
- menos friccion operativa

No es una herramienta para spam, no promete dinero automatico y no se plantea como autopublicador irresponsable.

## Que estamos construyendo

ClipTurbo esta orientado a un flujo real de contenido:

1. definir idea o tema
2. generar variantes de hook
3. redactar guion en espanol
4. elegir voz o proveedor TTS
5. seleccionar assets
6. generar subtitulos
7. renderizar video vertical o horizontal
8. revisar
9. exportar o publicar en borrador

## Enfoque Spain-first

- idioma principal: espanol
- prioridad inicial: Espana
- preparado para es-ES, es-MX, es-AR, es-VE y espanol neutro
- copy, tono y formatos pensados para publico hispano
- borrador por defecto y revision humana antes de publicar

## Modelos y voces en espanol

ClipTurbo se esta organizando para trabajar con prompts y salidas en espanol desde el origen del sistema.

Prioridades de integracion:
- modelos LLM con buen desempeno en espanol
- voces TTS naturales para es-ES y espanol latino
- subtitulado con puntuacion correcta en espanol
- configuracion desacoplada por proveedor

Estrategia tecnica:
- `LLMProvider`
- `TTSProvider`
- `STTProvider`
- `SubtitleProvider`
- `ThumbnailProvider`
- `PublisherProvider`
- `StorageProvider`

El core no debe depender de un proveedor concreto.

## Estado actual del repositorio

Esta fase implementa la base operativa del proyecto:
- gobierno para `Codex`, `Claude Code` y `GitHub Copilot`
- prompt maestro optimizado para ahorro de tokens
- subagentes especializados por dominio
- skills reutilizables y compactas
- manifiestos de arquitectura, tokens y memoria
- memoria dual: `docs/lessons/` y Engram
- esqueleto Python para `api`, `worker` y `core`

## Arquitectura base

- `apps/api-fastapi`: API principal
- `apps/worker-media`: worker para pipeline multimedia
- `packages/clipturbo_core`: contratos y tipos compartidos
- `agents/`: agentes y subagentes operativos
- `agents/skills/`: checklists y procedimientos compactos
- `docs/`: arquitectura, prompts, producto y runbooks
- `manifests/`: reglas base del sistema

## Ejecucion local

- API: ejecutar `uvicorn app.main:app --reload` desde `apps/api-fastapi`
- worker: ejecutar `python -m worker` desde `apps/worker-media`

Los nombres de carpeta con guiones son deliberados para claridad organizativa; por eso los comandos de arranque se documentan por directorio de trabajo.

Pipeline directo desde la raiz:

`python apps/worker-media/worker/run_prompt_video.py --topic "motivacion estoica" --script-engine auto --tts-engine auto --correction-engine auto --publish-drafts`

Para validar que el guion cambia por tema, usa un topic diferente:

`python apps/worker-media/worker/run_prompt_video.py --topic "soy un depresivo" --script-engine hf --script-model "Qwen/Qwen2.5-0.5B-Instruct" --tts-engine fluido --correction-engine hf --correction-model "jorgeortizfuentes/spanish-spellchecker-t5-base-wiki200000"`

El JSON de salida incluye `resolved_script_provider` para saber si el guion salió de HF directo o de fallback topic-driven.

Correccion con modelo HF en espanol:

1. `python -m pip install transformers sentencepiece torch`
2. `python apps/worker-media/worker/run_prompt_video.py --topic "motivacion estoica" --correction-engine hf --correction-model "jorgeortizfuentes/spanish-spellchecker-t5-base-wiki200000"`

Importante: el nombre del modelo no se ejecuta como comando en PowerShell; siempre se pasa como argumento de `--correction-model`.

## Compatibilidad de agentes

- `Codex`: [AGENTS.md](AGENTS.md)
- `Claude Code`: [CLAUDE.md](CLAUDE.md)
- `GitHub Copilot`: [.github/copilot-instructions.md](.github/copilot-instructions.md)

## Flujo de trabajo del repo

1. Leer [AGENTS.md](AGENTS.md).
2. Consultar [manifests/clipturbo-context.md](manifests/clipturbo-context.md).
3. Revisar [tasks/todo.md](tasks/todo.md) y [tasks/lessons.md](tasks/lessons.md).
4. Elegir el subagente correcto.
5. Cargar solo la skill minima necesaria.
6. Ejecutar con validacion proporcional al riesgo.
7. Registrar decision o leccion en `docs/lessons/` y en Engram.

## Politica de tokens

- memoria primero
- contexto minimo
- un solo subagente por defecto
- resumir antes de expandir
- reutilizar manifiestos y skills
- evitar duplicacion de reglas

Ver [manifests/token-policy.md](manifests/token-policy.md).

## Memoria operativa

Toda decision relevante debe persistirse en dos capas:
- repo local: [docs/lessons/README.md](docs/lessons/README.md)
- memoria externa: Engram, basado en `https://github.com/Gentleman-Programming/engram`

## Hoja inmediata

- modelar entidades base del dominio
- definir contratos iniciales de providers
- incorporar configuracion de entorno
- conectar cola de trabajos
- empezar pipeline de guion, voz y subtitulos en espanol
- preparar publicacion asistida con borrador por defecto

## Validacion minima

- `python -m pytest`
- `python -m ruff check .`
- `python -m mypy apps packages`
