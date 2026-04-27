# API Overview
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/overview](https://platform.kimi.ai/docs/overview)
> **Tópico:** #API
> **Sincronización:** 2026-04-23 20:53:23

## 📝 Resumen Ejecutivo
Analizando contenido estructurado...

## ⚙️ Detalles Técnicos
- **Endpoints detectados:** Ninguno
- **Tablas de datos:** 2 detectadas.

## 💎 Contenido Destilado
> ## Documentation Index
> Fetch the complete documentation index at: https://platform.kimi.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# API Overview

## Service Address

```
https://api.moonshot.ai
```

Kimi Open Platform provides OpenAI-compatible HTTP APIs. You can use the OpenAI SDK directly.

When using SDKs, set `base_url` to `https://api.moonshot.ai/v1`. When calling HTTP endpoints directly, use the full path such as `https://api.moonshot.ai/v1/chat/completions`.

## OpenAI Compatibility

Our API is compatible with the OpenAI Chat Completions API in request/response format. This means:

* You can use the official OpenAI SDKs (Python / Node.js) directly
* Most OpenAI-compatible third-party tools and frameworks (LangChain, Dify, Coze, etc.) are supported
* Simply point `base_url` to `https://api.moonshot.ai/v1` to switch

<Note>
  Some parameters are Kimi-specific extensions: the `thinking` parameter needs to be passed via the SDK's `extra_body`; `partial` is a field on assistant messages within the messages array (`"partial": true`), not a top-level request parameter. See [Tool Use](/api/tool-use) and [Partial Mode](/api/partial) for details.
</Note>

## Authentication

All API requests require an API Key in the HTTP header:

```
Authorization: Bearer $MOONSHOT_API_KEY
```

API Keys can be created and managed in the [Kimi Open Platform Console](https://platform.kimi.ai/console/api-keys).

<Warning>
  Your API Key is sensi... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: Sí
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
