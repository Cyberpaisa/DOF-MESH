# Migrating from OpenAI to Kimi API
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/migrating-from-openai-to-kimi](https://platform.kimi.ai/docs/migrating-from-openai-to-kimi)
> **Tópico:** #Agents
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

# Migrating from OpenAI to Kimi API

## About API Compatibility

The Kimi API is compatible with OpenAI's interface specifications. You can use the [Python](https://github.com/openai/openai-python) or [NodeJS](https://github.com/openai/openai-node) SDKs provided by OpenAI to call and use the Kimi large language model. This means that if your application or service is developed based on OpenAI's models, you can seamlessly migrate to using the Kimi large language model by simply replacing the `base_url` and `api_key` with the configuration for the Kimi large language model. Here is an example of how to do this:

<Tabs>
  <Tab title="python">
    ```python theme={null}
    from openai import OpenAI

    client = OpenAI(
        api_key="MOONSHOT_API_KEY", # <-- Replace MOONSHOT_API_KEY with the API Key you obtained from the Kimi Open Platform
        base_url="https://api.moonshot.ai/v1", # <-- Replace the base_url from https://api.openai.com/v1 to https://api.moonshot.ai/v1
    )
    ```
  </Tab>

  <Tab title="node.js">
    ```js theme={null}
    const OpenAI = require("openai");

    const client = new OpenAI({
        apiKey: "MOONSHOT_API_KEY", // <-- Replace MOONSHOT_API_KEY with the API Key you obtained from the Kimi Open Platform
        baseURL: "https://api.moonshot.ai/v1",  // <-- Replac... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: Sí
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
