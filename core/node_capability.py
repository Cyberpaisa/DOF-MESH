"""
Node Capability Manifest (NCM) — Declaración de capacidades por nodo.

Cada nodo en el mesh declara sus capacidades al unirse:
memory_gb, z3_timeout_ms, chain_support, agent_type, tier.
El Supervisor usa el NCM para asignar constraints según capacidad.

Tiered Z3 Validation:
  - Tier 1 (Core): Z3 completo, nodos de alta capacidad, <100ms
  - Tier 2 (Standard): Z3 parcial, nodos medianos, <300ms
  - Tier 3 (Edge): Verificación diferida/heurística, nodos ligeros, <500ms
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Dict, List, Optional

logger = logging.getLogger("core.node_capability")


class NodeTier(IntEnum):
    CORE = 1       # Z3 completo, alta capacidad
    STANDARD = 2   # Z3 parcial
    EDGE = 3       # Verificación ligera/diferida


@dataclass
class NodeManifest:
    node_id: str
    memory_gb: float
    z3_timeout_ms: int
    chain_support: List[str]  # ej: ["avalanche-c", "fuji"]
    agent_type: str           # ej: "validator", "executor", "observer"
    tier: NodeTier
    region: str = "unknown"
    registered_at: Optional[datetime] = None

    def __post_init__(self):
        if self.registered_at is None:
            self.registered_at = datetime.now(timezone.utc)


@dataclass(frozen=True)
class TierRequirements:
    min_memory_gb: float
    max_z3_timeout_ms: int
    z3_mode: str  # "full", "partial", "deferred"


# Requisitos por tier
TIER_REQUIREMENTS = {
    NodeTier.CORE: TierRequirements(min_memory_gb=16.0, max_z3_timeout_ms=100, z3_mode="full"),
    NodeTier.STANDARD: TierRequirements(min_memory_gb=8.0, max_z3_timeout_ms=300, z3_mode="partial"),
    NodeTier.EDGE: TierRequirements(min_memory_gb=2.0, max_z3_timeout_ms=500, z3_mode="deferred"),
}


class NodeCapabilityRegistry:
    """
    Registro de capacidades de nodos en el mesh.

    Uso:
        registry = NodeCapabilityRegistry()
        manifest = registry.register_node(
            node_id="node-42",
            memory_gb=32.0,
            z3_timeout_ms=50,
            chain_support=["avalanche-c"],
            agent_type="validator",
        )
        # Auto-clasifica como Tier 1 (CORE)

        # Buscar nodos por tier
        core_nodes = registry.get_nodes_by_tier(NodeTier.CORE)

        # Asignar constraint según complejidad
        node = registry.best_node_for_constraint(complexity="high")
    """

    def __init__(self):
        self._nodes: Dict[str, NodeManifest] = {}

    def register_node(self, node_id: str, memory_gb: float, z3_timeout_ms: int,
                      chain_support: List[str], agent_type: str,
                      region: str = "unknown") -> NodeManifest:
        """Registra un nodo y auto-clasifica su tier."""
        tier = self._classify_tier(memory_gb, z3_timeout_ms)
        manifest = NodeManifest(
            node_id=node_id,
            memory_gb=memory_gb,
            z3_timeout_ms=z3_timeout_ms,
            chain_support=chain_support,
            agent_type=agent_type,
            tier=tier,
            region=region,
        )
        self._nodes[node_id] = manifest
        logger.info(
            f"[NCM] Nodo {node_id} registrado: Tier {tier.name}, "
            f"{memory_gb}GB RAM, Z3 timeout {z3_timeout_ms}ms"
        )
        return manifest

    def _classify_tier(self, memory_gb: float, z3_timeout_ms: int) -> NodeTier:
        """Clasifica un nodo según sus capacidades."""
        core_req = TIER_REQUIREMENTS[NodeTier.CORE]
        std_req = TIER_REQUIREMENTS[NodeTier.STANDARD]

        if memory_gb >= core_req.min_memory_gb and z3_timeout_ms <= core_req.max_z3_timeout_ms:
            return NodeTier.CORE
        elif memory_gb >= std_req.min_memory_gb and z3_timeout_ms <= std_req.max_z3_timeout_ms:
            return NodeTier.STANDARD
        return NodeTier.EDGE

    def get_node(self, node_id: str) -> Optional[NodeManifest]:
        return self._nodes.get(node_id)

    def get_nodes_by_tier(self, tier: NodeTier) -> List[NodeManifest]:
        return [n for n in self._nodes.values() if n.tier == tier]

    def get_nodes_by_chain(self, chain: str) -> List[NodeManifest]:
        return [n for n in self._nodes.values() if chain in n.chain_support]

    def best_node_for_constraint(self, complexity: str = "medium") -> Optional[NodeManifest]:
        """Retorna el mejor nodo disponible para un constraint de complejidad dada."""
        if complexity == "high":
            candidates = self.get_nodes_by_tier(NodeTier.CORE)
        elif complexity == "medium":
            candidates = self.get_nodes_by_tier(NodeTier.CORE) + self.get_nodes_by_tier(NodeTier.STANDARD)
        else:  # low
            candidates = list(self._nodes.values())

        if not candidates:
            return None
        # Retorna el de menor z3_timeout (más rápido)
        return min(candidates, key=lambda n: n.z3_timeout_ms)

    def remove_node(self, node_id: str) -> bool:
        if node_id in self._nodes:
            del self._nodes[node_id]
            return True
        return False

    def tier_distribution(self) -> Dict[str, int]:
        """Retorna conteo de nodos por tier."""
        dist = {t.name: 0 for t in NodeTier}
        for node in self._nodes.values():
            dist[node.tier.name] += 1
        return dist

    @property
    def total_nodes(self) -> int:
        return len(self._nodes)

    @property
    def z3_mode_for_tier(self) -> Dict[str, str]:
        return {t.name: TIER_REQUIREMENTS[t].z3_mode for t in NodeTier}
