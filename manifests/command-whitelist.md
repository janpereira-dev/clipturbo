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
