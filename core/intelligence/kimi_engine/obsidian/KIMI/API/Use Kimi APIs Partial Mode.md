# Use Kimi API's Partial Mode
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/use-partial-mode-feature-of-kimi-api](https://platform.kimi.ai/docs/use-partial-mode-feature-of-kimi-api)
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

# Use Kimi API's Partial Mode

Sometimes, we want the Kimi large language model to continue a given sentence. For example, in some customer service scenarios, we want the smart robot to start every sentence with "Dear customer, hello." For such needs, the Kimi API offers Partial Mode. Let's use specific code to explain how Partial Mode works:

<Tabs>
  <Tab title="python">
    ```python theme={null}
    from openai import OpenAI

    client = OpenAI(
        api_key = "MOONSHOT_API_KEY", # Replace MOONSHOT_API_KEY with the API Key you obtained from the Kimi Open Platform
        base_url = "https://api.moonshot.ai/v1",
    )

    completion = client.chat.completions.create(
        model = "kimi-k2.6",
        messages = [
            {"role": "system", "content": "You are Kimi, an AI assistant provided by Moonshot AI. You are proficient in Chinese and English conversations. You provide users with safe, helpful, and accurate answers. You also reject any questions involving terrorism, racism, or explicit content. Moonshot AI is a proper noun and should not be translated."},
            {"role": "user", "content": "Hello?"},
            {
                "partial": True, # <-- The partial parameter is used to enable Partial Mode
            	"role": "assistant", # <-- We add a message with role=as... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: No
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
