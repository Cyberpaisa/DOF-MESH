# Cancel Batch
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/batch-cancel](https://platform.kimi.ai/docs/batch-cancel)
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

# Cancel Batch

> Cancel an in-progress batch task. The status will change to cancelling and then to cancelled. Only tasks in validating, in_progress, or finalizing status can be cancelled.

For complete usage examples, see the [Batch API Guide](/guide/use-batch-api).

## OpenAPI

````yaml POST /v1/batches/{batch_id}/cancel
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
  /v1/batches/{batch_id}/cancel:
    post:
      tags:
        - Batch
      summary: Cancel Batch
      description: >-
        Cancel an in-progress batch task. The status will change to cancelling
        and then to cancelled. Only tasks in validating, in_progress, or
        finalizing status can be cancelled.
      parameters:
        - name: batch_id
          in: path
          required: true
          description: The ID of the batch task
          schema:
            type: string
      responses:
        '200':
          description: The cancelled batch task
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BatchObject'
        '400':
          description: Bad request - Task statu... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: No
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
