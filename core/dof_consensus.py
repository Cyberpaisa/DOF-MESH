"""
dof_consensus.py — VectorClock + GossipProtocol para DOF Mesh Hyperion.

Componente #3 del orden de implementación consensuado por:
  DeepSeek R1, GPT-4.5, Grok-4.1, Kimi K2.5, Gemini 2.0 Flash.

VectorClock: detección de conflictos entre réplicas.
GossipProtocol: replicación eventual in-process (fanout=3, 50ms).
  - No usa red real — peers se registran por referencia (single machine).
  - En producción: reemplazar _send() con gRPC/HTTP.
"""
import hashlib
import logging
import random
import threading
import time
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("core.dof_consensus")


# ── VectorClock ───────────────────────────────────────────────────────────────

class VectorClock:
    """
    Reloj vectorial para ordenamiento causal y detección de conflictos.

    Ejemplo:
        vc_a = VectorClock()
        vc_a.increment("node-a")          # {"node-a": 1}
        vc_b = VectorClock.from_dict({"node-a": 1})
        vc_b.increment("node-b")          # {"node-a": 1, "node-b": 1}
        vc_a.conflicts_with(vc_b)         # True — eventos concurrentes
        vc_a.is_ancestor_of(vc_b)         # False
    """

    def __init__(self) -> None:
        self.clock: dict[str, int] = {}

    def increment(self, node_id: str) -> None:
        self.clock[node_id] = self.clock.get(node_id, 0) + 1

    def merge(self, other: "VectorClock") -> "VectorClock":
        """Retorna nuevo clock con máximo por componente."""
        merged = VectorClock()
        keys = set(self.clock) | set(other.clock)
        merged.clock = {
            k: max(self.clock.get(k, 0), other.clock.get(k, 0))
            for k in keys
        }
        return merged

    def is_ancestor_of(self, other: "VectorClock") -> bool:
        """True si self ≤ other (self ocurrió antes o igual que other)."""
        for node, tick in self.clock.items():
            if tick > other.clock.get(node, 0):
                return False
        return True

    def conflicts_with(self, other: "VectorClock") -> bool:
        """True si self y other son concurrentes (ninguno es ancestro del otro)."""
        return (
            not self.is_ancestor_of(other)
            and not other.is_ancestor_of(self)
        )

    def to_dict(self) -> dict:
        return dict(self.clock)

    @classmethod
    def from_dict(cls, d: dict) -> "VectorClock":
        vc = cls()
        vc.clock = {k: int(v) for k, v in d.items()}
        return vc

    def copy(self) -> "VectorClock":
        return VectorClock.from_dict(self.clock)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VectorClock):
            return False
        return self.clock == other.clock

    def __repr__(self) -> str:
        return f"VectorClock({self.clock})"


# ── GossipState ───────────────────────────────────────────────────────────────

@dataclass
class GossipState:
    """Entrada en el gossip store — clave + valor + clock + timestamp."""
    node_id: str
    key: str
    value: Any
    clock: VectorClock
    timestamp: float = field(default_factory=time.time)
    ttl: int = 3

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "key": self.key,
            "value": self.value,
            "clock": self.clock.to_dict(),
            "timestamp": self.timestamp,
            "ttl": self.ttl,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GossipState":
        return cls(
            node_id=d["node_id"],
            key=d["key"],
            value=d["value"],
            clock=VectorClock.from_dict(d["clock"]),
            timestamp=d["timestamp"],
            ttl=d.get("ttl", 3),
        )


# ── GossipProtocol ────────────────────────────────────────────────────────────

class GossipProtocol:
    """
    Protocolo de gossip en memoria para replicación eventual.

    Cada nodo tiene su propio store. Los peers se registran por referencia
    (in-process). En producción reemplazar _send() con gRPC.

    Ejemplo:
        a = GossipProtocol("node-a")
        b = GossipProtocol("node-b")
        c = GossipProtocol("node-c")
        a.register_peer(b); a.register_peer(c)
        b.register_peer(a); b.register_peer(c)

        a.start()
        b.start()
        a.put("shard_map", {"machine-a": [0,1,2]})
        time.sleep(0.2)
        b.get("shard_map")  # → {"machine-a": [0,1,2]}  (replicado)
    """

    def __init__(self, node_id: str, fanout: int = 3, interval_ms: int = 50) -> None:
        self.node_id = node_id
        self.fanout = fanout
        self.interval = interval_ms / 1000.0
        self._store: dict[str, GossipState] = {}
        self._peers: list["GossipProtocol"] = []
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._rounds = 0
        self._merges = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def register_peer(self, peer: "GossipProtocol") -> None:
        if peer is not self and peer not in self._peers:
            self._peers.append(peer)

    def put(self, key: str, value: Any) -> None:
        """Escribir clave con vector clock incrementado."""
        with self._lock:
            existing = self._store.get(key)
            if existing:
                clock = existing.clock.copy()
            else:
                clock = VectorClock()
            clock.increment(self.node_id)
            self._store[key] = GossipState(
                node_id=self.node_id,
                key=key,
                value=value,
                clock=clock,
                timestamp=time.time(),
            )

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            state = self._store.get(key)
            return state.value if state else None

    def get_with_clock(self, key: str) -> Optional[tuple[Any, VectorClock]]:
        with self._lock:
            state = self._store.get(key)
            return (state.value, state.clock.copy()) if state else None

    def keys(self) -> list[str]:
        with self._lock:
            return list(self._store.keys())

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._gossip_loop, daemon=True, name=f"gossip-{self.node_id}"
        )
        self._thread.start()
        logger.info("GossipProtocol[%s] started (fanout=%d, interval=%dms)",
                    self.node_id, self.fanout, int(self.interval * 1000))

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def status(self) -> dict:
        with self._lock:
            return {
                "node_id": self.node_id,
                "keys": len(self._store),
                "peers": len(self._peers),
                "rounds": self._rounds,
                "merges": self._merges,
                "fanout": self.fanout,
            }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _gossip_loop(self) -> None:
        while self._running:
            time.sleep(self.interval)
            self._gossip_round()

    def _gossip_round(self) -> None:
        if not self._peers:
            return
        self._rounds += 1
        targets = random.sample(self._peers, min(self.fanout, len(self._peers)))
        with self._lock:
            snapshot = list(self._store.values())
        for target in targets:
            for state in snapshot:
                if state.ttl > 0:
                    target._receive(state)

    def _receive(self, remote: GossipState) -> None:
        with self._lock:
            local = self._store.get(remote.key)
            if local is None:
                # Nunca visto — aceptar
                self._store[remote.key] = GossipState(
                    node_id=remote.node_id,
                    key=remote.key,
                    value=deepcopy(remote.value),
                    clock=remote.clock.copy(),
                    timestamp=remote.timestamp,
                    ttl=remote.ttl - 1,
                )
                self._merges += 1
            elif remote.clock.is_ancestor_of(local.clock):
                # Local es más nuevo — ignorar
                pass
            elif local.clock.is_ancestor_of(remote.clock):
                # Remote es más nuevo — actualizar
                self._store[remote.key] = GossipState(
                    node_id=remote.node_id,
                    key=remote.key,
                    value=deepcopy(remote.value),
                    clock=remote.clock.copy(),
                    timestamp=remote.timestamp,
                    ttl=remote.ttl - 1,
                )
                self._merges += 1
            else:
                # Conflicto — LWW (Last Write Wins) por timestamp
                resolved = self._resolve_conflict(local, remote)
                self._store[remote.key] = resolved
                self._merges += 1

    def _resolve_conflict(self, local: GossipState, remote: GossipState) -> GossipState:
        """Last Write Wins por timestamp. Merge del vector clock."""
        winner = remote if remote.timestamp >= local.timestamp else local
        merged_clock = local.clock.merge(remote.clock)
        return GossipState(
            node_id=winner.node_id,
            key=winner.key,
            value=deepcopy(winner.value),
            clock=merged_clock,
            timestamp=max(local.timestamp, remote.timestamp),
            ttl=max(local.ttl, remote.ttl) - 1,
        )
