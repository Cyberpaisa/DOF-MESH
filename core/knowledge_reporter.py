from __future__ import annotations
"""
Knowledge Reporter — DOF Approval Pipeline, Componente 1.
Input:  docs/knowledge/YYYY-MM-DD-{slug}.json
Output: docs/knowledge/pending/{id_aprobacion}.json con score DOF 0-100
"""

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
KNOWLEDGE_DIR = BASE_DIR / "docs" / "knowledge"
PENDING_DIR = KNOWLEDGE_DIR / "pending"

_RELEVANCE_SCORE = {"alta": 60, "media": 35, "baja": 10}


def _score_dof(data: dict) -> int:
    base = _RELEVANCE_SCORE.get(data.get("relevancia_dof", "baja"), 10)
    apps = min(len(data.get("aplicaciones_dof", [])), 5) * 5
    tech = min(len(data.get("tecnologias", [])), 5) * 2
    return min(base + apps + tech, 100)


def build_report(json_path: Path) -> dict:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    meta = data.get("metadata", {})

    score = _score_dof(data)
    resumen = data.get("resumen", [])
    apps = data.get("aplicaciones_dof", [])
    techs = data.get("tecnologias", [])

    report = {
        "id_aprobacion": uuid.uuid4().hex[:8],
        "score_dof": score,
        "relevancia_dof": data.get("relevancia_dof", "baja"),
        "resumen_corto": resumen[0] if resumen else "",
        "ideas_clave": apps[:3],
        "tecnologias": techs[:5],
        "tags": data.get("tags", []),
        "url_video": meta.get("url", ""),
        "titulo": meta.get("title", json_path.stem),
        "fecha": meta.get("ingested_at", datetime.now().isoformat())[:10],
        "source_json": str(json_path.name),
        "created_at": datetime.now().isoformat(),
        "status": "pending",
    }

    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    out = PENDING_DIR / f"{report['id_aprobacion']}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    print(f"✓ Report {report['id_aprobacion']} — score: {score}/100 ({report['relevancia_dof']})")
    return report


def report_latest() -> dict:
    jsons = sorted(KNOWLEDGE_DIR.glob("*.json"))
    if not jsons:
        raise FileNotFoundError("No JSONs in docs/knowledge/")
    return build_report(jsons[-1])


def report_all_pending() -> list[dict]:
    """Generate reports for all JSONs without a pending report."""
    existing_sources = set()
    if PENDING_DIR.exists():
        for p in PENDING_DIR.glob("*.json"):
            try:
                d = json.loads(p.read_text())
                existing_sources.add(d.get("source_json", ""))
            except Exception:
                pass

    reports = []
    for j in sorted(KNOWLEDGE_DIR.glob("*.json")):
        if j.name not in existing_sources:
            reports.append(build_report(j))
    return reports


if __name__ == "__main__":
    if len(sys.argv) > 1:
        build_report(Path(sys.argv[1]))
    else:
        results = report_all_pending()
        if not results:
            print("Sin JSONs nuevos para reportar.")
