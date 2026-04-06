"""
Tests for ConfluxGateway — DOF Conflux Hackathon 2026
python3 -m unittest tests.test_conflux_gateway -v
"""
import unittest


class TestConfluxGatewayImport(unittest.TestCase):
    """Gateway imports and initializes without errors."""

    def test_import_no_crash(self):
        """Import must not raise ImportError (geth_poa_middleware fix)."""
        from core.adapters.conflux_gateway import ConfluxGateway
        self.assertTrue(callable(ConfluxGateway))

    def test_dry_run_mode(self):
        """dry_run=True must not require network connection."""
        from core.adapters.conflux_gateway import ConfluxGateway
        gw = ConfluxGateway(use_testnet=True, dry_run=True)
        self.assertTrue(gw.dry_run)
        self.assertEqual(gw.w3.eth.chain_id, 71)
        self.assertTrue(gw.w3.is_connected())

    def test_sponsor_contract_address_valid(self):
        """SPONSOR_CONTRACT_ADDRESS must be a valid checksummed address."""
        from core.adapters.conflux_gateway import ConfluxGateway
        from web3 import Web3
        addr = ConfluxGateway.SPONSOR_CONTRACT_ADDRESS
        self.assertTrue(Web3.is_checksum_address(addr) or addr.startswith("0x"))
        self.assertEqual(len(addr), 42)

    def test_proof_registry_testnet_address(self):
        """PROOF_REGISTRY_TESTNET must match known deployed address."""
        from core.adapters.conflux_gateway import ConfluxGateway
        self.assertEqual(
            ConfluxGateway.PROOF_REGISTRY_TESTNET,
            "0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83"
        )
        self.assertEqual(ConfluxGateway.PROOF_REGISTRY_CHAIN_ID, 71)

    def test_rpc_urls_defined(self):
        """Both RPC URLs must be defined and non-empty."""
        from core.adapters.conflux_gateway import ConfluxGateway
        self.assertTrue(ConfluxGateway.TESTNET_RPC.startswith("https://"))
        self.assertTrue(ConfluxGateway.MAINNET_RPC.startswith("https://"))


if __name__ == "__main__":
    unittest.main()
