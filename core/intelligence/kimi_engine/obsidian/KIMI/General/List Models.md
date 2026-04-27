# List Models
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/list-models](https://platform.kimi.ai/docs/list-models)
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

# List Models

> List all currently available models.

List all currently available models.

## OpenAPI

````yaml GET /v1/models
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
  /v1/models:
    get:
      tags:
        - Models
      summary: List Models
      description: List all currently available models.
      responses:
        '200':
          description: Model list
          content:
            application/json:
              schema:
                type: object
                properties:
                  object:
                    type: string
                    example: list
                  data:
                    type: array
                    items:
                      type: object
                      properties:
                        id:
                          type: string
                          description: Model ID
                          example: kimi-k2.5
                        object:
                          type: string
                          example: model
                        created:
                          type: integer
                          description: Crea... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: No
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
