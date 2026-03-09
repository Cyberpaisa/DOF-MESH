"""
Tests for core.proof_storage — local and IPFS proof storage.

Verifies:
- Local storage works without config
- store_proof / retrieve_proof round-trip
- list_proofs returns stored proof hashes
- IPFS fallback to local when not configured
"""

import os
import shutil
import unittest
import tempfile

from core.proof_storage import ProofStorage


class TestLocalStorage(unittest.TestCase):
    """Test local proof storage."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.storage = ProofStorage(mode="local", proof_dir=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_store_returns_path(self):
        ref = self.storage.store_proof("test transcript")
        self.assertTrue(os.path.exists(ref))

    def test_retrieve_round_trip(self):
        ref = self.storage.store_proof("my proof data")
        retrieved = self.storage.retrieve_proof(ref)
        self.assertEqual(retrieved, "my proof data")

    def test_deterministic_filename(self):
        """Same transcript → same file (idempotent)."""
        ref1 = self.storage.store_proof("same data")
        ref2 = self.storage.store_proof("same data")
        self.assertEqual(ref1, ref2)

    def test_different_transcripts_different_files(self):
        ref1 = self.storage.store_proof("data A")
        ref2 = self.storage.store_proof("data B")
        self.assertNotEqual(ref1, ref2)

    def test_list_proofs(self):
        self.storage.store_proof("proof 1")
        self.storage.store_proof("proof 2")
        proofs = self.storage.list_proofs()
        self.assertEqual(len(proofs), 2)

    def test_list_proofs_empty(self):
        proofs = self.storage.list_proofs()
        self.assertEqual(proofs, [])

    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.storage.retrieve_proof("nonexistent")


class TestIPFSFallback(unittest.TestCase):
    """Test IPFS mode falls back to local when not configured."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.storage = ProofStorage(
            mode="ipfs", proof_dir=self.tmpdir,
            ipfs_gateway="", ipfs_key=""
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_ipfs_fallback_to_local(self):
        """IPFS mode without config should fall back to local."""
        ref = self.storage.store_proof("test data")
        self.assertTrue(os.path.exists(ref))

    def test_ipfs_fallback_retrieve(self):
        ref = self.storage.store_proof("test data")
        retrieved = self.storage.retrieve_proof(ref)
        self.assertEqual(retrieved, "test data")


class TestProofStorageInit(unittest.TestCase):
    """Test ProofStorage initialization."""

    def test_default_mode(self):
        s = ProofStorage()
        self.assertEqual(s.mode, "local")

    def test_custom_mode(self):
        s = ProofStorage(mode="both")
        self.assertEqual(s.mode, "both")


if __name__ == "__main__":
    unittest.main()
