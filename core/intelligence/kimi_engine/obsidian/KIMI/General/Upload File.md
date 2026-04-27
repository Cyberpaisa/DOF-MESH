# Upload File
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/files-upload](https://platform.kimi.ai/docs/files-upload)
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

# Upload File

> Uploads a file for extraction, image understanding, or video understanding.

<Note>
  Each user can upload a maximum of 1,000 files. Each file must not exceed 100 MB, and the total size of all uploaded files must not exceed 10 GB. The file parsing service is currently free, but rate limiting may be applied during peak traffic periods.
</Note>

<Accordion title="Supported Formats">
  Supported formats include `.pdf`, `.txt`, `.csv`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx`, `.md`, `.jpeg`, `.png`, `.bmp`, `.gif`, `.svg`, `.svgz`, `.webp`, `.ico`, `.xbm`, `.dib`, `.pjp`, `.tif`, `.pjpeg`, `.avif`, `.dot`, `.apng`, `.epub`, `.tiff`, `.jfif`, `.html`, `.json`, `.mobi`, `.log`, `.go`, `.h`, `.c`, `.cpp`, `.cxx`, `.cc`, `.cs`, `.java`, `.js`, `.css`, `.jsp`, `.php`, `.py`, `.py3`, `.asp`, `.yaml`, `.yml`, `.ini`, `.conf`, `.ts`, `.tsx`, and more.
</Accordion>

<Accordion title="File Content Extraction Example">
  When uploading a file, use `purpose="file-extract"` if you want the model to use the extracted file contents as context.

  <Tabs>
    <Tab title="python">
      ```python showLineNumbers expandable theme={null}
      from pathlib import Path
      from openai import OpenAI

      client = OpenAI(
          api_key = "$MOONSHOT_API_KEY",
          base_url = "https:/... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: No
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
