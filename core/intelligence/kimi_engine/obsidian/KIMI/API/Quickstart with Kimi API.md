# Quickstart with Kimi API
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/start-using-kimi-api](https://platform.kimi.ai/docs/start-using-kimi-api)
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

# Quickstart with Kimi API

The Kimi API allows you to interact with the Kimi large language model. Here is a simple example code:

<Tabs>
  <Tab title="python">
    ```python theme={null}
    from openai import OpenAI

    client = OpenAI(
        api_key="MOONSHOT_API_KEY", # Replace MOONSHOT_API_KEY with the API Key you obtained from the Kimi Open Platform
        base_url="https://api.moonshot.ai/v1",
    )

    completion = client.chat.completions.create(
        model = "kimi-k2.6",
        messages = [
            {"role": "system", "content": "You are Kimi, an AI assistant provided by Moonshot AI. You are proficient in Chinese and English conversations. You provide users with safe, helpful, and accurate answers. You will reject any requests involving terrorism, racism, or explicit content. Moonshot AI is a proper noun and should not be translated."},
            {"role": "user", "content": "Hello, my name is Li Lei. What is 1+1?"}
        ]
    )

    # We receive a response from the Kimi large language model via the API (role=assistant)
    print(completion.choices[0].message.content)
    ```
  </Tab>

  <Tab title="node.js">
    ```js theme={null}
    const OpenAI = require("openai")

    const client = new OpenAI({
        apiKey: "MOONSHOT_API_KEY", // Replace MOONSHOT_API_KEY with t... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: No
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
