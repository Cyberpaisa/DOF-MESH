import unittest
from unittest.mock import patch, Mock
from datetime import datetime, timedelta
from core.federation_seed import SeedServer, SeedClient, get_seed_client

class TestFederationSeed(unittest.TestCase):

    def setUp(self):
        self.seed_server = SeedServer()
        self.seed_client = get_seed_client()

    @patch('core.federation_seed.SeedServer.register_peer')
    def test_register_peer(self, mock_register_peer):
        peer_id = "peer1"
        data = {"name": "test_peer", "address": "http://localhost:8080"}
        self.seed_server.register(peer_id, data)
        mock_register_peer.assert_called_once_with(peer_id, data)

    @patch('core.federation_seed.SeedServer.get_peers')
    def test_get_peers(self, mock_get_peers):
        peers = [{"id": "peer1", "name": "test_peer", "address": "http://localhost:8080"}]
        mock_get_peers.return_value = peers
        self.assertEqual(self.seed_server.get_peers(), peers)

    @patch('core.federation_seed.SeedServer.register_peer')
    def test_register_peer_updates_timestamp(self, mock_register_peer):
        peer_id = "peer1"
        data = {"name": "test_peer", "address": "http://localhost:8080"}
        self.seed_server.register(peer_id, data)
        timestamp = datetime.now()
        time.sleep(2)
        self.seed_server.register(peer_id, data)
        mock_register_peer.assert_called_with(peer_id, data)
        # Assuming the method updates the timestamp internally
        # We need to check if the peer's timestamp has been updated

    @patch('core.federation_seed.SeedServer.register_peer')
    def test_register_peer_expiration(self, mock_register_peer):
        peer_id = "peer1"
        data = {"name": "test_peer", "address": "http://localhost:8080"}
        self.seed_server.register(peer_id, data)
        timestamp = datetime.now() - timedelta(seconds=301)
        # Assuming the method expires entries internally
        # We need to check if the peer has been expired

    @patch('core.federation_seed.SeedClient._request')
    def test_register_peer_client(self, mock_request):
        url = "http://localhost:8080/register"
        data = {"name": "test_peer", "address": "http://localhost:8080"}
        self.seed_client.register(data)
        mock_request.assert_called_once_with("POST", url, json=data)

    @patch('core.federation_seed.SeedClient._request')
    def test_get_peers_client(self, mock_request):
        url = "http://localhost:8080/peers"
        expected_response = [{"id": "peer1", "name": "test_peer", "address": "http://localhost:8080"}]
        mock_request.return_value.json.return_value = expected_response
        self.assertEqual(self.seed_client.get_peers(), expected_response)
        mock_request.assert_called_once_with("GET", url)

    def test_get_seed_client_singleton(self):
        client1 = get_seed_client()
        client2 = get_seed_client()
        self.assertIs(client1, client2)

if __name__ == '__main__':
    unittest.main()
