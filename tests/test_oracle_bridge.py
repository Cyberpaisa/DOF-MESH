"""
Tests for core/oracle_bridge.py — ERC-8004 Oracle Bridge.

Covers:
  - CertificateSigner: key generation, signing, verification
  - OracleBridge: attestation creation, publishing rules, transaction prep, batch, verify
  - AttestationRegistry: persistence, lookup, compliance rate, export
  - dof public API exports
"""

import os
import json
import tempfile
import unittest
from unittest.mock import MagicMock

from core.oracle_bridge import (
    OracleBridge,
    AttestationCertificate,
    CertificateSigner,
    AttestationRegistry,
)


class TestCertificateSigner(unittest.TestCase):
    """Test HMAC-SHA256 signing functionality."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._key_path = os.path.join(self._tmpdir, "test_key.json")
        self.signer = CertificateSigner(key_path=self._key_path)

    def test_key_generation(self):
        """Signing key is generated and persisted to file."""
        self.assertTrue(os.path.exists(self._key_path))
        with open(self._key_path, "r") as f:
            data = json.load(f)
        self.assertIn("secret_key_hex", data)
        self.assertEqual(data["algorithm"], "HMAC-SHA256")

    def test_sign_returns_hex(self):
        """sign() returns a hex string."""
        sig = self.signer.sign(b"test payload")
        self.assertIsInstance(sig, str)
        # HMAC-SHA256 produces 64 hex chars
        self.assertEqual(len(sig), 64)

    def test_sign_deterministic(self):
        """Same input produces same signature."""
        sig1 = self.signer.sign(b"deterministic")
        sig2 = self.signer.sign(b"deterministic")
        self.assertEqual(sig1, sig2)

    def test_sign_different_inputs(self):
        """Different inputs produce different signatures."""
        sig1 = self.signer.sign(b"input_a")
        sig2 = self.signer.sign(b"input_b")
        self.assertNotEqual(sig1, sig2)

    def test_verify_valid(self):
        """verify() returns True for valid signature."""
        data = b"verify me"
        sig = self.signer.sign(data)
        self.assertTrue(self.signer.verify(data, sig))

    def test_verify_invalid(self):
        """verify() returns False for tampered signature."""
        data = b"verify me"
        self.assertFalse(self.signer.verify(data, "deadbeef" * 8))

    def test_key_reload(self):
        """A new signer with same key_path produces same signatures."""
        sig1 = self.signer.sign(b"reload test")
        signer2 = CertificateSigner(key_path=self._key_path)
        sig2 = signer2.sign(b"reload test")
        self.assertEqual(sig1, sig2)

    def test_get_public_id(self):
        """get_public_id() returns a non-empty hex string."""
        pid = self.signer.get_public_id()
        self.assertIsInstance(pid, str)
        self.assertGreater(len(pid), 0)


class TestOracleBridge(unittest.TestCase):
    """Test attestation creation, publishing, and verification."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._key_path = os.path.join(self._tmpdir, "test_key.json")
        self.signer = CertificateSigner(key_path=self._key_path)

        # Mock OAGS identity
        self.oags = MagicMock()
        self.oags.get_agent_card.return_value = {"identity_hash": "test-agent-hash-123"}

        self.bridge = OracleBridge(self.signer, self.oags)

    def test_create_attestation_compliant(self):
        """Attestation with GCR=1.0 is COMPLIANT."""
        cert = self.bridge.create_attestation(
            task_id="task-001",
            metrics={"SS": 0.95, "GCR": 1.0, "PFI": 0.1, "RP": 0.8, "SSR": 0.9},
        )
        self.assertIsInstance(cert, AttestationCertificate)
        self.assertEqual(cert.governance_status, "COMPLIANT")
        self.assertEqual(cert.task_id, "task-001")
        self.assertEqual(cert.agent_identity, "test-agent-hash-123")

    def test_create_attestation_non_compliant(self):
        """Attestation with GCR < 1.0 is NON_COMPLIANT."""
        cert = self.bridge.create_attestation(
            task_id="task-002",
            metrics={"SS": 0.8, "GCR": 0.7, "PFI": 0.3},
        )
        self.assertEqual(cert.governance_status, "NON_COMPLIANT")

    def test_z3_verified_all_pass(self):
        """z3_verified is True when all Z3 results are VERIFIED."""
        z3_results = [
            {"result": "VERIFIED"},
            {"result": "VERIFIED"},
        ]
        cert = self.bridge.create_attestation(
            task_id="task-z3",
            metrics={"GCR": 1.0},
            z3_results=z3_results,
        )
        self.assertTrue(cert.z3_verified)

    def test_z3_verified_partial_fail(self):
        """z3_verified is False when any Z3 result is not VERIFIED."""
        z3_results = [
            {"result": "VERIFIED"},
            {"result": "COUNTEREXAMPLE_FOUND"},
        ]
        cert = self.bridge.create_attestation(
            task_id="task-z3-fail",
            metrics={"GCR": 1.0},
            z3_results=z3_results,
        )
        self.assertFalse(cert.z3_verified)

    def test_should_publish_compliant(self):
        """COMPLIANT attestations should be published."""
        cert = self.bridge.create_attestation(
            task_id="pub-001",
            metrics={"SS": 0.95, "GCR": 1.0},
        )
        self.assertTrue(self.bridge.should_publish(cert))

    def test_should_not_publish_non_compliant(self):
        """NON_COMPLIANT attestations should NOT be published."""
        cert = self.bridge.create_attestation(
            task_id="pub-002",
            metrics={"SS": 0.95, "GCR": 0.5},
        )
        self.assertFalse(self.bridge.should_publish(cert))

    def test_should_publish_low_ss_warning(self):
        """COMPLIANT + low SS still publishes (with warning)."""
        cert = self.bridge.create_attestation(
            task_id="pub-003",
            metrics={"SS": 0.3, "GCR": 1.0},
        )
        self.assertTrue(self.bridge.should_publish(cert))

    def test_prepare_transaction(self):
        """Transaction structure has required ERC-8004 fields."""
        cert = self.bridge.create_attestation(
            task_id="tx-001",
            metrics={"SS": 0.9, "GCR": 1.0},
        )
        tx = self.bridge.prepare_transaction(cert)
        self.assertIn("to", tx)
        self.assertIn("data", tx)
        self.assertIn("chain", tx)
        self.assertEqual(tx["chain"], "avalanche-c-chain")
        self.assertEqual(tx["data"]["agent_id"], "test-agent-hash-123")
        self.assertEqual(tx["data"]["validation_signal"], "COMPLIANT")

    def test_batch_attestations(self):
        """Batch groups multiple attestations into one transaction."""
        certs = [
            self.bridge.create_attestation(f"batch-{i}", {"GCR": 1.0})
            for i in range(3)
        ]
        batch = self.bridge.batch_attestations(certs)
        self.assertIn("batch_id", batch)
        self.assertEqual(batch["certificates"], 3)
        self.assertEqual(len(batch["transaction_data"]), 3)

    def test_verify_attestation_valid(self):
        """verify_attestation() returns True for untampered certificate."""
        cert = self.bridge.create_attestation(
            task_id="verify-001",
            metrics={"SS": 0.9, "GCR": 1.0},
        )
        self.assertTrue(self.bridge.verify_attestation(cert))

    def test_verify_attestation_tampered(self):
        """verify_attestation() returns False for tampered certificate."""
        cert = self.bridge.create_attestation(
            task_id="verify-002",
            metrics={"SS": 0.9, "GCR": 1.0},
        )
        cert.metrics["SS"] = 0.1  # tamper
        self.assertFalse(self.bridge.verify_attestation(cert))

    def test_certificate_hash_unique(self):
        """Different attestations produce different certificate hashes."""
        cert1 = self.bridge.create_attestation("hash-001", {"GCR": 1.0})
        cert2 = self.bridge.create_attestation("hash-002", {"GCR": 1.0})
        self.assertNotEqual(cert1.certificate_hash, cert2.certificate_hash)


class TestAttestationRegistry(unittest.TestCase):
    """Test off-chain local registry with JSONL persistence."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._key_path = os.path.join(self._tmpdir, "test_key.json")
        self.signer = CertificateSigner(key_path=self._key_path)

        self.oags = MagicMock()
        self.oags.get_agent_card.return_value = {"identity_hash": "reg-agent"}
        self.bridge = OracleBridge(self.signer, self.oags)

        # Patch LOGS_DIR to temp
        import core.oracle_bridge as ob_mod
        self._orig_logs = ob_mod.LOGS_DIR
        ob_mod.LOGS_DIR = self._tmpdir

    def tearDown(self):
        import core.oracle_bridge as ob_mod
        ob_mod.LOGS_DIR = self._orig_logs

    def test_add_and_lookup(self):
        """Add attestation and retrieve by hash."""
        registry = AttestationRegistry()
        cert = self.bridge.create_attestation("reg-001", {"GCR": 1.0})
        registry.add(cert)

        found = registry.get_attestation(cert.certificate_hash)
        self.assertIsNotNone(found)
        self.assertEqual(found.task_id, "reg-001")

    def test_compliance_rate(self):
        """Compliance rate is correctly computed."""
        registry = AttestationRegistry()
        registry.add(self.bridge.create_attestation("c1", {"GCR": 1.0}))
        registry.add(self.bridge.create_attestation("c2", {"GCR": 1.0}))
        registry.add(self.bridge.create_attestation("c3", {"GCR": 0.5}))

        rate = registry.get_compliance_rate()
        self.assertAlmostEqual(rate, 2.0 / 3.0, places=4)

    def test_export_for_chain(self):
        """export_for_chain() returns only unpublished COMPLIANT certs."""
        registry = AttestationRegistry()
        registry.add(self.bridge.create_attestation("e1", {"GCR": 1.0}))
        registry.add(self.bridge.create_attestation("e2", {"GCR": 0.5}))

        pending = registry.export_for_chain()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["task_id"], "e1")

    def test_mark_published(self):
        """mark_published() flags the certificate and removes from export."""
        registry = AttestationRegistry()
        cert = self.bridge.create_attestation("mp-001", {"GCR": 1.0})
        registry.add(cert)

        registry.mark_published(cert.certificate_hash)
        pending = registry.export_for_chain()
        self.assertEqual(len(pending), 0)

    def test_agent_history(self):
        """get_agent_history() filters by agent identity."""
        registry = AttestationRegistry()
        registry.add(self.bridge.create_attestation("ah-1", {"GCR": 1.0}))
        registry.add(self.bridge.create_attestation("ah-2", {"GCR": 0.5}))

        history = registry.get_agent_history("reg-agent")
        self.assertEqual(len(history), 2)


class TestDofOracleExports(unittest.TestCase):
    """Verify dof/__init__.py exports Oracle Bridge symbols."""

    def test_oracle_bridge_importable(self):
        from dof import OracleBridge
        self.assertTrue(callable(OracleBridge))

    def test_attestation_certificate_importable(self):
        from dof import AttestationCertificate
        self.assertIsNotNone(AttestationCertificate)

    def test_certificate_signer_importable(self):
        from dof import CertificateSigner
        self.assertTrue(callable(CertificateSigner))

    def test_attestation_registry_importable(self):
        from dof import AttestationRegistry
        self.assertTrue(callable(AttestationRegistry))


if __name__ == "__main__":
    unittest.main()
