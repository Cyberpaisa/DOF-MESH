# Estimate Tokens
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/estimate](https://platform.kimi.ai/docs/estimate)
> **Tópico:** #API
> **Sincronización:** 2026-04-23 20:53:23

## 📝 Resumen Ejecutivo
Analizando contenido estructurado...

## ⚙️ Detalles Técnicos
- **Endpoints detectados:** Ninguno
- **Tablas de datos:** 0 detectadas.

## 💎 Contenido Destilado
> ## Documentation Index
> Fetch the complete documentation index at: https://platform.kimi.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Estimate Tokens

> Estimates the number of tokens that would be used for a given set of messages and model. The input structure is almost identical to that of chat completion.

The input structure for `estimate-token-count` is almost identical to that of `chat completion`.

<Accordion title="Plain Text Call Example">
  ```bash theme={null}
  curl 'https://api.moonshot.ai/v1/tokenizers/estimate-token-count' \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $MOONSHOT_API_KEY" \
    -d '{
      "model": "kimi-k2.6",
      "messages": [
          {
              "role": "system",
              "content": "You are Kimi, an AI assistant provided by Moonshot AI. You excel in Chinese and English conversations. You provide users with safe, helpful, and accurate answers. You refuse to answer any questions involving terrorism, racism, pornography, or violence. Moonshot AI is a proper noun and should not be translated into other languages."
          },
          {
              "role": "user",
              "content": "Hello, my name is Li Lei. What is 1+1?"
          }
      ]
  }'
  ```
</Accordion>

<Accordion title="Vision Call Example">
  ```python theme={null}
  import os
  import base64
  import json
  import requests

  api_key = os.environ.get("MOONSHOT_API_KEY")
  endpoi... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: No
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
