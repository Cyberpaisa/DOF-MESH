"""
Sentinel Lite v2 — Motor de validación unificado para agentes autónomos.

Integra lógica de 3 fuentes:
- Super-Sentinel: 10 checks individuales (health, tls, latency, a2a, mcp, x402,
  on_chain, proxy, ratings, identity)
- TRACER Protocol: 6 dimensiones de scoring (Trust, Reliability, Autonomy,
  Capability, Economics, Reputation)
- Survival Engine: Estado económico del agente (THRIVING, SUSTAINABLE,
  CONSERVATION, DEAD)

Solo stdlib: hashlib, urllib, ssl, json, socket, concurrent.futures.
Ejecución paralela con ThreadPoolExecutor.
"""

import hashlib
import json
import logging
import os
import re
import socket
import ssl
import struct
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("core.sentinel_lite")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SENTINEL_LOG_DIR = os.path.join(BASE_DIR, "logs", "sentinel")
VALIDATIONS_FILE = os.path.join(SENTINEL_LOG_DIR, "validations.jsonl")

# ── Constantes ───────────────────────────────────────────────────────────────

DEFAULT_RPC = "https://api.avax.network/ext/bc/C/rpc"

TRACER_WEIGHTS = {
    "trust": 0.20,
    "reliability": 0.20,
    "autonomy": 0.15,
    "capability": 0.20,
    "economics": 0.10,
    "reputation": 0.15,
}

SCORE_THRESHOLDS = {
    "PASS": 70,
    "PARTIAL": 40,
    "FAIL": 0,
}

SURVIVAL_TIERS = {
    "THRIVING": 100.0,
    "SUSTAINABLE": 10.0,
    "CONSERVATION": 0.0,
    "DEAD": -1.0,  # balance exactamente 0 o negativo
}

TLS_GRADES = {
    "A+": 100,
    "A": 90,
    "B": 70,
    "C": 50,
    "D": 30,
    "F": 10,
}

TRACER_CLASSIFICATIONS = {
    "excellent": 80,
    "good": 65,
    "acceptable": 50,
    "poor": 35,
    "unreliable": 0,
}

# EIP-1967 implementation slot
EIP1967_IMPL_SLOT = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"

# ── Dataclasses ──────────────────────────────────────────────────────────────


@dataclass
class SentinelCheck:
    """Resultado de un check individual del Sentinel."""
    name: str
    score: int  # 0-100
    max_score: int
    passed: bool
    data: Dict[str, Any] = field(default_factory=dict)
    elapsed_ms: float = 0.0


@dataclass
class TRACERScore:
    """Score TRACER con 6 dimensiones."""
    total: float  # 0-100
    classification: str  # excellent, good, acceptable, poor, unreliable
    dimensions: Dict[str, float] = field(default_factory=dict)
    weights: Dict[str, float] = field(default_factory=lambda: dict(TRACER_WEIGHTS))
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class SurvivalStatus:
    """Estado económico del agente (Survival Engine)."""
    tier: str  # THRIVING, SUSTAINABLE, CONSERVATION, DEAD
    balance_usdc: float
    hours_until_death: float
    should_reduce: bool
    costs_per_hour: float
    earnings_per_hour: float


@dataclass
class ValidationReport:
    """Reporte completo de validación."""
    agent_address: str
    overall_score: float
    result: str  # PASS, PARTIAL, FAIL
    checks: List[SentinelCheck] = field(default_factory=list)
    tracer: Optional[TRACERScore] = None
    survival: Optional[SurvivalStatus] = None
    timestamp: str = ""
    valid_until: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        d = {
            "agent_address": self.agent_address,
            "overall_score": self.overall_score,
            "result": self.result,
            "checks": [asdict(c) for c in self.checks],
            "timestamp": self.timestamp,
            "valid_until": self.valid_until,
        }
        if self.tracer:
            d["tracer"] = asdict(self.tracer)
        if self.survival:
            d["survival"] = asdict(self.survival)
        return d


# ── Sentinel Engine ──────────────────────────────────────────────────────────


class SentinelEngine:
    """Motor de validación unificado: 10 checks + TRACER + Survival."""

    def __init__(self, log_path: str = "", max_workers: int = 6):
        self._log_path = log_path or VALIDATIONS_FILE
        self._max_workers = max_workers

    # ── 10 Checks individuales ────────────────────────────────────────────

    def check_health(self, endpoint: str) -> SentinelCheck:
        """GET /health o /api/health — 200 en <5s → passed."""
        start = time.time()
        base = endpoint.rstrip("/")
        paths = ["/health", "/api/health"]
        for path in paths:
            url = base + path
            try:
                req = urllib.request.Request(url, method="GET")
                resp = urllib.request.urlopen(req, timeout=5)
                code = resp.getcode()
                if code == 200:
                    elapsed = time.time() - start
                    return SentinelCheck(
                        name="health", score=100, max_score=100,
                        passed=True,
                        data={"url": url, "status": code, "time_s": round(elapsed, 3)},
                        elapsed_ms=round(elapsed * 1000, 1),
                    )
            except Exception:
                continue
        elapsed_ms = round((time.time() - start) * 1000, 1)
        return SentinelCheck(
            name="health", score=0, max_score=100, passed=False,
            data={"error": "Health endpoint unreachable"},
            elapsed_ms=elapsed_ms,
        )

    def check_tls(self, endpoint: str) -> SentinelCheck:
        """Verificar SSL/certificado: grade A+ a F, días restantes."""
        start = time.time()
        try:
            from urllib.parse import urlparse
            parsed = urlparse(endpoint)
            hostname = parsed.hostname or ""
            port = parsed.port or 443

            if parsed.scheme == "http":
                return SentinelCheck(
                    name="tls", score=0, max_score=100, passed=False,
                    data={"error": "Not HTTPS", "grade": "F"},
                    elapsed_ms=round((time.time() - start) * 1000, 1),
                )

            ctx = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=5) as sock:
                with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    version = ssock.version()

            # Calcular días restantes
            not_after = cert.get("notAfter", "")
            days_remaining = -1
            if not_after:
                try:
                    expire = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                    days_remaining = (expire - datetime.utcnow()).days
                except ValueError:
                    pass

            # Determinar grade
            grade = self._tls_grade(version or "", days_remaining, cipher)
            score = TLS_GRADES.get(grade, 10)

            return SentinelCheck(
                name="tls", score=score, max_score=100,
                passed=score >= 50,
                data={
                    "grade": grade,
                    "version": version,
                    "cipher": cipher[0] if cipher else "unknown",
                    "days_remaining": days_remaining,
                    "issuer": str(cert.get("issuer", "")),
                },
                elapsed_ms=round((time.time() - start) * 1000, 1),
            )
        except Exception as e:
            return SentinelCheck(
                name="tls", score=0, max_score=100, passed=False,
                data={"error": str(e)[:200], "grade": "F"},
                elapsed_ms=round((time.time() - start) * 1000, 1),
            )

    @staticmethod
    def _tls_grade(version: str, days_remaining: int, cipher: tuple = None) -> str:
        """Calcula grade TLS basado en versión, cipher y cert."""
        if "TLSv1.3" in version:
            base = "A+"
        elif "TLSv1.2" in version:
            base = "A"
        elif "TLSv1.1" in version:
            base = "C"
        elif "TLSv1" in version:
            base = "D"
        else:
            base = "F"

        # Degradar por certificado próximo a expirar
        if 0 <= days_remaining < 7:
            base = "D"
        elif 0 <= days_remaining < 30:
            # Bajar un grado
            grades_order = ["A+", "A", "B", "C", "D", "F"]
            idx = grades_order.index(base) if base in grades_order else 5
            base = grades_order[min(idx + 1, 5)]

        return base

    def check_latency(self, endpoint: str) -> SentinelCheck:
        """Medir tiempo de respuesta. <200ms=100, <500=80, <1s=60, <3s=40, >3s=20."""
        start = time.time()
        base = endpoint.rstrip("/")
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
                    return SentinelCheck(
                        name="latency", score=score, max_score=100,
                        passed=score >= 40,
                        data={"latency_ms": round(latency_ms, 1), "url": url},
                        elapsed_ms=round((time.time() - start) * 1000, 1),
                    )
            except Exception:
                continue
        return SentinelCheck(
            name="latency", score=0, max_score=100, passed=False,
            data={"error": "Could not measure latency"},
            elapsed_ms=round((time.time() - start) * 1000, 1),
        )

    def check_a2a(self, endpoint: str) -> SentinelCheck:
        """Verificar /.well-known/agent.json."""
        start = time.time()
        base = endpoint.rstrip("/")
        paths = ["/.well-known/agent.json", "/api/agent-card"]
        for path in paths:
            url = base + path
            try:
                req = urllib.request.Request(url, method="GET")
                resp = urllib.request.urlopen(req, timeout=5)
                if resp.getcode() == 200:
                    body = resp.read().decode("utf-8", errors="replace")
                    try:
                        agent_data = json.loads(body)
                    except json.JSONDecodeError:
                        agent_data = {}
                    return SentinelCheck(
                        name="a2a", score=100, max_score=100,
                        passed=True,
                        data={"path": path, "has_skills": "skills" in agent_data},
                        elapsed_ms=round((time.time() - start) * 1000, 1),
                    )
            except Exception:
                continue
        return SentinelCheck(
            name="a2a", score=0, max_score=100, passed=False,
            data={"error": "No A2A endpoint found"},
            elapsed_ms=round((time.time() - start) * 1000, 1),
        )

    def check_mcp(self, metadata: dict) -> SentinelCheck:
        """Contar tools en metadata. >10→100, >5→80, >0→60, 0→30."""
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
        return SentinelCheck(
            name="mcp", score=score, max_score=100,
            passed=count > 0,
            data={"tool_count": count},
            elapsed_ms=round((time.time() - start) * 1000, 1),
        )

    def check_x402(self, metadata_or_endpoint: Any) -> SentinelCheck:
        """Buscar x402/payment en metadata dict o endpoint URL."""
        start = time.time()

        # Si es dict → verificar offline
        if isinstance(metadata_or_endpoint, dict):
            text = json.dumps(metadata_or_endpoint).lower()
            found = "x402" in text or "payment" in text
            return SentinelCheck(
                name="x402", score=100 if found else 0, max_score=100,
                passed=found,
                data={"source": "metadata", "found": found},
                elapsed_ms=round((time.time() - start) * 1000, 1),
            )

        # Si es str → GET endpoint
        if isinstance(metadata_or_endpoint, str):
            base = metadata_or_endpoint.rstrip("/")
            paths = ["/.well-known/agent.json", "/api/agent-card"]
            for path in paths:
                url = base + path
                try:
                    req = urllib.request.Request(url, method="GET")
                    resp = urllib.request.urlopen(req, timeout=5)
                    body = resp.read().decode("utf-8", errors="replace").lower()
                    if "x402" in body or "payment" in body:
                        return SentinelCheck(
                            name="x402", score=100, max_score=100,
                            passed=True,
                            data={"source": "endpoint", "url": url},
                            elapsed_ms=round((time.time() - start) * 1000, 1),
                        )
                except Exception:
                    continue

        return SentinelCheck(
            name="x402", score=0, max_score=100, passed=False,
            data={"error": "No x402 capability detected"},
            elapsed_ms=round((time.time() - start) * 1000, 1),
        )

    def check_on_chain(self, address: str, rpc_url: str = DEFAULT_RPC) -> SentinelCheck:
        """eth_getCode via JSON-RPC — verificar si address es contrato."""
        start = time.time()
        try:
            payload = json.dumps({
                "jsonrpc": "2.0",
                "method": "eth_getCode",
                "params": [address, "latest"],
                "id": 1,
            }).encode()
            req = urllib.request.Request(
                rpc_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=10)
            result = json.loads(resp.read().decode("utf-8"))
            code = result.get("result", "0x")
            is_contract = code not in ("0x", "0x0", "")
            return SentinelCheck(
                name="on_chain", score=100 if is_contract else 40, max_score=100,
                passed=True,
                data={
                    "is_contract": is_contract,
                    "code_length": len(code) if code else 0,
                    "rpc": rpc_url,
                },
                elapsed_ms=round((time.time() - start) * 1000, 1),
            )
        except Exception as e:
            return SentinelCheck(
                name="on_chain", score=0, max_score=100, passed=False,
                data={"error": str(e)[:200]},
                elapsed_ms=round((time.time() - start) * 1000, 1),
            )

    def check_proxy(self, address: str, rpc_url: str = DEFAULT_RPC) -> SentinelCheck:
        """Detectar si address es proxy — verificar EIP-1967 storage slot."""
        start = time.time()
        try:
            payload = json.dumps({
                "jsonrpc": "2.0",
                "method": "eth_getStorageAt",
                "params": [address, EIP1967_IMPL_SLOT, "latest"],
                "id": 1,
            }).encode()
            req = urllib.request.Request(
                rpc_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=10)
            result = json.loads(resp.read().decode("utf-8"))
            storage_val = result.get("result", "0x" + "0" * 64)

            # Si el slot tiene un valor distinto a 0x00...00, es proxy
            is_proxy = storage_val != "0x" + "0" * 64 and storage_val != "0x"
            impl_address = "0x" + storage_val[-40:] if is_proxy else None

            return SentinelCheck(
                name="proxy", score=80 if is_proxy else 50, max_score=100,
                passed=True,
                data={
                    "is_proxy": is_proxy,
                    "implementation": impl_address,
                    "slot": EIP1967_IMPL_SLOT,
                },
                elapsed_ms=round((time.time() - start) * 1000, 1),
            )
        except Exception as e:
            return SentinelCheck(
                name="proxy", score=0, max_score=100, passed=False,
                data={"error": str(e)[:200]},
                elapsed_ms=round((time.time() - start) * 1000, 1),
            )

    def check_ratings(self, ratings_list: list) -> SentinelCheck:
        """Score basado en volumen de reviews + promedio."""
        start = time.time()
        if not ratings_list:
            return SentinelCheck(
                name="ratings", score=0, max_score=100, passed=False,
                data={"count": 0, "average": 0},
                elapsed_ms=round((time.time() - start) * 1000, 1),
            )
        count = len(ratings_list)
        avg = sum(ratings_list) / count

        # Scoring: volumen (40%) + promedio normalizado a 100 (60%)
        if count >= 50:
            volume_score = 100
        elif count >= 20:
            volume_score = 80
        elif count >= 5:
            volume_score = 60
        elif count >= 1:
            volume_score = 40
        else:
            volume_score = 0

        # avg se asume en rango 0-5
        avg_score = min(100, (avg / 5.0) * 100)
        score = round(volume_score * 0.4 + avg_score * 0.6)

        return SentinelCheck(
            name="ratings", score=score, max_score=100,
            passed=score >= 40,
            data={"count": count, "average": round(avg, 2), "volume_score": volume_score},
            elapsed_ms=round((time.time() - start) * 1000, 1),
        )

    def check_identity(self, address: str) -> SentinelCheck:
        """Formato válido 0x + 40 hex. Genera identity_hash determinístico."""
        start = time.time()
        pattern = r"^0x[0-9a-fA-F]{40}$"
        if re.match(pattern, address):
            identity_hash = hashlib.sha256(
                f"{address}:43114".encode()
            ).hexdigest()
            return SentinelCheck(
                name="identity", score=80, max_score=100,
                passed=True,
                data={
                    "valid": True,
                    "identity_hash": identity_hash,
                    "chain_id": 43114,
                },
                elapsed_ms=round((time.time() - start) * 1000, 1),
            )
        return SentinelCheck(
            name="identity", score=0, max_score=100,
            passed=False,
            data={"valid": False, "address": address[:50]},
            elapsed_ms=round((time.time() - start) * 1000, 1),
        )

    # ── TRACER Scoring ────────────────────────────────────────────────────

    @staticmethod
    def calculate_tracer(
        checks: List[SentinelCheck],
        metrics: Optional[Dict[str, Any]] = None,
    ) -> TRACERScore:
        """Calcula score TRACER con 6 dimensiones a partir de checks.

        Mapeo de checks a dimensiones:
        - Trust ← tls, proxy, identity
        - Reliability ← health, latency
        - Autonomy ← mcp, a2a
        - Capability ← on_chain, mcp
        - Economics ← x402
        - Reputation ← ratings
        """
        checks_by_name = {c.name: c for c in checks}
        metrics = metrics or {}

        # Trust (20%): tls, proxy, identity
        trust_scores = []
        for name in ("tls", "proxy", "identity"):
            if name in checks_by_name:
                trust_scores.append(checks_by_name[name].score)
        # Enriquecer con métricas opcionales
        if metrics.get("has_verified_wallet"):
            trust_scores.append(100)
        if metrics.get("is_open_source"):
            trust_scores.append(80)
        if metrics.get("has_audits"):
            trust_scores.append(90)
        trust = sum(trust_scores) / len(trust_scores) if trust_scores else 0

        # Reliability (20%): health, latency
        reliability_scores = []
        for name in ("health", "latency"):
            if name in checks_by_name:
                reliability_scores.append(checks_by_name[name].score)
        if metrics.get("uptime_percent") is not None:
            reliability_scores.append(metrics["uptime_percent"])
        if metrics.get("success_rate") is not None:
            reliability_scores.append(metrics["success_rate"] * 100)
        reliability = sum(reliability_scores) / len(reliability_scores) if reliability_scores else 0

        # Autonomy (15%): mcp, a2a
        autonomy_scores = []
        for name in ("mcp", "a2a"):
            if name in checks_by_name:
                autonomy_scores.append(checks_by_name[name].score)
        if metrics.get("can_delegate"):
            autonomy_scores.append(80)
        if metrics.get("has_auto_recovery"):
            autonomy_scores.append(90)
        autonomy = sum(autonomy_scores) / len(autonomy_scores) if autonomy_scores else 0

        # Capability (20%): on_chain, mcp
        capability_scores = []
        for name in ("on_chain", "mcp"):
            if name in checks_by_name:
                capability_scores.append(checks_by_name[name].score)
        if metrics.get("skills_verified"):
            capability_scores.append(min(100, metrics["skills_verified"] * 10))
        if metrics.get("certifications"):
            capability_scores.append(min(100, metrics["certifications"] * 20))
        capability = sum(capability_scores) / len(capability_scores) if capability_scores else 0

        # Economics (10%): x402
        economics_scores = []
        if "x402" in checks_by_name:
            economics_scores.append(checks_by_name["x402"].score)
        if metrics.get("gas_efficiency") is not None:
            economics_scores.append(metrics["gas_efficiency"])
        if metrics.get("total_transactions") is not None:
            txs = metrics["total_transactions"]
            if txs >= 1000:
                economics_scores.append(100)
            elif txs >= 100:
                economics_scores.append(80)
            elif txs >= 10:
                economics_scores.append(60)
            else:
                economics_scores.append(30)
        economics = sum(economics_scores) / len(economics_scores) if economics_scores else 0

        # Reputation (15%): ratings
        reputation_scores = []
        if "ratings" in checks_by_name:
            reputation_scores.append(checks_by_name["ratings"].score)
        if metrics.get("feedback_score") is not None:
            reputation_scores.append(metrics["feedback_score"])
        if metrics.get("trust_connections") is not None:
            conns = metrics["trust_connections"]
            if conns >= 20:
                reputation_scores.append(100)
            elif conns >= 5:
                reputation_scores.append(70)
            else:
                reputation_scores.append(40)
        reputation = sum(reputation_scores) / len(reputation_scores) if reputation_scores else 0

        dimensions = {
            "trust": round(trust, 2),
            "reliability": round(reliability, 2),
            "autonomy": round(autonomy, 2),
            "capability": round(capability, 2),
            "economics": round(economics, 2),
            "reputation": round(reputation, 2),
        }

        # Total ponderado
        total = sum(
            dimensions[dim] * TRACER_WEIGHTS[dim]
            for dim in TRACER_WEIGHTS
        )
        total = round(total, 2)

        # Classification
        if total >= 80:
            classification = "excellent"
        elif total >= 65:
            classification = "good"
        elif total >= 50:
            classification = "acceptable"
        elif total >= 35:
            classification = "poor"
        else:
            classification = "unreliable"

        return TRACERScore(
            total=total,
            classification=classification,
            dimensions=dimensions,
        )

    # ── Survival Engine ───────────────────────────────────────────────────

    @staticmethod
    def calculate_survival(
        balance_usdc: float,
        costs_per_hour: float = 0.01,
        earnings_per_hour: float = 0.0,
    ) -> SurvivalStatus:
        """Calcula estado económico del agente.

        Tiers:
        - THRIVING: balance > $100
        - SUSTAINABLE: balance > $10
        - CONSERVATION: balance > $0
        - DEAD: balance <= $0
        """
        if balance_usdc <= 0:
            tier = "DEAD"
            hours = 0.0
        elif balance_usdc > 100:
            tier = "THRIVING"
            hours = balance_usdc / costs_per_hour if costs_per_hour > 0 else float("inf")
        elif balance_usdc > 10:
            tier = "SUSTAINABLE"
            hours = balance_usdc / costs_per_hour if costs_per_hour > 0 else float("inf")
        else:
            tier = "CONSERVATION"
            hours = balance_usdc / costs_per_hour if costs_per_hour > 0 else float("inf")

        net_rate = earnings_per_hour - costs_per_hour
        # Si las pérdidas superan 24h, recomendar reducir
        should_reduce = tier in ("CONSERVATION", "DEAD")
        if net_rate < 0 and balance_usdc > 0:
            hours_of_loss = balance_usdc / abs(net_rate)
            if hours_of_loss < 24:
                should_reduce = True

        return SurvivalStatus(
            tier=tier,
            balance_usdc=balance_usdc,
            hours_until_death=round(hours, 2),
            should_reduce=should_reduce,
            costs_per_hour=costs_per_hour,
            earnings_per_hour=earnings_per_hour,
        )

    # ── Validación principal ──────────────────────────────────────────────

    def validate(
        self,
        address: str,
        endpoint: Optional[str] = None,
        metadata: Optional[dict] = None,
        rpc_url: Optional[str] = None,
        ratings: Optional[List[float]] = None,
        balance: Optional[float] = None,
        costs_per_hour: float = 0.01,
        earnings_per_hour: float = 0.0,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> ValidationReport:
        """Ejecuta todos los checks en paralelo, calcula TRACER, survival."""
        rpc = rpc_url or DEFAULT_RPC
        meta = metadata or {}

        # Preparar tareas para ejecución paralela
        futures = {}
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            # Identity — siempre
            futures[executor.submit(self.check_identity, address)] = "identity"

            # MCP — siempre si hay metadata
            if meta:
                futures[executor.submit(self.check_mcp, meta)] = "mcp"
                futures[executor.submit(self.check_x402, meta)] = "x402"

            # Checks con endpoint
            if endpoint:
                futures[executor.submit(self.check_health, endpoint)] = "health"
                futures[executor.submit(self.check_latency, endpoint)] = "latency"
                futures[executor.submit(self.check_a2a, endpoint)] = "a2a"
                futures[executor.submit(self.check_tls, endpoint)] = "tls"
                # x402 via endpoint si no hay metadata
                if not meta:
                    futures[executor.submit(self.check_x402, endpoint)] = "x402"

            # Checks on-chain
            if address and re.match(r"^0x[0-9a-fA-F]{40}$", address):
                futures[executor.submit(self.check_on_chain, address, rpc)] = "on_chain"
                futures[executor.submit(self.check_proxy, address, rpc)] = "proxy"

            # Ratings
            if ratings is not None:
                futures[executor.submit(self.check_ratings, ratings)] = "ratings"

            # Recolectar resultados
            checks = []
            for future in as_completed(futures):
                try:
                    check = future.result(timeout=15)
                    checks.append(check)
                except Exception as e:
                    name = futures[future]
                    checks.append(SentinelCheck(
                        name=name, score=0, max_score=100, passed=False,
                        data={"error": str(e)[:200]},
                    ))

        # Calcular TRACER
        tracer = self.calculate_tracer(checks, metrics)

        # Calcular Survival si hay datos
        survival = None
        if balance is not None:
            survival = self.calculate_survival(balance, costs_per_hour, earnings_per_hour)

        # Score general = TRACER total
        overall = tracer.total

        # Resultado
        if overall >= SCORE_THRESHOLDS["PASS"]:
            result_str = "PASS"
        elif overall >= SCORE_THRESHOLDS["PARTIAL"]:
            result_str = "PARTIAL"
        else:
            result_str = "FAIL"

        report = ValidationReport(
            agent_address=address,
            overall_score=overall,
            result=result_str,
            checks=checks,
            tracer=tracer,
            survival=survival,
        )

        self._save(report)
        return report

    def validate_offline(
        self,
        address: str,
        metadata: Optional[dict] = None,
        ratings: Optional[List[float]] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> ValidationReport:
        """Validación sin red — solo checks que no requieren conectividad."""
        checks = []
        meta = metadata or {}

        # Identity
        checks.append(self.check_identity(address))

        # MCP + x402 desde metadata
        if meta:
            checks.append(self.check_mcp(meta))
            checks.append(self.check_x402(meta))

        # Ratings si hay
        if ratings is not None:
            checks.append(self.check_ratings(ratings))

        # TRACER
        tracer = self.calculate_tracer(checks, metrics)

        overall = tracer.total
        if overall >= SCORE_THRESHOLDS["PASS"]:
            result_str = "PASS"
        elif overall >= SCORE_THRESHOLDS["PARTIAL"]:
            result_str = "PARTIAL"
        else:
            result_str = "FAIL"

        report = ValidationReport(
            agent_address=address,
            overall_score=overall,
            result=result_str,
            checks=checks,
            tracer=tracer,
        )

        self._save(report)
        return report

    # ── Storage ───────────────────────────────────────────────────────────

    def _save(self, report: ValidationReport) -> None:
        """Guarda resultado en JSONL."""
        try:
            os.makedirs(os.path.dirname(self._log_path), exist_ok=True)
            with open(self._log_path, "a") as f:
                f.write(json.dumps(report.to_dict(), default=str) + "\n")
        except Exception as e:
            logger.warning("Could not save sentinel result: %s", e)


# ── Backwards compatibility aliases ──────────────────────────────────────────
# Para que código existente que importe SentinelLite siga funcionando

class SentinelLite(SentinelEngine):
    """Alias de compatibilidad para SentinelEngine."""

    def check_erc8004_identity(self, agent_address: str, chain_id: int = 43114) -> SentinelCheck:
        """Alias para check_identity."""
        return self.check_identity(agent_address)

    def check_metadata_dict(self, metadata: dict) -> SentinelCheck:
        """Verifica metadata desde dict — alias para check_mcp con scoring de campos."""
        start = time.time()
        required = {"name", "description", "version"}
        if not isinstance(metadata, dict):
            return SentinelCheck(
                name="metadata", score=0, max_score=100, passed=False,
                data={"error": "Not a dict"},
                elapsed_ms=round((time.time() - start) * 1000, 1),
            )
        present = {k for k in required if metadata.get(k)}
        if present == required:
            score = 100
            details = "All required fields present"
        elif present:
            score = 50
            details = f"Partial: missing {', '.join(sorted(required - present))}"
        else:
            score = 0
            details = "No required fields found"
        return SentinelCheck(
            name="metadata", score=score, max_score=100,
            passed=score >= 50,
            data={"details": details, "present": sorted(present)},
            elapsed_ms=round((time.time() - start) * 1000, 1),
        )

    def check_mcp_tools(self, metadata: dict) -> SentinelCheck:
        """Alias para check_mcp."""
        return self.check_mcp(metadata)

    def check_x402_from_metadata(self, metadata: dict) -> SentinelCheck:
        """Alias para check_x402 con dict."""
        return self.check_x402(metadata)


# ── Alias de dataclasses para compatibilidad ─────────────────────────────────
CheckResult = SentinelCheck
SentinelResult = ValidationReport
