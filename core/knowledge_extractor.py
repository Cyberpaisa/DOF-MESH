"""
Knowledge Extractor — DOF Knowledge Pipeline, Componente 2.
Input:  docs/knowledge/YYYY-MM-DD-{slug}.md
Output: docs/knowledge/YYYY-MM-DD-{slug}.json + MemoryManager injection
"""

import json
import logging
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger("dof.knowledge_extractor")

BASE_DIR = Path(__file__).parent.parent
KNOWLEDGE_DIR = BASE_DIR / "docs" / "knowledge"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "dof-analyst"
CHUNK_WORDS = 3500

EXTRACTION_PROMPT = """Eres analista del sistema DOF-MESH v0.7.0.
Analiza esta transcripción y responde SOLO con JSON válido, sin markdown, sin explicaciones.

Formato exacto:
{
  "resumen": ["punto 1", "punto 2", "punto 3", "punto 4", "punto 5"],
  "aplicaciones_dof": ["aplicación concreta 1", "aplicación concreta 2", "aplicación concreta 3"],
  "tecnologias": ["tech1", "tech2", "tech3"],
  "proyectos_personas": ["nombre1", "nombre2"],
  "relevancia_dof": "alta|media|baja",
  "tags": ["tag1", "tag2", "tag3"]
}

Transcripción:
"""


def _ollama(prompt: str, timeout: int = 300) -> str:
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 1024},
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())["response"].strip()


def _chunk_text(text: str) -> list[str]:
    words = text.split()
    return [" ".join(words[i:i + CHUNK_WORDS]) for i in range(0, len(words), CHUNK_WORDS)]


def _merge_extractions(extractions: list[dict]) -> dict:
    merged = {
        "resumen": [],
        "aplicaciones_dof": [],
        "tecnologias": set(),
        "proyectos_personas": set(),
        "relevancia_dof": "baja",
        "tags": set(),
    }
    relevance_rank = {"alta": 2, "media": 1, "baja": 0}
    for e in extractions:
        merged["resumen"].extend(e.get("resumen", []))
        merged["aplicaciones_dof"].extend(e.get("aplicaciones_dof", []))
        merged["tecnologias"].update(e.get("tecnologias", []))
        merged["proyectos_personas"].update(e.get("proyectos_personas", []))
        merged["tags"].update(e.get("tags", []))
        if relevance_rank.get(e.get("relevancia_dof", "baja"), 0) > \
           relevance_rank.get(merged["relevancia_dof"], 0):
            merged["relevancia_dof"] = e["relevancia_dof"]
    merged["resumen"] = merged["resumen"][:5]
    merged["aplicaciones_dof"] = merged["aplicaciones_dof"][:5]
    merged["tecnologias"] = sorted(merged["tecnologias"])
    merged["proyectos_personas"] = sorted(merged["proyectos_personas"])
    merged["tags"] = sorted(merged["tags"])
    return merged


def _inject_memory(slug: str, extraction: dict, md_path: Path):
    try:
        from core.memory_manager import MemoryManager
        mm = MemoryManager()
        value = (
            f"Conocimiento ingestado desde YouTube: {slug}\n"
            f"Resumen: {'; '.join(extraction['resumen'])}\n"
            f"Aplicaciones DOF: {'; '.join(extraction['aplicaciones_dof'])}\n"
            f"Tecnologías: {', '.join(extraction['tecnologias'])}"
        )
        mm.store_long_term(
            key=f"knowledge:{slug}",
            value=value,
            source="knowledge_extractor",
            tags=["youtube", "auto-ingested"] + extraction.get("tags", []),
        )
        logger.info(f"Injected to MemoryManager: knowledge:{slug}")
    except Exception as e:
        logger.warning(f"MemoryManager injection skipped: {e}")


def _queue_daemon(slug: str, json_path: Path):
    queue_dir = BASE_DIR / "logs" / "commander" / "queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    entry = {
        "id": f"{ts}_knowledge",
        "instruction": f"Nuevo conocimiento ingestado desde YouTube: {slug}. Ver {json_path}",
        "from": "knowledge_extractor",
        "chat_id": 0,
        "timestamp": ts,
        "status": "pending",
    }
    (queue_dir / f"{ts}_knowledge.json").write_text(json.dumps(entry))
    logger.info(f"Queued for daemon: {ts}_knowledge.json")


def extract(md_path: Path) -> Path:
    md_path = Path(md_path)
    content = md_path.read_text(encoding="utf-8")

    meta = {}
    meta_match = re.search(r"<!-- meta:({.*?}) -->", content)
    if meta_match:
        meta = json.loads(meta_match.group(1))

    transcript_match = re.search(r"## Transcripción\n\n(.+)", content, re.DOTALL)
    transcript = transcript_match.group(1).strip() if transcript_match else content

    chunks = _chunk_text(transcript)
    extractions = []
    for i, chunk in enumerate(chunks):
        logger.info(f"Processing chunk {i+1}/{len(chunks)} ({len(chunk.split())} words)...")
        raw = _ollama(EXTRACTION_PROMPT + chunk)
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            try:
                extractions.append(json.loads(json_match.group()))
            except json.JSONDecodeError:
                logger.warning(f"Chunk {i+1} JSON parse failed, skipping")

    if not extractions:
        raise ValueError("No valid extractions from Ollama")

    result = _merge_extractions(extractions) if len(extractions) > 1 else extractions[0]
    result["metadata"] = meta
    result["source_md"] = str(md_path.name)
    result["extracted_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    json_path = md_path.with_suffix(".json")
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))

    slug = md_path.stem
    _inject_memory(slug, result, md_path)
    _queue_daemon(slug, json_path)

    print(f"✓ {json_path.name} — relevancia: {result.get('relevancia_dof', '?')}")
    return json_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        mds = sorted(KNOWLEDGE_DIR.glob("*.md"))
        if not mds:
            print("Sin archivos .md en docs/knowledge/")
            sys.exit(1)
        target = mds[-1]
    else:
        target = Path(sys.argv[1])
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [EXTRACTOR] %(message)s")
    extract(target)
