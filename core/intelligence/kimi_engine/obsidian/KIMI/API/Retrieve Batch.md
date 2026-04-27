# Retrieve Batch
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/batch-retrieve](https://platform.kimi.ai/docs/batch-retrieve)
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

# Retrieve Batch

> Retrieve the status and details of a specific batch task.

For complete usage examples, see the [Batch API Guide](/guide/use-batch-api).

## OpenAPI

````yaml GET /v1/batches/{batch_id}
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
  /v1/batches/{batch_id}:
    get:
      tags:
        - Batch
      summary: Retrieve Batch
      description: Retrieve the status and details of a specific batch task.
      parameters:
        - name: batch_id
          in: path
          required: true
          description: The ID of the batch task
          schema:
            type: string
      responses:
        '200':
          description: Batch task details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BatchObject'
        '401':
          description: Unauthorized - Invalid or missing API key
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '404':
          description: Batch task not found
          content:
            application/json:
              sch... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: No
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
