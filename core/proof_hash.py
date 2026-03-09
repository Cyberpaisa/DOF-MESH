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
