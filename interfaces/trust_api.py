"""
trust_api.py — Trust Score API pública para agentes ERC-8004.

Cualquier agente puede consultar el trust score de otro agente.
Usa solo stdlib (http.server) — sin FastAPI ni frameworks externos.

Endpoints:
  GET  /health                              — status del servicio
  GET  /api/v1/trust-score/<agent_id>       — trust score de un agente
  GET  /api/v1/governance/verify/<proof_hash> — verificar governance proof
  GET  /api/v1/stats                        — estadísticas del servicio
  POST /api/v1/governance/attest            — recibir output y generar proof

Uso:
  PYTHONPATH=. python3 interfaces/trust_api.py --port 8004

Cyber Paisa / Enigma Group — DOF Mesh Legion
"""

import argparse
import hashlib
import json
import logging
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger("trust_api")

# ═══════════════════════════════════════════════════════
# Constantes
# ═══════════════════════════════════════════════════════

RATE_LIMIT_MAX = 100  # max requests per minute per IP
RATE_LIMIT_WINDOW = 60  # seconds
VALID_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")

# ═══════════════════════════════════════════════════════
# Modelos de datos
# ═══════════════════════════════════════════════════════


@dataclass
class TrustBreakdown:
    """Desglose del trust score por dimensión."""
    engagement: float = 0.0
    service: float = 0.0
    publisher: float = 0.0
    compliance: float = 0.0
    momentum: float = 0.0


@dataclass
class TrustResult:
    """Resultado completo del trust score."""
    agent_id: str = ""
    score: float = 0.0
    classification: str = "poor"
    breakdown: TrustBreakdown = field(default_factory=TrustBreakdown)
    valid_format: bool = False
    scored_at: str = ""


@dataclass
class GovernanceProof:
    """Proof de governance generado por attestation."""
    proof_hash: str = ""
    agent_id: str = ""
    output_hash: str = ""
    timestamp: str = ""
    verified: bool = False


# ═══════════════════════════════════════════════════════
# Rate Limiter (in-memory)
# ═══════════════════════════════════════════════════════


class RateLimiter:
    """Rate limiter simple: max N requests por ventana de tiempo por IP."""

    def __init__(self, max_requests: int = RATE_LIMIT_MAX, window_seconds: int = RATE_LIMIT_WINDOW):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, ip: str) -> bool:
        """Retorna True si la IP no ha excedido el límite."""
        now = time.time()
        cutoff = now - self.window_seconds
        # Limpiar entradas viejas
        self._requests[ip] = [t for t in self._requests[ip] if t > cutoff]
        if len(self._requests[ip]) >= self.max_requests:
            return False
        self._requests[ip].append(now)
        return True

    def reset(self):
        """Reset para testing."""
        self._requests.clear()


# ═══════════════════════════════════════════════════════
# Trust Score Engine (determinístico)
# ═══════════════════════════════════════════════════════


def _deterministic_hash(agent_id: str) -> int:
    """Hash determinístico del agent_id para generar scores reproducibles."""
    return int(hashlib.sha256(agent_id.encode()).hexdigest(), 16)


def compute_trust_score(agent_id: str) -> TrustResult:
    """
    Calcula el trust score de un agente de forma determinística.

    Score base 50 + bonuses por:
    - Formato válido de address (0x...)
    - Hash-based simulated history length
    - Hash-based simulated attestations
    - Hash-based simulated health status
    """
    now = datetime.now(timezone.utc).isoformat()
    valid = bool(VALID_ADDRESS_RE.match(agent_id))

    if not valid:
        return TrustResult(
            agent_id=agent_id,
            score=0.0,
            classification="invalid",
            breakdown=TrustBreakdown(),
            valid_format=False,
            scored_at=now,
        )

    h = _deterministic_hash(agent_id)

    # Score base 50
    base = 50.0

    # Bonus por "historial" simulado (0-15 puntos) — Engagement (30%)
    history_bonus = (h % 16)
    engagement = min(30.0, history_bonus * 2.0)

    # Bonus por "attestations on-chain" simulado (0-10 puntos) — Service (25%)
    attest_bonus = ((h >> 8) % 11)
    service = min(25.0, attest_bonus * 2.5)

    # Bonus por "health endpoint activo" simulado (0 o 10) — Publisher (20%)
    health_active = ((h >> 16) % 3) != 0  # 2/3 probability
    publisher = 20.0 if health_active else 5.0

    # Compliance — basado en checksum validity (15%)
    checksum_ok = ((h >> 24) % 4) != 0  # 3/4 probability
    compliance = 15.0 if checksum_ok else 3.0

    # Momentum — basado en actividad reciente simulada (10%)
    momentum = min(10.0, ((h >> 32) % 11))

    breakdown = TrustBreakdown(
        engagement=round(engagement, 1),
        service=round(service, 1),
        publisher=round(publisher, 1),
        compliance=round(compliance, 1),
        momentum=round(momentum, 1),
    )

    total = base + engagement + service + publisher + compliance + momentum
    score = min(100.0, round(total, 1))

    # Clasificación
    if score >= 85:
        classification = "excellent"
    elif score >= 70:
        classification = "good"
    elif score >= 50:
        classification = "acceptable"
    else:
        classification = "poor"

    return TrustResult(
        agent_id=agent_id,
        score=score,
        classification=classification,
        breakdown=breakdown,
        valid_format=True,
        scored_at=now,
    )


# ═══════════════════════════════════════════════════════
# Governance Proof Engine
# ═══════════════════════════════════════════════════════

# In-memory store de proofs (para el servicio)
_proof_store: dict[str, GovernanceProof] = {}


def generate_governance_proof(agent_id: str, output_data: str) -> GovernanceProof:
    """Genera un proof hash para un output de governance."""
    now = datetime.now(timezone.utc).isoformat()
    output_hash = hashlib.sha256(output_data.encode()).hexdigest()
    combined = f"{agent_id}:{output_hash}:{now}"
    proof_hash = hashlib.sha256(combined.encode()).hexdigest()

    proof = GovernanceProof(
        proof_hash=proof_hash,
        agent_id=agent_id,
        output_hash=output_hash,
        timestamp=now,
        verified=True,
    )
    _proof_store[proof_hash] = proof
    return proof


def verify_governance_proof(proof_hash: str) -> Optional[GovernanceProof]:
    """Verifica si un proof hash existe y es válido."""
    return _proof_store.get(proof_hash)


# ═══════════════════════════════════════════════════════
# Trust API Server
# ═══════════════════════════════════════════════════════


class TrustAPIServer:
    """
    Servidor HTTP para Trust Score API pública.
    Usa solo stdlib — sin FastAPI ni uvicorn.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8004):
        self.host = host
        self.port = port
        self._start_time = time.time()
        self._total_queries = 0
        self._agents_scored: set[str] = set()
        self._rate_limiter = RateLimiter()
        logger.info("TrustAPI ready: %s:%d", host, port)

    def get_stats(self) -> dict:
        """Estadísticas del servicio."""
        return {
            "total_queries": self._total_queries,
            "agents_scored": len(self._agents_scored),
            "uptime_seconds": round(time.time() - self._start_time),
            "proofs_stored": len(_proof_store),
            "rate_limit": f"{RATE_LIMIT_MAX}/min",
        }

    def run(self):
        """Arranca el servidor HTTP."""
        server_ref = self

        class Handler(TrustAPIHandler):
            server_instance = server_ref

        httpd = HTTPServer((self.host, self.port), Handler)
        logger.info("Trust Score API escuchando en http://%s:%d", self.host, self.port)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Trust API detenida.")
            httpd.server_close()


class TrustAPIHandler(BaseHTTPRequestHandler):
    """Handler HTTP para todos los endpoints de Trust API."""

    server_instance: "TrustAPIServer" = None  # Set by TrustAPIServer.run()

    def log_message(self, fmt, *args):
        logger.debug(fmt, *args)

    # ── Helpers ──────────────────────────────────────────

    def _get_client_ip(self) -> str:
        forwarded = self.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return self.client_address[0] if self.client_address else "unknown"

    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _json_response(self, code: int, data: dict, success: bool = True):
        response = {
            "success": success,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        body = json.dumps(response, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _error_response(self, code: int, message: str):
        self._json_response(code, {"error": message}, success=False)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw)

    def _check_rate_limit(self) -> bool:
        """Retorna True si se permite la request. Si no, envía 429."""
        srv = self.server_instance
        if srv is None:
            return True
        ip = self._get_client_ip()
        if not srv._rate_limiter.is_allowed(ip):
            self._error_response(429, "Rate limit exceeded. Max 100 requests/min.")
            return False
        return True

    # ── Routes ───────────────────────────────────────────

    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        if not self._check_rate_limit():
            return

        srv = self.server_instance
        if srv:
            srv._total_queries += 1

        path = self.path.split("?")[0].rstrip("/")

        if path == "/health":
            self._handle_health()
        elif path.startswith("/api/v1/trust-score/"):
            agent_id = path.split("/api/v1/trust-score/", 1)[1]
            self._handle_trust_score(agent_id)
        elif path.startswith("/api/v1/governance/verify/"):
            proof_hash = path.split("/api/v1/governance/verify/", 1)[1]
            self._handle_governance_verify(proof_hash)
        elif path == "/api/v1/stats":
            self._handle_stats()
        else:
            self._error_response(404, f"Not found: {path}")

    def do_POST(self):
        if not self._check_rate_limit():
            return

        srv = self.server_instance
        if srv:
            srv._total_queries += 1

        path = self.path.split("?")[0].rstrip("/")

        if path == "/api/v1/governance/attest":
            self._handle_governance_attest()
        else:
            self._error_response(404, f"Not found: {path}")

    # ── Handlers ─────────────────────────────────────────

    def _handle_health(self):
        srv = self.server_instance
        uptime = round(time.time() - srv._start_time) if srv else 0
        self._json_response(200, {
            "status": "ok",
            "service": "DOF-MESH Trust Score API",
            "version": "1.0.0",
            "uptime_seconds": uptime,
        })

    def _handle_trust_score(self, agent_id: str):
        result = compute_trust_score(agent_id)
        srv = self.server_instance
        if srv and result.valid_format:
            srv._agents_scored.add(agent_id)

        if not result.valid_format:
            self._json_response(400, {
                "error": "Invalid agent_id format. Expected 0x... (40 hex chars)",
                "agent_id": agent_id,
            }, success=False)
            return

        self._json_response(200, asdict(result))

    def _handle_governance_verify(self, proof_hash: str):
        proof = verify_governance_proof(proof_hash)
        if proof:
            self._json_response(200, asdict(proof))
        else:
            self._json_response(404, {
                "error": "Proof not found",
                "proof_hash": proof_hash,
            }, success=False)

    def _handle_stats(self):
        srv = self.server_instance
        if srv:
            self._json_response(200, srv.get_stats())
        else:
            self._json_response(200, {
                "total_queries": 0,
                "agents_scored": 0,
                "uptime_seconds": 0,
                "proofs_stored": 0,
                "rate_limit": f"{RATE_LIMIT_MAX}/min",
            })

    def _handle_governance_attest(self):
        try:
            body = self._read_body()
        except (json.JSONDecodeError, ValueError):
            self._error_response(400, "Invalid JSON body")
            return

        agent_id = body.get("agent_id", "")
        output_data = body.get("output", "")

        if not agent_id:
            self._error_response(400, "Missing required field: agent_id")
            return
        if not output_data:
            self._error_response(400, "Missing required field: output")
            return

        proof = generate_governance_proof(agent_id, output_data)
        self._json_response(201, asdict(proof))


# ═══════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )
    parser = argparse.ArgumentParser(description="DOF-MESH Trust Score API")
    parser.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8004, help="Port (default: 8004)")
    args = parser.parse_args()

    server = TrustAPIServer(host=args.host, port=args.port)
    server.run()
