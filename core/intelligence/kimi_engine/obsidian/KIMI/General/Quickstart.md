# Quickstart
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/quickstart](https://platform.kimi.ai/docs/quickstart)
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

# Quickstart

## Single-turn Chat

Interact with the Chat Completions API using the OpenAI SDK and cURL:

<CodeGroup>
  ```python Python theme={null}
  from openai import OpenAI

  client = OpenAI(
      api_key="$MOONSHOT_API_KEY",
      base_url="https://api.moonshot.ai/v1",
  )

  completion = client.chat.completions.create(
      model="kimi-k2.6",
      messages=[
          {"role": "system", "content": "You are Kimi, an AI assistant provided by Moonshot AI. You are proficient in Chinese and English conversations. You provide users with safe, helpful, and accurate answers. You will reject any questions involving terrorism, racism, or explicit content. Moonshot AI is a proper noun and should not be translated."},
          {"role": "user", "content": "Hello, my name is Li Lei. What is 1+1?"}
      ],
  )

  print(completion.choices[0].message.content)
  ```

  ```bash cURL theme={null}
  curl https://api.moonshot.ai/v1/chat/completions \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $MOONSHOT_API_KEY" \
      -d '{
          "model": "kimi-k2.6",
          "messages": [
              {"role": "system", "content": "You are Kimi, an AI assistant provided by Moonshot AI. You are proficient in Chinese and English conversations. You provide users with safe, helpful, ... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: No
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
