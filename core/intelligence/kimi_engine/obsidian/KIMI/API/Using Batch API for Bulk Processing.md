# Using Batch API for Bulk Processing
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/use-batch-api](https://platform.kimi.ai/docs/use-batch-api)
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

# Using Batch API for Bulk Processing

When you need to process large-scale tasks with low real-time requirements, the Batch API is the ideal choice. It supports submitting tasks in bulk via files, saving 40% on inference costs compared to real-time API calls.

<Note>
  Batch API supports both the `kimi-k2.6` and `kimi-k2.5` models. The `temperature`, `top_p`, and other parameters cannot be modified for these models — do not include them in the request body.
</Note>

<CardGroup cols={2}>
  <Card title="Create Batch" icon="plus" href="/api/batch-create">
    Upload a JSONL file and create a batch task
  </Card>

  <Card title="List Batches" icon="list" href="/api/batch-list">
    List batch tasks for your organization
  </Card>

  <Card title="Retrieve Batch" icon="circle-info" href="/api/batch-retrieve">
    Get status and details for a specific batch task
  </Card>

  <Card title="Cancel Batch" icon="xmark" href="/api/batch-cancel">
    Cancel an in-progress batch task
  </Card>
</CardGroup>

## Workflow

This guide walks through a complete text classification example using the Batch API:

### 1. Build the Input File

Each line in the JSONL file is an independent JSON object representing a single inference request:

```json theme={null}
{"custom_id": "request-1", "method": "POST", "url": "/v1/c... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: No
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
