"""
Deterministic serialization and hashing of Z3 proofs.

CRITICAL: Serialization must be DETERMINISTIC.
Same solver state → same transcript → same hash. Always.

Uses keccak256 for compatibility with Ethereum/Avalanche attestations.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Optional

logger = logging.getLogger("core.proof_hash")

# Try to use web3's keccak, fallback to sha3_256
try:
    from web3 import Web3
    def _keccak256(data: bytes) -> bytes:
        return Web3.keccak(data)
except ImportError:
    def _keccak256(data: bytes) -> bytes:
        return hashlib.sha3_256(data).digest()


class ProofSerializer:
    """Deterministic serialization and hashing of Z3 proof transcripts."""

    @staticmethod
    def serialize_proof(solver_assertions: list[str],
                        result: str,
                        invariants: list[str],
                        model_data: Optional[dict] = None) -> str:
        """Serialize a Z3 proof result to a deterministic transcript.

        Args:
            solver_assertions: List of Z3 assertion strings (sorted).
            result: Solver result ("PROVEN", "VIOLATED", "TIMEOUT").
            invariants: List of invariant IDs checked.
            model_data: Optional counterexample data.

        Returns:
            Deterministic string transcript.
        """
        # Sort everything for determinism
        transcript = {
            "assertions": sorted(solver_assertions),
            "invariants": sorted(invariants),
            "result": result,
            "model": _serialize_model_data(model_data) if model_data else None,
        }
        # json.dumps with sort_keys ensures deterministic output
        return json.dumps(transcript, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def hash_proof(transcript: str) -> bytes:
        """Compute keccak256 hash of a proof transcript.

        Args:
            transcript: Deterministic proof transcript string.

        Returns:
            32-byte keccak256 hash.
        """
        if not transcript:
            return b"\x00" * 32
        return _keccak256(transcript.encode("utf-8"))

    @staticmethod
    def verify_hash(transcript: str, expected_hash: bytes) -> bool:
        """Verify that a transcript matches its expected hash.

        Args:
            transcript: Proof transcript.
            expected_hash: Expected keccak256 hash.

        Returns:
            True if hash matches.
        """
        computed = ProofSerializer.hash_proof(transcript)
        return computed == expected_hash

    @staticmethod
    def serialize_model(model_dict: dict) -> str:
        """Serialize a Z3 model to deterministic string.

        Args:
            model_dict: Dictionary of variable → value mappings.

        Returns:
            Deterministic JSON string.
        """
        return json.dumps(
            _serialize_model_data(model_dict),
            sort_keys=True,
            separators=(",", ":"),
        )


class ProofBatcher:
    """Batch multiple Z3 proof hashes into a Merkle tree for on-chain publishing.

    Bridges ProofSerializer (keccak256 hashes) with MerkleTree (SHA256 tree)
    so that N proof results can be attested with a single on-chain root.

    Usage:
        batcher = ProofBatcher()
        batcher.add_proof(["a>0"], "PROVEN", ["INV-1"])
        batcher.add_proof(["b<1"], "PROVEN", ["INV-2"])
        result = batcher.finalize()
        # result.root → Merkle root, result.proofs → per-leaf verification paths
    """

    def __init__(self):
        self._entries: list[dict] = []

    @property
    def size(self) -> int:
        """Number of proofs queued."""
        return len(self._entries)

    def add_proof(self, solver_assertions: list[str], result: str,
                  invariants: list[str],
                  model_data: Optional[dict] = None) -> str:
        """Serialize and hash a proof, queue for batching.

        Returns:
            Hex-encoded keccak256 hash of the proof transcript.
        """
        transcript = ProofSerializer.serialize_proof(
            solver_assertions, result, invariants, model_data
        )
        proof_hash = ProofSerializer.hash_proof(transcript)
        hex_hash = proof_hash.hex()

        self._entries.append({
            "transcript": transcript,
            "hash": hex_hash,
            "result": result,
            "invariants": sorted(invariants),
        })
        return hex_hash

    def finalize(self) -> dict:
        """Build a Merkle tree from all queued proof hashes.

        Returns:
            Dict with root, leaf_count, leaves, depth, and entries metadata.
            Returns empty dict if no proofs queued.
        """
        if not self._entries:
            return {}

        from core.merkle_tree import MerkleTree

        leaves = [e["hash"] for e in self._entries]
        tree = MerkleTree(leaves)

        proofs = {}
        for i, leaf in enumerate(leaves):
            proofs[leaf] = tree.get_proof(i)

        result = {
            "root": tree.root,
            "leaf_count": len(leaves),
            "leaves": leaves,
            "depth": tree.depth,
            "proofs": proofs,
            "entries": [
                {"hash": e["hash"], "result": e["result"],
                 "invariants": e["invariants"]}
                for e in self._entries
            ],
        }

        self._entries.clear()
        return result

    def verify_entry(self, finalized: dict, leaf_hash: str) -> bool:
        """Verify a single proof's inclusion in a finalized batch.

        Args:
            finalized: Result from finalize().
            leaf_hash: Hex hash of the proof to verify.

        Returns:
            True if the proof is included and its Merkle proof is valid.
        """
        from core.merkle_tree import MerkleTree

        if not finalized or leaf_hash not in finalized.get("proofs", {}):
            return False
        proof = finalized["proofs"][leaf_hash]
        return MerkleTree.verify_proof(leaf_hash, proof, finalized["root"])


def _serialize_model_data(data: Optional[dict]) -> Optional[dict]:
    """Recursively convert model data to serializable types."""
    if data is None:
        return None
    result = {}
    for k, v in sorted(data.items()):
        if isinstance(v, dict):
            result[str(k)] = _serialize_model_data(v)
        elif isinstance(v, (int, float, bool, str)):
            result[str(k)] = v
        else:
            result[str(k)] = str(v)
    return result
