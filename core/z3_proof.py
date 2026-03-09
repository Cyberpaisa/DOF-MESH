"""
Z3 Proof Attestation — attestation with embedded Z3 proof.

Each attestation includes a deterministic proof hash (keccak256 of the
proof transcript), making it verifiable by anyone.

Trust-by-proof: the attestation is only as strong as its Z3 proof.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Optional

from core.proof_hash import ProofSerializer

logger = logging.getLogger("core.z3_proof")


@dataclass
class Z3ProofAttestation:
    """Attestation with embedded Z3 proof."""

    # DOF identity fields
    agent_id: str
    trust_score: float
    timestamp: int = field(default_factory=lambda: int(time.time()))

    # Z3 proof fields
    z3_proof_hash: bytes = b""
    invariants_verified: list[str] = field(default_factory=list)
    solver_result: str = ""  # "PROVEN" | "TIMEOUT" | "VIOLATED"
    proof_transcript: str = ""
    storage_ref: Optional[str] = None  # IPFS CID or local path

    def compute_proof_hash(self) -> bytes:
        """Compute keccak256 hash of the proof transcript.

        This is DETERMINISTIC: same transcript → same hash, always.
        """
        self.z3_proof_hash = ProofSerializer.hash_proof(self.proof_transcript)
        return self.z3_proof_hash

    def verify(self) -> bool:
        """Verify that the proof hash matches the transcript.

        Returns True if the stored hash matches recomputed hash.
        """
        if not self.proof_transcript or not self.z3_proof_hash:
            return False
        return ProofSerializer.verify_hash(
            self.proof_transcript, self.z3_proof_hash
        )

    def to_attestation_payload(self) -> dict:
        """Convert to dict payload for on-chain registration."""
        return {
            "agent_id": self.agent_id,
            "trust_score": self.trust_score,
            "trust_score_scaled": int(self.trust_score * 10**18),
            "timestamp": self.timestamp,
            "z3_proof_hash": self.z3_proof_hash.hex() if self.z3_proof_hash else "",
            "invariants_verified": self.invariants_verified,
            "invariants_count": len(self.invariants_verified),
            "solver_result": self.solver_result,
            "storage_ref": self.storage_ref or "",
        }

    @classmethod
    def from_gate_verification(
        cls, gate_result, agent_id: str, trust_score: float
    ) -> Z3ProofAttestation:
        """Create attestation from a Z3Gate verification result.

        Args:
            gate_result: GateVerification from Z3Gate.
            agent_id: Agent identifier.
            trust_score: Current trust score.

        Returns:
            Z3ProofAttestation with proof hash computed.
        """
        transcript = gate_result.proof_transcript or ""
        invariants = []

        # Extract invariants from transcript
        if transcript:
            for line in transcript.split("\n"):
                line = line.strip()
                if line.startswith("INV-"):
                    inv_id = line.split(":")[0].strip()
                    invariants.append(inv_id)

        attestation = cls(
            agent_id=agent_id,
            trust_score=trust_score,
            invariants_verified=invariants,
            solver_result=gate_result.result.value if hasattr(gate_result.result, 'value') else str(gate_result.result),
            proof_transcript=transcript,
        )
        attestation.compute_proof_hash()
        return attestation
