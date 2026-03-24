"""Tests for core.honeypot — HoneypotManager, HoneypotNode, TrapTrigger."""
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch


class TestHoneypotAlert(unittest.TestCase):
    def _make_alert(self, **kwargs):
        from core.honeypot import HoneypotAlert
        defaults = dict(
            alert_id="TRAP-001",
            honeypot_id="honey-node-alpha",
            attacker_node="evil-agent",
            contact_time="2026-03-24T10:00:00+00:00",
            payload_preview="GET /admin",
        )
        defaults.update(kwargs)
        return HoneypotAlert(**defaults)

    def test_creation(self):
        a = self._make_alert()
        self.assertEqual(a.alert_id, "TRAP-001")
        self.assertEqual(a.attacker_node, "evil-agent")

    def test_default_severity_critical(self):
        a = self._make_alert()
        self.assertEqual(a.severity, "CRITICAL")

    def test_default_blocked_true(self):
        a = self._make_alert()
        self.assertTrue(a.blocked)

    def test_to_jsonl_returns_string(self):
        a = self._make_alert()
        line = a.to_jsonl()
        self.assertIsInstance(line, str)

    def test_to_jsonl_valid_json(self):
        a = self._make_alert()
        data = json.loads(a.to_jsonl())
        self.assertIn("alert_id", data)
        self.assertIn("attacker_node", data)

    def test_to_jsonl_no_newline(self):
        a = self._make_alert()
        self.assertNotIn("\n", a.to_jsonl())


class TestHoneypotManager(unittest.TestCase):
    def setUp(self):
        from core.honeypot import HoneypotManager
        self.mgr = HoneypotManager()

    def test_deploy_all_deploys_nodes(self):
        self.mgr.deploy_all()
        status = self.mgr.get_status()
        # Key is 'honeypots' in get_status()
        self.assertIn("honeypots", status)
        self.assertGreater(len(status["honeypots"]), 0)

    def test_get_status_returns_dict(self):
        status = self.mgr.get_status()
        self.assertIsInstance(status, dict)

    def test_is_blocked_false_for_unknown(self):
        self.assertFalse(self.mgr.is_blocked("unknown-node-xyz"))

    def test_check_contact_with_honeypot_returns_alert(self):
        from core.honeypot import HoneypotAlert
        self.mgr.deploy_all()
        with patch("builtins.open", unittest.mock.mock_open()):
            result = self.mgr.check_contact(
                from_node="attacker-99",
                to_node="honey-node-alpha",
                payload="probe"
            )
        self.assertIsInstance(result, HoneypotAlert)

    def test_check_contact_with_honeypot_blocks_attacker(self):
        self.mgr.deploy_all()
        with patch("builtins.open", unittest.mock.mock_open()):
            self.mgr.check_contact("spy-node", "honey-node-beta", "scan")
        self.assertTrue(self.mgr.is_blocked("spy-node"))

    def test_check_contact_with_normal_node_returns_none(self):
        self.mgr.deploy_all()
        result = self.mgr.check_contact("commander", "deepseek-coder", "task")
        self.assertIsNone(result)

    def test_get_alerts_returns_list(self):
        alerts = self.mgr.get_alerts()
        self.assertIsInstance(alerts, list)

    def test_get_alerts_limit(self):
        alerts = self.mgr.get_alerts(limit=5)
        self.assertLessEqual(len(alerts), 5)

    def test_add_callback_called_on_alert(self):
        self.mgr.deploy_all()
        fired = []
        self.mgr.add_callback(lambda a: fired.append(a))
        with patch("builtins.open", unittest.mock.mock_open()):
            self.mgr.check_contact("intruder", "honey-node-gamma", "exploit")
        self.assertEqual(len(fired), 1)


class TestHoneypotNode(unittest.TestCase):
    def _make_node(self):
        from core.honeypot import HoneypotManager, HoneypotNode, TrapTrigger
        mgr = HoneypotManager()
        trigger = TrapTrigger(mgr)
        return HoneypotNode("honey-node-alpha", trigger)

    def test_activate_marks_active(self):
        node = self._make_node()
        node.activate()
        status = node.status()
        self.assertTrue(status.get("active"))

    def test_status_has_node_id(self):
        node = self._make_node()
        status = node.status()
        self.assertIn("honey-node-alpha", status.get("node_id", ""))

    def test_receive_from_legit_returns_none_before_activate(self):
        node = self._make_node()
        result = node.receive("commander", "hello")
        # Non-activated node should not fire
        self.assertIsNone(result)

    def test_receive_after_activate_returns_alert(self):
        from core.honeypot import HoneypotAlert
        node = self._make_node()
        node.activate()
        with patch("builtins.open", unittest.mock.mock_open()):
            result = node.receive("evil-bot", "probe payload")
        self.assertIsInstance(result, HoneypotAlert)

    def test_receive_sets_attacker_node(self):
        from core.honeypot import HoneypotAlert
        node = self._make_node()
        node.activate()
        with patch("builtins.open", unittest.mock.mock_open()):
            alert = node.receive("bad-actor", "payload")
        self.assertEqual(alert.attacker_node, "bad-actor")


class TestTrapTrigger(unittest.TestCase):
    def _make_trigger(self):
        from core.honeypot import HoneypotManager, TrapTrigger
        mgr = HoneypotManager()
        return TrapTrigger(mgr), mgr

    def test_fire_returns_alert(self):
        from core.honeypot import HoneypotAlert
        trigger, _ = self._make_trigger()
        with patch("builtins.open", unittest.mock.mock_open()):
            alert = trigger.fire("honey-node-alpha", "attacker", "data")
        self.assertIsInstance(alert, HoneypotAlert)

    def test_fire_increments_count(self):
        trigger, _ = self._make_trigger()
        self.assertEqual(trigger.count, 0)  # count is a @property
        with patch("builtins.open", unittest.mock.mock_open()):
            trigger.fire("honey-node-alpha", "attacker", "x")
        self.assertEqual(trigger.count, 1)

    def test_fire_blocks_attacker(self):
        trigger, mgr = self._make_trigger()
        with patch("builtins.open", unittest.mock.mock_open()):
            trigger.fire("honey-node-alpha", "target-node", "probe")
        self.assertTrue(mgr.is_blocked("target-node"))

    def test_alert_id_starts_with_trap(self):
        trigger, _ = self._make_trigger()
        with patch("builtins.open", unittest.mock.mock_open()):
            alert = trigger.fire("honey-node-beta", "node-x", "p")
        self.assertTrue(alert.alert_id.startswith("TRAP-"))

    def test_thread_safe_count(self):
        trigger, _ = self._make_trigger()
        results = []
        def _fire():
            with patch("builtins.open", unittest.mock.mock_open()):
                trigger.fire("honey-node-alpha", "attacker", "x")
                results.append(True)
        threads = [threading.Thread(target=_fire) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(trigger.count, 5)  # count is a @property
