"""
Knowledge Daemon — DOF Knowledge Pipeline, Componente 3.
Monitorea docs/knowledge/ por .md nuevos y los procesa automáticamente.
100% Ollama local. Cero tokens Claude.

Uso:
    python3 core/knowledge_daemon.py          # corre forever
    python3 core/knowledge_daemon.py --once   # procesa pendientes y sale
"""

import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.knowledge_extractor import extract

logging.basicConfig(level=logging.INFO, format="%(asctime)s [KNOWLEDGE] %(message)s")
logger = logging.getLogger("dof.knowledge_daemon")

BASE_DIR = Path(__file__).parent.parent
KNOWLEDGE_DIR = BASE_DIR / "docs" / "knowledge"
STATE_FILE = BASE_DIR / "logs" / "daemon" / "knowledge_processed.jsonl"
POLL_INTERVAL = 30  # seconds


def _load_processed() -> set:
    """Load only successfully processed files — failures are retried."""
    if not STATE_FILE.exists():
        return set()
    processed = set()
    for line in STATE_FILE.read_text().splitlines():
        try:
            entry = json.loads(line)
            if entry.get("success"):
                processed.add(entry["file"])
        except Exception:
            pass
    return processed


def _mark_processed(filename: str, success: bool):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with STATE_FILE.open("a") as f:
        f.write(json.dumps({
            "file": filename,
            "success": success,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }) + "\n")


def _process_pending(processed: set) -> int:
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    # Primary criterion: no JSON yet. State file only skips known successes.
    new_mds = [
        p for p in sorted(KNOWLEDGE_DIR.glob("*.md"))
        if p.name != ".gitkeep"
        and not p.with_suffix(".json").exists()
        and p.name not in processed
    ]
    for md in new_mds:
        logger.info(f"Processing: {md.name}")
        try:
            extract(md)
            _mark_processed(md.name, success=True)
            processed.add(md.name)
        except Exception as e:
            logger.error(f"Failed {md.name}: {e}")
            _mark_processed(md.name, success=False)
    return len(new_mds)


def run(once: bool = False):
    logger.info("Knowledge Daemon started — watching docs/knowledge/")
    processed = _load_processed()

    while True:
        count = _process_pending(processed)
        if count:
            logger.info(f"Processed {count} new file(s)")
        if once:
            break
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run(once="--once" in sys.argv)
