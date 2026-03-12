import os
import time
import hashlib
import pytest
from web3.exceptions import Web3RPCError, ContractLogicError
from core.chain_adapter import DOFChainAdapter

@pytest.mark.integration
class TestMultichainE2E:
    """End-to-end testing targeting both Avalanche Mainnet and Conflux Testnet."""

    def publish_and_verify(self, chain_name: str):
        """Helper para probar flujo E2E completo en una chain."""
        adapter = DOFChainAdapter.from_chain_name(chain_name)

        if not adapter.config.contract_address:
            pytest.skip(f"No contract address configured for {chain_name}.")

        try:
            adapter.is_ready()  # Check basic readiness
        except Exception as e:
            pytest.skip(f"Chain {chain_name} no disponible: {e}")

        # Intentar inicializar Web3 para verificar connectividad final
        try:
            adapter._init_web3()
            if not adapter._web3.is_connected():
                pytest.skip(f"Chain {chain_name} RPC falió conexión.")
        except Exception as e:
            pytest.skip(f"Chain {chain_name} setup err: {e}")

        # Generar data de atestación fresca
        data = f"dof-e2e-{chain_name}-{time.time()}".encode()
        proof_hash = "0x" + hashlib.sha256(data).hexdigest()

        try:
            # 1. Publish (puede fallar por fondos si la config no los provee, no falla el test si no tiene fondos)
            try:
                tx_result = adapter.publish_attestation(
                    proof_hash=proof_hash,
                    agent_id=101,
                    metadata="dof-e2e-multichain-suite"
                )
                assert tx_result["status"] == "confirmed"
                assert "tx_hash" in tx_result
            except (Web3RPCError, ValueError) as funds_err:
                pytest.skip(f"Saltando publish en {chain_name} por fondos/env err: {funds_err}")

            # 2. Verify
            is_valid = adapter.verify_proof(proof_hash)
            assert is_valid is True

        except ContractLogicError as cle:
            pytest.fail(f"Falla ABI/Revert on {chain_name}: {cle}")


    def test_e2e_avalanche_mainnet(self):
        """Integración real en Avalanche C-Chain."""
        self.publish_and_verify("avalanche")

    def test_e2e_conflux_testnet(self):
        """Integración real en Conflux eSpace Testnet."""
        self.publish_and_verify("conflux_testnet")

