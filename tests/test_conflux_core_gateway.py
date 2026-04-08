"""Tests for core/adapters/conflux_core_gateway.py"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestConfluxCoreGateway(unittest.TestCase):

    def setUp(self):
        from core.adapters.conflux_core_gateway import ConfluxCoreGateway
        self.gw = ConfluxCoreGateway(use_testnet=True, dry_run=True)

    def test_import_and_instantiate(self):
        """ConfluxCoreGateway importa y se instancia sin errores."""
        from core.adapters.conflux_core_gateway import ConfluxCoreGateway
        gw = ConfluxCoreGateway(use_testnet=True, dry_run=True)
        self.assertIsNotNone(gw)

    def test_rpc_url_correct(self):
        """RPC URL de testnet es correcta."""
        self.assertEqual(self.gw.rpc_url, "https://test.confluxrpc.com")
        gw_main = __import__(
            "core.adapters.conflux_core_gateway",
            fromlist=["ConfluxCoreGateway"]
        ).ConfluxCoreGateway(use_testnet=False, dry_run=True)
        self.assertEqual(gw_main.rpc_url, "https://main.confluxrpc.com")

    def test_epoch_number_dry_run_returns_int(self):
        """get_epoch_number() en dry_run retorna int."""
        epoch = self.gw.get_epoch_number()
        self.assertIsInstance(epoch, int)
        self.assertGreater(epoch, 0)

    def test_describe_contains_required_fields(self):
        """describe() retorna dict con campos requeridos."""
        info = self.gw.describe()
        self.assertIn("type", info)
        self.assertIn("rpc_url", info)
        self.assertIn("rpc_protocol", info)
        self.assertEqual(info["type"], "conflux_core_space")
        self.assertEqual(info["rpc_protocol"], "cfx_*")

    def test_dry_run_no_network_calls(self):
        """dry_run=True nunca hace llamadas HTTP reales."""
        import unittest.mock as mock
        with mock.patch("requests.post") as mock_post:
            self.gw.get_epoch_number()
            self.gw.get_gas_price()
            self.gw.get_status()
            mock_post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
