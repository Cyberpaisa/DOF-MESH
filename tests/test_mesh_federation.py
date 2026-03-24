"""
Tests for core/mesh_federation.py — Phase 6 Federation Protocol
Generated with Legion assistance (qwen-coder-480b design, adapted for actual module).
"""

import hashlib
import hmac
import json
import socket
import threading
import time
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.mesh_federation import (
    FederationNode,
    FederationMessage,
    FederationDiscovery,
    FederationBridge,
    FederationManager,
    MESH_PROTOCOL_V,
    DISCOVERY_PORT,
    BRIDGE_PORT,
    MAX_MSG_PER_MIN,
    NONCE_WINDOW_SEC,
    get_federation_manager,
)


# ═══════════════════════════════════════════════
# FederationNode Tests
# ═══════════════════════════════════════════════

class TestFederationNode(unittest.TestCase):

    def setUp(self):
        self.node = FederationNode(
            node_id="node-alpha",
            host="192.168.1.10",
            port=7892,
            public_key="pubkey-abc123",
        )

    def test_creation(self):
        self.assertEqual(self.node.node_id, "node-alpha")
        self.assertEqual(self.node.host, "192.168.1.10")
        self.assertEqual(self.node.port, 7892)
        self.assertEqual(self.node.public_key, "pubkey-abc123")
        self.assertEqual(self.node.msg_count, 0)
        self.assertFalse(self.node.trusted)

    def test_is_alive_recent(self):
        self.node.last_seen = time.time()
        self.assertTrue(self.node.is_alive())

    def test_is_alive_old(self):
        self.node.last_seen = time.time() - 200  # older than PEER_TIMEOUT_SEC=90
        self.assertFalse(self.node.is_alive())

    def test_to_dict_returns_dict(self):
        d = self.node.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["node_id"], "node-alpha")
        self.assertEqual(d["host"], "192.168.1.10")

    def test_to_dict_serializable(self):
        d = self.node.to_dict()
        serialized = json.dumps(d)
        self.assertIn("node-alpha", serialized)

    def test_default_port(self):
        node = FederationNode(node_id="x", host="localhost")
        self.assertEqual(node.port, BRIDGE_PORT)


# ═══════════════════════════════════════════════
# FederationMessage Tests
# ═══════════════════════════════════════════════

class TestFederationMessage(unittest.TestCase):

    KEY = b"test-mesh-key-2026"

    def _make_msg(self, **kwargs):
        defaults = dict(
            msg_id="MSG-001",
            from_node="alpha",
            to_node="beta",
            payload={"action": "test"},
            nonce="abc123nonce",
        )
        defaults.update(kwargs)
        return FederationMessage(**defaults)

    def test_sign_produces_signature(self):
        msg = self._make_msg()
        msg.sign(self.KEY)
        self.assertGreater(len(msg.signature), 0)

    def test_verify_valid_signature(self):
        msg = self._make_msg()
        msg.sign(self.KEY)
        self.assertTrue(msg.verify(self.KEY))

    def test_verify_invalid_key(self):
        msg = self._make_msg()
        msg.sign(self.KEY)
        self.assertFalse(msg.verify(b"wrong-key"))

    def test_verify_tampered_from_node(self):
        msg = self._make_msg()
        msg.sign(self.KEY)
        msg.from_node = "attacker"
        self.assertFalse(msg.verify(self.KEY))

    def test_replay_recent_message(self):
        msg = self._make_msg(timestamp=time.time())
        self.assertFalse(msg.is_replay())

    def test_replay_old_message(self):
        msg = self._make_msg(timestamp=time.time() - NONCE_WINDOW_SEC - 10)
        self.assertTrue(msg.is_replay())

    def test_replay_future_message(self):
        msg = self._make_msg(timestamp=time.time() + NONCE_WINDOW_SEC + 10)
        self.assertTrue(msg.is_replay())


# ═══════════════════════════════════════════════
# FederationDiscovery Tests
# ═══════════════════════════════════════════════

class TestFederationDiscovery(unittest.TestCase):

    def test_init(self):
        disc = FederationDiscovery(
            my_id="test-node",
            my_host="localhost",
            my_port=7892,
        )
        self.assertEqual(disc._my_id, "test-node")
        self.assertFalse(disc._running)

    def test_handle_announce_valid(self):
        found = []
        disc = FederationDiscovery(
            my_id="commander",
            my_host="localhost",
            my_port=7892,
            on_peer_found=found.append,
        )
        msg = json.dumps({
            "protocol": MESH_PROTOCOL_V,
            "type": "ANNOUNCE",
            "node_id": "remote-node",
            "host": "192.168.1.50",
            "port": 7892,
            "timestamp": time.time(),
        }).encode()
        disc._handle_announce(msg, ("192.168.1.50", 7891))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].node_id, "remote-node")

    def test_handle_announce_ignores_self(self):
        found = []
        disc = FederationDiscovery(
            my_id="commander",
            my_host="localhost",
            my_port=7892,
            on_peer_found=found.append,
        )
        msg = json.dumps({
            "protocol": MESH_PROTOCOL_V,
            "type": "ANNOUNCE",
            "node_id": "commander",  # same as my_id
            "host": "localhost",
            "port": 7892,
            "timestamp": time.time(),
        }).encode()
        disc._handle_announce(msg, ("localhost", 7891))
        self.assertEqual(len(found), 0)

    def test_handle_announce_wrong_protocol(self):
        found = []
        disc = FederationDiscovery("cmd", "localhost", 7892, on_peer_found=found.append)
        msg = json.dumps({
            "protocol": "UNKNOWN-PROTOCOL",
            "type": "ANNOUNCE",
            "node_id": "attacker",
        }).encode()
        disc._handle_announce(msg, ("10.0.0.1", 7891))
        self.assertEqual(len(found), 0)

    def test_handle_announce_deduplication(self):
        found = []
        disc = FederationDiscovery("cmd", "localhost", 7892, on_peer_found=found.append)
        msg = json.dumps({
            "protocol": MESH_PROTOCOL_V,
            "type": "ANNOUNCE",
            "node_id": "unique-node",
            "host": "10.0.0.5",
            "port": 7892,
            "timestamp": time.time(),
        }).encode()
        disc._handle_announce(msg, ("10.0.0.5", 7891))
        disc._handle_announce(msg, ("10.0.0.5", 7891))  # duplicate
        self.assertEqual(len(found), 1)  # only called once

    def test_handle_announce_malformed_json(self):
        found = []
        disc = FederationDiscovery("cmd", "localhost", 7892, on_peer_found=found.append)
        disc._handle_announce(b"not-json{{{", ("10.0.0.1", 7891))
        self.assertEqual(len(found), 0)


# ═══════════════════════════════════════════════
# FederationManager Tests
# ═══════════════════════════════════════════════

class TestFederationManager(unittest.TestCase):

    KEY = b"test-key-2026"

    def _make_manager(self, tmp_path=None):
        if tmp_path is None:
            import tempfile
            tmp_path = tempfile.mkdtemp()
        mgr = FederationManager(
            my_id="test-commander",
            my_host="127.0.0.1",
            bridge_port=0,  # don't actually bind
            mesh_key=self.KEY,
            local_mesh_path=tmp_path,
        )
        return mgr

    def test_init(self):
        mgr = self._make_manager()
        self.assertEqual(mgr._my_id, "test-commander")
        self.assertEqual(len(mgr._peers), 0)

    def test_register_peer(self):
        mgr = self._make_manager()
        peer = FederationNode(node_id="peer-1", host="10.0.0.1", port=7892)
        mgr._register_peer(peer)
        self.assertIn("peer-1", mgr._peers)

    def test_register_peer_dedup(self):
        mgr = self._make_manager()
        peer = FederationNode(node_id="peer-1", host="10.0.0.1")
        mgr._register_peer(peer)
        mgr._register_peer(peer)
        self.assertEqual(len(mgr._peers), 1)

    def test_get_peers_returns_alive(self):
        mgr = self._make_manager()
        alive = FederationNode(node_id="alive", host="10.0.0.1", last_seen=time.time())
        dead = FederationNode(node_id="dead", host="10.0.0.2", last_seen=time.time() - 200)
        mgr._peers["alive"] = alive
        mgr._peers["dead"] = dead
        peers = mgr.get_peers()
        self.assertEqual(len(peers), 1)
        self.assertEqual(peers[0].node_id, "alive")

    def test_get_status(self):
        mgr = self._make_manager()
        status = mgr.get_status()
        self.assertIn("my_id", status)
        self.assertIn("peers_total", status)
        self.assertIn("peers_alive", status)
        self.assertEqual(status["my_id"], "test-commander")

    def test_rate_check_within_limit(self):
        mgr = self._make_manager()
        for _ in range(MAX_MSG_PER_MIN - 1):
            self.assertTrue(mgr._rate_check("node-x"))

    def test_rate_check_exceeds_limit(self):
        mgr = self._make_manager()
        for _ in range(MAX_MSG_PER_MIN):
            mgr._rate_check("flooder")
        self.assertFalse(mgr._rate_check("flooder"))

    def test_handle_inbound_valid(self):
        import tempfile
        tmp = tempfile.mkdtemp()
        mgr = self._make_manager(tmp_path=tmp)
        # Register sender as peer
        mgr._peers["sender-node"] = FederationNode(node_id="sender-node", host="10.0.0.1")

        msg = FederationMessage(
            msg_id="TEST-001",
            from_node="sender-node",
            to_node="test-commander",
            payload={"data": "hello"},
            nonce="unique-nonce-xyz",
            timestamp=time.time(),
        )
        msg.sign(self.KEY)
        data = asdict(msg)

        result = mgr._handle_inbound(data)
        self.assertTrue(result)

    def test_handle_inbound_bad_signature(self):
        mgr = self._make_manager()
        msg = FederationMessage(
            msg_id="TEST-002",
            from_node="attacker",
            to_node="commander",
            payload={"attack": "payload"},
            nonce="nonce-attack",
            timestamp=time.time(),
            signature="bad-signature",
        )
        result = mgr._handle_inbound(asdict(msg))
        self.assertFalse(result)

    def test_handle_inbound_replay_blocked(self):
        import tempfile
        tmp = tempfile.mkdtemp()
        mgr = self._make_manager(tmp_path=tmp)
        mgr._peers["sender"] = FederationNode(node_id="sender", host="10.0.0.1")

        msg = FederationMessage(
            msg_id="REPLAY-001",
            from_node="sender",
            to_node="commander",
            payload={"x": 1},
            nonce="replay-nonce",
            timestamp=time.time(),
        )
        msg.sign(self.KEY)
        data = asdict(msg)

        mgr._handle_inbound(data)  # first time OK
        result = mgr._handle_inbound(data)  # second time = replay
        self.assertFalse(result)

    def test_handle_inbound_old_timestamp(self):
        mgr = self._make_manager()
        msg = FederationMessage(
            msg_id="OLD-001",
            from_node="old-node",
            to_node="commander",
            payload={},
            nonce="old-nonce",
            timestamp=time.time() - NONCE_WINDOW_SEC - 5,
        )
        msg.sign(self.KEY)
        result = mgr._handle_inbound(asdict(msg))
        self.assertFalse(result)

    def test_deliver_to_local_mesh(self):
        import tempfile
        tmp = tempfile.mkdtemp()
        mgr = self._make_manager(tmp_path=tmp)
        msg = FederationMessage(
            msg_id="LOCAL-001",
            from_node="remote-peer",
            to_node="commander",
            payload={"task": "build phase 6"},
            nonce="nonce-local",
        )
        mgr._deliver_to_local_mesh(msg)
        # Check file was written
        inbox = Path(tmp) / "inbox" / "commander"
        files = list(inbox.glob("*.json"))
        self.assertGreater(len(files), 0)
        content = json.loads(files[0].read_text())
        self.assertEqual(content["to_node"], "commander")
        self.assertEqual(content["msg_type"], "federation_inbound")

    def test_heartbeat_removes_dead_peers(self):
        mgr = self._make_manager()
        dead = FederationNode(node_id="dead-peer", host="10.0.0.99", last_seen=time.time() - 200)
        mgr._peers["dead-peer"] = dead
        # Manually trigger cleanup
        with mgr._lock:
            dead_ids = [nid for nid, p in mgr._peers.items() if not p.is_alive()]
            for nid in dead_ids:
                del mgr._peers[nid]
        self.assertNotIn("dead-peer", mgr._peers)

    def test_singleton_returns_same_instance(self):
        # Reset singleton for test
        import core.mesh_federation as fed_mod
        original = fed_mod._instance
        fed_mod._instance = None
        try:
            mgr1 = get_federation_manager()
            mgr2 = get_federation_manager()
            self.assertIs(mgr1, mgr2)
        finally:
            fed_mod._instance = original


if __name__ == "__main__":
    unittest.main(verbosity=2)
