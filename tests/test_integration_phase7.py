import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import json
import time
from core.mesh_firewall import MeshFirewall
from core.mesh_federation import MeshFederation
from core.mesh_stun import MeshSTUN
from core.mesh_tunnel import MeshTunnel

class TestIntegrationPhase7(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.firewall = MeshFirewall()
        self.federation = MeshFederation()
        self.stun = MeshSTUN()
        self.tunnel = MeshTunnel()
        self.federation.firewall = self.firewall
        self.federation.stun = self.stun
        self.federation.tunnel = self.tunnel
        
    def tearDown(self):
        self.loop.close()
        asyncio.set_event_loop(None)
    
    # Firewall blocking tests
    def test_01_firewall_blocks_ip_before_federation(self):
        self.firewall.block_ip('192.168.1.100')
        result = self.firewall.check_ip('192.168.1.100')
        self.assertFalse(result['allowed'])
        
    def test_02_blocked_ip_cannot_send_federation_message(self):
        self.firewall.block_ip('10.0.0.5')
        msg = {'type': 'federation', 'src': '10.0.0.5', 'data': 'test'}
        processed = self.federation.process_incoming(msg, '10.0.0.5')
        self.assertIsNone(processed)
        
    def test_03_firewall_logs_blocked_attempt(self):
        self.firewall.block_ip('172.16.0.1')
        self.federation.process_incoming({'type': 'ping'}, '172.16.0.1')
        logs = self.firewall.get_logs()
        self.assertGreater(len(logs), 0)
        
    def test_04_firewall_allows_non_blocked_ip(self):
        self.firewall.allow_ip('192.168.2.1')
        result = self.firewall.check_ip('192.168.2.1')
        self.assertTrue(result['allowed'])
    
    # Valid message passing tests
    @patch('core.mesh_federation.MeshFederation.validate_message')
    def test_05_valid_message_passes_firewall(self, mock_validate):
        mock_validate.return_value = True
        msg = {'type': 'data', 'src': 'node1', 'payload': 'valid'}
        result = self.federation.process_incoming(msg, '192.168.1.1')
        self.assertIsNotNone(result)
        
    def test_06_message_reaches_local_inbox(self):
        self.federation.inbox = []
        msg = {'type': 'deliver', 'to': 'local', 'data': 'test123'}
        self.federation.deliver_local(msg)
        self.assertEqual(len(self.federation.inbox), 1)
        
    def test_07_federation_validates_signature(self):
        with patch('core.mesh_federation.MeshFederation.verify_signature') as mock_verify:
            mock_verify.return_value = True
            msg = {'sig': 'abc123', 'data': 'test'}
            valid = self.federation.validate_message(msg)
            self.assertTrue(valid)
            
    # Rate limiting tests
    def test_08_rate_limit_tracks_requests(self):
        self.firewall.rate_limits = {}
        for _ in range(5):
            self.firewall.check_rate_limit('192.168.3.1')
        self.assertEqual(self.firewall.rate_limits['192.168.3.1']['count'], 5)
        
    def test_09_rate_limit_exceeded_blocks_ip(self):
        self.firewall.rate_limit_threshold = 3
        self.firewall.rate_limit_window = 60
        ip = '10.1.1.1'
        for _ in range(4):
            self.firewall.check_rate_limit(ip)
        result = self.firewall.check_ip(ip)
        self.assertFalse(result['allowed'])
        
    def test_10_rate_limit_resets_after_window(self):
        self.firewall.rate_limit_window = 1
        ip = '10.2.2.2'
        self.firewall.check_rate_limit(ip)
        time.sleep(1.1)
        self.firewall.cleanup_rate_limits()
        self.assertNotIn(ip, self.firewall.rate_limits)
        
    # Whitelist tests
    def test_11_whitelisted_ip_bypasses_firewall(self):
        self.firewall.whitelist_ip('203.0.113.5')
        self.firewall.block_ip('203.0.113.5')  # Should still be allowed
        result = self.firewall.check_ip('203.0.113.5')
        self.assertTrue(result['allowed'])
        
    def test_12_whitelisted_ip_bypasses_rate_limit(self):
        self.firewall.whitelist_ip('198.51.100.1')
        self.firewall.rate_limit_threshold = 1
        for _ in range(5):
            allowed = self.firewall.check_rate_limit('198.51.100.1')
            self.assertTrue(allowed)
    
    def test_13_whitelist_overrides_block(self):
        self.firewall.whitelist_ip('192.0.2.1')
        self.firewall.block_ip('192.0.2.1')
        result = self.firewall.check_ip('192.0.2.1')
        self.assertTrue(result['allowed'])
        
    # STUN integration tests
    @patch('aiohttp.ClientSession.get')
    def test_14_stun_fetches_public_ip(self, mock_get):
        mock_resp = AsyncMock()
        mock_resp.json.return_value = {'ip': '203.0.113.10', 'port': 3478}
        mock_get.return_value.__aenter__.return_value = mock_resp
        
        async def test():
            return await self.stun.get_public_endpoint()
        result = self.loop.run_until_complete(test())
        self.assertEqual(result['ip'], '203.0.113.10')
        
    def test_15_federation_uses_stun_public_ip(self):
        self.stun.public_ip = '203.0.113.20'
        self.stun.public_port = 3344
        self.federation.stun = self.stun
        endpoint = self.federation.get_public_endpoint()
        self.assertEqual(endpoint['ip'], '203.0.113.20')
        
    @patch('core.mesh_stun.MeshSTUN.get_public_endpoint')
    def test_16_stun_error_handled(self, mock_stun):
        mock_stun.side_effect = Exception('STUN failed')
        self.federation.stun = self.stun
        endpoint = self.federation.get_public_endpoint()
        self.assertIsNone(endpoint)
        
    # Tunnel integration tests
    def test_17_tunnel_encrypt_decrypt(self):
        data = b'secret message'
        encrypted = self.tunnel.encrypt(data, 'testkey')
        decrypted = self.tunnel.decrypt(encrypted, 'testkey')
        self.assertEqual(data, decrypted)
        
    def test_18_tunnel_wrong_key_fails(self):
        data = b'test'
        encrypted = self.tunnel.encrypt(data, 'key1')
        with self.assertRaises(Exception):
            self.tunnel.decrypt(encrypted, 'wrongkey')
            
    def test_19_federation_delivers_through_tunnel(self):
        self.tunnel.encrypt = MagicMock(return_value=b'encrypted')
        self.federation.tunnel = self.tunnel
        result = self.federation.send_through_tunnel({'msg': 'hello'}, 'dest')
        self.assertTrue(result['encrypted'])
        
    def test_20_tunnel_message_roundtrip(self):
        original = {'type': 'data', 'payload': 'roundtrip test'}
        encrypted = self.tunnel.encrypt(json.dumps(original).encode(), 'shared_key')
        decrypted = json.loads(self.tunnel.decrypt(encrypted, 'shared_key').decode())
        self.assertEqual(original['payload'], decrypted['payload'])
        
    # Integration scenarios
    def test_21_full_path_valid_message(self):
        self.firewall.allow_ip('192.168.5.1')
        with patch('core.mesh_federation.MeshFederation.validate_message') as mock_val:
            mock_val.return_value = True
            msg = {'type': 'data', 'id': 'msg1'}
            result = self.federation.process_incoming(msg, '192.168.5.1')
            self.assertIsNotNone(result)
            
    def test_22_rate_limit_auto_block_integration(self):
        ip = '192.168.6.1'
        self.firewall.rate_limit_threshold = 2
        for _ in range(3):
            self.firewall.check_rate_limit(ip)
        result = self.firewall.check_ip(ip)
        self.assertFalse(result['allowed'])
        
    def test_23_whitelist_full_bypass_integration(self):
        self.firewall.whitelist_ip('192.168.7.1')
        self.firewall.block_ip('192.168.7.1')
        self.firewall.rate_limit_threshold = 0
        result = self.firewall.check_ip('192.168.7.1')
        self.assertTrue(result['allowed'])
        
    @patch('core.mesh_stun.MeshSTUN.get_public_endpoint')
    def test_24_stun_federation_integration(self, mock_stun):
        mock_stun.return_value = {'ip': '203.0.113.30', 'port': 4567}
        self.federation.stun = self.stun
        endpoint = self.federation.get_public_endpoint()
        self.assertEqual(endpoint['ip'], '203.0.113.30')
        self.federation.public_ip = endpoint['ip']
        self.assertEqual(self.federation.public_ip, '203.0.113.30')
        
    def test_25_tunnel_federation_delivery_integration(self):
        with patch('core.mesh_tunnel.MeshTunnel.encrypt') as mock_encrypt:
            mock_encrypt.return_value = b'enc_payload'
            self.federation.tunnel = self.tunnel
            delivered = self.federation.send_through_tunnel(
                {'data': 'test'}, 'target_node'
            )
            self.assertTrue(mock_encrypt.called)
            
    def test_26_firewall_logs_integration(self):
        self.firewall.block_ip('192.168.8.1')
        self.federation.process_incoming({'type': 'ping'}, '192.168.8.1')
        logs = self.firewall.get_logs()
        self.assertTrue(any('192.168.8.1' in str(log) for log in logs))
        
    def test_27_complete_roundtrip_with_all_components(self):
        # Setup
        self.firewall.allow_ip('10.10.10.10')
        self.stun.public_ip = '203.0.113.40'
        self.federation.stun = self.stun
        self.federation.tunnel = self.tunnel
        
        # Simulate incoming message
        with patch('core.mesh_federation.MeshFederation.validate_message') as mock_val:
            mock_val.return_value = True
            msg = {
                'type': 'tunneled',
                'encrypted': self.tunnel.encrypt(b'payload', 'key'),
                'dst': 'local'
            }
            result = self.federation.process_incoming(msg, '10.10.10.10')
            self.assertIsNotNone(result)

if __name__ == '__main__':
    unittest.main()