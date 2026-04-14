from __future__ import annotations
"""
core/threshold_consensus.py
Threshold Consensus para DOF Mesh — consenso distribuido con firmas colectivas.
Version: 0.1.0

Inspirado por Chorus (FROST threshold signatures) del hackathon Synthesis.
Implementa logica de consenso por threshold sin criptografia real FROST —
las signatures son hashes deterministicos.

Uso:
    tc = ThresholdConsensus(threshold=2/3)
    tc.register_node("node-1")
    tc.register_node("node-2")
    tc.register_node("node-3")
    proposal = tc.propose("upgrade-v2", proposer="node-1")
    tc.vote("node-1", proposal.id, True, "sig1")
    tc.vote("node-2", proposal.id, True, "sig2")
    result = tc.tally(proposal.id)  # APPROVED
"""

import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs", "consensus")


@dataclass
class Vote:
    """Voto individual de un nodo."""
    node_id: str
    proposal_id: str
    approve: bool
    signature: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Proposal:
    """Propuesta de decision del mesh."""
    id: str
    decision: str
    proposer: str
    votes: dict = field(default_factory=dict)  # node_id -> Vote
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    result: str = "PENDING"  # PENDING | APPROVED | REJECTED

    def to_dict(self) -> dict:
        data = asdict(self)
        # Convertir votes dict de Vote objects a dicts
        data["votes"] = {k: v if isinstance(v, dict) else asdict(v)
                         for k, v in self.votes.items()}
        return data


class ThresholdConsensus:
    """
    Consenso por threshold para el DOF Mesh.

    Los nodos registrados votan propuestas. Una propuesta se aprueba
    si alcanza el threshold (default: 2/3 de los nodos).
    Las signatures son hashes deterministicos (simula FROST).
    """

    def __init__(self, threshold: float = 2 / 3):
        """
        Args:
            threshold: Fraccion de votos aprobatorios necesarios (0.0 a 1.0).
        """
        if not 0.0 < threshold <= 1.0:
            raise ValueError(f"Threshold debe estar entre 0.0 y 1.0, recibido: {threshold}")
        self._threshold = threshold
        self._nodes: set[str] = set()
        self._proposals: dict[str, Proposal] = {}

    @property
    def threshold(self) -> float:
        return self._threshold

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    def register_node(self, node_id: str) -> bool:
        """
        Registra un nodo como participante del consenso.

        Returns:
            True si el nodo fue registrado, False si ya existia.
        """
        if node_id in self._nodes:
            return False
        self._nodes.add(node_id)
        logger.info(f"Nodo registrado: {node_id} (total: {len(self._nodes)})")
        return True

    def unregister_node(self, node_id: str) -> bool:
        """Elimina un nodo del consenso."""
        if node_id not in self._nodes:
            return False
        self._nodes.discard(node_id)
        logger.info(f"Nodo eliminado: {node_id} (total: {len(self._nodes)})")
        return True

    def is_registered(self, node_id: str) -> bool:
        """Verifica si un nodo esta registrado."""
        return node_id in self._nodes

    def propose(self, decision: str, proposer: str) -> Proposal:
        """
        Genera una propuesta de decision.

        Args:
            decision: Descripcion de la decision a votar.
            proposer: ID del nodo que propone.

        Returns:
            Proposal con ID unico.

        Raises:
            ValueError: Si el proposer no esta registrado.
        """
        if proposer not in self._nodes:
            raise ValueError(
                f"Nodo '{proposer}' no esta registrado. "
                f"Registra primero con register_node()."
            )

        proposal_id = hashlib.sha256(
            f"{decision}:{proposer}:{time.time()}:{uuid.uuid4()}".encode()
        ).hexdigest()[:16]

        proposal = Proposal(
            id=proposal_id,
            decision=decision,
            proposer=proposer,
        )

        self._proposals[proposal_id] = proposal
        logger.info(f"Propuesta creada: {proposal_id} por {proposer}")
        return proposal

    def vote(
        self,
        node_id: str,
        proposal_id: str,
        approve: bool,
        signature: str,
    ) -> Vote:
        """
        Registra el voto de un nodo en una propuesta.

        Args:
            node_id: ID del nodo que vota.
            proposal_id: ID de la propuesta.
            approve: True para aprobar, False para rechazar.
            signature: Firma del nodo (hash deterministico).

        Returns:
            Vote registrado.

        Raises:
            ValueError: Si el nodo no esta registrado, la propuesta no existe,
                        la propuesta ya fue resuelta, o el nodo ya voto.
        """
        if node_id not in self._nodes:
            raise ValueError(f"Nodo '{node_id}' no esta registrado.")

        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise ValueError(f"Propuesta '{proposal_id}' no encontrada.")

        if proposal.result != "PENDING":
            raise ValueError(
                f"Propuesta '{proposal_id}' ya fue resuelta: {proposal.result}"
            )

        if node_id in proposal.votes:
            raise ValueError(
                f"Nodo '{node_id}' ya voto en propuesta '{proposal_id}'."
            )

        v = Vote(
            node_id=node_id,
            proposal_id=proposal_id,
            approve=approve,
            signature=signature,
        )

        proposal.votes[node_id] = v
        logger.info(
            f"Voto registrado: {node_id} -> "
            f"{'APPROVE' if approve else 'REJECT'} en {proposal_id}"
        )
        return v

    def tally(self, proposal_id: str) -> str:
        """
        Cuenta los votos y determina el resultado.

        El resultado se determina asi:
        - Si votos aprobatorios >= threshold * total_nodos: APPROVED
        - Si votos rechazados > (1 - threshold) * total_nodos: REJECTED
          (es decir, ya es imposible alcanzar el threshold)
        - Si no: PENDING

        Args:
            proposal_id: ID de la propuesta.

        Returns:
            "APPROVED", "REJECTED" o "PENDING".

        Raises:
            ValueError: Si la propuesta no existe.
        """
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise ValueError(f"Propuesta '{proposal_id}' no encontrada.")

        if proposal.result != "PENDING":
            return proposal.result

        total = len(self._nodes)
        if total == 0:
            return "PENDING"

        approvals = sum(1 for v in proposal.votes.values() if v.approve)
        rejections = sum(1 for v in proposal.votes.values() if not v.approve)
        needed = self._threshold * total

        if approvals >= needed:
            proposal.result = "APPROVED"
            proposal.resolved_at = time.time()
            self._log_proposal(proposal)
            logger.info(f"Propuesta {proposal_id}: APPROVED ({approvals}/{total})")
        elif rejections > total - needed:
            # Ya no es posible alcanzar threshold
            proposal.result = "REJECTED"
            proposal.resolved_at = time.time()
            self._log_proposal(proposal)
            logger.info(f"Propuesta {proposal_id}: REJECTED ({rejections}/{total})")

        return proposal.result

    def get_collective_signature(self, proposal_id: str) -> Optional[str]:
        """
        Genera una firma colectiva concatenando las signatures aprobadas.
        Simula la salida de FROST threshold signatures.

        Args:
            proposal_id: ID de la propuesta.

        Returns:
            Hash de las signatures concatenadas, o None si no hay aprobaciones.

        Raises:
            ValueError: Si la propuesta no existe.
        """
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise ValueError(f"Propuesta '{proposal_id}' no encontrada.")

        approve_sigs = sorted(
            [v.signature for v in proposal.votes.values() if v.approve]
        )

        if not approve_sigs:
            return None

        combined = ":".join(approve_sigs)
        return hashlib.sha256(combined.encode()).hexdigest()

    def verify_threshold(
        self, proposal_id: str, threshold: Optional[float] = None
    ) -> bool:
        """
        Verifica si una propuesta alcanzo el threshold requerido.

        Args:
            proposal_id: ID de la propuesta.
            threshold: Threshold customizado (default: usa el del constructor).

        Returns:
            True si los votos aprobatorios >= threshold * total_nodos.

        Raises:
            ValueError: Si la propuesta no existe.
        """
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise ValueError(f"Propuesta '{proposal_id}' no encontrada.")

        t = threshold if threshold is not None else self._threshold
        total = len(self._nodes)
        if total == 0:
            return False

        approvals = sum(1 for v in proposal.votes.values() if v.approve)
        return approvals >= t * total

    def get_proposal(self, proposal_id: str) -> Optional[Proposal]:
        """Obtiene una propuesta por ID."""
        return self._proposals.get(proposal_id)

    def list_proposals(self) -> list[Proposal]:
        """Lista todas las propuestas."""
        return list(self._proposals.values())

    def _log_proposal(self, proposal: Proposal):
        """Persiste la propuesta resuelta en JSONL."""
        os.makedirs(LOGS_DIR, exist_ok=True)
        log_path = os.path.join(LOGS_DIR, "proposals.jsonl")
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **proposal.to_dict(),
        }
        try:
            with open(log_path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.warning(f"Error escribiendo log de propuesta: {e}")
