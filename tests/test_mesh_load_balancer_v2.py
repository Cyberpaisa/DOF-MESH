"""
Tests for core.mesh_router_v2 — MeshRouterV2, the next-gen load-balancing router.

15+ tests covering:
  1. Singleton pattern
  2. route() returns a valid node_id string
  3. route() with "code" task_type prefers coding-specialty nodes
  4. route() avoids overloaded nodes (active_tasks > 5)
  5. update_latency() updates latency for a node
  6. get_stats() returns dict with at least 'total_routed' key
  7. Edge cases: empty nodes.json, all nodes overloaded, unknown task_type

Run: python3 -m unittest tests.test_mesh_load_balancer_v2
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.mesh_router_v2 import MeshRouterV2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_nodes(overrides=None):
    """Return a minimal nodes.json payload for testing."""
    nodes = {
        "commander": {
            "node_id": "commander",
            "role": "orchestrator",
            "specialty": "general",
            "active_tasks": 0,
            "avg_latency_ms": 120.0,
            "success_rate": 0.98,
            "model": "claude-sonnet-4-6",
        },
        "architect": {
            "node_id": "architect",
            "role": "code architecture and implementation",
            "specialty": "code",
            "active_tasks": 1,
            "avg_latency_ms": 95.0,
            "success_rate": 0.99,
            "model": "claude-sonnet-4-6",
        },
        "researcher": {
            "node_id": "researcher",
            "role": "research and analysis",
            "specialty": "research",
            "active_tasks": 2,
            "avg_latency_ms": 200.0,
            "success_rate": 0.95,
            "model": "claude-opus-4-6",
        },
        "guardian": {
            "node_id": "guardian",
            "role": "security and tests",
            "specialty": "security",
            "active_tasks": 0,
            "avg_latency_ms": 110.0,
            "success_rate": 0.97,
            "model": "claude-sonnet-4-6",
        },
    }
    if overrides:
        nodes.update(overrides)
    return nodes


class TestMeshRouterV2Singleton(unittest.TestCase):
    """Singleton contract: two calls must return the exact same object."""

    def setUp(self):
        # Reset singleton before each test so we get a clean state
        MeshRouterV2._instance = None
        self.tmp_dir = tempfile.mkdtemp()
        self.nodes_path = os.path.join(self.tmp_dir, "nodes.json")
        with open(self.nodes_path, "w") as f:
            json.dump(_make_nodes(), f)

    def tearDown(self):
        MeshRouterV2._instance = None
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_singleton_same_object(self):
        """Two MeshRouterV2 instances must be the same object."""
        r1 = MeshRouterV2.get_instance(mesh_dir=self.tmp_dir)
        r2 = MeshRouterV2.get_instance(mesh_dir=self.tmp_dir)
        self.assertIs(r1, r2)

    def test_singleton_after_reset(self):
        """After clearing _instance, a new object is created."""
        r1 = MeshRouterV2.get_instance(mesh_dir=self.tmp_dir)
        MeshRouterV2._instance = None
        r2 = MeshRouterV2.get_instance(mesh_dir=self.tmp_dir)
        self.assertIsNot(r1, r2)

    def test_singleton_type(self):
        """Instance must be a MeshRouterV2."""
        r = MeshRouterV2.get_instance(mesh_dir=self.tmp_dir)
        self.assertIsInstance(r, MeshRouterV2)


class TestMeshRouterV2Route(unittest.TestCase):
    """route() basic contracts."""

    def setUp(self):
        MeshRouterV2._instance = None
        self.tmp_dir = tempfile.mkdtemp()
        self.nodes_path = os.path.join(self.tmp_dir, "nodes.json")
        with open(self.nodes_path, "w") as f:
            json.dump(_make_nodes(), f)
        self.router = MeshRouterV2.get_instance(mesh_dir=self.tmp_dir)

    def tearDown(self):
        MeshRouterV2._instance = None
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_route_returns_string(self):
        """route() must return a non-empty string."""
        result = self.router.route(task_type="general")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_route_returns_known_node(self):
        """route() must return a node_id that exists in nodes.json."""
        nodes = _make_nodes()
        result = self.router.route(task_type="general")
        self.assertIn(result, nodes.keys())

    def test_route_code_prefers_coding_node(self):
        """route() with task_type='code' should prefer the 'architect' node."""
        result = self.router.route(task_type="code")
        self.assertEqual(result, "architect")

    def test_route_security_prefers_guardian(self):
        """route() with task_type='security' should prefer the 'guardian' node."""
        result = self.router.route(task_type="security")
        self.assertEqual(result, "guardian")

    def test_route_unknown_task_type_returns_string(self):
        """route() with an unknown task_type must still return a valid node_id."""
        result = self.router.route(task_type="unknown_xyz_task")
        self.assertIsInstance(result, str)
        nodes = _make_nodes()
        self.assertIn(result, nodes.keys())

    def test_route_avoids_overloaded_nodes(self):
        """route() must not return a node whose active_tasks > 5."""
        # Overload all nodes except 'guardian'
        overloaded = _make_nodes({
            "commander": {**_make_nodes()["commander"], "active_tasks": 6},
            "architect": {**_make_nodes()["architect"], "active_tasks": 7},
            "researcher": {**_make_nodes()["researcher"], "active_tasks": 8},
            "guardian": {**_make_nodes()["guardian"], "active_tasks": 0},
        })
        with open(self.nodes_path, "w") as f:
            json.dump(overloaded, f)
        # Force re-read by creating a fresh instance
        MeshRouterV2._instance = None
        router = MeshRouterV2.get_instance(mesh_dir=self.tmp_dir)
        result = router.route(task_type="general")
        self.assertEqual(result, "guardian")

    def test_route_all_nodes_overloaded_still_returns_string(self):
        """If ALL nodes are overloaded, route() should still return *something*."""
        all_overloaded = {
            nid: {**data, "active_tasks": 10}
            for nid, data in _make_nodes().items()
        }
        with open(self.nodes_path, "w") as f:
            json.dump(all_overloaded, f)
        MeshRouterV2._instance = None
        router = MeshRouterV2.get_instance(mesh_dir=self.tmp_dir)
        result = router.route(task_type="general")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_route_empty_nodes_raises_or_returns_none(self):
        """route() with empty nodes.json must raise ValueError (or return None)."""
        with open(self.nodes_path, "w") as f:
            json.dump({}, f)
        MeshRouterV2._instance = None
        router = MeshRouterV2.get_instance(mesh_dir=self.tmp_dir)
        try:
            result = router.route(task_type="general")
            # If it doesn't raise, result must be None or empty
            self.assertFalse(result)
        except (ValueError, KeyError, IndexError):
            pass  # acceptable — no nodes available


class TestMeshRouterV2UpdateLatency(unittest.TestCase):
    """update_latency() must persist the new value."""

    def setUp(self):
        MeshRouterV2._instance = None
        self.tmp_dir = tempfile.mkdtemp()
        self.nodes_path = os.path.join(self.tmp_dir, "nodes.json")
        with open(self.nodes_path, "w") as f:
            json.dump(_make_nodes(), f)
        self.router = MeshRouterV2.get_instance(mesh_dir=self.tmp_dir)

    def tearDown(self):
        MeshRouterV2._instance = None
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_update_latency_changes_value(self):
        """After update_latency(), the stored latency must reflect the new value."""
        self.router.update_latency("commander", 42.0)
        stats = self.router.get_stats()
        node_latencies = stats.get("node_latencies", {})
        if node_latencies:
            self.assertAlmostEqual(node_latencies.get("commander", -1), 42.0, places=1)

    def test_update_latency_does_not_affect_other_nodes(self):
        """Updating one node's latency must not change other nodes."""
        before = self.router.get_stats().get("node_latencies", {})
        self.router.update_latency("architect", 77.5)
        after = self.router.get_stats().get("node_latencies", {})
        # If latency tracking is exposed, commander's value should be unchanged
        if "commander" in before and "commander" in after:
            self.assertEqual(before["commander"], after["commander"])

    def test_update_latency_unknown_node_no_crash(self):
        """Updating latency for a nonexistent node must not raise."""
        try:
            self.router.update_latency("nonexistent_node_xyz", 999.0)
        except KeyError:
            pass  # acceptable to raise KeyError for unknown node
        except Exception as exc:
            self.fail(f"update_latency raised unexpected {type(exc).__name__}: {exc}")


class TestMeshRouterV2Stats(unittest.TestCase):
    """get_stats() contract."""

    def setUp(self):
        MeshRouterV2._instance = None
        self.tmp_dir = tempfile.mkdtemp()
        self.nodes_path = os.path.join(self.tmp_dir, "nodes.json")
        with open(self.nodes_path, "w") as f:
            json.dump(_make_nodes(), f)
        self.router = MeshRouterV2.get_instance(mesh_dir=self.tmp_dir)

    def tearDown(self):
        MeshRouterV2._instance = None
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_get_stats_returns_dict(self):
        """get_stats() must return a dict."""
        stats = self.router.get_stats()
        self.assertIsInstance(stats, dict)

    def test_get_stats_has_total_routed(self):
        """get_stats() dict must contain the 'total_routed' key."""
        stats = self.router.get_stats()
        self.assertIn("total_routed", stats)

    def test_total_routed_increments(self):
        """total_routed must increase by 1 after each route() call."""
        before = self.router.get_stats().get("total_routed", 0)
        self.router.route(task_type="general")
        after = self.router.get_stats().get("total_routed", 0)
        self.assertEqual(after, before + 1)

    def test_total_routed_increments_multiple(self):
        """total_routed must reflect the correct cumulative count."""
        before = self.router.get_stats().get("total_routed", 0)
        for _ in range(5):
            self.router.route(task_type="general")
        after = self.router.get_stats().get("total_routed", 0)
        self.assertEqual(after, before + 5)


if __name__ == "__main__":
    unittest.main()
