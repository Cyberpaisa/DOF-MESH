"""
Tests for the proof attestation pipeline — end-to-end flow.

Verifies:
- GateVerification → Z3ProofAttestation → ProofStorage round-trip
- Proof hash determinism across the pipeline
- Attestation payload is valid for on-chain registration
- Pipeline works with real TransitionVerifier results
"""

import os
import shutil
import unittest
import tempfile

from core.z3_proof import Z3ProofAttestation
from core.proof_hash import ProofSerializer
from core.proof_storage import ProofStorage
from core.transitions import TransitionVerifier


class TestPipelineEndToEnd(unittest.TestCase):
    """End-to-end pipeline: verify → attest → store → retrieve → verify."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.storage = ProofStorage(mode="local", proof_dir=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_full_pipeline(self):
        """TransitionVerifier → serialize → attest → store → retrieve → verify."""
        # Step 1: Run Z3 verification
        verifier = TransitionVerifier()
        result = verifier.verify_invariant("INV-1")
        self.assertEqual(result.status, "PROVEN")

        # Step 2: Create proof transcript
        transcript = ProofSerializer.serialize_proof(
            solver_assertions=["threat_detected → NOT publish_allowed"],
            result=result.status,
            invariants=[result.invariant_id],
        )

        # Step 3: Create attestation
        attestation = Z3ProofAttestation(
            agent_id="test-agent",
            trust_score=0.9,
            invariants_verified=[result.invariant_id],
            solver_result=result.status,
            proof_transcript=transcript,
        )
        attestation.compute_proof_hash()

        # Step 4: Store proof
        ref = self.storage.store_proof(transcript)
        attestation.storage_ref = ref

        # Step 5: Retrieve and verify
        retrieved = self.storage.retrieve_proof(ref)
        self.assertEqual(retrieved, transcript)
        self.assertTrue(attestation.verify())

    def test_pipeline_all_invariants(self):
        """Run pipeline for all 8 invariants."""
        verifier = TransitionVerifier()
        results = verifier.verify_all()

        invariant_ids = []
        assertions = []
        for inv_id, r in results.items():
            self.assertEqual(r.status, "PROVEN")
            invariant_ids.append(inv_id)
            assertions.append(f"{inv_id}: {r.description}")

        transcript = ProofSerializer.serialize_proof(
            solver_assertions=assertions,
            result="PROVEN",
            invariants=invariant_ids,
        )

        attestation = Z3ProofAttestation(
            agent_id="pipeline-agent",
            trust_score=0.95,
            invariants_verified=invariant_ids,
            solver_result="PROVEN",
            proof_transcript=transcript,
        )
        attestation.compute_proof_hash()

        ref = self.storage.store_proof(transcript)
        attestation.storage_ref = ref

        payload = attestation.to_attestation_payload()
        self.assertEqual(payload["invariants_count"], 8)
        self.assertEqual(payload["solver_result"], "PROVEN")
        self.assertTrue(attestation.verify())


class TestPipelineDeterminism(unittest.TestCase):
    """Verify determinism across the pipeline."""

    def test_same_verification_same_hash(self):
        """Running the same verification twice produces the same hash."""
        transcript = ProofSerializer.serialize_proof(
            ["constraint_a", "constraint_b"], "PROVEN", ["INV-1", "INV-2"]
        )
        h1 = ProofSerializer.hash_proof(transcript)

        transcript2 = ProofSerializer.serialize_proof(
            ["constraint_b", "constraint_a"], "PROVEN", ["INV-2", "INV-1"]
        )
        h2 = ProofSerializer.hash_proof(transcript2)

        self.assertEqual(h1, h2)

    def test_attestation_payload_hash_matches(self):
        """Payload hash matches the computed proof hash."""
        attestation = Z3ProofAttestation(
            agent_id="det-agent",
            trust_score=0.85,
            proof_transcript="deterministic test",
        )
        attestation.compute_proof_hash()
        payload = attestation.to_attestation_payload()
        self.assertEqual(
            payload["z3_proof_hash"],
            attestation.z3_proof_hash.hex()
        )


class TestPipelinePayloadForChain(unittest.TestCase):
    """Verify attestation payload is valid for on-chain registration."""

    def test_trust_score_scaled_correctly(self):
        a = Z3ProofAttestation(agent_id="a", trust_score=0.85)
        payload = a.to_attestation_payload()
        # 0.85 * 10^18 = 850000000000000000
        self.assertEqual(payload["trust_score_scaled"], 850000000000000000)

    def test_proof_hash_is_hex_string(self):
        a = Z3ProofAttestation(
            agent_id="a", trust_score=0.5,
            proof_transcript="test",
        )
        a.compute_proof_hash()
        payload = a.to_attestation_payload()
        self.assertEqual(len(payload["z3_proof_hash"]), 64)  # 32 bytes hex

    def test_empty_storage_ref(self):
        a = Z3ProofAttestation(agent_id="a", trust_score=0.5)
        payload = a.to_attestation_payload()
        self.assertEqual(payload["storage_ref"], "")


class TestPipelineWithStorage(unittest.TestCase):
    """Test pipeline with proof storage integration."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.storage = ProofStorage(mode="local", proof_dir=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_store_and_list(self):
        transcript = ProofSerializer.serialize_proof(
            ["a > 0"], "PROVEN", ["INV-1"]
        )
        self.storage.store_proof(transcript)
        proofs = self.storage.list_proofs()
        self.assertEqual(len(proofs), 1)

    def test_multiple_proofs(self):
        for i in range(3):
            t = ProofSerializer.serialize_proof(
                [f"constraint_{i}"], "PROVEN", [f"INV-{i}"]
            )
            self.storage.store_proof(t)
        self.assertEqual(len(self.storage.list_proofs()), 3)


if __name__ == "__main__":
    unittest.main()
