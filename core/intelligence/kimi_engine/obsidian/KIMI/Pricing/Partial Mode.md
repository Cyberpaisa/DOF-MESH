# Partial Mode
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/partial](https://platform.kimi.ai/docs/partial)
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

# Partial Mode

When using large language models, sometimes we want to guide the model's output by prefilling part of the response. In the Kimi large language model, we provide Partial Mode to achieve this. It helps control the output format, guide the content, and maintain better consistency in role-playing scenarios. Simply add `"partial": True` to the last message entry with `role` of `assistant` to enable Partial Mode.

```json theme={null}
{"role": "assistant", "content": leading_text, "partial": True},
```

<Note>
  **Note!**

  Do not mix Partial Mode with response\_format=json\_object, or you may get unexpected model responses.
</Note>

## Examples

### JSON Mode

Here is an example of using Partial Mode to achieve JSON Mode.

<CodeGroup>
  ```python Python expandable theme={null}
  from openai import OpenAI

  client = OpenAI(
      api_key="$MOONSHOT_API_KEY",
      base_url="https://api.moonshot.ai/v1",
  )

  completion = client.chat.completions.create(
      model="kimi-k2.6",
      messages=[
          {
              "role": "system",
              "content": "Extract the name, size, price, and color from the product description and output them in a JSON object.",
          },
          {
              "role": "user",
              "content": "The DaMi SmartHome Mini is a compact ... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: Sí
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
