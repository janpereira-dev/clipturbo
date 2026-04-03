# HF Gated Fallback

- contexto: una ruta de `model-routing` usaba un modelo gated y el pipeline caia con `401 Unauthorized`.
- decision: implementar fallback de modelos en runtime para generacion y correccion HF.
- motivo: evitar parada total por permisos de repositorio/modelo en Hugging Face.
- validacion: tests unitarios nuevos para fallback (`test_hf_model_access_fallback.py`) y suite completa en verde.
- siguiente paso: mantener solo modelos abiertos en el manifiesto por defecto y dejar gated unicamente bajo override explicito.
