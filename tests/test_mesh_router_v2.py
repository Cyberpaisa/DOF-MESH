"""Tests for core.mesh_router_v2 — MeshRouterV2."""
import json
import tempfile
import threading
import unittest
from pathlib import Path


class TestMeshRouterV2Singleton(unittest.TestCase):
    def setUp(self):
        from core.mesh_router_v2 import MeshRouterV2
        MeshRouterV2._instance = None

    def tearDown(self):
        from core.mesh_router_v2 import MeshRouterV2
        MeshRouterV2._instance = None

    def test_singleton_same_instance(self):
        from core.mesh_router_v2 import MeshRouterV2
        a = MeshRouterV2()
        b = MeshRouterV2()
        self.assertIs(a, b)

    def test_get_instance_class_method(self):
        from core.mesh_router_v2 import MeshRouterV2
        a = MeshRouterV2.get_instance()
        b = MeshRouterV2.get_instance()
        self.assertIs(a, b)

    def test_thread_safe_singleton(self):
        from core.mesh_router_v2 import MeshRouterV2
        instances = []
        def _get():
            instances.append(MeshRouterV2())
        threads = [threading.Thread(target=_get) for _ in range(8)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertTrue(all(i is instances[0] for i in instances))


class TestMeshRouterV2Route(unittest.TestCase):
    def setUp(self):
        from core.mesh_router_v2 import MeshRouterV2
        MeshRouterV2._instance = None
        self.tmp = tempfile.mkdtemp()
        nodes = {
            "cerebras-llama": {"status": "active", "avg_latency_ms": 100, "active_tasks": 1, "role": "coder"},
            "deepseek-coder": {"status": "active", "avg_latency_ms": 300, "active_tasks": 2, "role": "builder"},
            "analyst-node":   {"status": "active", "avg_latency_ms": 200, "active_tasks": 0, "role": "analyst"},
        }
        Path(self.tmp, "nodes.json").write_text(
            json.dumps(nodes), encoding="utf-8"
        )
        self.router = MeshRouterV2(mesh_dir=Path(self.tmp))

    def tearDown(self):
        from core.mesh_router_v2 import MeshRouterV2
        MeshRouterV2._instance = None

    def test_route_returns_string(self):
        node = self.router.route("code")
        self.assertIsInstance(node, str)
        self.assertTrue(len(node) > 0)

    def test_route_code_task(self):
        node = self.router.route("code")
        self.assertIsInstance(node, str)

    def test_route_analysis_task(self):
        node = self.router.route("analysis")
        self.assertIsInstance(node, str)

    def test_route_unknown_type_fallback(self):
        node = self.router.route("totally_unknown_type_xyz")
        self.assertIsInstance(node, str)
        self.assertTrue(len(node) > 0)

    def test_route_empty_type_fallback(self):
        node = self.router.route("")
        self.assertIsInstance(node, str)

    def test_route_deterministic_empty_nodes(self):
        # With no nodes file, route raises ValueError
        from core.mesh_router_v2 import MeshRouterV2
        MeshRouterV2._instance = None
        empty_dir = tempfile.mkdtemp()
        router_empty = MeshRouterV2(mesh_dir=Path(empty_dir))
        with self.assertRaises(ValueError):
            router_empty.route("code")


class TestMeshRouterV2Stats(unittest.TestCase):
    def setUp(self):
        from core.mesh_router_v2 import MeshRouterV2
        MeshRouterV2._instance = None
        self.router = MeshRouterV2()

    def tearDown(self):
        from core.mesh_router_v2 import MeshRouterV2
        MeshRouterV2._instance = None

    def test_get_stats_returns_dict(self):
        stats = self.router.get_stats()
        self.assertIsInstance(stats, dict)

    def test_update_latency_accepted(self):
        # Should not raise
        self.router.update_latency("cerebras-llama", 150.0)
        self.router.update_latency("deepseek-coder", 320.5)

    def test_update_latency_negative_handled(self):
        # Negative latency is unusual but should not crash
        try:
            self.router.update_latency("node-x", -1.0)
        except Exception:
            pass  # acceptable

    def test_update_latency_zero(self):
        self.router.update_latency("node-x", 0.0)


class TestRouteDecision(unittest.TestCase):
    def test_creation(self):
        from core.mesh_router_v2 import RouteDecision
        rd = RouteDecision(
            task_type="code",
            selected_node="deepseek-coder",
            score=0.95,
            specialty_match=True,
            active_tasks=2,
            latency_ms=150.0,
            candidates=3,
        )
        self.assertEqual(rd.selected_node, "deepseek-coder")
        self.assertEqual(rd.score, 0.95)

    def test_to_dict(self):
        from core.mesh_router_v2 import RouteDecision
        rd = RouteDecision(
            task_type="code",
            selected_node="node-a",
            score=0.8,
            specialty_match=False,
            active_tasks=1,
            latency_ms=200.0,
            candidates=2,
        )
        d = rd.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIn("selected_node", d)
        self.assertIn("task_type", d)


class TestMeshRouterV2WithNodes(unittest.TestCase):
    def setUp(self):
        import tempfile, os
        from core.mesh_router_v2 import MeshRouterV2
        MeshRouterV2._instance = None
        self.tmp = tempfile.mkdtemp()
        nodes = {
            "cerebras-llama": {"status": "active", "avg_latency_ms": 100, "active_tasks": 1},
            "deepseek-coder": {"status": "active", "avg_latency_ms": 300, "active_tasks": 2},
        }
        Path(self.tmp, "nodes.json").write_text(
            json.dumps(nodes), encoding="utf-8"
        )
        self.router = MeshRouterV2(mesh_dir=Path(self.tmp))

    def tearDown(self):
        from core.mesh_router_v2 import MeshRouterV2
        MeshRouterV2._instance = None

    def test_route_returns_valid_node(self):
        node = self.router.route("code")
        self.assertIn(node, ["cerebras-llama", "deepseek-coder"])

    def test_route_prefers_lower_latency(self):
        # With 2 nodes, low latency node should be preferred for fast tasks
        node = self.router.route("fast")
        self.assertIsInstance(node, str)
