# Tool Use
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/tool-use](https://platform.kimi.ai/docs/tool-use)
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

# Tool Use

Mastering the use of tools is a key hallmark of intelligence, and the Kimi large language model is no exception. Tool Use or Function Calling is a crucial feature of the Kimi large language model. When invoking the API to use the model service, you can describe tools or functions in the Messages, and the Kimi large language model will intelligently select and output a JSON object containing the parameters required to call one or more functions, thus enabling the Kimi large language model to link and utilize external tools.

Here is a simple example of tool invocation:

```json theme={null}
{
  "model": "kimi-k2.6",
  "messages": [
    {
      "role": "user",
      "content": "Determine whether 3214567 is a prime number through programming."
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "CodeRunner",
        "description": "A code executor that supports running Python and JavaScript code",
        "parameters": {
          "properties": {
            "language": {
              "type": "string",
              "enum": ["python", "javascript"]
            },
            "code": {
              "type": "string",
              "description": "The code is written here"
            }
          },
          "type": "object"
        }
      }
    ... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: Sí
- Soporte de Agentes: Sí

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
