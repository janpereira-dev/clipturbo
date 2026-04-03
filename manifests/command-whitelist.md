# Command Whitelist

## Inventario

- `rg --files`
- `Get-ChildItem -Force`
- `git status --short --branch`

## Python

- `python --version`
- `python -m pytest`
- `python -m pip list`
- `python -m pip install -e .[dev]`
- `python -m pip install transformers sentencepiece torch`
- `python apps/worker-media/worker/run_prompt_video.py --topic "motivacion estoica" --tts-engine auto --correction-engine auto --publish-drafts`

## Calidad

- `ruff check .`
- `mypy apps packages`

## Infra

- `docker compose config`
- `ffmpeg -version`

## Diagnostico futuro

- jobs
- migraciones
- colas
- workers

Documentar comandos nuevos solo cuando ya se usen de forma repetida o segura.
