# Use Kimi API for Tool Calls
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/use-kimi-api-to-complete-tool-calls](https://platform.kimi.ai/docs/use-kimi-api-to-complete-tool-calls)
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

# Use Kimi API for Tool Calls

*Tool calls, or `tool_calls`, evolved from function calls (`function_call`). In certain contexts, or when reading compatibility code, you can consider `tool_calls` and `function_call` to be the same. `function_call` is a subset of `tool_calls`.*

## What are Tool Calls?

Tool calls give the Kimi large language model the ability to perform specific actions. The Kimi large language model can engage in conversations and answer questions, which is its "talking" ability. Through tool calls, it also gains the ability to "do" things. With `tool_calls`, the Kimi large language model can help you search the internet, query databases, and even control smart home devices.

A tool call involves several steps:

1. Define the tool using JSON Schema format;
2. Submit the defined tool to the Kimi large language model via the `tools` parameter. You can submit multiple tools at once;
3. The Kimi large language model will decide which tool(s) to use based on the context of the current conversation. It can also choose not to use any tools;
4. The Kimi large language model will output the parameters and information needed to call the tool in JSON format;
5. Use the parameters output by the Kimi large language model to execute the corresponding tool and submit the results back to the Ki... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: Sí
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
