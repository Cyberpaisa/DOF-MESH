"""
A2A Server — Exposes crews as discoverable services.

Other agents (LangGraph, AutoGen, etc.) can:
  1. Discover our crews via /.well-known/agent-card.json
  2. Send tasks and receive results via JSON-RPC

Usage:
  python a2a_server.py                    → Port 8000
  python a2a_server.py --port 9000        → Custom port
  python a2a_server.py --crew research    → Research crew only
"""

import argparse
import json
import hmac
import hashlib
import os
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# HMAC Authentication
A2A_SECRET = os.getenv("A2A_SECRET_KEY", "")
A2A_AUTH_ENABLED = bool(A2A_SECRET)
TIMESTAMP_MAX_AGE = 30  # seconds


def _verify_hmac(headers: dict, body: bytes) -> tuple[bool, str]:
    """Verify HMAC SHA256 signature.

    Required headers: X-API-KEY, X-TIMESTAMP, X-SIGNATURE
    Signature = HMAC-SHA256(secret, timestamp + body)
    """
    if not A2A_AUTH_ENABLED:
        return True, "auth_disabled"

    api_key = headers.get("X-Api-Key", headers.get("x-api-key", ""))
    timestamp = headers.get("X-Timestamp", headers.get("x-timestamp", ""))
    signature = headers.get("X-Signature", headers.get("x-signature", ""))

    if not all([api_key, timestamp, signature]):
        return False, "missing_auth_headers"

    # Timestamp validation (< 30s)
    try:
        ts = float(timestamp)
        if abs(time.time() - ts) > TIMESTAMP_MAX_AGE:
            return False, "timestamp_expired"
    except ValueError:
        return False, "invalid_timestamp"

    # HMAC verification
    message = f"{timestamp}".encode() + body
    expected = hmac.new(A2A_SECRET.encode(), message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return False, "invalid_signature"

    return True, "ok"

# ═══════════════════════════════════════════════════════
# AGENT CARD — Describe our capabilities
# ═══════════════════════════════════════════════════════

AGENT_CARD = {
    "name": "Enigma Group Agent System",
    "description": "Multi-agent AI system with 8 specialized agents and 11 crews for research, development, content, and analysis.",
    "url": "http://localhost:8000",
    "version": "1.0.0",
    "protocol_version": "0.3",
    "capabilities": {
        "streaming": False,
        "push_notifications": False,
    },
    "default_input_modes": ["text/plain", "application/json"],
    "default_output_modes": ["text/plain", "application/json"],
    "skills": [
        {
            "id": "research",
            "name": "Market Research",
            "description": "Deep market research with web data, competitor analysis, and Go/No-Go recommendations. Returns structured ResearchReport + MVPPlan.",
        },
        {
            "id": "code-review",
            "name": "Code Review",
            "description": "Full code review with architecture analysis, security audit, and actionable fixes. Returns CodeReviewReport.",
        },
        {
            "id": "data-analysis",
            "name": "Data Analysis",
            "description": "Analyze Excel/CSV/DB data with statistics, anomaly detection, and Python scripts.",
        },
        {
            "id": "build-project",
            "name": "Build Project",
            "description": "Generate a complete functional project from a description: research, plan, code, and review.",
        },
        {
            "id": "grant-hunt",
            "name": "Grant Hunter",
            "description": "Find and analyze grant/hackathon opportunities across blockchain ecosystems with narrative strategy.",
        },
        {
            "id": "content",
            "name": "Content Creator",
            "description": "Create Web3 content: Twitter threads, blog posts, pitch decks, grant narratives.",
        },
        {
            "id": "daily-ops",
            "name": "Daily Operations",
            "description": "Morning scan: ecosystem news, metrics, daily plan, social content.",
        },
        {
            "id": "enigma-audit",
            "name": "Enigma Agent Audit",
            "description": "Audit ERC-8004 AI agents on Avalanche: endpoints, metadata, trust scores.",
        },
    ],
}


# ═══════════════════════════════════════════════════════
# EXECUTE CREW BY SKILL ID
# ═══════════════════════════════════════════════════════

def execute_skill(skill_id: str, input_text: str) -> dict:
    """Execute the crew for a given skill with supervisor + governance + tracing."""
    from crew import (
        create_research_crew,
        create_code_review_crew,
        create_data_analysis_crew,
        create_build_project_crew,
        create_grant_hunt_crew,
        create_content_crew,
        create_daily_ops_crew,
        create_enigma_audit_crew,
    )
    from core.crew_runner import run_crew as run_crew_supervised

    logger.info(f"Executing skill '{skill_id}' with input: {input_text[:100]}...")

    try:
        if skill_id == "research":
            crew = create_research_crew(input_text)
        elif skill_id == "code-review":
            crew = create_code_review_crew(input_text)
        elif skill_id == "data-analysis":
            crew = create_data_analysis_crew(input_text)
        elif skill_id == "build-project":
            crew = create_build_project_crew(input_text)
        elif skill_id == "grant-hunt":
            crew = create_grant_hunt_crew(input_text)
        elif skill_id == "content":
            crew = create_content_crew(input_text)
        elif skill_id == "daily-ops":
            crew = create_daily_ops_crew()
        elif skill_id == "enigma-audit":
            crew = create_enigma_audit_crew(input_text)
        else:
            return {"error": f"Unknown skill: {skill_id}"}

        result = run_crew_supervised(
            crew_name=skill_id,
            crew=crew,
            input_text=input_text,
            max_retries=3,
        )

        status_mapped = "completed" if result["status"] == "ok" else result["status"]
        sup = result.get("supervisor")
        gov = result.get("governance")

        logger.info(f"Skill '{skill_id}' {status_mapped} in {result.get('elapsed_ms', 0):.0f}ms")

        return {
            "status": status_mapped,
            "skill": skill_id,
            "result": result.get("output", ""),
            "elapsed_seconds": result.get("elapsed_ms", 0) / 1000,
            "run_id": result.get("run_id"),
            "supervisor": {
                "decision": sup["decision"],
                "score": sup["score"],
            } if sup else None,
            "governance": {
                "passed": gov["passed"],
                "score": gov["score"],
            } if gov else None,
            "retries": result.get("retries", 0),
        }

    except Exception as e:
        logger.error(f"Skill '{skill_id}' failed: {e}")
        return {"status": "error", "skill": skill_id, "error": str(e)}


# ═══════════════════════════════════════════════════════
# HTTP SERVER — A2A Protocol
# ═══════════════════════════════════════════════════════

class A2AHandler(BaseHTTPRequestHandler):
    """HTTP handler implementing simplified A2A protocol."""

    def do_GET(self):
        if self.path == "/.well-known/agent-card.json":
            self._send_json(200, AGENT_CARD)
        elif self.path == "/health":
            self._send_json(200, {"status": "ok", "agents": 8, "crews": 11})
        elif self.path == "/skills":
            self._send_json(200, {"skills": AGENT_CARD["skills"]})
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length)

        # HMAC Authentication
        valid, reason = _verify_hmac(dict(self.headers), body_bytes)
        if not valid:
            logger.warning(f"Auth failed: {reason}")
            self._send_json(401, {"error": "Unauthorized", "reason": reason})
            return

        try:
            data = json.loads(body_bytes.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return

        # JSON-RPC style
        if "method" in data:
            method = data["method"]
            params = data.get("params", {})

            if method == "tasks/send":
                skill_id = params.get("skill_id", "research")
                input_text = params.get("input", params.get("message", ""))
                result = execute_skill(skill_id, input_text)
                self._send_json(200, {"jsonrpc": "2.0", "result": result, "id": data.get("id")})

            elif method == "agent/discover":
                self._send_json(200, {"jsonrpc": "2.0", "result": AGENT_CARD, "id": data.get("id")})

            else:
                self._send_json(400, {"error": f"Unknown method: {method}"})

        # Simple REST style
        elif "skill" in data:
            result = execute_skill(data["skill"], data.get("input", ""))
            self._send_json(200, result)

        else:
            self._send_json(400, {"error": "Missing 'method' or 'skill' in request body"})

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", os.getenv("A2A_ALLOWED_ORIGIN", "*"))
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Api-Key, X-Timestamp, X-Signature")
        self.send_header("Access-Control-Max-Age", "3600")
        self.end_headers()

    def _send_json(self, status: int, data: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", os.getenv("A2A_ALLOWED_ORIGIN", "*"))
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))

    def log_message(self, format, *args):
        logger.info(f"[A2A] {args[0]}")


def start_server(port: int = 8000):
    """Start the A2A server."""
    server = HTTPServer(("0.0.0.0", port), A2AHandler)
    logger.info(f"A2A Server running on http://localhost:{port}")
    logger.info(f"Agent card: http://localhost:{port}/.well-known/agent-card.json")
    logger.info(f"Health: http://localhost:{port}/health")
    logger.info(f"Skills: {[s['id'] for s in AGENT_CARD['skills']]}")
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enigma A2A Server")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    start_server(args.port)
