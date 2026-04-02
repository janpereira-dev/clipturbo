# Runbook de Desarrollo

## Inicio rapido

1. crear entorno virtual
2. instalar `.[dev]`
3. ejecutar `python -m pytest`
4. ejecutar `ruff check .`
5. ejecutar `mypy apps packages`

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

Este comando es placeholder operativo hasta que exista un entrypoint real de jobs.

## Antes de cerrar una tarea

1. revisar `tasks/todo.md`
2. ejecutar validacion proporcional
3. actualizar `tasks/lessons.md`
4. guardar leccion en `docs/lessons/`
5. registrar en Engram
