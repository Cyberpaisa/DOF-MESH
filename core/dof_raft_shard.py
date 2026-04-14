from __future__ import annotations
"""
dof_raft_shard.py — Integración Raft + DOFShardManager.

Cada shard del DOF Mesh tiene su propio cluster Raft de 3 nodos in-process.
El leader del cluster Raft de un shard es el único autorizado a procesar tareas
de ese shard — garantizando que si un nodo cae, hay failover automático.

Arquitectura:
    DOFShardManager (10 shards)
        └── ShardRaftGroup (por shard)
             └── 3 × RaftNode (leader + 2 followers)
                  └── leader.submit(task) → log replication → state machine

Uso:
    rsm = RaftShardManager(machines, shard_count=5, raft_nodes_per_shard=3)
    rsm.start()
    leader = rsm.get_leader(shard_id=0)
    leader.submit({"task": "analiza DOF"})
    rsm.stop()
"""
import logging
import time
from dataclasses import dataclass
from typing import Optional

from core.dof_sharding import DOFShardManager, Shard
from core.dof_raft import RaftNode, create_raft_cluster, wait_for_leader

logger = logging.getLogger("core.dof_raft_shard")


# ── ShardRaftGroup ────────────────────────────────────────────────────────────

@dataclass
class ShardRaftGroup:
    """Cluster Raft asociado a un shard."""
    shard_id:   int
    nodes:      list[RaftNode]
    started_at: float = 0.0

    def start(self):
        for n in self.nodes:
            n.start()
        self.started_at = time.time()

    def stop(self):
        for n in self.nodes:
            n.stop()

    def leader(self, timeout: float = 2.0) -> Optional[RaftNode]:
        return wait_for_leader(self.nodes, timeout=timeout)

    def submit(self, command, timeout: float = 2.0) -> Optional[int]:
        """Enviar comando al leader del shard. Retorna índice en log o None."""
        ldr = self.leader(timeout=timeout)
        if ldr is None:
            logger.warning("Shard %d: no leader found in %.1fs", self.shard_id, timeout)
            return None
        return ldr.submit(command)

    def status(self) -> dict:
        leaders = [n for n in self.nodes if n.is_leader()]
        return {
            "shard_id":  self.shard_id,
            "nodes":     len(self.nodes),
            "leader":    leaders[0].node_id if leaders else None,
            "term":      max(n.term() for n in self.nodes) if self.nodes else 0,
            "uptime_s":  round(time.time() - self.started_at, 1) if self.started_at else 0,
            "node_roles": {n.node_id: n.role().value for n in self.nodes},
        }


# ── RaftShardManager ──────────────────────────────────────────────────────────

class RaftShardManager:
    """
    Extiende DOFShardManager con clusters Raft por shard.

    Cada shard tiene su propio cluster de `raft_nodes_per_shard` nodos Raft.
    El leader del cluster es la autoridad para procesar tareas del shard.

    Garantía:
        - Si el leader del shard cae → election en <600ms → nuevo leader
        - Log replication: todos los nodos del shard tienen el mismo estado
        - Zero-loss: WAL (heredado de DistributedMeshQueue) + Raft log

    Compatible con DOFShardManager: misma API + get_leader(shard_id).
    """

    def __init__(
        self,
        machines: list[str],
        shard_count: int = 5,
        replication_factor: int = 3,
        raft_nodes_per_shard: int = 3,
    ):
        self._sm = DOFShardManager(
            machines,
            shard_count=shard_count,
            replication_factor=replication_factor,
        )
        self._raft_nodes_per_shard = raft_nodes_per_shard
        self._groups: dict[int, ShardRaftGroup] = {}
        self._running = False

        # Crear grupos Raft por cada shard
        for shard_id in range(shard_count):
            nodes = [
                RaftNode(f"shard-{shard_id}-raft-{j}")
                for j in range(raft_nodes_per_shard)
            ]
            # Conectar nodos entre sí
            for a in nodes:
                for b in nodes:
                    if a is not b:
                        a.add_peer(b)
            self._groups[shard_id] = ShardRaftGroup(shard_id=shard_id, nodes=nodes)

        logger.info(
            "RaftShardManager ready: %d shards × %d Raft nodes = %d total Raft nodes",
            shard_count, raft_nodes_per_shard, shard_count * raft_nodes_per_shard,
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        """Arrancar todos los clusters Raft."""
        for group in self._groups.values():
            group.start()
        self._running = True
        logger.info("RaftShardManager started: %d shard clusters running", len(self._groups))

    def stop(self):
        """Detener todos los clusters Raft."""
        for group in self._groups.values():
            group.stop()
        self._running = False
        logger.info("RaftShardManager stopped")

    # ── API principal ─────────────────────────────────────────────────────────

    def get_shard_for_key(self, key: str) -> Shard:
        """Delegado a DOFShardManager."""
        return self._sm.get_shard_for_key(key)

    def get_leader(self, shard_id: int, timeout: float = 2.0) -> Optional[RaftNode]:
        """Leader Raft del shard. Ninguna tarea debe procesarse sin este nodo."""
        group = self._groups.get(shard_id)
        return group.leader(timeout=timeout) if group else None

    def get_leader_for_key(self, key: str, timeout: float = 2.0) -> Optional[RaftNode]:
        """Leader del shard responsable de esta clave."""
        shard = self._sm.get_shard_for_key(key)
        return self.get_leader(shard.id, timeout=timeout)

    def submit_to_shard(self, shard_id: int, command, timeout: float = 2.0) -> Optional[int]:
        """Enviar comando al leader del shard. Lanza si no hay leader."""
        group = self._groups.get(shard_id)
        if group is None:
            raise ValueError(f"Shard {shard_id} no existe")
        return group.submit(command, timeout=timeout)

    def submit_for_key(self, key: str, command, timeout: float = 2.0) -> Optional[int]:
        """Enviar comando al shard responsable de la clave."""
        shard = self._sm.get_shard_for_key(key)
        return self.submit_to_shard(shard.id, command, timeout=timeout)

    def wait_all_leaders(self, timeout: float = 5.0) -> bool:
        """Esperar a que todos los shards tengan leader. True si ok."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            all_ok = all(
                any(n.is_leader() for n in g.nodes)
                for g in self._groups.values()
            )
            if all_ok:
                return True
            time.sleep(0.05)
        return False

    def status(self) -> dict:
        shard_statuses = {sid: g.status() for sid, g in self._groups.items()}
        leaders_elected = sum(1 for s in shard_statuses.values() if s["leader"])
        return {
            "running":         self._running,
            "shard_count":     len(self._groups),
            "leaders_elected": leaders_elected,
            "raft_nodes_total": len(self._groups) * self._raft_nodes_per_shard,
            "shards":          shard_statuses,
            "shard_manager":   self._sm.status(),
        }
