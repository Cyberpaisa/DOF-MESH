"""
Knowledge API — DOF Approval Pipeline, servidor HTTP local.
Expone los endpoints que consume la Chrome extension dof-youtube.

GET  /latest         → pending/latest.json (último video pendiente)
GET  /pending        → lista de todos los pending
POST /approve/{rid}  → aprueba un reporte
POST /reject/{rid}   → rechaza un reporte
GET  /health         → {"status": "ok"}

Puerto: 19019
Uso:
    python3 core/knowledge_api.py          # corre forever
    python3 core/knowledge_api.py --once   # no-op, solo verifica salud
"""

import json
import logging
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [KNOWLEDGE-API] %(message)s")
logger = logging.getLogger("dof.knowledge_api")

BASE_DIR = Path(__file__).parent.parent
PENDING_DIR = BASE_DIR / "docs" / "knowledge" / "pending"

PORT = 19019
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


class KnowledgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002
        logger.info("%s %s", self.address_string(), format % args)

    def _send(self, code: int, body: dict | list):
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        path = self.path.rstrip("/")

        if path == "/health":
            self._send(200, {"status": "ok", "port": PORT})

        elif path == "/latest":
            latest = PENDING_DIR / "latest.json"
            if latest.exists():
                try:
                    data = json.loads(latest.read_text(encoding="utf-8"))
                    self._send(200, data)
                except Exception as e:
                    self._send(500, {"error": str(e)})
            else:
                self._send(404, {"error": "no pending report"})

        elif path == "/pending":
            if not PENDING_DIR.exists():
                self._send(200, [])
                return
            reports = []
            for p in sorted(PENDING_DIR.glob("*.json")):
                if p.name == "latest.json":
                    continue
                try:
                    reports.append(json.loads(p.read_text(encoding="utf-8")))
                except Exception:
                    pass
            self._send(200, reports)

        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.rstrip("/")

        if path == "/ingest":
            self._handle_ingest()
        elif path.startswith("/approve/"):
            rid = path[len("/approve/"):]
            self._handle_action(rid, action="approve")
        elif path.startswith("/reject/"):
            rid = path[len("/reject/"):]
            self._handle_action(rid, action="reject")
        else:
            self._send(404, {"error": "not found"})

    def _handle_ingest(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            url = body.get("url", "").strip()
            if not url or "youtube.com/watch" not in url and "youtu.be/" not in url:
                self._send(400, {"error": "invalid YouTube URL"})
                return
        except Exception as e:
            self._send(400, {"error": str(e)})
            return

        # Encola en background — no bloqueamos la respuesta HTTP
        import threading
        def _run():
            try:
                from core.youtube_ingestor import ingest
                from core.knowledge_daemon import _process_pending, _load_processed
                from core.knowledge_reporter import report_all_pending
                from core.knowledge_notifier import notify_all_pending
                ingest(url)
                processed = _load_processed()
                _process_pending(processed)
                reports = report_all_pending()
                if reports:
                    notify_all_pending()
                logger.info(f"Ingest pipeline done for {url}")
            except Exception as e:
                logger.error(f"Ingest failed: {e}")

        threading.Thread(target=_run, daemon=True).start()
        self._send(202, {"status": "queued", "url": url})

    def _handle_action(self, rid: str, action: str):
        if not rid or not rid.isalnum():
            self._send(400, {"error": "invalid rid"})
            return
        try:
            from core.knowledge_approver import approve, reject
            ok = approve(rid) if action == "approve" else reject(rid)
            status = "approved" if action == "approve" else "rejected"
            self._send(200 if ok else 404, {"rid": rid, "status": status if ok else "not_found"})
        except Exception as e:
            logger.error(f"Action {action} failed for {rid}: {e}")
            self._send(500, {"error": str(e)})


def run(port: int = PORT):
    server = HTTPServer(("127.0.0.1", port), KnowledgeHandler)
    logger.info(f"Knowledge API running on http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopped.")


if __name__ == "__main__":
    if "--once" in sys.argv:
        import urllib.request
        try:
            r = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2)
            print(json.loads(r.read()))
        except Exception:
            print(f"Knowledge API not running on port {PORT}")
    else:
        run()
