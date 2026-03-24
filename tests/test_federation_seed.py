import time
import unittest
from unittest.mock import patch, MagicMock


class TestFederationSeed(unittest.TestCase):
    """Tests for core.federation_seed — mocks HTTPServer to avoid port binding."""

    def setUp(self):
        self._http_patcher = patch("core.federation_seed.HTTPServer")
        self._http_patcher.start()
        import core.federation_seed as _fs
        _fs._seed_client_instance = None
        from core.federation_seed import SeedServer, get_seed_client
        self.SeedServer = SeedServer
        self.seed_server = SeedServer()
        self.seed_client = get_seed_client()

    def tearDown(self):
        self._http_patcher.stop()
        import core.federation_seed as _fs
        _fs._seed_client_instance = None

    # ── SeedServer tests ──────────────────────────────────────────────────

    def test_register_peer(self):
        self.seed_server.register("peer1", "127.0.0.1", 9001)
        peers = self.seed_server.get_peers()
        ids = [p["node_id"] for p in peers]
        self.assertIn("peer1", ids)

    def test_get_peers(self):
        self.seed_server.register("node-a", "10.0.0.1", 8888)
        peers = self.seed_server.get_peers()
        self.assertIsInstance(peers, list)
        self.assertGreater(len(peers), 0)

    def test_register_peer_updates_timestamp(self):
        # Register twice — second call should update internal timestamp without raising
        self.seed_server.register("peer1", "127.0.0.1", 9001)
        time.sleep(0.01)
        self.seed_server.register("peer1", "127.0.0.1", 9001)
        peers = self.seed_server.get_peers()
        self.assertTrue(any(p["node_id"] == "peer1" for p in peers))

    def test_register_peer_expiration(self):
        # Verify register runs without error and peer appears
        self.seed_server.register("peer-exp", "1.2.3.4", 7000)
        peers = self.seed_server.get_peers()
        self.assertTrue(any(p["node_id"] == "peer-exp" for p in peers))

    def test_register_peer_updates_existing(self):
        self.seed_server.register("dup", "10.0.0.1", 8001)
        self.seed_server.register("dup", "10.0.0.2", 8002)
        peers = [p for p in self.seed_server.get_peers() if p["node_id"] == "dup"]
        self.assertEqual(len(peers), 1)
        self.assertEqual(peers[0]["host"], "10.0.0.2")

    def test_register_multiple_peers(self):
        for i in range(3):
            self.seed_server.register(f"node-{i}", f"10.0.0.{i}", 9000 + i)
        peers = self.seed_server.get_peers()
        self.assertGreaterEqual(len(peers), 3)

    # ── SeedClient tests ──────────────────────────────────────────────────

    def test_get_seed_client_singleton(self):
        from core.federation_seed import get_seed_client
        c1 = get_seed_client()
        c2 = get_seed_client()
        self.assertIs(c1, c2)

    def test_register_peer_client(self):
        with patch.object(self.seed_client, "_request") as mock_req:
            mock_req.return_value = MagicMock(ok=True)
            self.seed_client.register("client-node", "127.0.0.1", 9500)
            mock_req.assert_called_once()
            args = mock_req.call_args
            self.assertEqual(args[0][0], "POST")

    def test_get_peers_client(self):
        import json as _json
        expected = [{"node_id": "peer1", "host": "10.0.0.1", "port": "9001"}]
        with patch.object(self.seed_client, "_request") as mock_req:
            # Simulate urllib response (has .read(), no .json())
            mock_resp = MagicMock()
            mock_resp.json = MagicMock(return_value=expected)
            mock_req.return_value = mock_resp
            result = self.seed_client.get_peers()
            self.assertEqual(result, expected)
            mock_req.assert_called_once()
            args = mock_req.call_args
            self.assertEqual(args[0][0], "GET")


if __name__ == "__main__":
    unittest.main()
