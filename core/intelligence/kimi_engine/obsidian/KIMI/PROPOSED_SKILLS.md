# 🛠️ PROPOSED KIMI SKILLS
> Basado en el análisis automático de la documentación 2026.

### Skill: `kimi_api_call`
- **Descripción:** Realiza una llamada estándar a la API de Kimi.
- **Input:** `{ 'model': str, 'messages': list, 'temperature': float }`
- **Output:** `{ 'choices': list, 'usage': dict }`
- **Pasos:**
  - Configurar API_KEY
  - Enviar POST a https://api.kimi.ai/v1/chat/completions
  - Manejar respuesta JSON

---
### Skill: `kimi_streaming_handler`
- **Descripción:** Maneja respuestas en streaming de Kimi para baja latencia.
- **Input:** `{ 'model': str, 'prompt': str }`
- **Output:** `Stream de tokens (SSE)`
- **Pasos:**
  - Activar flag stream=true
  - Iterar sobre eventos 'data:'
  - Recomponer mensaje final

---
