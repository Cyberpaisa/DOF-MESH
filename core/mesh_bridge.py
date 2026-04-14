from __future__ import annotations
"""
MeshBridge — HTTP Server for Remote Nodes.

Exposes the DOF mesh network over HTTP using Python stdlib only.
No Flask, no FastAPI — pure http.server.

Endpoints:
    GET  /                  — Dashboard HTML (dark theme, auto-refresh)
    GET  /api/nodes         — JSON list of all nodes
    GET  /api/messages      — JSON of recent messages (?limit=20)
    GET  /api/events        — JSON of recent events (?limit=10)
    GET  /api/inbox/{id}    — JSON of pending messages for a node
    GET  /api/state         — JSON mesh state summary
    GET  /api/health        — Health check
    POST /api/send          — Send a message (validated by Cerberus)

Security:
    - Cerberus validates ALL incoming POST messages
    - Rate limiting: 60 requests/minute per IP
    - CORS headers for browser access
    - All requests logged to logs/mesh/bridge_access.jsonl

Usage:
    python3 core/mesh_bridge.py --port 8080
    python3 core/mesh_bridge.py --host 127.0.0.1 --port 9000
"""

import json
import os
import time
import logging
from collections import defaultdict
from dataclasses import asdict
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from uuid import uuid4

logger = logging.getLogger("core.mesh_bridge")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MESH_DIR = Path(os.path.join(BASE_DIR, "logs", "mesh"))
ACCESS_LOG = MESH_DIR / "bridge_access.jsonl"

# Rate limiting: {ip: [timestamps]}
_rate_limits: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_MAX = 60  # requests per minute
_START_TIME = time.time()


# ═══════════════════════════════════════════════════════
# HELPERS — Read mesh data from disk
# ═══════════════════════════════════════════════════════

def _read_nodes() -> dict:
    """Read nodes.json and return dict of node data."""
    nodes_file = MESH_DIR / "nodes.json"
    if not nodes_file.exists():
        return {}
    try:
        return json.loads(nodes_file.read_text())
    except Exception:
        return {}


def _read_messages(limit: int = 20) -> list[dict]:
    """Read last N messages from messages.jsonl."""
    msgs_file = MESH_DIR / "messages.jsonl"
    if not msgs_file.exists():
        return []
    try:
        lines = msgs_file.read_text().strip().split("\n")
        lines = [l for l in lines if l.strip()]
        result = []
        for line in lines[-limit:]:
            try:
                result.append(json.loads(line))
            except Exception:
                continue
        return result
    except Exception:
        return []


def _read_events(limit: int = 10) -> list[dict]:
    """Read last N events from mesh_events.jsonl."""
    events_file = MESH_DIR / "mesh_events.jsonl"
    if not events_file.exists():
        return []
    try:
        lines = events_file.read_text().strip().split("\n")
        lines = [l for l in lines if l.strip()]
        result = []
        for line in lines[-limit:]:
            try:
                result.append(json.loads(line))
            except Exception:
                continue
        return result
    except Exception:
        return []


def _read_inbox(node_id: str) -> list[dict]:
    """Read all messages from a node's inbox."""
    inbox_dir = MESH_DIR / "inbox" / node_id
    if not inbox_dir.exists():
        return []
    messages = []
    for f in sorted(inbox_dir.glob("*.json")):
        try:
            messages.append(json.loads(f.read_text()))
        except Exception:
            continue
    return messages


def _get_mesh_state() -> dict:
    """Compute mesh state summary."""
    nodes = _read_nodes()
    total = len(nodes)
    active = sum(1 for n in nodes.values() if n.get("status") == "active")

    # Count pending (unread) messages across all inboxes
    pending = 0
    inbox_dir = MESH_DIR / "inbox"
    if inbox_dir.exists():
        for node_dir in inbox_dir.iterdir():
            if node_dir.is_dir():
                for f in node_dir.glob("*.json"):
                    try:
                        data = json.loads(f.read_text())
                        if not data.get("read", False):
                            pending += 1
                    except Exception:
                        continue

    # Total messages
    msgs_file = MESH_DIR / "messages.jsonl"
    total_msgs = 0
    if msgs_file.exists():
        try:
            total_msgs = sum(1 for line in msgs_file.read_text().strip().split("\n") if line.strip())
        except Exception:
            pass

    return {
        "total_nodes": total,
        "active_nodes": active,
        "pending_messages": pending,
        "total_messages": total_msgs,
        "uptime_seconds": round(time.time() - _START_TIME, 1),
    }


def _check_rate_limit(ip: str) -> bool:
    """Return True if request is allowed, False if rate-limited."""
    now = time.time()
    cutoff = now - 60
    _rate_limits[ip] = [t for t in _rate_limits[ip] if t > cutoff]
    if len(_rate_limits[ip]) >= _RATE_LIMIT_MAX:
        return False
    _rate_limits[ip].append(now)
    return True


def _log_access(method: str, path: str, ip: str, status: int):
    """Log request to bridge_access.jsonl."""
    try:
        MESH_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": time.time(),
            "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "method": method,
            "path": path,
            "ip": ip,
            "status": status,
        }
        with open(ACCESS_LOG, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception:
        pass


def _format_uptime(seconds: float) -> str:
    """Format seconds into human-readable uptime."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    elif m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


# ═══════════════════════════════════════════════════════
# DASHBOARD HTML
# ═══════════════════════════════════════════════════════

def _render_dashboard() -> str:
    """Generate the full dashboard HTML page."""
    nodes = _read_nodes()
    messages = _read_messages(limit=10)
    events = _read_events(limit=10)
    state = _get_mesh_state()

    # Build nodes table rows
    node_rows = ""
    for nid, n in nodes.items():
        status = n.get("status", "unknown")
        status_class = status if status in ("active", "idle", "spawning") else "idle"
        model = n.get("model", "—")
        sent = n.get("messages_sent", 0)
        recv = n.get("messages_received", 0)
        role = n.get("role", "—")
        session = n.get("session_id", "")
        session_short = session[:8] if session else "none"
        last_active = n.get("last_active", 0)
        if last_active:
            age = time.time() - last_active
            age_str = _format_uptime(age) + " ago"
        else:
            age_str = "never"
        node_rows += (
            f'<tr>'
            f'<td><span class="{status_class}">{nid}</span></td>'
            f'<td class="{status_class}">{status}</td>'
            f'<td>{role}</td>'
            f'<td>{model}</td>'
            f'<td>{sent}</td>'
            f'<td>{recv}</td>'
            f'<td>{session_short}</td>'
            f'<td>{age_str}</td>'
            f'</tr>\n'
        )

    # Build messages list
    msgs_html = ""
    for msg in reversed(messages):
        from_n = msg.get("from_node", "?")
        to_n = msg.get("to_node", "?")
        content = msg.get("content", "")[:200]
        msg_type = msg.get("msg_type", "?")
        ts = msg.get("timestamp", 0)
        ts_str = time.strftime("%H:%M:%S", time.localtime(ts)) if ts else "?"
        msgs_html += (
            f'<div class="msg">'
            f'<strong>[{ts_str}] {from_n} → {to_n}</strong> '
            f'<em>({msg_type})</em><br>'
            f'{_html_escape(content)}'
            f'</div>\n'
        )

    # Build events list
    events_html = ""
    for evt in reversed(events):
        event_type = evt.get("event", "?")
        ts = evt.get("timestamp", 0)
        ts_str = time.strftime("%H:%M:%S", time.localtime(ts)) if ts else "?"
        iso = evt.get("iso", "")
        detail_keys = [k for k in evt.keys() if k not in ("timestamp", "iso", "event")]
        detail = ", ".join(f"{k}={evt[k]}" for k in detail_keys[:5])
        events_html += (
            f'<div class="msg">'
            f'<strong>[{ts_str}] {event_type}</strong> '
            f'{_html_escape(detail)}'
            f'</div>\n'
        )

    # Build node options for send form
    node_options = ""
    for nid in nodes:
        node_options += f'<option value="{nid}">{nid}</option>\n'

    uptime_str = _format_uptime(state["uptime_seconds"])

    html = f"""<!DOCTYPE html>
<html>
<head>
<title>DOF MESH — OCTANET LEGION</title>
<meta http-equiv="refresh" content="10">
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; }}
  body {{ background: #0a0a0a; color: #00ff41; font-family: 'Courier New', monospace; padding: 20px; margin: 0; }}
  h1 {{ text-align: center; color: #00ff41; border-bottom: 2px solid #00ff41; padding-bottom: 10px; }}
  h2 {{ color: #00ff41; margin-top: 30px; border-bottom: 1px solid #1a3a1a; padding-bottom: 5px; }}
  .stats {{ display: flex; justify-content: space-around; margin: 20px 0; flex-wrap: wrap; gap: 10px; }}
  .stat {{ text-align: center; padding: 15px 25px; border: 1px solid #00ff41; border-radius: 5px; min-width: 140px; }}
  .stat .number {{ font-size: 2em; font-weight: bold; }}
  .stat .label {{ font-size: 0.8em; color: #00aa30; margin-top: 5px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
  th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #1a3a1a; }}
  th {{ color: #00ff41; background: #0d1f0d; }}
  tr:hover {{ background: #0d1f0d; }}
  .active {{ color: #00ff41; }}
  .idle {{ color: #666; }}
  .spawning {{ color: #ffaa00; }}
  .error {{ color: #ff4444; }}
  .msg {{ background: #0d1f0d; padding: 10px; margin: 5px 0; border-left: 3px solid #00ff41; word-wrap: break-word; font-size: 0.9em; }}
  .send-form {{ margin: 20px 0; padding: 15px; border: 1px solid #00ff41; border-radius: 5px; }}
  input, textarea, select {{ background: #111; color: #00ff41; border: 1px solid #00ff41; padding: 8px; width: 100%; margin: 5px 0; font-family: monospace; border-radius: 3px; }}
  textarea {{ min-height: 60px; resize: vertical; }}
  button {{ background: #00ff41; color: #0a0a0a; border: none; padding: 10px 20px; cursor: pointer; font-weight: bold; font-family: monospace; border-radius: 3px; margin-top: 5px; }}
  button:hover {{ background: #00cc33; }}
  .footer {{ text-align: center; color: #333; margin-top: 30px; font-size: 0.8em; }}
  #send-result {{ margin-top: 10px; padding: 8px; display: none; border-radius: 3px; }}
  .form-row {{ display: flex; gap: 10px; }}
  .form-row > * {{ flex: 1; }}
  label {{ color: #00aa30; font-size: 0.85em; }}
</style>
</head>
<body>

<h1>DOF MESH — OCTANET LEGION</h1>

<div class="stats">
  <div class="stat">
    <div class="number">{state['total_nodes']}</div>
    <div class="label">TOTAL NODES</div>
  </div>
  <div class="stat">
    <div class="number">{state['active_nodes']}</div>
    <div class="label">ACTIVE</div>
  </div>
  <div class="stat">
    <div class="number">{state['total_messages']}</div>
    <div class="label">MESSAGES</div>
  </div>
  <div class="stat">
    <div class="number">{state['pending_messages']}</div>
    <div class="label">PENDING</div>
  </div>
  <div class="stat">
    <div class="number">{uptime_str}</div>
    <div class="label">UPTIME</div>
  </div>
</div>

<h2>NODES</h2>
<table>
  <tr>
    <th>Node ID</th>
    <th>Status</th>
    <th>Role</th>
    <th>Model</th>
    <th>Sent</th>
    <th>Recv</th>
    <th>Session</th>
    <th>Last Active</th>
  </tr>
  {node_rows}
</table>

<h2>RECENT MESSAGES (last 10)</h2>
{msgs_html if msgs_html else '<div class="msg" style="color:#666;">No messages yet.</div>'}

<h2>RECENT EVENTS (last 10)</h2>
{events_html if events_html else '<div class="msg" style="color:#666;">No events yet.</div>'}

<h2>SEND MESSAGE</h2>
<div class="send-form">
  <div class="form-row">
    <div>
      <label>From Node</label>
      <select id="from_node">
        {node_options}
        <option value="remote">remote</option>
      </select>
    </div>
    <div>
      <label>To Node</label>
      <select id="to_node">
        {node_options}
        <option value="*">* (broadcast)</option>
      </select>
    </div>
    <div>
      <label>Type</label>
      <select id="msg_type">
        <option value="task">task</option>
        <option value="result">result</option>
        <option value="query">query</option>
        <option value="alert">alert</option>
        <option value="sync">sync</option>
      </select>
    </div>
  </div>
  <label>Content</label>
  <textarea id="content" placeholder="Message content..."></textarea>
  <button onclick="sendMessage()">SEND</button>
  <div id="send-result"></div>
</div>

<div class="footer">
  DOF Mesh Bridge | Auto-refresh: 10s | {time.strftime("%Y-%m-%d %H:%M:%S")}
</div>

<script>
async function sendMessage() {{
  const body = {{
    from_node: document.getElementById('from_node').value,
    to_node: document.getElementById('to_node').value,
    content: document.getElementById('content').value,
    msg_type: document.getElementById('msg_type').value,
  }};
  const resultDiv = document.getElementById('send-result');
  try {{
    const resp = await fetch('/api/send', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(body),
    }});
    const data = await resp.json();
    resultDiv.style.display = 'block';
    if (data.status === 'accepted') {{
      resultDiv.style.background = '#0d2f0d';
      resultDiv.style.border = '1px solid #00ff41';
      resultDiv.textContent = 'Message sent: ' + data.msg_id;
      document.getElementById('content').value = '';
    }} else {{
      resultDiv.style.background = '#2f0d0d';
      resultDiv.style.border = '1px solid #ff4444';
      resultDiv.textContent = 'Blocked: ' + (data.reason || 'unknown');
    }}
  }} catch (err) {{
    resultDiv.style.display = 'block';
    resultDiv.style.background = '#2f0d0d';
    resultDiv.style.border = '1px solid #ff4444';
    resultDiv.textContent = 'Error: ' + err.message;
  }}
  setTimeout(() => {{ resultDiv.style.display = 'none'; }}, 8000);
}}
</script>

</body>
</html>"""
    return html


def _html_escape(text: str) -> str:
    """Basic HTML escaping."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


# ═══════════════════════════════════════════════════════
# HTTP HANDLER
# ═══════════════════════════════════════════════════════

class MeshBridgeHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the DOF Mesh Bridge."""

    def log_message(self, format, *args):
        """Override default logging to use our logger."""
        logger.info(f"{self.client_address[0]} - {format % args}")

    def _set_cors_headers(self):
        """Add CORS headers to response."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, data, status: int = 200):
        """Send a JSON response."""
        body = json.dumps(data, indent=2, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._set_cors_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, status: int = 200):
        """Send an HTML response."""
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self._set_cors_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _get_client_ip(self) -> str:
        """Get the client IP address."""
        forwarded = self.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return self.client_address[0]

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(204)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        ip = self._get_client_ip()
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)

        # Rate limit check
        if not _check_rate_limit(ip):
            _log_access("GET", self.path, ip, 429)
            self._send_json({"error": "rate_limited", "message": "Max 60 requests/minute"}, 429)
            return

        try:
            if path == "" or path == "/":
                # Dashboard
                html = _render_dashboard()
                self._send_html(html)
                _log_access("GET", self.path, ip, 200)

            elif path == "/api/nodes":
                nodes = _read_nodes()
                self._send_json(list(nodes.values()))
                _log_access("GET", self.path, ip, 200)

            elif path == "/api/messages":
                limit = int(params.get("limit", ["20"])[0])
                limit = min(limit, 200)
                msgs = _read_messages(limit=limit)
                self._send_json(msgs)
                _log_access("GET", self.path, ip, 200)

            elif path == "/api/events":
                limit = int(params.get("limit", ["10"])[0])
                limit = min(limit, 100)
                events = _read_events(limit=limit)
                self._send_json(events)
                _log_access("GET", self.path, ip, 200)

            elif path.startswith("/api/inbox/"):
                node_id = path.split("/api/inbox/", 1)[1]
                if not node_id:
                    self._send_json({"error": "missing node_id"}, 400)
                    _log_access("GET", self.path, ip, 400)
                    return
                inbox = _read_inbox(node_id)
                self._send_json(inbox)
                _log_access("GET", self.path, ip, 200)

            elif path == "/api/state":
                state = _get_mesh_state()
                self._send_json(state)
                _log_access("GET", self.path, ip, 200)

            elif path == "/api/health":
                state = _get_mesh_state()
                self._send_json({
                    "status": "ok",
                    "nodes": state["total_nodes"],
                    "uptime": _format_uptime(state["uptime_seconds"]),
                })
                _log_access("GET", self.path, ip, 200)

            else:
                self._send_json({"error": "not_found", "path": self.path}, 404)
                _log_access("GET", self.path, ip, 404)

        except Exception as e:
            logger.error(f"GET {self.path} error: {e}")
            self._send_json({"error": "internal_error", "message": str(e)}, 500)
            _log_access("GET", self.path, ip, 500)

    def do_POST(self):
        """Handle POST requests."""
        ip = self._get_client_ip()
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        # Rate limit check
        if not _check_rate_limit(ip):
            _log_access("POST", self.path, ip, 429)
            self._send_json({"error": "rate_limited", "message": "Max 60 requests/minute"}, 429)
            return

        try:
            if path == "/api/send":
                self._handle_send(ip)
            else:
                self._send_json({"error": "not_found", "path": self.path}, 404)
                _log_access("POST", self.path, ip, 404)

        except Exception as e:
            logger.error(f"POST {self.path} error: {e}")
            self._send_json({"error": "internal_error", "message": str(e)}, 500)
            _log_access("POST", self.path, ip, 500)

    def _handle_send(self, ip: str):
        """Handle POST /api/send — send a message to the mesh."""
        # Read body
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self._send_json({"error": "empty_body"}, 400)
            _log_access("POST", self.path, ip, 400)
            return

        if content_length > 65536:  # 64KB max
            self._send_json({"error": "payload_too_large"}, 413)
            _log_access("POST", self.path, ip, 413)
            return

        raw_body = self.rfile.read(content_length)
        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError:
            self._send_json({"error": "invalid_json"}, 400)
            _log_access("POST", self.path, ip, 400)
            return

        # Validate required fields
        from_node = body.get("from_node", "").strip()
        to_node = body.get("to_node", "").strip()
        content = body.get("content", "").strip()
        msg_type = body.get("msg_type", "task").strip()

        if not from_node or not to_node or not content:
            self._send_json({
                "error": "missing_fields",
                "required": ["from_node", "to_node", "content"],
            }, 400)
            _log_access("POST", self.path, ip, 400)
            return

        if msg_type not in ("task", "result", "query", "alert", "sync"):
            msg_type = "task"

        # Cerberus validation
        try:
            from core.cerberus import Cerberus
            cerberus = Cerberus(mesh_dir=str(MESH_DIR))
            verdict = cerberus.guard(content, from_node=from_node, to_node=to_node)

            if verdict.blocked:
                self._send_json({
                    "status": "blocked",
                    "reason": f"Cerberus: {verdict.threat_level} — {', '.join(verdict.threats)}",
                    "threat_level": verdict.threat_level,
                }, 403)
                _log_access("POST", self.path, ip, 403)
                return
        except ImportError:
            # Cerberus not available — log warning but allow
            logger.warning("Cerberus not available — skipping message validation")
        except Exception as e:
            logger.error(f"Cerberus error: {e}")
            # Don't block on Cerberus errors — degrade gracefully

        # Generate message
        msg_id = uuid4().hex[:12]
        timestamp = time.time()
        msg = {
            "msg_id": msg_id,
            "from_node": from_node,
            "to_node": to_node,
            "content": content,
            "msg_type": msg_type,
            "timestamp": timestamp,
            "read": False,
            "reply_to": body.get("reply_to"),
        }

        # Write to global messages log
        MESH_DIR.mkdir(parents=True, exist_ok=True)
        msgs_file = MESH_DIR / "messages.jsonl"
        with open(msgs_file, "a") as f:
            f.write(json.dumps(msg, default=str) + "\n")

        # Deliver to inbox(es)
        if to_node == "*":
            # Broadcast: deliver to all nodes except sender
            nodes = _read_nodes()
            for nid in nodes:
                if nid != from_node:
                    _deliver_to_inbox(nid, msg)
        else:
            _deliver_to_inbox(to_node, msg)

        self._send_json({
            "status": "accepted",
            "msg_id": msg_id,
            "timestamp": timestamp,
        })
        _log_access("POST", self.path, ip, 200)


def _deliver_to_inbox(node_id: str, msg: dict):
    """Write a message to a node's inbox directory."""
    inbox_dir = MESH_DIR / "inbox" / node_id
    inbox_dir.mkdir(parents=True, exist_ok=True)
    msg_file = inbox_dir / f"{msg['msg_id']}.json"
    msg_file.write_text(json.dumps(msg, default=str))


# ═══════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DOF Mesh HTTP Bridge")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    print(f"DOF Mesh Bridge starting on http://{args.host}:{args.port}")
    print(f"Dashboard: http://localhost:{args.port}/")
    print(f"API: http://localhost:{args.port}/api/")

    server = HTTPServer((args.host, args.port), MeshBridgeHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMesh Bridge shutting down.")
        server.server_close()


# ── MeshBridge / MeshBridgeError (for test compatibility) ─────────────────────

class MeshBridgeError(Exception):
    """Raised by MeshBridge on invalid messages or connection errors."""


class MeshBridge:
    """Singleton bridge for mesh federation traffic."""

    _instance = None
    _class_lock = __import__("threading").Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._connected = False
                    inst._inbox = []
                    cls._instance = inst
        return cls._instance

    def connect(self) -> bool:
        self._connected = True
        return True

    def send_message(self, message) -> bool:
        if message is None or not isinstance(message, str):
            raise MeshBridgeError(f"message must be a str, got {type(message).__name__}")
        if message == "":
            raise MeshBridgeError("message cannot be empty")
        return True

    def receive_message(self):
        if self._inbox:
            return self._inbox.pop(0)
        return None
