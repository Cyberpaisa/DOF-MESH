"""
DOF Router — Agent Metrics Tracking.

Tracks per-agent success/failure statistics and latency to inform
intelligent routing decisions. Persists to JSONL for auditability.
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field

logger = logging.getLogger("dof.router.metrics")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_METRICS_PATH = os.path.join(BASE_DIR, "logs", "router", "agent_metrics.jsonl")


@dataclass
class AgentMetrics:
    """Runtime metrics for a single agent in the mesh."""

    agent_id: str
    success_count: int = 0
    failure_count: int = 0
    total_latency_ms: float = 0.0
    consecutive_failures: int = 0
    last_used: float = 0.0  # unix timestamp
    history: list = field(default_factory=list)  # últimas 10 entradas {success, latency_ms, ts}

    @property
    def success_rate(self) -> float:
        """Porcentaje de éxito en las últimas 10 operaciones (0.0 – 1.0)."""
        recent = self.history[-10:] if len(self.history) >= 10 else self.history
        if not recent:
            return 1.0
        return sum(1 for e in recent if e["success"]) / len(recent)

    @property
    def avg_latency_ms(self) -> float:
        """Latencia promedio de las últimas 10 operaciones."""
        recent = self.history[-10:] if len(self.history) >= 10 else self.history
        if not recent:
            return 0.0
        return sum(e["latency_ms"] for e in recent) / len(recent)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_latency_ms": self.total_latency_ms,
            "consecutive_failures": self.consecutive_failures,
            "last_used": self.last_used,
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentMetrics":
        m = cls(agent_id=data["agent_id"])
        m.success_count = data.get("success_count", 0)
        m.failure_count = data.get("failure_count", 0)
        m.total_latency_ms = data.get("total_latency_ms", 0.0)
        m.consecutive_failures = data.get("consecutive_failures", 0)
        m.last_used = data.get("last_used", 0.0)
        m.history = data.get("history", [])
        return m


class MetricsStore:
    """Almacén de métricas para todos los agentes del mesh.

    Soporta actualización en memoria y persistencia en JSONL para auditoría.
    """

    def __init__(self, metrics_path: str = ""):
        self._agents: dict[str, AgentMetrics] = {}
        self._path = metrics_path or DEFAULT_METRICS_PATH
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(self._path), exist_ok=True)

    def get(self, agent_id: str) -> AgentMetrics:
        """Retorna métricas del agente (crea entrada nueva si no existe)."""
        if agent_id not in self._agents:
            self._agents[agent_id] = AgentMetrics(agent_id=agent_id)
        return self._agents[agent_id]

    def update(self, agent_id: str, success: bool, latency_ms: float) -> AgentMetrics:
        """Actualiza métricas para el agente y añade entrada al historial."""
        m = self.get(agent_id)
        m.last_used = time.time()
        m.total_latency_ms += latency_ms

        if success:
            m.success_count += 1
            m.consecutive_failures = 0
        else:
            m.failure_count += 1
            m.consecutive_failures += 1

        # Mantener historial completo (sin límite interno — success_rate usa últimas 10)
        m.history.append({
            "success": success,
            "latency_ms": latency_ms,
            "ts": m.last_used,
        })

        logger.debug(
            f"[metrics] {agent_id} success={success} latency={latency_ms:.1f}ms "
            f"consec_fail={m.consecutive_failures} rate={m.success_rate:.2f}"
        )
        return m

    def all_agents(self) -> list:
        """Retorna lista de todos los AgentMetrics conocidos."""
        return list(self._agents.values())

    def save(self, path: str = "") -> None:
        """Persiste métricas en JSONL (una línea por agente)."""
        target = path or self._path
        os.makedirs(os.path.dirname(target), exist_ok=True)
        try:
            with open(target, "w", encoding="utf-8") as fh:
                for m in self._agents.values():
                    fh.write(json.dumps(m.to_dict()) + "\n")
            logger.debug(f"[metrics] Saved {len(self._agents)} agents → {target}")
        except Exception as exc:
            logger.error(f"[metrics] save failed: {exc}")

    def load(self, path: str = "") -> None:
        """Carga métricas desde JSONL. Combina con estado en memoria."""
        source = path or self._path
        if not os.path.exists(source):
            logger.debug(f"[metrics] No metrics file at {source} — starting fresh")
            return
        try:
            with open(source, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    m = AgentMetrics.from_dict(data)
                    self._agents[m.agent_id] = m
            logger.debug(f"[metrics] Loaded {len(self._agents)} agents from {source}")
        except Exception as exc:
            logger.error(f"[metrics] load failed: {exc}")
