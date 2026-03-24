"""Tests for core/mesh_monitor.py — Phase 7 mesh monitor."""
import json
import time
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.mesh_monitor import MeshMonitor, get_monitor


def _make_nodes_json(nodes: dict, path: Path):
    """Write a nodes.json file for testing."""
    path.write_text(json.dumps(nodes))


def _make_messages_jsonl(messages: list, path: Path):
    """Write a messages.jsonl file for testing."""
    path.write_text("\n".join(json.dumps(m) for m in messages))


class TestMeshMonitorInit(unittest.TestCase):

    def setUp(self):
        MeshMonitor._instance = None

    def test_creates_instance(self):
        m = MeshMonitor()
        self.assertIsNotNone(m)

    def test_node_status_empty_initially(self):
        m = MeshMonitor()
        self.assertIsInstance(m.node_status, dict)

    def test_alert_callbacks_empty_initially(self):
        m = MeshMonitor()
        self.assertIsInstance(m.alert_callbacks, list)
        self.assertEqual(len(m.alert_callbacks), 0)


class TestMeshMonitorCheck(unittest.TestCase):

    def setUp(self):
        MeshMonitor._instance = None
        self.tmp = tempfile.mkdtemp()
        self.nodes_file = Path(self.tmp) / "nodes.json"
        self.messages_file = Path(self.tmp) / "messages.jsonl"
        self.status_file = Path(self.tmp) / "monitor.jsonl"

    def _make_monitor(self):
        m = MeshMonitor()
        m.nodes_file = self.nodes_file
        m.messages_file = self.messages_file
        m.status_file = self.status_file
        return m

    def test_check_returns_dict(self):
        self.nodes_file.write_text("{}")
        m = self._make_monitor()
        result = m.check()
        self.assertIsInstance(result, dict)

    def test_check_returns_nodes_key(self):
        self.nodes_file.write_text("{}")
        m = self._make_monitor()
        result = m.check()
        self.assertIn("nodes", result)

    def test_check_reads_nodes_json(self):
        nodes = {
            "node-alpha": {"last_active": 0, "status": "idle"},
            "node-beta":  {"last_active": 0, "status": "idle"},
        }
        self.nodes_file.write_text(json.dumps(nodes))
        m = self._make_monitor()
        result = m.check()
        self.assertIn("node-alpha", result["nodes"])
        self.assertIn("node-beta", result["nodes"])

    def test_alive_node_detected(self):
        from datetime import datetime
        nodes = {
            "alive-node": {"last_active": datetime.now().isoformat(), "status": "active"},
        }
        self.nodes_file.write_text(json.dumps(nodes))
        m = self._make_monitor()
        result = m.check()
        # alive-node has recent timestamp → should be alive
        self.assertTrue(result["nodes"]["alive-node"]["alive"])

    def test_dead_node_detected(self):
        from datetime import datetime, timedelta
        old_time = (datetime.now() - timedelta(seconds=200)).isoformat()
        nodes = {
            "dead-node": {"last_active": old_time, "status": "idle"},
        }
        self.nodes_file.write_text(json.dumps(nodes))
        m = self._make_monitor()
        result = m.check()
        self.assertFalse(result["nodes"]["dead-node"]["alive"])

    def test_monitor_jsonl_written(self):
        self.nodes_file.write_text("{}")
        m = self._make_monitor()
        m.check()
        self.assertTrue(self.status_file.exists())

    def test_monitor_jsonl_valid_json(self):
        self.nodes_file.write_text("{}")
        m = self._make_monitor()
        m.check()
        lines = self.status_file.read_text().strip().split("\n")
        for line in lines:
            data = json.loads(line)
            self.assertIn("nodes", data)

    def test_alert_callback_fires_for_offline_node(self):
        from datetime import datetime, timedelta
        old = (datetime.now() - timedelta(seconds=200)).isoformat()
        nodes = {"offline-node": {"last_active": old, "status": "idle"}}
        self.nodes_file.write_text(json.dumps(nodes))
        m = self._make_monitor()
        cb = MagicMock()
        m.register_alert_callback(cb)
        m.check()
        cb.assert_called()

    def test_register_alert_callback_stored(self):
        m = self._make_monitor()
        cb = MagicMock()
        m.register_alert_callback(cb)
        self.assertIn(cb, m.alert_callbacks)

    def test_get_status_returns_dict(self):
        self.nodes_file.write_text("{}")
        m = self._make_monitor()
        status = m.get_status()
        self.assertIsInstance(status, dict)
        self.assertIn("nodes", status)

    def test_missing_nodes_file_handled(self):
        # No nodes file — should not crash
        m = self._make_monitor()
        result = m.check()
        self.assertIsInstance(result, dict)

    def test_check_returns_alerts_key(self):
        self.nodes_file.write_text("{}")
        m = self._make_monitor()
        result = m.check()
        self.assertIn("alerts", result)


class TestGetMonitorSingleton(unittest.TestCase):

    def setUp(self):
        MeshMonitor._instance = None

    def test_same_instance_twice(self):
        m1 = get_monitor()
        m2 = get_monitor()
        self.assertIs(m1, m2)

    def test_returns_mesh_monitor(self):
        self.assertIsInstance(get_monitor(), MeshMonitor)


if __name__ == "__main__":
    unittest.main(verbosity=2)
