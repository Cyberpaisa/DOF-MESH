# Check Balance
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/balance](https://platform.kimi.ai/docs/balance)
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

# Check Balance

> REST API to check your available, voucher, and cash balances on Kimi OpenPlatform.

## OpenAPI

````yaml GET /v1/users/me/balance
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
  /v1/users/me/balance:
    get:
      tags:
        - Billing
      summary: Check Balance
      description: >-
        REST API to check your available, voucher, and cash balances on Kimi
        OpenPlatform.
      responses:
        '200':
          description: Balance information
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BalanceResponse'
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
components:
  schemas:
    BalanceResponse:
      type: object
      properties:
        c... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: No
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
