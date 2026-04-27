# List Files
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/files-list](https://platform.kimi.ai/docs/files-list)
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

# List Files

> Lists all files uploaded by the current user.

<Accordion title="Usage Example">
  ```python theme={null}
  file_list = client.files.list()

  for file in file_list.data:
      print(file)  # Inspect the metadata of each file
  ```
</Accordion>

## OpenAPI

````yaml GET /v1/files
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
  /v1/files:
    get:
      tags:
        - Files
      summary: List Files
      description: Lists all files uploaded by the current user.
      responses:
        '200':
          description: List of uploaded files
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/FileListResponse'
        '401':
          description: Unauthorized - Invalid or missing API key
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
      security:
        - bearerAuth: []
components... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: No
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
