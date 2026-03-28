"""
ByzantineNodeGuard — Reputación por nodo para DOF Mesh Legion.

Asigna score de reputación 0.0-1.0 a cada nodo.
Penaliza timeouts Z3, fallos de consenso y attestations inválidas.
Cuarentena automática si reputación < 0.3.
Restaurable en <50 transacciones limpias.

Estados:
  ACTIVE      — reputación >= 0.3, opera normalmente
  QUARANTINED — reputación < 0.3, rechazado del consenso
  PROBATION   — reputación 0.3-0.5, opera con restricciones
"""

import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("core.byzantine_node_guard")

QUARANTINE_THRESHOLD = 0.3
PROBATION_THRESHOLD = 0.5
REPUTATION_INCREMENT = 0.01   # por transacción exitosa
REPUTATION_PENALTY = 0.05     # por fallo
TIMEOUT_PENALTY = 0.03        # por timeout Z3 (menos severo que fallo)
MAX_REPUTATION = 1.0
MIN_REPUTATION = 0.0


class NodeStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PROBATION = "PROBATION"
    QUARANTINED = "QUARANTINED"


@dataclass(frozen=True)
class NodeSnapshot:
    node_id: str
    reputation: float
    status: NodeStatus
    total_transactions: int
    failed_transactions: int
    consecutive_clean: int


class ByzantineNodeGuard:
    """
    Gestiona reputación de nodos en el mesh.

    Uso:
        guard = ByzantineNodeGuard()
        guard.record_success("node-42")
        guard.record_failure("node-42", reason="z3_timeout")
        if not guard.is_allowed("node-42"):
            raise NodeQuarantinedException("node-42")
    """

    def __init__(self):
        self._reputation: Dict[str, float] = defaultdict(lambda: 1.0)
        self._total: Dict[str, int] = defaultdict(int)
        self._failed: Dict[str, int] = defaultdict(int)
        self._consecutive_clean: Dict[str, int] = defaultdict(int)

    def record_success(self, node_id: str) -> float:
        """Registra transacción exitosa. Incrementa reputación +0.01."""
        self._total[node_id] += 1
        self._consecutive_clean[node_id] += 1
        new_rep = min(MAX_REPUTATION, self._reputation[node_id] + REPUTATION_INCREMENT)
        self._reputation[node_id] = round(new_rep, 4)
        logger.debug(f"[Guard] {node_id} success → rep={new_rep:.3f}")
        return new_rep

    def record_failure(self, node_id: str, reason: str = "unknown") -> float:
        """Registra fallo. Penaliza -0.05. Si rep<0.3 → cuarentena."""
        self._total[node_id] += 1
        self._failed[node_id] += 1
        self._consecutive_clean[node_id] = 0

        penalty = TIMEOUT_PENALTY if "timeout" in reason.lower() else REPUTATION_PENALTY
        new_rep = max(MIN_REPUTATION, self._reputation[node_id] - penalty)
        self._reputation[node_id] = round(new_rep, 4)

        status = self.status(node_id)
        if status == NodeStatus.QUARANTINED:
            logger.error(f"[Guard] {node_id} QUARANTINED — rep={new_rep:.3f} (reason={reason})")
        else:
            logger.warning(f"[Guard] {node_id} failure ({reason}) → rep={new_rep:.3f}")
        return new_rep

    def is_allowed(self, node_id: str) -> bool:
        """True si el nodo puede participar en consenso."""
        return self._reputation[node_id] >= QUARANTINE_THRESHOLD

    def status(self, node_id: str) -> NodeStatus:
        rep = self._reputation[node_id]
        if rep < QUARANTINE_THRESHOLD:
            return NodeStatus.QUARANTINED
        elif rep < PROBATION_THRESHOLD:
            return NodeStatus.PROBATION
        return NodeStatus.ACTIVE

    def reputation(self, node_id: str) -> float:
        return self._reputation[node_id]

    def snapshot(self, node_id: str) -> NodeSnapshot:
        return NodeSnapshot(
            node_id=node_id,
            reputation=self._reputation[node_id],
            status=self.status(node_id),
            total_transactions=self._total[node_id],
            failed_transactions=self._failed[node_id],
            consecutive_clean=self._consecutive_clean[node_id],
        )

    def reset_node(self, node_id: str) -> None:
        """Reset manual de reputación (requiere intervención Soberano)."""
        self._reputation[node_id] = 1.0
        self._consecutive_clean[node_id] = 0
        logger.info(f"[Guard] {node_id} reset manual a reputación 1.0")

    def all_quarantined(self) -> List[str]:
        """Retorna lista de nodos en cuarentena."""
        return [nid for nid in self._reputation if self._reputation[nid] < QUARANTINE_THRESHOLD]

    def can_restore(self, node_id: str) -> bool:
        """True si el nodo tiene >= 50 transacciones consecutivas limpias para restaurar."""
        return self._consecutive_clean[node_id] >= 50
