"""
Merkle Attestation Batching — Agrupa N governance decisions en 1 root attestation.

En vez de N attestations individuales en Avalanche C-Chain, construye un
Merkle tree de los hashes de decisiones y emite 1 sola attestation del root.
Reduce gas cost ~70%.

Incluye verificación de inclusión: dado un leaf + proof → verificar que
pertenece al batch sin necesidad de reconstruir el árbol completo.
"""
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Tuple

logger = logging.getLogger("core.merkle_attestation")


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def _hash_pair(left: str, right: str) -> str:
    combined = left + right if left <= right else right + left
    return _sha256(combined)


@dataclass(frozen=True)
class MerkleProof:
    leaf_hash: str
    proof_hashes: List[str]
    leaf_index: int
    root: str


@dataclass
class AttestationBatch:
    batch_id: str
    root_hash: str
    leaf_count: int
    timestamp: datetime
    committed: bool = False


class MerkleAttestationBatcher:
    """
    Agrupa decisiones de governance en batches y genera Merkle root.

    Uso:
        batcher = MerkleAttestationBatcher(max_batch_size=20)
        batcher.add_decision("decision_hash_1")
        batcher.add_decision("decision_hash_2")
        batch = batcher.seal_batch()  # genera Merkle root

        # Verificar inclusión
        proof = batcher.get_proof("decision_hash_1")
        assert batcher.verify_proof(proof)
    """

    def __init__(self, max_batch_size: int = 20):
        self.max_batch_size = max_batch_size
        self._pending: List[str] = []  # hashes de decisiones pendientes
        self._batches: List[AttestationBatch] = []
        self._last_tree: List[List[str]] = []  # niveles del último Merkle tree
        self._last_leaves: List[str] = []
        self._batch_counter: int = 0

    def add_decision(self, decision_hash: str) -> int:
        """Agrega un hash de decisión al batch pendiente. Retorna posición."""
        if len(self._pending) >= self.max_batch_size:
            raise BatchFullError(
                f"Batch lleno ({self.max_batch_size}). Llama seal_batch() primero."
            )
        self._pending.append(decision_hash)
        return len(self._pending) - 1

    def seal_batch(self) -> AttestationBatch:
        """Cierra el batch actual, construye Merkle tree, retorna batch con root hash."""
        if not self._pending:
            raise EmptyBatchError("No hay decisiones pendientes para sellar.")

        leaves = [_sha256(h) for h in self._pending]

        # Padding a potencia de 2
        while len(leaves) & (len(leaves) - 1) != 0:
            leaves.append(leaves[-1])

        tree = [leaves[:]]
        current_level = leaves
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                pair_hash = _hash_pair(current_level[i], current_level[i + 1])
                next_level.append(pair_hash)
            tree.append(next_level)
            current_level = next_level

        root = current_level[0]
        self._last_tree = tree
        self._last_leaves = self._pending[:]

        self._batch_counter += 1
        batch = AttestationBatch(
            batch_id=f"batch-{self._batch_counter}",
            root_hash=root,
            leaf_count=len(self._pending),
            timestamp=datetime.now(timezone.utc),
        )
        self._batches.append(batch)
        self._pending.clear()

        logger.info(
            f"[Merkle] Batch {batch.batch_id} sellado: "
            f"{batch.leaf_count} decisiones → root={root[:12]}…"
        )
        return batch

    def get_proof(self, decision_hash: str) -> MerkleProof:
        """Genera Merkle proof para una decisión del último batch sellado."""
        if decision_hash not in self._last_leaves:
            raise KeyError(f"Decisión {decision_hash[:12]}… no encontrada en último batch")

        leaf_index = self._last_leaves.index(decision_hash)
        leaf_hash = _sha256(decision_hash)

        proof_hashes = []
        idx = leaf_index
        for level in self._last_tree[:-1]:  # todos los niveles excepto root
            # Padding index
            if idx >= len(level):
                break
            sibling_idx = idx ^ 1  # XOR con 1 da el hermano
            if sibling_idx < len(level):
                proof_hashes.append(level[sibling_idx])
            idx //= 2

        return MerkleProof(
            leaf_hash=leaf_hash,
            proof_hashes=proof_hashes,
            leaf_index=leaf_index,
            root=self._last_tree[-1][0],
        )

    @staticmethod
    def verify_proof(proof: MerkleProof) -> bool:
        """Verifica que un Merkle proof es válido."""
        current = proof.leaf_hash
        idx = proof.leaf_index

        for sibling in proof.proof_hashes:
            if idx % 2 == 0:
                current = _hash_pair(current, sibling)
            else:
                current = _hash_pair(sibling, current)
            idx //= 2

        return current == proof.root

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    @property
    def batch_count(self) -> int:
        return len(self._batches)

    @property
    def batches(self) -> List[AttestationBatch]:
        return list(self._batches)


class BatchFullError(Exception):
    pass

class EmptyBatchError(Exception):
    pass
