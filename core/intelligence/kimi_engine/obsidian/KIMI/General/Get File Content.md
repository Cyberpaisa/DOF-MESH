# Get File Content
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/files-content](https://platform.kimi.ai/docs/files-content)
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

# Get File Content

> Retrieves extracted text content for files uploaded with purpose `file-extract`.

<Accordion title="Usage Example">
  <Tabs>
    <Tab title="python">
      ```python theme={null}
      # Note: retrieve_content is marked with a warning in the latest version. Use the line below instead.
      # If you are using an older version, you can use retrieve_content.
      file_content = client.files.content(file_id=file_object.id).text
      ```
    </Tab>

    <Tab title="curl">
      ```bash theme={null}
      curl https://api.moonshot.ai/v1/files/{file_id}/content \
        -H "Authorization: Bearer $MOONSHOT_API_KEY"
      ```
    </Tab>
  </Tabs>
</Accordion>

## OpenAPI

````yaml GET /v1/files/{file_id}/content
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
  /v1/files/{file_id}/content:
    get:
      tags:
        - Files
      summary: Get File Content
      description: >-
        Retrieves extracted text content for files uploaded with purpose
        `file-extract`.
      parameters:
        - name: file_id
          in: path
          required: true
          description: The file identifier
    ... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: No
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
