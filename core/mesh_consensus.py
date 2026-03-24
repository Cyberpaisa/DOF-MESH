"""
core/mesh_consensus.py - Raft consensus simplificado para DOF Mesh
"""

import json
import time
import random
import threading
import logging
from enum import Enum, auto
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConsensusState(Enum):
    """Estados del nodo en el consenso Raft"""
    FOLLOWER = auto()
    CANDIDATE = auto()
    LEADER = auto()


# Backward-compat alias
NodeState = ConsensusState


@dataclass
class LogEntry:
    """Entrada individual en el log de Raft"""
    term: int
    index: int
    value: Any
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'term': self.term,
            'index': self.index,
            'value': self.value,
            'timestamp': self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogEntry':
        return cls(
            term=data['term'],
            index=data['index'],
            value=data['value'],
            timestamp=data.get('timestamp', time.time())
        )


class RaftLog:
    """Log de Raft con persistencia en JSONL"""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entries: List[LogEntry] = []
        self.commit_index = 0
        self.last_applied = 0
        self.log_file = Path(f"logs/mesh/consensus_{node_id}.jsonl")
        self._ensure_log_dir()
        self._load_log()

    def _ensure_log_dir(self) -> None:
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_log(self) -> None:
        if not self.log_file.exists():
            return
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line.strip())
                        entry = LogEntry.from_dict(data)
                        self.entries.append(entry)
            if self.entries:
                self.commit_index = len(self.entries) - 1
                self.last_applied = self.commit_index
        except Exception as e:
            logger.error(f"Error cargando log: {e}")

    def _persist_entry(self, entry: LogEntry) -> None:
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry.to_dict()) + '\n')
        except Exception as e:
            logger.error(f"Error persistiendo entrada: {e}")

    def append(self, term: int, value: Any) -> LogEntry:
        index = len(self.entries)
        entry = LogEntry(term=term, index=index, value=value)
        self.entries.append(entry)
        self._persist_entry(entry)
        return entry

    def get_entry(self, index: int) -> Optional[LogEntry]:
        if 0 <= index < len(self.entries):
            return self.entries[index]
        return None

    def get_last_entry(self) -> Optional[LogEntry]:
        if self.entries:
            return self.entries[-1]
        return None

    def commit(self, index: int) -> bool:
        if 0 <= index < len(self.entries):
            self.commit_index = index
            return True
        return False

    def apply(self) -> List[Any]:
        applied = []
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.get_entry(self.last_applied)
            if entry:
                applied.append(entry.value)
        return applied

    def __len__(self) -> int:
        return len(self.entries)


class ConsensusNode:
    """Nodo Raft con API compatible con tests de integración."""

    def __init__(self, node_id: str, peers: Optional[List[str]] = None):
        self.node_id = node_id
        self.peers: List[str] = peers or []
        self.state: ConsensusState = ConsensusState.FOLLOWER
        self.current_term: int = 0
        self.voted_for: Optional[str] = None
        # log es una lista de dicts: [{'term': int, 'data': Any}]
        self.log: List[Dict[str, Any]] = []
        self.leader_id: Optional[str] = None
        self.votes_received: set = set()
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # API pública (usada por los tests)
    # ------------------------------------------------------------------

    def vote(self, candidate_id: str, term: int) -> bool:
        """Vota por candidate_id si el término es suficientemente alto."""
        with self._lock:
            if term < self.current_term:
                return False
            if term == self.current_term and self.voted_for is not None and self.voted_for != candidate_id:
                return False
            # Actualizar término y votar
            self.current_term = term
            self.voted_for = candidate_id
            return True

    def propose(self, term: int) -> bool:
        """Recibe una propuesta de liderazgo (AppendEntries/heartbeat).
        Acepta si term >= current_term, retrocediendo a FOLLOWER si aplica."""
        with self._lock:
            if term < self.current_term:
                return False
            self.current_term = term
            self.state = ConsensusState.FOLLOWER
            self.leader_id = None
            return True

    def append_entry(self, term: int, entry_data: Any) -> bool:
        """Añade una entrada al log si el término es válido (>= current_term)."""
        with self._lock:
            if term < self.current_term:
                return False
            self.current_term = term
            self.log.append({'term': term, 'data': entry_data})
            return True

    def become_candidate(self) -> None:
        """Transición a estado CANDIDATE, incrementa término."""
        with self._lock:
            self.state = ConsensusState.CANDIDATE
            self.current_term += 1
            self.voted_for = self.node_id
            self.votes_received = {self.node_id}

    def become_leader(self) -> None:
        """Transición a estado LEADER."""
        with self._lock:
            self.state = ConsensusState.LEADER
            self.leader_id = self.node_id

    def get_state(self) -> ConsensusState:
        """Retorna el estado actual del nodo."""
        return self.state

    def start_election(self) -> None:
        """Inicia una elección (alias de become_candidate para compat. interna)."""
        self.become_candidate()


# ------------------------------------------------------------------
# Singleton registry por node_id
# ------------------------------------------------------------------
_node_registry: Dict[str, ConsensusNode] = {}
_registry_lock = threading.Lock()


def get_consensus_node(node_id: str, peers: Optional[List[str]] = None) -> ConsensusNode:
    """Retorna (o crea) el ConsensusNode singleton para el node_id dado."""
    with _registry_lock:
        if node_id not in _node_registry:
            _node_registry[node_id] = ConsensusNode(node_id=node_id, peers=peers or [])
        return _node_registry[node_id]


def reset_registry() -> None:
    """Limpia el registry de nodos (útil para tests)."""
    with _registry_lock:
        _node_registry.clear()


# Backward-compat: ConsensusEngine como alias de ConsensusNode
ConsensusEngine = ConsensusNode
