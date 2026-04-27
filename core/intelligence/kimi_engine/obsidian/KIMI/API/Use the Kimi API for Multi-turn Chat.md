# Use the Kimi API for Multi-turn Chat
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/engage-in-multi-turn-conversations-using-kimi-api](https://platform.kimi.ai/docs/engage-in-multi-turn-conversations-using-kimi-api)
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

# Use the Kimi API for Multi-turn Chat

The Kimi API is different from the Kimi intelligent assistant. **The API itself doesn't have a memory function; it's stateless**. This means that when you make multiple requests to the API, the Kimi large language model doesn't remember what you asked in the previous request. For example, if you tell the Kimi large language model that you are 27 years old in one request, it won't remember that you are 27 years old in the next request.

So, we need to manually keep track of the context for each request. In other words, we have to manually add the content of the previous request to the next one so that the Kimi large language model can see what we have talked about before. We will modify the example used in the previous chapter to show how to maintain a list of messages to give the Kimi large language model a memory and enable multi-turn conversation functionality.

*Note: We have added the key points for implementing multi-turn conversations as comments in the code.*

<Tabs>
  <Tab title="python">
    ```python theme={null}
    from openai import OpenAI

    client = OpenAI(
        api_key = "MOONSHOT_API_KEY", # Replace MOONSHOT_API_KEY with the API Key you obtained from the Kimi Open Platform
        base_url = "https://api.moonshot.ai/v1",
    )

    # ... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: No
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
