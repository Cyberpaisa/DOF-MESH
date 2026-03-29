"""Tests for core/zk_layer.py — ZK Layer over Z3 constraints."""
import sys
import os
import unittest
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.zk_layer import (
    ZKLayer, ZKProof, ConstraintCommitment,
    _sha3, _commit, _constraint_hash, _merkle_root, _merkle_path,
    DOF_CONSTRAINTS,
)


class TestCommitmentFunctions(unittest.TestCase):

    def test_commit_is_deterministic_given_same_inputs(self):
        c1 = _commit("output_hash_abc", "nonce123")
        c2 = _commit("output_hash_abc", "nonce123")
        self.assertEqual(c1, c2)

    def test_commit_different_outputs_different_hashes(self):
        c1 = _commit("output_a", "nonce")
        c2 = _commit("output_b", "nonce")
        self.assertNotEqual(c1, c2)

    def test_commit_same_output_different_nonces_different_commitments(self):
        """Hiding property: same output + different nonce = different commitment."""
        c1 = _commit("output", "nonce_1")
        c2 = _commit("output", "nonce_2")
        self.assertNotEqual(c1, c2)

    def test_commit_format(self):
        c = _commit("output", "nonce")
        self.assertTrue(c.startswith("0x"))
        self.assertEqual(len(c), 66)  # 0x + 64 hex chars

    def test_merkle_root_single_leaf(self):
        root = _merkle_root(["0x" + "a" * 64])
        self.assertTrue(root.startswith("0x"))

    def test_merkle_root_empty(self):
        root = _merkle_root([])
        self.assertTrue(root.startswith("0x"))

    def test_merkle_root_changes_with_leaves(self):
        leaves1 = ["0x" + "a" * 64, "0x" + "b" * 64]
        leaves2 = ["0x" + "a" * 64, "0x" + "c" * 64]
        self.assertNotEqual(_merkle_root(leaves1), _merkle_root(leaves2))

    def test_merkle_root_deterministic(self):
        leaves = ["0x" + "a" * 64, "0x" + "b" * 64]
        self.assertEqual(_merkle_root(leaves), _merkle_root(leaves))


class TestZKLayer(unittest.TestCase):

    def setUp(self):
        self.zk = ZKLayer()

    def test_commit_and_prove_returns_zkproof(self):
        proof = self.zk.commit_and_prove("agent output text")
        self.assertIsInstance(proof, ZKProof)

    def test_proof_has_merkle_root(self):
        proof = self.zk.commit_and_prove("output")
        self.assertTrue(proof.merkle_root.startswith("0x"))

    def test_proof_all_satisfied_by_default(self):
        proof = self.zk.commit_and_prove("output")
        self.assertTrue(proof.all_satisfied)

    def test_proof_is_valid(self):
        proof = self.zk.commit_and_prove("output")
        self.assertTrue(proof.is_valid)

    def test_verify_valid_proof(self):
        proof = self.zk.commit_and_prove("any agent output")
        self.assertTrue(self.zk.verify(proof))

    def test_verify_tampered_proof_fails(self):
        proof = self.zk.commit_and_prove("output")
        # Tamper with a commitment
        proof.commitments[0]["satisfied"] = False
        self.assertFalse(self.zk.verify(proof))

    def test_verify_tampered_merkle_root_fails(self):
        proof = self.zk.commit_and_prove("output")
        proof.merkle_root = "0x" + "f" * 64
        self.assertFalse(self.zk.verify(proof))

    def test_proof_does_not_reveal_output(self):
        """The proof must not contain the original output text."""
        output = "SECRET AGENT OUTPUT CONTENT XYZ"
        proof = self.zk.commit_and_prove(output)
        proof_str = json.dumps(proof.to_dict())
        self.assertNotIn(output, proof_str)

    def test_proof_does_not_reveal_nonces(self):
        """Public proof must not contain nonces."""
        proof = self.zk.commit_and_prove("output")
        for c in proof.commitments:
            self.assertNotIn("nonce", c)

    def test_failed_constraint_invalidates_proof(self):
        z3_results = {c: True for c in DOF_CONSTRAINTS}
        z3_results["no_privilege_escalation"] = False  # one fails
        proof = self.zk.commit_and_prove("bad output", z3_results=z3_results)
        self.assertFalse(proof.all_satisfied)
        self.assertFalse(self.zk.verify(proof))

    def test_selective_disclosure(self):
        proof = self.zk.commit_and_prove("output")
        first_commitment = proof.commitments[0]["commitment"]
        result = self.zk.verify_selective_disclosure(proof, 0, first_commitment)
        self.assertTrue(result)

    def test_proof_timing_recorded(self):
        proof = self.zk.commit_and_prove("output")
        self.assertGreaterEqual(proof.proof_time_ms, 0.0)

    def test_proof_id_is_unique(self):
        p1 = self.zk.commit_and_prove("output1")
        p2 = self.zk.commit_and_prove("output2")
        self.assertNotEqual(p1.proof_id, p2.proof_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
