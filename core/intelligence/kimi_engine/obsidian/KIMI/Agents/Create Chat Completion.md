# Create Chat Completion
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/chat](https://platform.kimi.ai/docs/chat)
> **Tópico:** #Agents
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

# Create Chat Completion

> Creates a completion for the chat message. Supports standard chat, Partial Mode, and Tool Use (Function Calling).

Create a chat completion request. The model generates a response based on the provided message list.

<Accordion title="Content Field Description">
  The `content` field supports the following two forms:

  **Plain text string**

  ```json theme={null}
  "content": "Hello"
  ```

  **Array of objects** (for multimodal input)

  Each element in the array is distinguished by the `type` field:

  ```json theme={null}
  "content": [
      { "type": "text", "text": "Describe this image" },
      { "type": "image_url", "image_url": { "url": "data:image/png;base64,..." } },
      { "type": "video_url", "video_url": { "url": "data:video/mp4;base64,..." } }
  ]
  ```

  `image_url` and `video_url` also support passing a string directly, equivalent to the `url` field in object form:

  ```json theme={null}
  { "type": "image_url", "image_url": "data:image/png;base64,..." }
  ```

  #### Parameter Description

  Each element in the array has the following fields:

  | Parameter   | Required                       | Description                                                                             | Type                                       |
  | ----------- | -... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: Sí
- Soporte de Agentes: Sí

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
