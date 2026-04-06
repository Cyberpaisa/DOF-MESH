"""
Knowledge Notifier — DOF Approval Pipeline, Componente 2.
Input:  docs/knowledge/pending/{id}.json
Output: Notificación a Telegram con botones inline + POST al frontend
"""

import json
import logging
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger("dof.knowledge_notifier")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [NOTIFIER] %(message)s")

BASE_DIR = Path(__file__).parent.parent
PENDING_DIR = BASE_DIR / "docs" / "knowledge" / "pending"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("DOF_CHAT_ID")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def _tg_api(method: str, payload: dict) -> dict:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _relevance_emoji(r: str) -> str:
    return {"alta": "🔴", "media": "🟡", "baja": "⚪"}.get(r, "⚪")


def _escape_md(text: str) -> str:
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text


def _build_telegram_message(report: dict) -> str:
    e = _relevance_emoji(report["relevancia_dof"])
    ideas = "\n".join(f"  • {_escape_md(i)}" for i in report["ideas_clave"])
    techs = _escape_md(", ".join(report["tecnologias"][:4]))
    titulo = _escape_md(report["titulo"])
    url = report["url_video"]
    rid = report["id_aprobacion"]
    score = report["score_dof"]
    rel = report["relevancia_dof"].upper()
    return (
        f"*DOF Knowledge — Nuevo video*\n\n"
        f"{e} *Relevancia:* {rel}  \\|  *Score:* {score}/100\n\n"
        f"*{titulo}*\n"
        f"{_escape_md(url)}\n\n"
        f"*Ideas clave:*\n{ideas}\n\n"
        f"*Tecnologías:* {techs}\n\n"
        f"`ID: {rid}`"
    )


def _send_telegram(report: dict) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados — skip")
        return False
    rid = report["id_aprobacion"]
    payload = {
        "chat_id": int(TELEGRAM_CHAT_ID),
        "text": _build_telegram_message(report),
        "parse_mode": "MarkdownV2",
        "reply_markup": {
            "inline_keyboard": [[
                {"text": "✅ Aprobar", "callback_data": f"aprobar_{rid}"},
                {"text": "❌ Rechazar", "callback_data": f"rechazar_{rid}"},
            ]]
        },
    }
    try:
        _tg_api("sendMessage", payload)
        logger.info(f"Telegram: sent {rid}")
        return True
    except Exception as e:
        logger.error(f"Telegram error: {e}")
        return False


def _send_frontend(report: dict) -> bool:
    url = f"{FRONTEND_URL}/api/knowledge/pending"
    data = json.dumps(report).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            logger.info(f"Frontend: {resp.status} for {report['id_aprobacion']}")
        return True
    except Exception as e:
        logger.warning(f"Frontend not available ({e}) — skip")
        return False


def notify(report_path: Path) -> dict:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    rid = report["id_aprobacion"]

    tg_ok = _send_telegram(report)
    fe_ok = _send_frontend(report)

    result = {
        "id_aprobacion": rid,
        "telegram": tg_ok,
        "frontend": fe_ok,
    }
    logger.info(f"Notified {rid}: telegram={tg_ok} frontend={fe_ok}")
    return result


def notify_all_pending() -> list[dict]:
    if not PENDING_DIR.exists():
        return []
    results = []
    for p in sorted(PENDING_DIR.glob("*.json")):
        try:
            results.append(notify(p))
        except Exception as e:
            logger.error(f"Failed {p.name}: {e}")
    return results


if __name__ == "__main__":
    if len(sys.argv) > 1:
        notify(Path(sys.argv[1]))
    else:
        results = notify_all_pending()
        if not results:
            print("Sin reportes pending.")
        for r in results:
            tg = "✓" if r["telegram"] else "✗"
            fe = "✓" if r["frontend"] else "✗"
            print(f"{r['id_aprobacion']} — Telegram:{tg} Frontend:{fe}")
