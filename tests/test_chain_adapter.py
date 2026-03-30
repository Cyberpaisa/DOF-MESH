# tests/test_chain_adapter.py
# Tests unitarios para DOFChainAdapter — NO requieren conexión real
# Usan dry_run=True para mockear todas las llamadas on-chain

import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from core.chain_adapter import DOFChainAdapter, ChainConfig


class TestChainsConfig(unittest.TestCase):
    """Valida la estructura de chains_config.json."""

    def test_config_loads(self):
        config = DOFChainAdapter.load_chains_config()
        self.assertIn("chains", config)
        self.assertIn("version", config)

    def test_required_chains_present(self):
        config = DOFChainAdapter.load_chains_config()
        chains = config["chains"]
        required = [
            "avalanche", "conflux_espace", "conflux_testnet",
            "ethereum", "base", "arbitrum", "polygon", "celo"
        ]
        for chain in required:
            self.assertIn(chain, chains, f"Chain '{chain}' faltante en chains_config.json")

    def test_avalanche_has_contract(self):
        config = DOFChainAdapter.load_chains_config()
        avax = config["chains"]["avalanche"]
        self.assertIsNotNone(avax["contract_address"])
        self.assertTrue(avax["contract_address"].startswith("0x"))
        self.assertEqual(avax["status"], "mainnet")

    def test_all_chains_have_required_fields(self):
        config = DOFChainAdapter.load_chains_config()
        required_fields = ["chain_id", "name", "rpc_url", "status", "native_token"]
        for key, data in config["chains"].items():
            for field in required_fields:
                self.assertIn(field, data, f"Campo '{field}' faltante en chain '{key}'")

    def test_chain_ids_unique(self):
        config = DOFChainAdapter.load_chains_config()
        ids = [data["chain_id"] for data in config["chains"].values()]
        self.assertEqual(len(ids), len(set(ids)), "chain_ids duplicados detectados")


class TestDOFChainAdapterInit(unittest.TestCase):
    """Tests de inicialización del adapter."""

    def test_from_chain_name_avalanche(self):
        adapter = DOFChainAdapter.from_chain_name("avalanche", dry_run=True)
        self.assertEqual(adapter.config.chain_id, 43114)
        self.assertEqual(adapter.config.status, "mainnet")

    def test_from_chain_name_conflux_testnet(self):
        adapter = DOFChainAdapter.from_chain_name("conflux_testnet", dry_run=True)
        self.assertEqual(adapter.config.chain_id, 71)
        self.assertEqual(adapter.config.gas_multiplier, 2.0)

    def test_from_chain_id_base(self):
        adapter = DOFChainAdapter.from_chain_id(8453, dry_run=True)
        self.assertEqual(adapter.config.chain_key, "base")

    def test_from_chain_id_arbitrum(self):
        adapter = DOFChainAdapter.from_chain_id(42161, dry_run=True)
        self.assertEqual(adapter.config.chain_key, "arbitrum")

    def test_invalid_chain_raises(self):
        with self.assertRaisesRegex(ValueError, "no encontrada"):
            DOFChainAdapter.from_chain_name("nonexistent_chain")

    def test_list_supported_chains(self):
        chains = DOFChainAdapter.list_supported_chains()
        self.assertGreaterEqual(len(chains), 8)
        names = [c["chain_key"] for c in chains]
        self.assertIn("avalanche", names)
        self.assertIn("conflux_testnet", names)
        self.assertIn("base", names)


class TestDOFChainAdapterOperations(unittest.TestCase):
    """Tests de publish_attestation y verify_proof en dry_run."""

    def test_publish_attestation_dry_run(self):
        adapter = DOFChainAdapter.from_chain_name("avalanche", dry_run=True)
        result = adapter.publish_attestation(
            proof_hash="0x" + "a" * 64,
            agent_id=1687,
            metadata="test_metadata"
        )
        self.assertEqual(result["status"], "dry_run")
        self.assertEqual(result["chain_id"], 43114)
        self.assertTrue(result["tx_hash"].startswith("0x"))

    def test_publish_attestation_no_contract_skips(self):
        adapter = DOFChainAdapter.from_chain_name("conflux_testnet", dry_run=True)
        result = adapter.publish_attestation(
            proof_hash="0x" + "b" * 64,
            agent_id=1686,
            metadata=""
        )
        self.assertIn(result["status"], ("dry_run", "skipped"))

    def test_verify_proof_dry_run(self):
        adapter = DOFChainAdapter.from_chain_name("avalanche", dry_run=True)
        result = adapter.verify_proof("0x" + "c" * 64)
        self.assertTrue(result)

    def test_get_chain_info(self):
        adapter = DOFChainAdapter.from_chain_name("celo", dry_run=True)
        info = adapter.get_chain_info()
        self.assertEqual(info["chain_id"], 42220)
        self.assertEqual(info["native_token"], "CELO")

    def test_all_chains_instantiate(self):
        """Verifica que todas las chains en config se pueden instanciar."""
        config = DOFChainAdapter.load_chains_config()
        for chain_key in config["chains"]:
            adapter = DOFChainAdapter.from_chain_name(chain_key, dry_run=True)
            self.assertGreater(adapter.config.chain_id, 0)


class TestDOFChainAdapterIsReady(unittest.TestCase):
    """Tests del método is_ready()."""

    def test_avalanche_is_ready(self):
        adapter = DOFChainAdapter.from_chain_name("avalanche", dry_run=True)
        self.assertTrue(adapter.is_ready())

    def test_conflux_testnet_not_ready_without_contract(self):
        adapter = DOFChainAdapter.from_chain_name("conflux_testnet", dry_run=True)
        if adapter.config.contract_address is None:
            self.assertFalse(adapter.is_ready())


if __name__ == "__main__":
    unittest.main()
