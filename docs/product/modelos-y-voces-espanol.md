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

- `Azure Speech`
  - buena cobertura para `es-ES`, `es-MX` y variantes latinas
  - voces utiles para narracion neutra y comercial
- `ElevenLabs`
  - voces naturales para demos premium y contenido con mas expresividad
- `Edge TTS`
  - opcion ligera para desarrollo, pruebas y fallback economico

### Nivel 2

- `OpenAI TTS`
  - evaluar cuando la calidad en espanol y coste encajen con el producto
- `Piper`
  - opcion local para ejecucion offline o control de infraestructura

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
