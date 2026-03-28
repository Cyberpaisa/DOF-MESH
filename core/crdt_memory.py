"""
CRDT Memory Layer — Conflict-free Replicated Data Types para memoria distribuida.

Implementa un G-Counter (Grow-only Counter) y un LWW-Register (Last-Writer-Wins Register)
como primitivas CRDT para sincronización de memoria entre nodos heterogéneos
sin necesidad de consenso.

G-Counter: cada nodo tiene su propio contador. El valor global es la suma.
            Solo operaciones de incremento (grow-only). Merge es max() por nodo.

LWW-Register: cada nodo puede escribir un valor con timestamp.
              El valor con timestamp más reciente gana. Merge toma el más reciente.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("core.crdt_memory")


class GCounter:
    """Grow-only Counter CRDT — cada nodo incrementa su propio slot."""

    def __init__(self):
        self._counts: Dict[str, int] = {}

    def increment(self, node_id: str, amount: int = 1) -> int:
        """Incrementa el contador del nodo. Retorna nuevo valor del nodo."""
        if amount < 0:
            raise ValueError("GCounter solo permite incrementos positivos")
        self._counts[node_id] = self._counts.get(node_id, 0) + amount
        return self._counts[node_id]

    def value(self) -> int:
        """Valor global: suma de todos los nodos."""
        return sum(self._counts.values())

    def node_value(self, node_id: str) -> int:
        return self._counts.get(node_id, 0)

    def merge(self, other: "GCounter") -> None:
        """Merge con otro GCounter: max() por nodo."""
        for node_id, count in other._counts.items():
            self._counts[node_id] = max(self._counts.get(node_id, 0), count)

    @property
    def nodes(self) -> list[str]:
        return list(self._counts.keys())


@dataclass
class LWWEntry:
    value: Any
    timestamp: datetime
    node_id: str


class LWWRegister:
    """Last-Writer-Wins Register CRDT — el timestamp más reciente gana."""

    def __init__(self):
        self._entry: Optional[LWWEntry] = None

    def write(self, value: Any, node_id: str,
              timestamp: Optional[datetime] = None) -> None:
        """Escribe un valor. Si el timestamp es más reciente que el actual, lo reemplaza."""
        ts = timestamp or datetime.now(timezone.utc)
        if self._entry is None or ts >= self._entry.timestamp:
            self._entry = LWWEntry(value=value, timestamp=ts, node_id=node_id)

    def read(self) -> Optional[Any]:
        return self._entry.value if self._entry else None

    def merge(self, other: "LWWRegister") -> None:
        """Merge: gana el timestamp más reciente."""
        if other._entry is None:
            return
        if self._entry is None or other._entry.timestamp > self._entry.timestamp:
            self._entry = other._entry

    @property
    def last_writer(self) -> Optional[str]:
        return self._entry.node_id if self._entry else None

    @property
    def last_timestamp(self) -> Optional[datetime]:
        return self._entry.timestamp if self._entry else None


class CRDTMemoryStore:
    """
    Store de memoria distribuida basado en CRDTs.

    Combina G-Counters (para métricas acumulativas) y LWW-Registers (para estado).

    Uso:
        store = CRDTMemoryStore()

        # Contador de verificaciones
        store.increment_counter("z3_verifications", "node-1")
        store.increment_counter("z3_verifications", "node-2", amount=5)
        total = store.counter_value("z3_verifications")  # 6

        # Estado del agente (LWW)
        store.set_register("agent-1687-status", "active", "node-1")
        status = store.get_register("agent-1687-status")  # "active"
    """

    def __init__(self):
        self._counters: Dict[str, GCounter] = {}
        self._registers: Dict[str, LWWRegister] = {}

    def increment_counter(self, name: str, node_id: str, amount: int = 1) -> int:
        if name not in self._counters:
            self._counters[name] = GCounter()
        self._counters[name].increment(node_id, amount)
        return self._counters[name].value()

    def counter_value(self, name: str) -> int:
        counter = self._counters.get(name)
        return counter.value() if counter else 0

    def set_register(self, key: str, value: Any, node_id: str,
                     timestamp: Optional[datetime] = None) -> None:
        if key not in self._registers:
            self._registers[key] = LWWRegister()
        self._registers[key].write(value, node_id, timestamp)

    def get_register(self, key: str) -> Optional[Any]:
        reg = self._registers.get(key)
        return reg.read() if reg else None

    def merge_store(self, other: "CRDTMemoryStore") -> None:
        """Merge completo de dos stores."""
        for name, counter in other._counters.items():
            if name not in self._counters:
                self._counters[name] = GCounter()
            self._counters[name].merge(counter)
        for key, register in other._registers.items():
            if key not in self._registers:
                self._registers[key] = LWWRegister()
            self._registers[key].merge(register)

    @property
    def counter_names(self) -> list[str]:
        return list(self._counters.keys())

    @property
    def register_keys(self) -> list[str]:
        return list(self._registers.keys())
