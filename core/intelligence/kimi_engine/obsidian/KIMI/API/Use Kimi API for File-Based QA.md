# Use Kimi API for File-Based Q&A
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/use-kimi-api-for-file-based-qa](https://platform.kimi.ai/docs/use-kimi-api-for-file-based-qa)
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

# Use Kimi API for File-Based Q&A

The Kimi intelligent assistant can upload files and answer questions based on those files. The Kimi API offers the same functionality. Below, we'll walk through a practical example of how to upload files and ask questions using the Kimi API:

<Tabs>
  <Tab title="python">
    ```python theme={null}
    from pathlib import Path
    from openai import OpenAI

    client = OpenAI(
        api_key="MOONSHOT_API_KEY", # Replace MOONSHOT_API_KEY with the API Key you obtained from the Kimi Open Platform
        base_url="https://api.moonshot.ai/v1",
    )

    # 'moonshot.pdf' is an example file. We support text and image files. For image files, we provide OCR capabilities.
    # To upload a file, you can use the file upload API from the openai library. Create a file object using Path from the standard library pathlib and pass it to the file parameter. Set the purpose parameter to 'file-extract'. Note that the file upload interface currently only supports 'file-extract' as a purpose value.
    file_object = client.files.create(file=Path("moonshot.pdf"), purpose="file-extract")

    # Get the result
    # file_content = client.files.retrieve_content(file_id=file_object.id)
    # Note: The retrieve_content API in some older examples is marked as deprecated in the latest... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: No
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
