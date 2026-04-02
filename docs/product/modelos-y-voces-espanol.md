# Modelos y Voces en Espanol

## Objetivo

Definir una estrategia inicial de proveedores y modelos que priorice calidad real en espanol antes que cantidad de integraciones.

## Criterios de seleccion

- buen rendimiento en espanol de Espana y espanol latino
- instrucciones estables para copy, hooks y guiones
- coste razonable para MVP
- latencia aceptable para uso interactivo
- API o integracion mantenible
- reemplazabilidad por adapter

## Prioridad de modelos LLM

### Nivel 1

- `OpenAI`: generacion de ideas, hooks, guiones, refinado editorial y variantes cortas
- `Google Gemini`: segunda opcion para generacion y comparacion
- `Ollama`: opcion local para pruebas, privacidad o fallback

### Nivel 2

- `Azure OpenAI`: despliegue empresarial o compliance reforzado
- `Anthropic`: apoyo para revision editorial o planeacion si se integra por adapter externo

## Casos de uso por tipo de modelo

- ideas y hooks: modelos rapidos y baratos con buena obediencia
- guion final: modelos mas fuertes y consistentes en espanol
- revision editorial: modelos con buen seguimiento de instrucciones
- metadata de publicacion: modelos medios

## Prioridad de voces TTS

### Nivel 1

- `MeloTTS`
  - mejor balance local para espanol cuando se prioriza naturalidad
  - si el entorno es Windows conviene ejecutar con Docker para evitar friccion
- `Piper`
  - opcion local, simple y estable para salir rapido en offline
  - voces recomendadas: `es_ES-davefx-medium`, `es_ES-sharvard-medium`, `es_MX-claude-high`, `es_AR-daniela-high`
- `XTTS-v2`
  - opcion local cuando se prioriza calidad alta y clonacion de voz
  - setup y coste operativo mas altos

### Nivel 2

- `Azure Speech`
  - buena cobertura para `es-ES`, `es-MX` y variantes latinas
- `ElevenLabs`
  - voces naturales para demos premium y contenido expresivo
- `Edge TTS`
  - fallback economico para desarrollo
- `OpenAI TTS`
  - evaluar segun coste, latencia y calidad en espanol

## Perfiles de voz iniciales

- `es-ES-neutral-femenina`
- `es-ES-neutral-masculina`
- `es-ES-dinamica`
- `es-MX-neutral`
- `es-LATAM-neutral`

## Reglas editoriales para espanol

- evitar traduccion literal o robotica
- respetar tildes y signos de apertura
- CTA naturales para Espana
- numeros, fechas y moneda localizados
- subtitulos con puntuacion legible, no solo fragmentos

## Regla de implementacion

La v1 no debe integrar muchos proveedores a medias. Debe integrar pocos proveedores bien abstraidos y medibles.

## Ranking practico local

1. `MeloTTS` para mejor espanol local si aceptas setup mas pesado.
2. `Piper` para simpleza offline y despliegue rapido.
3. `XTTS-v2` para calidad alta y clonacion con mayor coste tecnico.
