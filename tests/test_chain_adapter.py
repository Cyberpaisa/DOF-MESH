# tests/test_chain_adapter.py
# Tests unitarios para DOFChainAdapter — NO requieren conexión real
# Usan dry_run=True para mockear todas las llamadas on-chain

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from core.chain_adapter import DOFChainAdapter, ChainConfig


class TestChainsConfig:
    """Valida la estructura de chains_config.json."""

    def test_config_loads(self):
        config = DOFChainAdapter.load_chains_config()
        assert "chains" in config
        assert "version" in config

    def test_required_chains_present(self):
        config = DOFChainAdapter.load_chains_config()
        chains = config["chains"]
        required = [
            "avalanche", "conflux_espace", "conflux_testnet",
            "ethereum", "base", "arbitrum", "polygon", "celo"
        ]
        for chain in required:
            assert chain in chains, f"Chain '{chain}' faltante en chains_config.json"

    def test_avalanche_has_contract(self):
        config = DOFChainAdapter.load_chains_config()
        avax = config["chains"]["avalanche"]
        assert avax["contract_address"] is not None
        assert avax["contract_address"].startswith("0x")
        assert avax["status"] == "mainnet"

    def test_all_chains_have_required_fields(self):
        config = DOFChainAdapter.load_chains_config()
        required_fields = ["chain_id", "name", "rpc_url", "status", "native_token"]
        for key, data in config["chains"].items():
            for field in required_fields:
                assert field in data, f"Campo '{field}' faltante en chain '{key}'"

    def test_chain_ids_unique(self):
        config = DOFChainAdapter.load_chains_config()
        ids = [data["chain_id"] for data in config["chains"].values()]
        assert len(ids) == len(set(ids)), "chain_ids duplicados detectados"


class TestDOFChainAdapterInit:
    """Tests de inicialización del adapter."""

    def test_from_chain_name_avalanche(self):
        adapter = DOFChainAdapter.from_chain_name("avalanche", dry_run=True)
        assert adapter.config.chain_id == 43114
        assert adapter.config.status == "mainnet"

    def test_from_chain_name_conflux_testnet(self):
        adapter = DOFChainAdapter.from_chain_name("conflux_testnet", dry_run=True)
        assert adapter.config.chain_id == 71
        assert adapter.config.gas_multiplier == 2.0

    def test_from_chain_id_base(self):
        adapter = DOFChainAdapter.from_chain_id(8453, dry_run=True)
        assert adapter.config.chain_key == "base"

    def test_from_chain_id_arbitrum(self):
        adapter = DOFChainAdapter.from_chain_id(42161, dry_run=True)
        assert adapter.config.chain_key == "arbitrum"

    def test_invalid_chain_raises(self):
        with pytest.raises(ValueError, match="no encontrada"):
            DOFChainAdapter.from_chain_name("nonexistent_chain")

    def test_list_supported_chains(self):
        chains = DOFChainAdapter.list_supported_chains()
        assert len(chains) >= 8
        names = [c["chain_key"] for c in chains]
        assert "avalanche" in names
        assert "conflux_testnet" in names
        assert "base" in names


class TestDOFChainAdapterOperations:
    """Tests de publish_attestation y verify_proof en dry_run."""

    def test_publish_attestation_dry_run(self):
        adapter = DOFChainAdapter.from_chain_name("avalanche", dry_run=True)
        result = adapter.publish_attestation(
            proof_hash="0x" + "a" * 64,
            agent_id=1687,
            metadata="test_metadata"
        )
        assert result["status"] == "dry_run"
        assert result["chain_id"] == 43114
        assert result["tx_hash"].startswith("0x")

    def test_publish_attestation_no_contract_skips(self):
        adapter = DOFChainAdapter.from_chain_name("conflux_testnet", dry_run=True)
        # conflux_testnet no tiene contract_address todavía
        result = adapter.publish_attestation(
            proof_hash="0x" + "b" * 64,
            agent_id=1686,
            metadata=""
        )
        # Si no tiene contrato, retorna skipped
        assert result["status"] in ("dry_run", "skipped")

    def test_verify_proof_dry_run(self):
        adapter = DOFChainAdapter.from_chain_name("avalanche", dry_run=True)
        result = adapter.verify_proof("0x" + "c" * 64)
        assert result is True

    def test_get_chain_info(self):
        adapter = DOFChainAdapter.from_chain_name("celo", dry_run=True)
        info = adapter.get_chain_info()
        assert info["chain_id"] == 42220
        assert info["native_token"] == "CELO"
        assert "LatAm" in info["notes"] or info["notes"] == ""

    def test_all_chains_instantiate(self):
        """Verifica que todas las chains en config se pueden instanciar."""
        config = DOFChainAdapter.load_chains_config()
        for chain_key in config["chains"]:
            adapter = DOFChainAdapter.from_chain_name(chain_key, dry_run=True)
            assert adapter.config.chain_id > 0


class TestDOFChainAdapterIsReady:
    """Tests del método is_ready()."""

    def test_avalanche_is_ready(self):
        adapter = DOFChainAdapter.from_chain_name("avalanche", dry_run=True)
        assert adapter.is_ready() is True

    def test_conflux_testnet_not_ready_without_contract(self):
        adapter = DOFChainAdapter.from_chain_name("conflux_testnet", dry_run=True)
        # Solo es ready si tiene contract_address
        if adapter.config.contract_address is None:
            assert adapter.is_ready() is False
