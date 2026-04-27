# Errors
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/errors](https://platform.kimi.ai/docs/errors)
> **Tópico:** #General
> **Sincronización:** 2026-04-23 20:53:23

## 📝 Resumen Ejecutivo
Analizando contenido estructurado...

## ⚙️ Detalles Técnicos
- **Endpoints detectados:** Ninguno
- **Tablas de datos:** 6 detectadas.

## 💎 Contenido Destilado
> ## Documentation Index
> Fetch the complete documentation index at: https://platform.kimi.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Errors

When a request fails, the API returns a JSON error response:

```json theme={null}
{
    "error": {
        "type": "content_filter",
        "message": "The request was rejected because it was considered high risk"
    }
}
```

## Error List

### 400 — Bad Request

| error type              | error message                                                                                                                | Description                                                                                                       |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `content_filter`        | The request was rejected because it was considered high risk                                                                 | Content moderation rejected the request. Your input or generated content may contain unsafe or sensitive content. |
| `invalid_request_error` | Invalid request: \{error\_details}                                                                                           | Invalid request, usually due to incorrect format or missing required pa... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: No
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
