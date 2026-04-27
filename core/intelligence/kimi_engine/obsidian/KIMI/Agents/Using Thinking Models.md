# Using Thinking Models
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/use-kimi-k2-thinking-model](https://platform.kimi.ai/docs/use-kimi-k2-thinking-model)
> **Tópico:** #Agents
> **Sincronización:** 2026-04-23 20:53:23

## 📝 Resumen Ejecutivo
Analizando contenido estructurado...

## ⚙️ Detalles Técnicos
- **Endpoints detectados:** Ninguno
- **Tablas de datos:** 1 detectadas.

## 💎 Contenido Destilado
> ## Documentation Index
> Fetch the complete documentation index at: https://platform.kimi.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Using Thinking Models

> Both the `kimi-k2-thinking` and `kimi-k2.6` models have powerful thinking capabilities, supporting deep reasoning and multi-step tool use to solve complex problems.
>
> * **`kimi-k2-thinking`**: A dedicated thinking model with thinking forcibly enabled
> * **\[Recommended] `kimi-k2.6`**: A model that can enable or disable thinking capability, enabled by default. You can disable thinking by using `{"type": "disabled"}`

If you are doing benchmark testing with kimi api, please refer to this [benchmark best practice](/guide/benchmark-best-practice).

## Basic use case

### Using the kimi-k2-thinking model

You can simply use it by switching the `model` parameter:

<Tabs>
  <Tab title="curl">
    ```bash theme={null}
    $ curl https://api.moonshot.ai/v1/chat/completions \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $MOONSHOT_API_KEY" \
        -d '{
            "model": "kimi-k2-thinking",
            "messages": [
                {
                    "role": "system",
                    "content": "You are Kimi."
                },
                {
                    "role": "user",
                    "content": "Please explain why 1+1=2."
                }
            ],
            "temperature": 1.0
       }'

    ```
  </Tab>
... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: Sí
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
