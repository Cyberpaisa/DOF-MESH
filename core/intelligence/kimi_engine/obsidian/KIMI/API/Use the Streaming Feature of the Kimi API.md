# Use the Streaming Feature of the Kimi API
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/utilize-the-streaming-output-feature-of-kimi-api](https://platform.kimi.ai/docs/utilize-the-streaming-output-feature-of-kimi-api)
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

# Use the Streaming Feature of the Kimi API

When the Kimi large language model receives a question from a user, it first performs inference and then **generates the response one Token at a time**. In the examples from our first two chapters, we chose to wait for the Kimi large language model to generate all Tokens before printing its response. This usually takes several seconds. If your question is complex enough and the response from the Kimi large language model is long enough, the time to wait for the complete response can be stretched to 10 or even 20 seconds, which greatly reduces the user experience. To improve this situation and provide timely feedback to users, we offer the ability to stream output, known as Streaming. We will explain the principles of Streaming and illustrate it with actual code:

* How to use streaming output;
* Common issues when using streaming output;
* How to handle streaming output without using the Python SDK;

## How to Use Streaming Output

Streaming, in a nutshell, means that whenever the Kimi large language model generates a certain number of Tokens (usually 1 Token), it immediately sends these Tokens to the client, instead of waiting for all Tokens to be generated before sending them to the client. When you chat with [Kimi AI Assistant](https://kimi.ai), th... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: No
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
