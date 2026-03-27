"""
Sentinel Lite — Validador ligero de agentes externos.

Verifica la confiabilidad de agentes externos antes de interactuar con ellos.
NO depende de Enigma ni de ningún servicio externo — solo stdlib.
Cada check retorna score 0-100. El score compuesto es un promedio ponderado.

Pesos: health(25%), identity(20%), metadata(15%), a2a(15%),
       response_time(10%), mcp(10%), x402(5%).
"""

import hashlib
import json
import logging
import os
import re
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("core.sentinel_lite")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SENTINEL_LOG_DIR = os.path.join(BASE_DIR, "logs", "sentinel")
VALIDATIONS_FILE = os.path.join(SENTINEL_LOG_DIR, "validations.jsonl")

# ── Pesos de cada check ──────────────────────────────────────────────────────

CHECK_WEIGHTS = {
    "health": 0.25,
    "identity": 0.20,
    "metadata": 0.15,
    "a2a": 0.15,
    "response_time": 0.10,
    "mcp_tools": 0.10,
    "x402": 0.05,
}

# ── Dataclasses ──────────────────────────────────────────────────────────────


@dataclass
class CheckResult:
    """Resultado de un check individual."""
    name: str
    score: int
    max_score: int
    details: str
    elapsed_ms: float


@dataclass
class SentinelResult:
    """Resultado completo de la validación Sentinel Lite."""
    agent_address: str
    total_score: int
    verdict: str  # PASS | WARN | FAIL
    checks: dict  # name -> CheckResult (serializado)
    timestamp: str
    checks_run: int
    checks_passed: int  # checks con score >= 60

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# ── Sentinel Lite ────────────────────────────────────────────────────────────

class SentinelLite:
    """Validador ligero de agentes externos para DOF-MESH."""

    def __init__(self, log_path: str = ""):
        self._log_path = log_path or VALIDATIONS_FILE

    # ── Checks individuales ──────────────────────────────────────────────

    def check_health(self, endpoint_url: str) -> CheckResult:
        """GET a /health o /api/health. 200 en <5s → 100, >5s → 50, falla → 0."""
        start = time.time()
        base = endpoint_url.rstrip("/")
        paths = ["/health", "/api/health"]
        for path in paths:
            url = base + path
            try:
                req = urllib.request.Request(url, method="GET")
                t0 = time.time()
                resp = urllib.request.urlopen(req, timeout=5)
                elapsed = time.time() - t0
                code = resp.getcode()
                if code == 200:
                    score = 100 if elapsed < 5.0 else 50
                    return CheckResult(
                        name="health", score=score, max_score=100,
                        details=f"{url} → {code} in {elapsed:.2f}s",
                        elapsed_ms=round((time.time() - start) * 1000, 1),
                    )
            except urllib.error.URLError:
                continue
            except Exception:
                continue
        elapsed_ms = round((time.time() - start) * 1000, 1)
        return CheckResult(
            name="health", score=0, max_score=100,
            details="Health endpoint unreachable",
            elapsed_ms=elapsed_ms,
        )

    def check_erc8004_identity(self, agent_address: str, chain_id: int = 43114) -> CheckResult:
        """Valida formato 0x + 40 hex. Genera identity_hash determinístico."""
        start = time.time()
        pattern = r"^0x[0-9a-fA-F]{40}$"
        if re.match(pattern, agent_address):
            identity_hash = hashlib.sha256(
                f"{agent_address}:{chain_id}".encode()
            ).hexdigest()
            return CheckResult(
                name="identity", score=80, max_score=100,
                details=f"Valid ERC-8004 address, identity_hash={identity_hash[:16]}...",
                elapsed_ms=round((time.time() - start) * 1000, 1),
            )
        return CheckResult(
            name="identity", score=0, max_score=100,
            details=f"Invalid address format: {agent_address}",
            elapsed_ms=round((time.time() - start) * 1000, 1),
        )

    def check_metadata(self, metadata_url: str) -> CheckResult:
        """GET a metadata URL. Verifica campos requeridos: name, description, version."""
        start = time.time()
        required = {"name", "description", "version"}
        try:
            req = urllib.request.Request(metadata_url, method="GET")
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read().decode("utf-8"))
            return self._score_metadata(data, required, start)
        except Exception as e:
            return CheckResult(
                name="metadata", score=0, max_score=100,
                details=f"Metadata fetch failed: {str(e)[:100]}",
                elapsed_ms=round((time.time() - start) * 1000, 1),
            )

    def _score_metadata(self, data: dict, required: set, start: float) -> CheckResult:
        """Puntúa metadata basado en campos presentes."""
        if not isinstance(data, dict):
            return CheckResult(
                name="metadata", score=0, max_score=100,
                details="Metadata is not a dict",
                elapsed_ms=round((time.time() - start) * 1000, 1),
            )
        present = {k for k in required if data.get(k)}
        if present == required:
            score = 100
            details = "All required fields present"
        elif present:
            score = 50
            missing = required - present
            details = f"Partial: missing {', '.join(sorted(missing))}"
        else:
            score = 0
            details = "No required fields found"
        return CheckResult(
            name="metadata", score=score, max_score=100,
            details=details,
            elapsed_ms=round((time.time() - start) * 1000, 1),
        )

    def check_metadata_dict(self, metadata: dict) -> CheckResult:
        """Verifica metadata desde un dict (sin red)."""
        start = time.time()
        required = {"name", "description", "version"}
        return self._score_metadata(metadata, required, start)

    def check_a2a_capability(self, endpoint_url: str) -> CheckResult:
        """Verifica si el agente expone /.well-known/agent.json o /api/agent-card."""
        start = time.time()
        base = endpoint_url.rstrip("/")
        paths = ["/.well-known/agent.json", "/api/agent-card"]
        for path in paths:
            url = base + path
            try:
                req = urllib.request.Request(url, method="GET")
                resp = urllib.request.urlopen(req, timeout=5)
                if resp.getcode() == 200:
                    return CheckResult(
                        name="a2a", score=100, max_score=100,
                        details=f"A2A endpoint found: {path}",
                        elapsed_ms=round((time.time() - start) * 1000, 1),
                    )
            except Exception:
                continue
        return CheckResult(
            name="a2a", score=0, max_score=100,
            details="No A2A endpoint found",
            elapsed_ms=round((time.time() - start) * 1000, 1),
        )

    def check_response_time(self, endpoint_url: str) -> CheckResult:
        """Mide latencia del health endpoint. <200ms→100, <500→80, <1000→60, <3000→40, else→20."""
        start = time.time()
        base = endpoint_url.rstrip("/")
        paths = ["/health", "/api/health"]
        for path in paths:
            url = base + path
            try:
                req = urllib.request.Request(url, method="GET")
                t0 = time.time()
                resp = urllib.request.urlopen(req, timeout=10)
                latency_ms = (time.time() - t0) * 1000
                if resp.getcode() == 200:
                    if latency_ms < 200:
                        score = 100
                    elif latency_ms < 500:
                        score = 80
                    elif latency_ms < 1000:
                        score = 60
                    elif latency_ms < 3000:
                        score = 40
                    else:
                        score = 20
                    return CheckResult(
                        name="response_time", score=score, max_score=100,
                        details=f"Latency: {latency_ms:.0f}ms",
                        elapsed_ms=round((time.time() - start) * 1000, 1),
                    )
            except Exception:
                continue
        return CheckResult(
            name="response_time", score=0, max_score=100,
            details="Could not measure response time",
            elapsed_ms=round((time.time() - start) * 1000, 1),
        )

    def check_mcp_tools(self, metadata: dict) -> CheckResult:
        """Cuenta tools en metadata. >10→100, >5→80, >0→60, 0→30."""
        start = time.time()
        tools = metadata.get("tools") or metadata.get("mcpTools") or []
        count = len(tools) if isinstance(tools, list) else 0
        if count > 10:
            score = 100
        elif count > 5:
            score = 80
        elif count > 0:
            score = 60
        else:
            score = 30
        return CheckResult(
            name="mcp_tools", score=score, max_score=100,
            details=f"{count} tools found",
            elapsed_ms=round((time.time() - start) * 1000, 1),
        )

    def check_x402_capability(self, endpoint_url: str) -> CheckResult:
        """Verifica si el agente tiene endpoints x402 (busca en agent.json)."""
        start = time.time()
        base = endpoint_url.rstrip("/")
        paths = ["/.well-known/agent.json", "/api/agent-card"]
        for path in paths:
            url = base + path
            try:
                req = urllib.request.Request(url, method="GET")
                resp = urllib.request.urlopen(req, timeout=5)
                body = resp.read().decode("utf-8").lower()
                if "x402" in body or "payment" in body:
                    return CheckResult(
                        name="x402", score=100, max_score=100,
                        details="x402/payment capability detected",
                        elapsed_ms=round((time.time() - start) * 1000, 1),
                    )
            except Exception:
                continue
        return CheckResult(
            name="x402", score=0, max_score=100,
            details="No x402 capability detected",
            elapsed_ms=round((time.time() - start) * 1000, 1),
        )

    def check_x402_from_metadata(self, metadata: dict) -> CheckResult:
        """Verifica x402 capability desde metadata dict (sin red)."""
        start = time.time()
        text = json.dumps(metadata).lower()
        if "x402" in text or "payment" in text:
            return CheckResult(
                name="x402", score=100, max_score=100,
                details="x402/payment capability in metadata",
                elapsed_ms=round((time.time() - start) * 1000, 1),
            )
        return CheckResult(
            name="x402", score=0, max_score=100,
            details="No x402 capability in metadata",
            elapsed_ms=round((time.time() - start) * 1000, 1),
        )

    # ── Validación principal ─────────────────────────────────────────────

    def validate(
        self,
        agent_address: str,
        endpoint_url: str | None = None,
        metadata_url: str | None = None,
    ) -> SentinelResult:
        """Ejecuta TODOS los checks disponibles y calcula score compuesto."""
        checks: dict[str, CheckResult] = {}

        # Identity — siempre se ejecuta
        checks["identity"] = self.check_erc8004_identity(agent_address)

        # Checks que requieren endpoint
        if endpoint_url:
            checks["health"] = self.check_health(endpoint_url)
            checks["a2a"] = self.check_a2a_capability(endpoint_url)
            checks["response_time"] = self.check_response_time(endpoint_url)
            checks["x402"] = self.check_x402_capability(endpoint_url)

        # Checks que requieren metadata URL
        if metadata_url:
            checks["metadata"] = self.check_metadata(metadata_url)

        return self._build_result(agent_address, checks)

    def validate_offline(
        self,
        agent_address: str,
        metadata: dict | None = None,
    ) -> SentinelResult:
        """Validación sin red — solo checks que no requieren conectividad."""
        checks: dict[str, CheckResult] = {}

        # Identity — siempre
        checks["identity"] = self.check_erc8004_identity(agent_address)

        # MCP tools si hay metadata
        if metadata:
            checks["mcp_tools"] = self.check_mcp_tools(metadata)
            checks["metadata"] = self.check_metadata_dict(metadata)
            checks["x402"] = self.check_x402_from_metadata(metadata)

        return self._build_result(agent_address, checks)

    # ── Internos ─────────────────────────────────────────────────────────

    def _build_result(
        self,
        agent_address: str,
        checks: dict[str, CheckResult],
    ) -> SentinelResult:
        """Calcula score compuesto y construye SentinelResult."""
        # Promedio ponderado — solo incluye checks que se ejecutaron
        weighted_sum = 0.0
        weight_total = 0.0
        for name, check in checks.items():
            weight = CHECK_WEIGHTS.get(name, 0.0)
            weighted_sum += check.score * weight
            weight_total += weight

        if weight_total > 0:
            total_score = round(weighted_sum / weight_total)
        else:
            total_score = 0

        # Verdict
        if total_score >= 60:
            verdict = "PASS"
        elif total_score >= 40:
            verdict = "WARN"
        else:
            verdict = "FAIL"

        checks_passed = sum(1 for c in checks.values() if c.score >= 60)

        result = SentinelResult(
            agent_address=agent_address,
            total_score=total_score,
            verdict=verdict,
            checks={name: asdict(c) for name, c in checks.items()},
            timestamp=datetime.now(timezone.utc).isoformat(),
            checks_run=len(checks),
            checks_passed=checks_passed,
        )

        # Persistir
        self._save(result)

        return result

    def _save(self, result: SentinelResult) -> None:
        """Guarda resultado en JSONL."""
        try:
            os.makedirs(os.path.dirname(self._log_path), exist_ok=True)
            with open(self._log_path, "a") as f:
                f.write(json.dumps(result.to_dict(), default=str) + "\n")
        except Exception as e:
            logger.warning("Could not save sentinel result: %s", e)
