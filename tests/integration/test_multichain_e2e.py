import os
import time
import hashlib
import unittest
from web3.exceptions import Web3RPCError, ContractLogicError
from core.chain_adapter import DOFChainAdapter


class TestMultichainE2E(unittest.TestCase):
    """End-to-end testing targeting both Avalanche Mainnet and Conflux Testnet."""

    def publish_and_verify(self, chain_name: str):
        """Helper para probar flujo E2E completo en una chain."""
        adapter = DOFChainAdapter.from_chain_name(chain_name)

        if not adapter.config.contract_address:
            self.skipTest(f"No contract address configured for {chain_name}.")

        try:
            adapter.is_ready()
        except Exception as e:
            self.skipTest(f"Chain {chain_name} no disponible: {e}")

        try:
            adapter._init_web3()
            if not adapter._web3.is_connected():
                self.skipTest(f"Chain {chain_name} RPC falió conexión.")
        except Exception as e:
            self.skipTest(f"Chain {chain_name} setup err: {e}")

        data = f"dof-e2e-{chain_name}-{time.time()}".encode()
        proof_hash = "0x" + hashlib.sha256(data).hexdigest()

        try:
            try:
                tx_result = adapter.publish_attestation(
                    proof_hash=proof_hash,
                    agent_id=101,
                    metadata="dof-e2e-multichain-suite"
                )
                self.assertEqual(tx_result["status"], "confirmed")
                self.assertIn("tx_hash", tx_result)
            except (Web3RPCError, ValueError) as funds_err:
                self.skipTest(f"Saltando publish en {chain_name} por fondos/env err: {funds_err}")

            is_valid = adapter.verify_proof(proof_hash)
            self.assertTrue(is_valid)

        except ContractLogicError as cle:
            self.fail(f"Falla ABI/Revert on {chain_name}: {cle}")

    def test_e2e_avalanche_mainnet(self):
        """Integración real en Avalanche C-Chain."""
        self.publish_and_verify("avalanche")

    def test_e2e_conflux_testnet(self):
        """Integración real en Conflux eSpace Testnet."""
        self.publish_and_verify("conflux_testnet")


if __name__ == "__main__":
    unittest.main()
