# Use Kimi API's Internet Search Functionality
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/use-web-search](https://platform.kimi.ai/docs/use-web-search)
> **Tópico:** #Pricing
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

# Use Kimi API's Internet Search Functionality

In the previous chapter ([Using Kimi API to Complete Tool Calls](/guide/use-kimi-api-to-complete-tool-calls)), we explained in detail how to use the `tool_calls` feature of the Kimi API to enable the Kimi large language model to perform internet searches. Let's review the process we implemented:

1. We defined tools using the JSON Schema format. For internet searches, we defined two tools: `search` and `crawl`.
2. We submitted the defined `search` and `crawl` tools to the Kimi large language model via the `tools` parameter.
3. The Kimi large language model would select to call `search` and `crawl` based on the context of the current conversation, generate the relevant parameters, and output them in JSON format.
4. We used the parameters output by the Kimi large language model to execute the `search` and `crawl` functions and submitted the results of these functions back to the Kimi large language model.
5. The Kimi large language model would then provide a response to the user based on the results of the tool executions.

In the process of implementing internet searches, we needed to implement the `search` and `crawl` functions ourselves, which might include:

1. Calling search engine APIs or implementing our own content search.
2. Retrieving searc... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: Sí
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
