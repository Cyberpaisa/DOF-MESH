"""
Tests for core/evolution/attestation.py

6 tests — todos con mocks, sin red ni chain real.
Patch target: core.evolution.attestation.DOFChainAdapter
"""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from dataclasses import asdict
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.evolution.attestation import (
    GenerationAttestation,
    attest_generation,
    attest_multichain,
    compute_gene_pool_hash,
)


def _make_attestation(**kwargs) -> GenerationAttestation:
    defaults = dict(
        generation=1,
        asr_before=50.0,
        asr_after=40.0,
        improvement_pp=10.0,
        genes_mutated=3,
        genes_crossed=2,
        survivors=7,
        gene_pool_hash="abc123",
        timestamp="2026-04-13T00:00:00+00:00",
        session="test",
    )
    defaults.update(kwargs)
    return GenerationAttestation(**defaults)


class TestGenerationAttestationDataclass(unittest.TestCase):

    def test_dataclass_serializable(self):
        """GenerationAttestation es serializable a dict y JSON."""
        att = _make_attestation()
        d = asdict(att)
        self.assertEqual(d["generation"], 1)
        self.assertEqual(d["improvement_pp"], 10.0)
        # Debe poder serializarse a JSON sin error
        json_str = json.dumps(d)
        self.assertIn('"generation": 1', json_str)


class TestComputeGenePoolHash(unittest.TestCase):

    def test_compute_gene_pool_hash_nonexistent_returns_unknown(self):
        """Ruta inexistente devuelve 'unknown'."""
        result = compute_gene_pool_hash("/nonexistent/path/gene_pool.jsonl")
        self.assertEqual(result, "unknown")

    def test_compute_gene_pool_hash_real_file(self):
        """Archivo real devuelve SHA-256 de 64 chars hex."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as f:
            f.write(b'{"id": "g001", "regex": "test", "category": "OVERRIDE"}\n')
            tmp_path = f.name
        try:
            result = compute_gene_pool_hash(tmp_path)
            self.assertEqual(len(result), 64)
            int(result, 16)  # debe ser hex válido
        finally:
            os.unlink(tmp_path)


class TestAttestGeneration(unittest.TestCase):

    def _mock_adapter(self, status="dry_run", tx_hash="0xabc123"):
        adapter = MagicMock()
        adapter.publish_attestation.return_value = {
            "status": status,
            "tx_hash": tx_hash,
        }
        return adapter

    def test_attest_generation_success(self):
        """attest_generation retorna success=True con adapter mock."""
        att = _make_attestation()
        mock_adapter = self._mock_adapter(status="dry_run", tx_hash="0xdeadbeef")

        with patch("core.evolution.attestation.DOFChainAdapter") as MockClass:
            MockClass.from_chain_name.return_value = mock_adapter
            result = attest_generation(att, chain="avalanche")

        self.assertTrue(result["success"])
        self.assertEqual(result["tx_hash"], "0xdeadbeef")
        self.assertEqual(result["chain"], "avalanche")
        self.assertEqual(result["generation"], 1)
        self.assertIsNone(result["error"])

        # Verificar que se llamó con los parámetros correctos
        MockClass.from_chain_name.assert_called_once_with("avalanche", dry_run=True)
        mock_adapter.publish_attestation.assert_called_once()
        call_kwargs = mock_adapter.publish_attestation.call_args
        self.assertEqual(call_kwargs.kwargs["agent_id"], 9999)
        self.assertTrue(call_kwargs.kwargs["proof_hash"].startswith("0x"))

    def test_attest_generation_handles_error(self):
        """Si publish_attestation lanza excepción → success=False, error en dict."""
        att = _make_attestation()

        with patch("core.evolution.attestation.DOFChainAdapter") as MockClass:
            MockClass.from_chain_name.side_effect = RuntimeError("chain unavailable")
            result = attest_generation(att, chain="avalanche")

        self.assertFalse(result["success"])
        self.assertIsNone(result["tx_hash"])
        self.assertIn("chain unavailable", result["error"])

    def test_attest_generation_adapter_none(self):
        """Si DOFChainAdapter es None → success=False con mensaje claro."""
        att = _make_attestation()
        with patch("core.evolution.attestation.DOFChainAdapter", None):
            result = attest_generation(att, chain="avalanche")

        self.assertFalse(result["success"])
        self.assertIn("DOFChainAdapter no disponible", result["error"])


class TestAttestMultichain(unittest.TestCase):

    def test_attest_multichain_returns_list(self):
        """attest_multichain(['avalanche']) → lista de 1 resultado."""
        att = _make_attestation()
        mock_adapter = MagicMock()
        mock_adapter.publish_attestation.return_value = {
            "status": "dry_run",
            "tx_hash": "0x111",
        }

        with patch("core.evolution.attestation.DOFChainAdapter") as MockClass:
            MockClass.from_chain_name.return_value = mock_adapter
            results = attest_multichain(att, chains=["avalanche"])

        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["success"])

    def test_attest_multichain_default_chain(self):
        """Sin chains arg, usa ['avalanche'] por defecto."""
        att = _make_attestation()
        mock_adapter = MagicMock()
        mock_adapter.publish_attestation.return_value = {
            "status": "dry_run", "tx_hash": "0x222",
        }

        with patch("core.evolution.attestation.DOFChainAdapter") as MockClass:
            MockClass.from_chain_name.return_value = mock_adapter
            results = attest_multichain(att)

        self.assertEqual(len(results), 1)
        MockClass.from_chain_name.assert_called_with("avalanche", dry_run=True)


if __name__ == "__main__":
    unittest.main()
