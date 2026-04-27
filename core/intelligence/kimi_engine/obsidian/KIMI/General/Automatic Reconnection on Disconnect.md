# Automatic Reconnection on Disconnect
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/auto-reconnect](https://platform.kimi.ai/docs/auto-reconnect)
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

# Automatic Reconnection on Disconnect

Due to concurrency limits, complex network environments, and other unforeseen circumstances, our connections may sometimes be interrupted. Typically, these intermittent disruptions don't last long. We want our services to remain stable even in such cases. Implementing a simple reconnection feature can be achieved with just a few lines of code.

```python theme={null}
from openai import OpenAI
import time

client = OpenAI(
    api_key = "$MOONSHOT_API_KEY",
    base_url = "https://api.moonshot.ai/v1",
)

def chat_once(msgs):
    response = client.chat.completions.create(
        model = "kimi-k2.6",
        messages = msgs
    )
    return response.choices[0].message.content

def chat(input: str, max_attempts: int = 100) -> str:
    messages = [
        {"role": "system", "content": "You are Kimi, an AI assistant provided by Moonshot AI. You are proficient in Chinese and English conversations. You aim to provide users with safe, helpful, and accurate answers. You will refuse to answer any questions related to terrorism, racism, or explicit content. Moonshot AI is a proper noun and should not be translated into other languages."},
    ]

    # We construct the user's latest question as a message (role=user) and append it to the end of the messages list
    m... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: No
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
