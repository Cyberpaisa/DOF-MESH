# Create Batch
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/batch-create](https://platform.kimi.ai/docs/batch-create)
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

# Create Batch

> Create a batch task. You need to first upload a JSONL file with purpose="batch" via the Files API, then use the returned file_id to create the task.

<Note>
  **Limits:**

  | Limit              | Description                                                  |
  | ------------------ | ------------------------------------------------------------ |
  | File format        | Must have `.jsonl` extension                                 |
  | File size          | Must be non-empty, max 100MB                                 |
  | Organization quota | Up to 1000 batch-purpose files per organization              |
  | Model consistency  | All requests in a batch must use the same model              |
  | `custom_id`        | Must be unique within the file                               |
  | Model access       | The specified model must exist and the user must have access |
</Note>

For complete usage examples, see the [Batch API Guide](/guide/use-batch-api).

## OpenAPI

````yaml POST /v1/batches
openapi: 3.1.0
info:
  title: Moonshot AI API
  version: 1.0.0
  description: API for Moonshot AI / Kimi large language model services
servers:
  - url: https://api.moonshot.ai
    description: Production
security: []
paths:
  /v1/batches:
    post:
      tags:
        - Batch
      summary: Cre... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: No
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
