import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger("constitution.update_coordinator")


class InsufficientQuorumError(Exception):
    pass


@dataclass
class UpdateProposal:
    version_hash: str
    proposed_by: str
    timestamp: datetime
    votes: List[str] = field(default_factory=list)
    committed: bool = False


class ConstitutionUpdateCoordinator:
    """
    Two-phase commit para actualizaciones de Constitution.
    Requiere quorum del 67% de nodos antes de commitear.
    Evita inconsistencias entre nodos durante actualizaciones.
    """

    def __init__(self, node_ids: List[str], quorum: float = 0.67):
        self.nodes = node_ids
        self.quorum = quorum
        self._proposals: dict[str, UpdateProposal] = {}
        self._committed_hashes: List[str] = []

    def propose_update(self, new_rules: dict, proposed_by: str) -> str:
        raw = str(sorted(str(new_rules).encode())).encode()
        version_hash = hashlib.sha256(raw).hexdigest()
        self._proposals[version_hash] = UpdateProposal(
            version_hash=version_hash,
            proposed_by=proposed_by,
            timestamp=datetime.now(timezone.utc),
        )
        logger.info(f"[Coordinator] Propuesta {version_hash[:12]}... de {proposed_by}")
        return version_hash

    def cast_vote(self, version_hash: str, node_id: str) -> None:
        if version_hash not in self._proposals:
            raise KeyError(f"Propuesta {version_hash[:12]}... no encontrada")
        proposal = self._proposals[version_hash]
        if node_id not in proposal.votes:
            proposal.votes.append(node_id)

    def try_commit(self, version_hash: str) -> bool:
        if version_hash not in self._proposals:
            raise KeyError(f"Propuesta {version_hash[:12]}... no encontrada")
        proposal = self._proposals[version_hash]
        vote_rate = len(proposal.votes) / len(self.nodes) if self.nodes else 0
        if vote_rate < self.quorum:
            raise InsufficientQuorumError(
                f"Quorum insuficiente: {vote_rate:.1%} < {self.quorum:.1%} "
                f"({len(proposal.votes)}/{len(self.nodes)} votos)"
            )
        proposal.committed = True
        self._committed_hashes.append(version_hash)
        logger.info(f"[Coordinator] Commit exitoso: {version_hash[:12]}... ({vote_rate:.1%} quorum)")
        return True

    def get_proposal(self, version_hash: str) -> Optional[UpdateProposal]:
        return self._proposals.get(version_hash)

    @property
    def committed_count(self) -> int:
        return len(self._committed_hashes)
