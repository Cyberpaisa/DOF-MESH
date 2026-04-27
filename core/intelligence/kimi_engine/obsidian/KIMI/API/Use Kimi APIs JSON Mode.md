# Use Kimi API's JSON Mode
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/use-json-mode-feature-of-kimi-api](https://platform.kimi.ai/docs/use-json-mode-feature-of-kimi-api)
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

# Use Kimi API's JSON Mode

In some scenarios, we want the model to output content in a fixed format JSON document. For example, when you want to summarize an article, you might expect a structured data format like this:

```json theme={null}
{
	"title": "Article Title",
	"author": "Article Author",
	"publish_time": "Publication Time",
	"summary": "Article Summary"
}
```

If you directly tell the Kimi large language model in the prompt: "Please output content in JSON format," the model can understand your request and generate a JSON document as required. However, the generated content often has some flaws. For instance, in addition to the JSON document, Kimi might output extra text to explain the JSON document:

```text theme={null}
Here is the JSON document you requested

{
	"title": "Article Title",
	"author": "Article Author",
	"publish_time": "Publication Time",
	"summary": "Article Summary"
}
```

Or the JSON document format might be incorrect and cannot be parsed properly, such as (note the comma at the end of the `summary` field):

```text theme={null}
{
	"title": "Article Title",
	"author": "Article Author",
	"publish_time": "Publication Time",
	"summary": "Article Summary",
}
```

Such a JSON document cannot be parsed correctly. To generate a standard and valid JSON document as expected... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: No
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
