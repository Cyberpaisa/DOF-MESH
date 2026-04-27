import os
import json
import re
from datetime import datetime

DATA_DIR = "data/raw_md/"
OBSIDIAN_DIR = "obsidian/KIMI/"
CHANGELOG_PATH = "CHANGELOG.md"

def parse_markdown(content, filename):
    # Extraer el título del primer H1
    title_match = re.search(r"^#\s+(.+)$", content, re.M)
    title = title_match.group(1).strip() if title_match else filename.replace(".md", "").replace("-", " ").title()
    
    # Detección de tópicos
    topic = "General"
    if "pricing" in filename.lower() or "price" in content.lower():
        topic = "Pricing"
    elif "api" in filename.lower() or "endpoint" in content.lower():
        topic = "API"
    elif "agent" in content.lower() or "tool" in content.lower():
        topic = "Agents"
    elif "batch" in filename.lower():
        topic = "Batch"

    # Estructura de metadatos
    structure = {
        "title": title,
        "url": f"https://platform.kimi.ai/docs/{filename.replace('.md', '')}",
        "topic": topic,
        "summary": "Analizando contenido estructurado...",
        "key_points": [],
        "technical_specs": {},
        "pricing": {},
        "limits": {},
        "api_endpoints": [],
        "agent_features": [],
        "risks": []
    }
    
    # Extraer Endpoints (Bloques de código con /v1/)
    endpoints = re.findall(r"(https://api\.kimi\.ai/v1/[^\s`\"']+)", content)
    structure["api_endpoints"] = list(set(endpoints))
    
    # Extraer Tablas de Markdown (Muy común en Pricing/Limits)
    tables = re.findall(r"(\|.+?\|\n\|[-:| ]+?\|\n(?:\|.+?\|\n)+)", content)
    if tables:
        structure["technical_specs"]["extracted_tables"] = len(tables)
        if topic == "Pricing":
            structure["pricing"]["tables"] = tables

    return structure

def generate_obsidian_note(structure, filename, raw_content):
    title = structure["title"]
    # Limpiar el título para el nombre de archivo
    safe_title = "".join([c for c in title if c.isalnum() or c in (" ", "-", "_")]).strip()
    
    content = f"""# {title}
> [!NOTE]
> **URL Original:** [{structure['url']}]({structure['url']})
> **Tópico:** #{structure['topic']}
> **Sincronización:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📝 Resumen Ejecutivo
{structure['summary']}

## ⚙️ Detalles Técnicos
- **Endpoints detectados:** {', '.join([f'`{e}`' for e in structure['api_endpoints']]) if structure['api_endpoints'] else 'Ninguno'}
- **Tablas de datos:** {structure['technical_specs'].get('extracted_tables', 0)} detectadas.

## 💎 Contenido Destilado
{raw_content[:1500]}... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: {'Sí' if 'tool' in raw_content.lower() else 'No'}
- Soporte de Agentes: {'Sí' if 'agent' in raw_content.lower() else 'No'}

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
"""
    
    target_dir = os.path.join(OBSIDIAN_DIR, structure['topic'])
    os.makedirs(target_dir, exist_ok=True)
    
    file_path = os.path.join(target_dir, f"{safe_title}.md")
    with open(file_path, "w") as f:
        f.write(content)
    
    return safe_title

def run_analysis():
    if not os.path.exists(DATA_DIR):
        print("Esperando a que el scraper genere archivos...")
        return

    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".md")]
    print(f"Iniciando análisis de {len(files)} documentos Markdown...")
    
    for f in files:
        with open(os.path.join(DATA_DIR, f), "r") as content_file:
            raw_md = content_file.read()
            structure = parse_markdown(raw_md, f)
            note_title = generate_obsidian_note(structure, f, raw_md)
            print(f"Nota generada en Obsidian: {note_title}")

if __name__ == "__main__":
    run_analysis()
