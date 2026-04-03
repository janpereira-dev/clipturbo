# Skill: No Hardcode Generacion

## Objetivo

Evitar contenido quemado en codigo para guiones, vocabulario, dialectos o correcciones ortograficas.

## Reglas

- no crear diccionarios estaticos de palabras regionales o correcciones
- no crear guiones predefinidos en codigo
- todo texto editorial debe salir de un modelo en ejecucion
- si falta informacion, reintentar con modelo (no inventar fallback fijo)
- exponer en logs/resumen que proveedor/modelo genero el contenido

## Checklist rapido

1. buscar en cambios strings largos de contenido editorial
2. revisar que no existan listas de reemplazo por vocabulario fijo
3. validar que `topic` impacta salida de guion
4. ejecutar tests de guardrail:
   - `python -m pytest tests/unit/test_no_hardcoded_content_guardrail.py`
5. registrar decision en `tasks/lessons.md` y Engram
