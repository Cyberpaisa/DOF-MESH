"""
Tests for core.z3_proof — Z3 proof attestations.

Verifies:
- Z3ProofAttestation dataclass fields
- compute_proof_hash determinism
- verify() correctness
- to_attestation_payload structure
- from_gate_verification factory
"""

import unittest
import time

from core.z3_proof import Z3ProofAttestation
from core.proof_hash import ProofSerializer


class TestZ3ProofAttestationDefaults(unittest.TestCase):
    """Test Z3ProofAttestation default values."""

    def test_default_fields(self):
        a = Z3ProofAttestation(agent_id="agent-1", trust_score=0.85)
        self.assertEqual(a.agent_id, "agent-1")
        self.assertEqual(a.trust_score, 0.85)
        self.assertEqual(a.z3_proof_hash, b"")
        self.assertEqual(a.invariants_verified, [])
        self.assertEqual(a.solver_result, "")
        self.assertEqual(a.proof_transcript, "")
        self.assertIsNone(a.storage_ref)

    def test_timestamp_auto(self):
        before = int(time.time())
        a = Z3ProofAttestation(agent_id="a", trust_score=0.5)
        after = int(time.time())
        self.assertGreaterEqual(a.timestamp, before)
        self.assertLessEqual(a.timestamp, after)

    def test_mutable_default_list(self):
        a1 = Z3ProofAttestation(agent_id="a", trust_score=0.5)
        a2 = Z3ProofAttestation(agent_id="b", trust_score=0.5)
        a1.invariants_verified.append("INV-1")
        self.assertEqual(a2.invariants_verified, [])


class TestComputeProofHash(unittest.TestCase):
    """Test compute_proof_hash."""

    def test_returns_bytes(self):
        a = Z3ProofAttestation(
            agent_id="a", trust_score=0.9,
            proof_transcript="test transcript",
        )
        h = a.compute_proof_hash()
        self.assertIsInstance(h, bytes)
        self.assertEqual(len(h), 32)

    def test_deterministic(self):
        """Same transcript → same hash. Always."""
        transcript = "INV-1: PROVEN\nINV-2: PROVEN"
        a1 = Z3ProofAttestation(agent_id="a", trust_score=0.9,
                                 proof_transcript=transcript)
        a2 = Z3ProofAttestation(agent_id="b", trust_score=0.1,
                                 proof_transcript=transcript)
        self.assertEqual(a1.compute_proof_hash(), a2.compute_proof_hash())

    def test_different_transcript_different_hash(self):
        a1 = Z3ProofAttestation(agent_id="a", trust_score=0.9,
                                 proof_transcript="transcript A")
        a2 = Z3ProofAttestation(agent_id="a", trust_score=0.9,
                                 proof_transcript="transcript B")
        self.assertNotEqual(a1.compute_proof_hash(), a2.compute_proof_hash())

    def test_empty_transcript(self):
        a = Z3ProofAttestation(agent_id="a", trust_score=0.5,
                                proof_transcript="")
        h = a.compute_proof_hash()
        self.assertEqual(h, b"\x00" * 32)

    def test_stores_hash_on_instance(self):
        a = Z3ProofAttestation(agent_id="a", trust_score=0.5,
                                proof_transcript="data")
        a.compute_proof_hash()
        self.assertNotEqual(a.z3_proof_hash, b"")


class TestVerify(unittest.TestCase):
    """Test verify() method."""

    def test_valid_proof_verifies(self):
        a = Z3ProofAttestation(
            agent_id="a", trust_score=0.9,
            proof_transcript="valid proof data",
        )
        a.compute_proof_hash()
        self.assertTrue(a.verify())

    def test_tampered_transcript_fails(self):
        a = Z3ProofAttestation(
            agent_id="a", trust_score=0.9,
            proof_transcript="original",
        )
        a.compute_proof_hash()
        a.proof_transcript = "tampered"
        self.assertFalse(a.verify())

    def test_empty_transcript_fails(self):
        a = Z3ProofAttestation(agent_id="a", trust_score=0.5)
        self.assertFalse(a.verify())

    def test_no_hash_fails(self):
        a = Z3ProofAttestation(agent_id="a", trust_score=0.5,
                                proof_transcript="data")
        self.assertFalse(a.verify())


class TestToAttestationPayload(unittest.TestCase):
    """Test to_attestation_payload."""

    def test_returns_dict(self):
        a = Z3ProofAttestation(
            agent_id="agent-42", trust_score=0.85,
            invariants_verified=["INV-1", "INV-2"],
            solver_result="PROVEN",
            proof_transcript="test",
        )
        a.compute_proof_hash()
        payload = a.to_attestation_payload()
        self.assertIsInstance(payload, dict)

    def test_required_fields(self):
        a = Z3ProofAttestation(
            agent_id="a", trust_score=0.9,
            invariants_verified=["INV-1"],
            solver_result="PROVEN",
        )
        a.compute_proof_hash()
        payload = a.to_attestation_payload()
        required = {"agent_id", "trust_score", "trust_score_scaled",
                     "timestamp", "z3_proof_hash", "invariants_verified",
                     "invariants_count", "solver_result", "storage_ref"}
        self.assertEqual(set(payload.keys()), required)

    def test_trust_score_scaled(self):
        a = Z3ProofAttestation(agent_id="a", trust_score=0.85)
        payload = a.to_attestation_payload()
        self.assertEqual(payload["trust_score_scaled"], int(0.85 * 10**18))

    def test_invariants_count(self):
        a = Z3ProofAttestation(
            agent_id="a", trust_score=0.5,
            invariants_verified=["INV-1", "INV-2", "INV-3"],
        )
        payload = a.to_attestation_payload()
        self.assertEqual(payload["invariants_count"], 3)


class TestFromGateVerification(unittest.TestCase):
    """Test from_gate_verification factory."""

    def _make_gate_result(self, result_val="APPROVED", transcript=""):
        """Create a mock GateVerification."""
        class MockResult:
            value = result_val
        class MockGate:
            result = MockResult()
            proof_transcript = transcript
        return MockGate()

    def test_creates_attestation(self):
        gate = self._make_gate_result(
            transcript="INV-1: PROVEN\nINV-2: PROVEN"
        )
        a = Z3ProofAttestation.from_gate_verification(gate, "agent-1", 0.9)
        self.assertIsInstance(a, Z3ProofAttestation)
        self.assertEqual(a.agent_id, "agent-1")
        self.assertEqual(a.trust_score, 0.9)

    def test_extracts_invariants(self):
        gate = self._make_gate_result(
            transcript="INV-1: PROVEN\nINV-6: PROVEN\nsome other line"
        )
        a = Z3ProofAttestation.from_gate_verification(gate, "a", 0.5)
        self.assertIn("INV-1", a.invariants_verified)
        self.assertIn("INV-6", a.invariants_verified)

    def test_computes_hash(self):
        gate = self._make_gate_result(transcript="test data")
        a = Z3ProofAttestation.from_gate_verification(gate, "a", 0.5)
        self.assertNotEqual(a.z3_proof_hash, b"")


if __name__ == "__main__":
    unittest.main()
