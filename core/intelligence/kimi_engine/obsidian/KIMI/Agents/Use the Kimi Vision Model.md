# Use the Kimi Vision Model
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/use-kimi-vision-model](https://platform.kimi.ai/docs/use-kimi-vision-model)
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

# Use the Kimi Vision Model

The Kimi Vision Model (including `moonshot-v1-8k-vision-preview` / `moonshot-v1-32k-vision-preview` / `moonshot-v1-128k-vision-preview` / `kimi-k2.6`/ `kimi-k2.6` and so on) can understand visual content, including text in the image, colors, and the shapes of objects. The latest `kimi-k2.6` model can also understand video content.

## Using base64 to Upload Images Directly

Here is how you can ask Kimi questions about an image using the following code:

```python theme={null}
import os
import base64

from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("MOONSHOT_API_KEY"),
    base_url="https://api.moonshot.ai/v1",
)

# Replace kimi.png with the path to the image you want Kimi to recognize
image_path = "kimi.png"

with open(image_path, "rb") as f:
    image_data = f.read()

# We use the built-in base64.b64encode function to encode the image into a base64 formatted image_url
image_url = f"data:image/{os.path.splitext(image_path)[1].lstrip('.')};base64,{base64.b64encode(image_data).decode('utf-8')}"

completion = client.chat.completions.create(
    model="kimi-k2.6",
    messages=[
        {"role": "system", "content": "You are Kimi."},
        {
            "role": "user",
            # Note here, the content has changed from the original str type to... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: Sí
- Soporte de Agentes: Sí

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
