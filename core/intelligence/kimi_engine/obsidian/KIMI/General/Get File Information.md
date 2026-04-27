# Get File Information
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/files-retrieve](https://platform.kimi.ai/docs/files-retrieve)
> **Tópico:** #General
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

# Get File Information

> Retrieves metadata for a specific uploaded file.

<Accordion title="Usage Example">
  ```python theme={null}
  client.files.retrieve(file_id=file_id)
  # FileObject(
  #     id='clg681objj8g9m7n4je0',
  #     bytes=761790,
  #     created_at=1700815879,
  #     filename='xlnet.pdf',
  #     object='file',
  #     purpose='file-extract',
  #     status='ok',
  #     status_details=''
  # )
  ```
</Accordion>

## OpenAPI

````yaml GET /v1/files/{file_id}
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
  /v1/files/{file_id}:
    get:
      tags:
        - Files
      summary: Get File Information
      description: Retrieves metadata for a specific uploaded file.
      parameters:
        - name: file_id
          in: path
          required: true
          description: The file identifier
          schema:
            type: string
      responses:
        '200':
          description: File metadata
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/FileObject'
        '401':
          description: Unauthorized - Invalid or missing API ... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: No
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
