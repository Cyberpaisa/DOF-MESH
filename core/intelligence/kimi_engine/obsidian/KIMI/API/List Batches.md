# List Batches
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/batch-list](https://platform.kimi.ai/docs/batch-list)
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

# List Batches

> List batch tasks for your organization.

For complete usage examples, see the [Batch API Guide](/guide/use-batch-api).

## OpenAPI

````yaml GET /v1/batches
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
    get:
      tags:
        - Batch
      summary: List Batches
      description: List batch tasks for your organization.
      parameters:
        - name: after
          in: query
          required: false
          description: >-
            Pagination cursor, pass the ID of the last batch from the previous
            page
          schema:
            type: string
        - name: limit
          in: query
          required: false
          description: Number of results per page, default 20
          schema:
            type: integer
            default: 20
      responses:
        '200':
          description: List of batch tasks
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BatchListResponse'
        '401':
          description: Unauthorized - Invalid or missing API key
          content:
            applicat... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: No
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
