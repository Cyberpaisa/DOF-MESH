"""
Knowledge Approver — DOF Approval Pipeline, Componente 3.
Escucha callbacks de Telegram (aprobar_/rechazar_) y POST /api/approve.
Aprobado → MemoryManager + daemon queue
Rechazado → docs/knowledge/rejected/

Uso:
    python3 core/knowledge_approver.py          # polling forever
    python3 core/knowledge_approver.py --once   # procesa updates pendientes y sale
"""

import json
import logging
import os
import sys
import time
import shutil
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [APPROVER] %(message)s")
logger = logging.getLogger("dof.knowledge_approver")

BASE_DIR = Path(__file__).parent.parent
PENDING_DIR = BASE_DIR / "docs" / "knowledge" / "pending"
REJECTED_DIR = BASE_DIR / "docs" / "knowledge" / "rejected"
QUEUE_DIR = BASE_DIR / "logs" / "commander" / "queue"
OFFSET_FILE = BASE_DIR / "logs" / "daemon" / "tg_approver_offset.txt"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
POLL_INTERVAL = 5  # seconds


# ── Telegram polling ──────────────────────────────────────────────────

def _tg(method: str, payload: dict = None) -> dict:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    data = json.dumps(payload or {}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _get_offset() -> int:
    if OFFSET_FILE.exists():
        try:
            return int(OFFSET_FILE.read_text().strip())
        except Exception:
            pass
    return 0


def _save_offset(offset: int):
    OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
    OFFSET_FILE.write_text(str(offset))


def _answer_callback(callback_id: str, text: str):
    try:
        _tg("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})
    except Exception:
        pass


# ── Approval logic ───────────────────────────────────────────────────

def _load_report(rid: str) -> dict | None:
    path = PENDING_DIR / f"{rid}.json"
    if not path.exists():
        logger.warning(f"Report not found: {rid}")
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def approve(rid: str) -> bool:
    report = _load_report(rid)
    if not report:
        return False

    # Inject to MemoryManager
    try:
        from core.memory_manager import MemoryManager
        mm = MemoryManager()
        value = (
            f"Conocimiento aprobado: {report['titulo']}\n"
            f"Score DOF: {report['score_dof']}/100\n"
            f"Ideas: {'; '.join(report['ideas_clave'])}\n"
            f"Tecnologías: {', '.join(report['tecnologias'])}\n"
            f"URL: {report['url_video']}"
        )
        mm.store_long_term(
            key=f"knowledge:{rid}",
            value=value,
            source="knowledge_approver",
            tags=["youtube", "approved"] + report.get("tags", []),
        )
        logger.info(f"MemoryManager: stored knowledge:{rid}")
    except Exception as e:
        logger.error(f"MemoryManager error: {e}")

    # Queue for autonomous_daemon
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    queue_entry = {
        "id": f"{ts}_approved_{rid}",
        "instruction": f"Conocimiento aprobado y disponible: {report['titulo']}. "
                       f"Score DOF {report['score_dof']}/100. "
                       f"Ideas: {'; '.join(report['ideas_clave'][:2])}",
        "from": "knowledge_approver",
        "chat_id": 0,
        "timestamp": ts,
        "status": "pending",
    }
    (QUEUE_DIR / f"{ts}_approved_{rid}.json").write_text(json.dumps(queue_entry))

    # Mark as approved and remove from pending
    report["status"] = "approved"
    report["approved_at"] = datetime.now().isoformat()
    approved_dir = BASE_DIR / "docs" / "knowledge" / "approved"
    approved_dir.mkdir(parents=True, exist_ok=True)
    (approved_dir / f"{rid}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    (PENDING_DIR / f"{rid}.json").unlink(missing_ok=True)

    logger.info(f"✓ APPROVED: {rid} — {report['titulo']}")
    return True


def reject(rid: str) -> bool:
    report = _load_report(rid)
    if not report:
        return False

    REJECTED_DIR.mkdir(parents=True, exist_ok=True)
    report["status"] = "rejected"
    report["rejected_at"] = datetime.now().isoformat()
    (REJECTED_DIR / f"{rid}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    (PENDING_DIR / f"{rid}.json").unlink(missing_ok=True)

    logger.info(f"✗ REJECTED: {rid} — {report['titulo']}")
    return True


# ── Telegram callback polling ────────────────────────────────────────

def _process_update(update: dict) -> bool:
    """Process one Telegram update. Returns True if it was an approval callback."""
    cb = update.get("callback_query")
    if not cb:
        return False

    data = cb.get("data", "")
    cb_id = cb["id"]

    if data.startswith("aprobar_"):
        rid = data[len("aprobar_"):]
        ok = approve(rid)
        _answer_callback(cb_id, "✅ Aprobado" if ok else "⚠ No encontrado")
        return True

    if data.startswith("rechazar_"):
        rid = data[len("rechazar_"):]
        ok = reject(rid)
        _answer_callback(cb_id, "❌ Rechazado" if ok else "⚠ No encontrado")
        return True

    return False


def poll(once: bool = False):
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN no configurado")
        return

    offset = _get_offset()
    logger.info(f"Knowledge Approver — polling Telegram (offset={offset})")

    while True:
        try:
            result = _tg("getUpdates", {"offset": offset, "timeout": 4, "allowed_updates": ["callback_query"]})
            for update in result.get("result", []):
                _process_update(update)
                offset = update["update_id"] + 1
                _save_offset(offset)
        except Exception as e:
            logger.warning(f"Poll error: {e}")

        if once:
            break
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    poll(once="--once" in sys.argv)
