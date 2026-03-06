"""
Merkle Tree — SHA256 batch attestation aggregation for on-chain publishing.

Aggregates N attestation certificate hashes into a single Merkle root.
One on-chain transaction stores the root; individual leaves are verifiable
off-chain with a proof (list of sibling hashes + directions).

Zero external dependencies — uses only hashlib from stdlib.

Usage:
    from core.merkle_tree import MerkleTree, MerkleBatcher

    # Direct tree construction
    tree = MerkleTree(["aabb...", "ccdd...", "eeff..."])
    root = tree.root
    proof = tree.get_proof(0)
    assert MerkleTree.verify_proof(tree.leaves[0], proof, root)

    # Batcher: queue attestations, flush when threshold reached
    batcher = MerkleBatcher(threshold=10)
    batcher.add(cert_hash_1)
    batcher.add(cert_hash_2)
    batch = batcher.flush()  # returns MerkleBatch with root + proofs
"""

import os
import json
import hashlib
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

logger = logging.getLogger("core.merkle_tree")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")


def _sha256(data: bytes) -> str:
    """SHA256 hash → hex string."""
    return hashlib.sha256(data).hexdigest()


def _hash_pair(left: str, right: str) -> str:
    """Hash two hex strings in sorted order (canonical pairing)."""
    # Sort to ensure deterministic ordering regardless of insertion order
    a, b = sorted([left, right])
    return _sha256(bytes.fromhex(a) + bytes.fromhex(b))


# ─────────────────────────────────────────────────────────────────────
# MerkleTree
# ─────────────────────────────────────────────────────────────────────

class MerkleTree:
    """SHA256 Merkle tree over a list of hex-encoded leaf hashes.

    Properties:
        root: Merkle root hex string (empty string if no leaves).
        leaves: Original leaf hashes in insertion order.
        depth: Tree depth (0 for single leaf).

    Methods:
        get_proof(index) → list of (sibling_hash, direction) tuples.
        verify_proof(leaf, proof, root) → bool  (static).
        to_dict() → serializable dict.
        from_dict(d) → MerkleTree  (static).
    """

    def __init__(self, leaves: list[str] | None = None):
        self._leaves: list[str] = list(leaves) if leaves else []
        self._layers: list[list[str]] = []
        self._root: str = ""
        if self._leaves:
            self._build()

    def _build(self):
        """Build all layers from leaves up to root."""
        if not self._leaves:
            self._root = ""
            self._layers = []
            return

        # Layer 0 = leaves
        current = list(self._leaves)
        self._layers = [current]

        while len(current) > 1:
            next_layer = []
            for i in range(0, len(current), 2):
                left = current[i]
                # If odd number of nodes, duplicate the last
                right = current[i + 1] if i + 1 < len(current) else current[i]
                next_layer.append(_hash_pair(left, right))
            self._layers.append(next_layer)
            current = next_layer

        self._root = current[0]

    @property
    def root(self) -> str:
        return self._root

    @property
    def leaves(self) -> list[str]:
        return list(self._leaves)

    @property
    def depth(self) -> int:
        return max(0, len(self._layers) - 1)

    def get_proof(self, index: int) -> list[tuple[str, str]]:
        """Get Merkle proof for leaf at given index.

        Returns:
            List of (sibling_hash, direction) tuples where direction
            is "left" or "right" indicating sibling position.

        Raises:
            IndexError: If index is out of range.
        """
        if not self._layers or index < 0 or index >= len(self._leaves):
            raise IndexError(f"Leaf index {index} out of range (0..{len(self._leaves) - 1})")

        proof = []
        idx = index

        for layer_idx in range(len(self._layers) - 1):
            layer = self._layers[layer_idx]
            # Determine sibling
            if idx % 2 == 0:
                # Current is left child → sibling is right
                sibling_idx = idx + 1
                if sibling_idx < len(layer):
                    proof.append((layer[sibling_idx], "right"))
                else:
                    # Odd node count: sibling is self (duplicate)
                    proof.append((layer[idx], "right"))
            else:
                # Current is right child → sibling is left
                proof.append((layer[idx - 1], "left"))

            # Move to parent index
            idx = idx // 2

        return proof

    @staticmethod
    def verify_proof(leaf: str, proof: list[tuple[str, str]], root: str) -> bool:
        """Verify a Merkle proof for a leaf against a root.

        Args:
            leaf: Hex-encoded leaf hash.
            proof: List of (sibling_hash, direction) tuples.
            root: Expected Merkle root.

        Returns:
            True if the proof is valid.
        """
        current = leaf
        for sibling, direction in proof:
            if direction == "left":
                current = _hash_pair(sibling, current)
            else:
                current = _hash_pair(current, sibling)
        return current == root

    def to_dict(self) -> dict:
        """Serialize tree to a dict (for JSONL persistence)."""
        return {
            "root": self._root,
            "leaves": self._leaves,
            "depth": self.depth,
            "leaf_count": len(self._leaves),
        }

    @staticmethod
    def from_dict(d: dict) -> "MerkleTree":
        """Reconstruct tree from serialized dict."""
        return MerkleTree(d.get("leaves", []))


# ─────────────────────────────────────────────────────────────────────
# MerkleBatch — result of flushing the batcher
# ─────────────────────────────────────────────────────────────────────

@dataclass
class MerkleBatch:
    """Result of a Merkle batcher flush."""
    batch_id: str
    root: str
    leaves: list[str]
    leaf_count: int
    proofs: dict[str, list[tuple[str, str]]]  # leaf_hash → proof
    timestamp: str
    published: bool = False
    tx_hash: str = ""


# ─────────────────────────────────────────────────────────────────────
# MerkleBatcher — queue + auto-flush
# ─────────────────────────────────────────────────────────────────────

class MerkleBatcher:
    """Queue attestation hashes and flush into Merkle batches.

    Args:
        threshold: Number of leaves that triggers auto_flush (0 = manual only).
        log_path: Path to JSONL log file for batch persistence.

    Usage:
        batcher = MerkleBatcher(threshold=10)
        batcher.add("aabb...")
        batcher.add("ccdd...")
        # ...add more...
        batch = batcher.flush()  # or auto-flushed at threshold
    """

    def __init__(self, threshold: int = 0, log_path: str = ""):
        self._queue: list[str] = []
        self._threshold = threshold
        self._batches: list[MerkleBatch] = []
        self._log_path = log_path or os.path.join(LOGS_DIR, "merkle_batches.jsonl")
        self._batch_counter = 0

    @property
    def queue_size(self) -> int:
        return len(self._queue)

    @property
    def batches(self) -> list[MerkleBatch]:
        return list(self._batches)

    def add(self, leaf_hash: str) -> MerkleBatch | None:
        """Add a leaf hash to the queue.

        If threshold > 0 and queue reaches threshold, auto-flushes
        and returns the resulting MerkleBatch. Otherwise returns None.
        """
        self._queue.append(leaf_hash)

        if self._threshold > 0 and len(self._queue) >= self._threshold:
            return self.flush()

        return None

    def flush(self) -> MerkleBatch | None:
        """Flush the current queue into a MerkleBatch.

        Returns:
            MerkleBatch with root and proofs, or None if queue is empty.
        """
        if not self._queue:
            return None

        self._batch_counter += 1
        leaves = list(self._queue)
        self._queue.clear()

        tree = MerkleTree(leaves)

        # Generate proofs for all leaves
        proofs = {}
        for i, leaf in enumerate(leaves):
            proofs[leaf] = tree.get_proof(i)

        batch = MerkleBatch(
            batch_id=f"batch-{self._batch_counter:04d}",
            root=tree.root,
            leaves=leaves,
            leaf_count=len(leaves),
            proofs=proofs,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        self._batches.append(batch)
        self._log_batch(batch)

        logger.info(
            f"Merkle batch {batch.batch_id}: {batch.leaf_count} leaves → "
            f"root={batch.root[:16]}..."
        )

        return batch

    def verify(self, batch: MerkleBatch) -> dict:
        """Verify all proofs in a batch.

        Returns:
            Dict with verified_count, failed_count, and per-leaf results.
        """
        results = {}
        verified = 0
        failed = 0

        for leaf, proof in batch.proofs.items():
            valid = MerkleTree.verify_proof(leaf, proof, batch.root)
            results[leaf] = valid
            if valid:
                verified += 1
            else:
                failed += 1

        return {
            "batch_id": batch.batch_id,
            "root": batch.root,
            "verified": verified,
            "failed": failed,
            "total": verified + failed,
            "all_valid": failed == 0,
            "results": results,
        }

    def _log_batch(self, batch: MerkleBatch):
        """Persist batch to JSONL log."""
        os.makedirs(os.path.dirname(self._log_path), exist_ok=True)
        entry = {
            "timestamp": batch.timestamp,
            "batch_id": batch.batch_id,
            "root": batch.root,
            "leaf_count": batch.leaf_count,
            "leaves": batch.leaves,
            "published": batch.published,
        }
        try:
            with open(self._log_path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log batch: {e}")
