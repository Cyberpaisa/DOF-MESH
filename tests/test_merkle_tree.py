"""
Tests for core/merkle_tree.py — MerkleTree and MerkleBatcher.

All tests are deterministic, no network or blockchain calls.
"""

import os
import sys
import json
import hashlib
import tempfile
import unittest

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.merkle_tree import MerkleTree, MerkleBatcher, MerkleBatch, _sha256, _hash_pair


def _h(s: str) -> str:
    """Helper: SHA256 hex of a string."""
    return hashlib.sha256(s.encode()).hexdigest()


class TestSHA256Helpers(unittest.TestCase):
    """Test internal hash helpers."""

    def test_sha256_deterministic(self):
        a = _sha256(b"hello")
        b = _sha256(b"hello")
        self.assertEqual(a, b)
        self.assertEqual(len(a), 64)

    def test_sha256_different_inputs(self):
        a = _sha256(b"hello")
        b = _sha256(b"world")
        self.assertNotEqual(a, b)

    def test_hash_pair_canonical_order(self):
        """hash_pair sorts inputs so order doesn't matter."""
        h1 = _h("a")
        h2 = _h("b")
        self.assertEqual(_hash_pair(h1, h2), _hash_pair(h2, h1))

    def test_hash_pair_different_pairs(self):
        h1 = _h("a")
        h2 = _h("b")
        h3 = _h("c")
        self.assertNotEqual(_hash_pair(h1, h2), _hash_pair(h1, h3))


class TestMerkleTreeConstruction(unittest.TestCase):
    """Test MerkleTree build and properties."""

    def test_empty_tree(self):
        tree = MerkleTree([])
        self.assertEqual(tree.root, "")
        self.assertEqual(tree.leaves, [])
        self.assertEqual(tree.depth, 0)

    def test_single_leaf(self):
        h = _h("single")
        tree = MerkleTree([h])
        self.assertEqual(tree.root, h)
        self.assertEqual(tree.leaves, [h])
        self.assertEqual(tree.depth, 0)

    def test_two_leaves(self):
        h1 = _h("a")
        h2 = _h("b")
        tree = MerkleTree([h1, h2])
        expected_root = _hash_pair(h1, h2)
        self.assertEqual(tree.root, expected_root)
        self.assertEqual(tree.depth, 1)

    def test_three_leaves_odd_duplication(self):
        """Odd leaf count duplicates last leaf."""
        h1 = _h("a")
        h2 = _h("b")
        h3 = _h("c")
        tree = MerkleTree([h1, h2, h3])
        self.assertNotEqual(tree.root, "")
        self.assertEqual(len(tree.leaves), 3)
        self.assertEqual(tree.depth, 2)

    def test_four_leaves(self):
        leaves = [_h(str(i)) for i in range(4)]
        tree = MerkleTree(leaves)
        self.assertEqual(tree.depth, 2)
        self.assertEqual(len(tree.leaves), 4)

    def test_power_of_two_leaves(self):
        leaves = [_h(str(i)) for i in range(8)]
        tree = MerkleTree(leaves)
        self.assertEqual(tree.depth, 3)

    def test_root_deterministic(self):
        leaves = [_h(str(i)) for i in range(5)]
        tree1 = MerkleTree(leaves)
        tree2 = MerkleTree(leaves)
        self.assertEqual(tree1.root, tree2.root)

    def test_different_leaves_different_root(self):
        tree1 = MerkleTree([_h("a"), _h("b")])
        tree2 = MerkleTree([_h("c"), _h("d")])
        self.assertNotEqual(tree1.root, tree2.root)


class TestMerkleProofs(unittest.TestCase):
    """Test proof generation and verification."""

    def test_proof_single_leaf(self):
        h = _h("only")
        tree = MerkleTree([h])
        proof = tree.get_proof(0)
        self.assertEqual(proof, [])
        self.assertTrue(MerkleTree.verify_proof(h, proof, tree.root))

    def test_proof_two_leaves(self):
        h1, h2 = _h("a"), _h("b")
        tree = MerkleTree([h1, h2])

        proof0 = tree.get_proof(0)
        self.assertTrue(MerkleTree.verify_proof(h1, proof0, tree.root))

        proof1 = tree.get_proof(1)
        self.assertTrue(MerkleTree.verify_proof(h2, proof1, tree.root))

    def test_proof_five_leaves_all_valid(self):
        leaves = [_h(str(i)) for i in range(5)]
        tree = MerkleTree(leaves)

        for i, leaf in enumerate(leaves):
            proof = tree.get_proof(i)
            self.assertTrue(
                MerkleTree.verify_proof(leaf, proof, tree.root),
                f"Proof failed for leaf {i}"
            )

    def test_proof_sixteen_leaves(self):
        leaves = [_h(str(i)) for i in range(16)]
        tree = MerkleTree(leaves)

        for i in range(16):
            proof = tree.get_proof(i)
            self.assertTrue(MerkleTree.verify_proof(leaves[i], proof, tree.root))

    def test_proof_invalid_leaf(self):
        leaves = [_h(str(i)) for i in range(4)]
        tree = MerkleTree(leaves)
        proof = tree.get_proof(0)
        # Wrong leaf should fail
        fake_leaf = _h("fake")
        self.assertFalse(MerkleTree.verify_proof(fake_leaf, proof, tree.root))

    def test_proof_invalid_root(self):
        leaves = [_h(str(i)) for i in range(4)]
        tree = MerkleTree(leaves)
        proof = tree.get_proof(0)
        fake_root = _h("fake_root")
        self.assertFalse(MerkleTree.verify_proof(leaves[0], proof, fake_root))

    def test_proof_index_out_of_range(self):
        tree = MerkleTree([_h("a")])
        with self.assertRaises(IndexError):
            tree.get_proof(1)
        with self.assertRaises(IndexError):
            tree.get_proof(-1)

    def test_proof_empty_tree(self):
        tree = MerkleTree([])
        with self.assertRaises(IndexError):
            tree.get_proof(0)


class TestMerkleTreeSerialization(unittest.TestCase):
    """Test to_dict / from_dict round-trip."""

    def test_round_trip(self):
        leaves = [_h(str(i)) for i in range(7)]
        tree = MerkleTree(leaves)
        d = tree.to_dict()

        self.assertEqual(d["root"], tree.root)
        self.assertEqual(d["leaves"], leaves)
        self.assertEqual(d["leaf_count"], 7)
        self.assertEqual(d["depth"], tree.depth)

        # Reconstruct
        tree2 = MerkleTree.from_dict(d)
        self.assertEqual(tree2.root, tree.root)
        self.assertEqual(tree2.leaves, tree.leaves)

    def test_json_serializable(self):
        tree = MerkleTree([_h("a"), _h("b"), _h("c")])
        d = tree.to_dict()
        s = json.dumps(d)
        self.assertIsInstance(s, str)
        parsed = json.loads(s)
        self.assertEqual(parsed["root"], tree.root)


class TestMerkleBatcher(unittest.TestCase):
    """Test MerkleBatcher queue/flush/verify."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._log_path = os.path.join(self._tmpdir, "test_batches.jsonl")

    def test_add_and_flush(self):
        batcher = MerkleBatcher(log_path=self._log_path)
        for i in range(5):
            batcher.add(_h(str(i)))

        self.assertEqual(batcher.queue_size, 5)
        batch = batcher.flush()
        self.assertIsNotNone(batch)
        self.assertEqual(batch.leaf_count, 5)
        self.assertNotEqual(batch.root, "")
        self.assertEqual(batcher.queue_size, 0)

    def test_flush_empty_returns_none(self):
        batcher = MerkleBatcher(log_path=self._log_path)
        self.assertIsNone(batcher.flush())

    def test_auto_flush_at_threshold(self):
        batcher = MerkleBatcher(threshold=3, log_path=self._log_path)
        result1 = batcher.add(_h("a"))
        result2 = batcher.add(_h("b"))
        self.assertIsNone(result1)
        self.assertIsNone(result2)

        # Third add triggers auto-flush
        result3 = batcher.add(_h("c"))
        self.assertIsNotNone(result3)
        self.assertEqual(result3.leaf_count, 3)
        self.assertEqual(batcher.queue_size, 0)

    def test_verify_batch(self):
        batcher = MerkleBatcher(log_path=self._log_path)
        for i in range(10):
            batcher.add(_h(str(i)))

        batch = batcher.flush()
        verification = batcher.verify(batch)

        self.assertTrue(verification["all_valid"])
        self.assertEqual(verification["verified"], 10)
        self.assertEqual(verification["failed"], 0)

    def test_batch_id_increments(self):
        batcher = MerkleBatcher(log_path=self._log_path)
        batcher.add(_h("a"))
        b1 = batcher.flush()
        batcher.add(_h("b"))
        b2 = batcher.flush()

        self.assertEqual(b1.batch_id, "batch-0001")
        self.assertEqual(b2.batch_id, "batch-0002")

    def test_batches_history(self):
        batcher = MerkleBatcher(log_path=self._log_path)
        batcher.add(_h("a"))
        batcher.flush()
        batcher.add(_h("b"))
        batcher.flush()

        self.assertEqual(len(batcher.batches), 2)

    def test_log_file_created(self):
        batcher = MerkleBatcher(log_path=self._log_path)
        batcher.add(_h("test"))
        batcher.flush()

        self.assertTrue(os.path.exists(self._log_path))
        with open(self._log_path) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertIn("root", entry)
        self.assertIn("batch_id", entry)
        self.assertEqual(entry["leaf_count"], 1)

    def test_multiple_batches_logged(self):
        batcher = MerkleBatcher(threshold=2, log_path=self._log_path)
        for i in range(6):
            batcher.add(_h(str(i)))

        # Should have auto-flushed 3 batches (6 / 2)
        self.assertEqual(len(batcher.batches), 3)

        with open(self._log_path) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 3)


class TestMerkleTreeEdgeCases(unittest.TestCase):
    """Edge cases and stress tests."""

    def test_duplicate_leaves(self):
        h = _h("same")
        tree = MerkleTree([h, h, h])
        self.assertNotEqual(tree.root, "")
        # All proofs should still verify
        for i in range(3):
            proof = tree.get_proof(i)
            self.assertTrue(MerkleTree.verify_proof(h, proof, tree.root))

    def test_large_tree_100_leaves(self):
        leaves = [_h(str(i)) for i in range(100)]
        tree = MerkleTree(leaves)
        self.assertNotEqual(tree.root, "")
        # Spot-check a few proofs
        for i in [0, 49, 99]:
            proof = tree.get_proof(i)
            self.assertTrue(MerkleTree.verify_proof(leaves[i], proof, tree.root))

    def test_none_leaves_default(self):
        tree = MerkleTree(None)
        self.assertEqual(tree.root, "")
        self.assertEqual(tree.leaves, [])


class TestOracleBridgeMerkleIntegration(unittest.TestCase):
    """Test OracleBridge.publish_merkle_batch integration."""

    def test_publish_merkle_batch_with_certs(self):
        """Create real attestation certificates and batch them."""
        from core.oracle_bridge import OracleBridge, CertificateSigner, AttestationCertificate

        signer = CertificateSigner(
            key_path=os.path.join(tempfile.mkdtemp(), "test_key.json")
        )
        bridge = OracleBridge(signer, oags=None)

        # Create 5 attestations
        certs = []
        for i in range(5):
            cert = bridge.create_attestation(
                task_id=f"test-task-{i}",
                metrics={"SS": 0.95, "GCR": 1.0, "PFI": 0.05, "RP": 0.9, "SSR": 0.88},
            )
            certs.append(cert)

        # Batch them
        result = bridge.publish_merkle_batch(certs)

        self.assertEqual(result["status"], "batched")
        self.assertEqual(result["leaf_count"], 5)
        self.assertTrue(result["all_proofs_valid"])
        self.assertIn("root", result)
        self.assertIn("batch", result)

    def test_publish_merkle_batch_empty(self):
        from core.oracle_bridge import OracleBridge, CertificateSigner

        signer = CertificateSigner(
            key_path=os.path.join(tempfile.mkdtemp(), "test_key.json")
        )
        bridge = OracleBridge(signer, oags=None)
        result = bridge.publish_merkle_batch([])
        self.assertEqual(result["status"], "error")


class TestMerkleTreePlainStringLeaves(unittest.TestCase):
    """MerkleTree must accept plain strings, not just pre-hashed hex leaves."""

    def test_plain_strings_build_without_error(self):
        mt = MerkleTree(["a", "b", "c"])
        self.assertNotEqual(mt.root, "")

    def test_plain_strings_root_is_hex(self):
        mt = MerkleTree(["hello", "world"])
        self.assertRegex(mt.root, r'^[0-9a-f]{64}$')

    def test_plain_strings_consistent_root(self):
        mt1 = MerkleTree(["x", "y"])
        mt2 = MerkleTree(["x", "y"])
        self.assertEqual(mt1.root, mt2.root)

    def test_none_leaves_are_skipped(self):
        mt = MerkleTree([None, "b", None])
        self.assertEqual(len(mt.leaves), 1)

    def test_all_none_leaves_empty_root(self):
        mt = MerkleTree([None, None])
        self.assertEqual(mt.root, "")

    def test_mixed_none_and_plain_strings(self):
        mt_with_none = MerkleTree([None, "a", "b"])
        mt_without = MerkleTree(["a", "b"])
        self.assertEqual(mt_with_none.root, mt_without.root)


if __name__ == "__main__":
    unittest.main()
