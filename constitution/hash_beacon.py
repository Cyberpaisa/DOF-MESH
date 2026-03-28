"""
Constitution Hash Beacon — Beacon de hash para sincronización de nodos.

Publica el hash del estado Constitution a intervalos regulares (cada N bloques).
Nodos que detectan su hash local diferente del beacon → modo HALT automático
hasta resincronización.

En producción, el beacon se publica en Avalanche C-Chain.
En esta implementación, simula el broadcast como almacenamiento local.
"""
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("constitution.hash_beacon")


class NodeSyncStatus(str, Enum):
    SYNCED = "SYNCED"
    HALTED = "HALTED"
    PENDING = "PENDING"


@dataclass(frozen=True)
class BeaconEntry:
    epoch: int
    state_hash: str
    block_number: int
    timestamp: datetime
    publisher_node: str


class ConstitutionHashBeacon:
    """
    Beacon que publica el hash canónico de Constitution cada N bloques.

    Uso:
        beacon = ConstitutionHashBeacon(beacon_interval=50)

        # Nodo líder publica
        beacon.publish(constitution_rules, block_number=100, publisher="node-1")

        # Otros nodos verifican
        status = beacon.check_sync("node-2", local_hash="abc123...")
        if status == NodeSyncStatus.HALTED:
            resync()
    """

    def __init__(self, beacon_interval: int = 50):
        self.beacon_interval = beacon_interval
        self._beacons: List[BeaconEntry] = []
        self._node_status: Dict[str, NodeSyncStatus] = {}
        self._current_epoch: int = 0

    def _compute_hash(self, data) -> str:
        raw = str(sorted(str(data).encode())).encode()
        return hashlib.sha256(raw).hexdigest()

    def publish(self, constitution_rules: dict, block_number: int,
                publisher: str) -> BeaconEntry:
        """Publica un nuevo beacon con el hash canónico de Constitution."""
        self._current_epoch += 1
        state_hash = self._compute_hash(constitution_rules)
        entry = BeaconEntry(
            epoch=self._current_epoch,
            state_hash=state_hash,
            block_number=block_number,
            timestamp=datetime.now(timezone.utc),
            publisher_node=publisher,
        )
        self._beacons.append(entry)
        logger.info(
            f"[Beacon] Epoch {self._current_epoch} publicado en bloque {block_number}: "
            f"hash={state_hash[:12]}… por {publisher}"
        )
        return entry

    def latest_beacon(self) -> Optional[BeaconEntry]:
        return self._beacons[-1] if self._beacons else None

    def check_sync(self, node_id: str, local_hash: str) -> NodeSyncStatus:
        """Verifica si un nodo está sincronizado con el beacon más reciente."""
        latest = self.latest_beacon()
        if latest is None:
            status = NodeSyncStatus.PENDING
        elif local_hash == latest.state_hash:
            status = NodeSyncStatus.SYNCED
        else:
            status = NodeSyncStatus.HALTED
            logger.warning(
                f"[Beacon] Nodo {node_id} HALTED — local={local_hash[:12]}… "
                f"vs beacon={latest.state_hash[:12]}…"
            )
        self._node_status[node_id] = status
        return status

    def acknowledge_sync(self, node_id: str) -> None:
        """Nodo confirma que se ha resincronizado."""
        self._node_status[node_id] = NodeSyncStatus.SYNCED
        logger.info(f"[Beacon] Nodo {node_id} resincronizado → SYNCED")

    def should_publish(self, current_block: int) -> bool:
        """Retorna True si es momento de publicar un nuevo beacon."""
        return current_block % self.beacon_interval == 0

    def get_node_status(self, node_id: str) -> NodeSyncStatus:
        return self._node_status.get(node_id, NodeSyncStatus.PENDING)

    def all_synced(self) -> bool:
        """True si todos los nodos conocidos están SYNCED."""
        if not self._node_status:
            return True
        return all(s == NodeSyncStatus.SYNCED for s in self._node_status.values())

    def halted_nodes(self) -> List[str]:
        return [nid for nid, s in self._node_status.items() if s == NodeSyncStatus.HALTED]

    @property
    def beacon_count(self) -> int:
        return len(self._beacons)

    @property
    def current_epoch(self) -> int:
        return self._current_epoch
