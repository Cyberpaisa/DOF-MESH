"""
Tests for core.proof_hash — deterministic serialization and hashing.

Verifies:
- serialize_proof is deterministic
- hash_proof returns 32 bytes
- verify_hash matches
- serialize_model is deterministic
- Different inputs → different hashes
"""

import unittest

from core.proof_hash import ProofSerializer


class TestSerializeProof(unittest.TestCase):
    """Test serialize_proof determinism."""

    def test_returns_string(self):
        result = ProofSerializer.serialize_proof(
            ["a > 0", "b < 1"], "PROVEN", ["INV-1"]
        )
        self.assertIsInstance(result, str)

    def test_deterministic_same_input(self):
        """Same input → same output. Always."""
        t1 = ProofSerializer.serialize_proof(
            ["a > 0", "b < 1"], "PROVEN", ["INV-1", "INV-2"]
        )
        t2 = ProofSerializer.serialize_proof(
            ["a > 0", "b < 1"], "PROVEN", ["INV-1", "INV-2"]
        )
        self.assertEqual(t1, t2)

    def test_deterministic_reordered_input(self):
        """Reordered inputs → same output (sorted internally)."""
        t1 = ProofSerializer.serialize_proof(
            ["b < 1", "a > 0"], "PROVEN", ["INV-2", "INV-1"]
        )
        t2 = ProofSerializer.serialize_proof(
            ["a > 0", "b < 1"], "PROVEN", ["INV-1", "INV-2"]
        )
        self.assertEqual(t1, t2)

    def test_different_result_different_output(self):
        t1 = ProofSerializer.serialize_proof([], "PROVEN", [])
        t2 = ProofSerializer.serialize_proof([], "VIOLATED", [])
        self.assertNotEqual(t1, t2)

    def test_with_model_data(self):
        result = ProofSerializer.serialize_proof(
            ["x > 0"], "VIOLATED", ["INV-1"],
            model_data={"x": 0.5, "y": True}
        )
        self.assertIn("model", result)

    def test_without_model_data(self):
        result = ProofSerializer.serialize_proof(
            ["x > 0"], "PROVEN", ["INV-1"]
        )
        self.assertIn("null", result)  # model is None → null in JSON


class TestHashProof(unittest.TestCase):
    """Test hash_proof."""

    def test_returns_32_bytes(self):
        h = ProofSerializer.hash_proof("test transcript")
        self.assertIsInstance(h, bytes)
        self.assertEqual(len(h), 32)

    def test_deterministic(self):
        h1 = ProofSerializer.hash_proof("same data")
        h2 = ProofSerializer.hash_proof("same data")
        self.assertEqual(h1, h2)

    def test_different_input_different_hash(self):
        h1 = ProofSerializer.hash_proof("data A")
        h2 = ProofSerializer.hash_proof("data B")
        self.assertNotEqual(h1, h2)

    def test_empty_string(self):
        h = ProofSerializer.hash_proof("")
        self.assertEqual(h, b"\x00" * 32)


class TestVerifyHash(unittest.TestCase):
    """Test verify_hash."""

    def test_valid_hash(self):
        transcript = "test transcript data"
        h = ProofSerializer.hash_proof(transcript)
        self.assertTrue(ProofSerializer.verify_hash(transcript, h))

    def test_tampered_data(self):
        h = ProofSerializer.hash_proof("original")
        self.assertFalse(ProofSerializer.verify_hash("tampered", h))

    def test_wrong_hash(self):
        self.assertFalse(ProofSerializer.verify_hash("data", b"\x00" * 32))


class TestSerializeModel(unittest.TestCase):
    """Test serialize_model."""

    def test_returns_string(self):
        result = ProofSerializer.serialize_model({"x": 0.5})
        self.assertIsInstance(result, str)

    def test_deterministic(self):
        m1 = ProofSerializer.serialize_model({"b": 1, "a": 2})
        m2 = ProofSerializer.serialize_model({"a": 2, "b": 1})
        self.assertEqual(m1, m2)

    def test_nested_dict(self):
        result = ProofSerializer.serialize_model({
            "pre": {"trust": 0.5},
            "post": {"trust": 0.3},
        })
        self.assertIn("pre", result)
        self.assertIn("post", result)


if __name__ == "__main__":
    unittest.main()
