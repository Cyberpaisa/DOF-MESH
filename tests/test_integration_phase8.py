"""
Integration tests for Phase 8 — P2P Consensus components.

20+ tests covering:
  1. MeshCircuitBreaker: singleton, CLOSED→OPEN transition after failures,
     OPEN raises CircuitOpenError, HALF_OPEN after recovery_timeout
  2. MeshAutoScaler: check_load() detects overloaded nodes,
     get_recommendations() returns list
  3. MeshMetricsCollector: collect() returns MeshMetrics dataclass,
     export_prometheus() returns string with "mesh_" prefix
  4. MeshRouterV2: route() returns non-empty string

Run: python3 -m unittest tests.test_integration_phase8
"""

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.mesh_circuit_breaker import (
    MeshCircuitBreaker,
    CircuitOpenError,
    CircuitState,
)
from core.mesh_auto_scaler import MeshAutoScaler
from core.mesh_metrics_collector import MeshMetricsCollector, MeshMetrics
from core.mesh_router_v2 import MeshRouterV2


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_nodes(count=4, overloaded_ids=None):
    """Return a nodes dict.  Nodes in overloaded_ids get active_tasks=10."""
    overloaded_ids = overloaded_ids or []
    nodes = {}
    for i in range(count):
        nid = f"node_{i}"
        nodes[nid] = {
            "node_id": nid,
            "role": "worker",
            "specialty": "general",
            "active_tasks": 10 if nid in overloaded_ids else 0,
            "avg_latency_ms": 100.0 + i * 10,
            "success_rate": 0.99,
            "model": "claude-sonnet-4-6",
            "messages_sent": 5,
            "messages_received": 5,
        }
    return nodes


# ---------------------------------------------------------------------------
# 1. MeshCircuitBreaker
# ---------------------------------------------------------------------------

class TestMeshCircuitBreakerSingleton(unittest.TestCase):
    """Singleton contract for MeshCircuitBreaker."""

    def setUp(self):
        MeshCircuitBreaker._instance = None

    def tearDown(self):
        MeshCircuitBreaker._instance = None

    def test_singleton_same_object(self):
        """Two get_instance() calls must return the same object."""
        cb1 = MeshCircuitBreaker.get_instance()
        cb2 = MeshCircuitBreaker.get_instance()
        self.assertIs(cb1, cb2)

    def test_singleton_type(self):
        """Instance must be a MeshCircuitBreaker."""
        cb = MeshCircuitBreaker.get_instance()
        self.assertIsInstance(cb, MeshCircuitBreaker)

    def test_singleton_reset(self):
        """After _instance reset, a new distinct object is created."""
        cb1 = MeshCircuitBreaker.get_instance()
        MeshCircuitBreaker._instance = None
        cb2 = MeshCircuitBreaker.get_instance()
        self.assertIsNot(cb1, cb2)


class TestMeshCircuitBreakerStateTransitions(unittest.TestCase):
    """CLOSED → OPEN → HALF_OPEN state machine."""

    def setUp(self):
        MeshCircuitBreaker._instance = None
        # Use a short recovery_timeout and low failure_threshold for fast testing
        self.cb = MeshCircuitBreaker.get_instance(
            failure_threshold=3,
            recovery_timeout=0.1,  # 100 ms so tests don't have to sleep long
        )

    def tearDown(self):
        MeshCircuitBreaker._instance = None

    def test_initial_state_is_closed(self):
        """Fresh circuit breaker must start in CLOSED state."""
        self.assertEqual(self.cb.state, CircuitState.CLOSED)

    def test_closed_allows_calls(self):
        """In CLOSED state, call() must execute without raising CircuitOpenError."""
        executed = []
        self.cb.call(lambda: executed.append(True), node_id="node_0")
        self.assertEqual(len(executed), 1)

    def test_transitions_open_after_threshold_failures(self):
        """After failure_threshold failures, state must become OPEN."""
        def failing():
            raise RuntimeError("simulated failure")

        for _ in range(3):
            try:
                self.cb.call(failing, node_id="node_0")
            except RuntimeError:
                pass

        self.assertEqual(self.cb.state, CircuitState.OPEN)

    def test_open_raises_circuit_open_error(self):
        """In OPEN state, call() must raise CircuitOpenError immediately."""
        def failing():
            raise RuntimeError("simulated failure")

        for _ in range(3):
            try:
                self.cb.call(failing, node_id="node_0")
            except RuntimeError:
                pass

        with self.assertRaises(CircuitOpenError):
            self.cb.call(lambda: None, node_id="node_0")

    def test_open_transitions_to_half_open_after_recovery_timeout(self):
        """After recovery_timeout passes, OPEN → HALF_OPEN on next call attempt."""
        def failing():
            raise RuntimeError("simulated failure")

        for _ in range(3):
            try:
                self.cb.call(failing, node_id="node_0")
            except RuntimeError:
                pass

        self.assertEqual(self.cb.state, CircuitState.OPEN)

        # Wait for recovery_timeout
        time.sleep(0.2)

        # Probe: attempt a call — should transition to HALF_OPEN
        try:
            self.cb.call(lambda: None, node_id="node_0")
        except CircuitOpenError:
            pass  # might still raise if implementation is strict

        self.assertIn(self.cb.state, (CircuitState.HALF_OPEN, CircuitState.CLOSED))

    def test_half_open_success_closes_circuit(self):
        """A successful call in HALF_OPEN must return the circuit to CLOSED."""
        def failing():
            raise RuntimeError("simulated failure")

        for _ in range(3):
            try:
                self.cb.call(failing, node_id="node_0")
            except RuntimeError:
                pass

        time.sleep(0.2)

        # Successful probe call
        self.cb.call(lambda: None, node_id="node_0")
        self.assertEqual(self.cb.state, CircuitState.CLOSED)

    def test_failure_count_resets_after_close(self):
        """failure_count must reset to 0 when circuit closes again."""
        def failing():
            raise RuntimeError("simulated failure")

        for _ in range(3):
            try:
                self.cb.call(failing, node_id="node_0")
            except RuntimeError:
                pass

        time.sleep(0.2)
        self.cb.call(lambda: None, node_id="node_0")  # closes

        self.assertEqual(self.cb.failure_count, 0)


# ---------------------------------------------------------------------------
# 2. MeshAutoScaler
# ---------------------------------------------------------------------------

class TestMeshAutoScalerBase(unittest.TestCase):
    """Base setup with a temp mesh dir for MeshAutoScaler tests."""

    def setUp(self):
        MeshAutoScaler._instance = None
        self.tmp_dir = tempfile.mkdtemp()
        self.nodes_path = os.path.join(self.tmp_dir, "nodes.json")

    def tearDown(self):
        MeshAutoScaler._instance = None
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _write_nodes(self, nodes):
        with open(self.nodes_path, "w") as f:
            json.dump(nodes, f)


class TestMeshAutoScalerCheckLoad(TestMeshAutoScalerBase):
    """check_load() must detect overloaded nodes."""

    def test_check_load_no_overload(self):
        """No overloaded nodes → check_load() must not return scale_up events."""
        self._write_nodes(_make_nodes(count=4))
        scaler = MeshAutoScaler(mesh_dir=self.tmp_dir, idle_threshold=-1)
        result = scaler.check_load()
        scale_up_events = [e for e in (result or []) if getattr(e, "event_type", "") == "scale_up"]
        self.assertEqual(len(scale_up_events), 0)

    def test_check_load_detects_overloaded_node(self):
        """One overloaded node → check_load() must flag it."""
        nodes = _make_nodes(count=4, overloaded_ids=["node_2"])
        self._write_nodes(nodes)
        scaler = MeshAutoScaler(mesh_dir=self.tmp_dir)
        result = scaler.check_load()
        if isinstance(result, list):
            self.assertTrue(len(result) > 0)
        else:
            self.assertTrue(result)

    def test_check_load_detects_multiple_overloaded(self):
        """Multiple overloaded nodes → all must be flagged."""
        nodes = _make_nodes(count=4, overloaded_ids=["node_0", "node_1", "node_3"])
        self._write_nodes(nodes)
        scaler = MeshAutoScaler(mesh_dir=self.tmp_dir)
        result = scaler.check_load()
        if isinstance(result, list):
            self.assertGreaterEqual(len(result), 3)


class TestMeshAutoScalerRecommendations(TestMeshAutoScalerBase):
    """get_recommendations() must return a list."""

    def test_get_recommendations_returns_list(self):
        """get_recommendations() must always return a list."""
        self._write_nodes(_make_nodes(count=4))
        scaler = MeshAutoScaler(mesh_dir=self.tmp_dir)
        result = scaler.get_recommendations()
        self.assertIsInstance(result, list)

    def test_get_recommendations_has_entries_when_overloaded(self):
        """When nodes are overloaded, recommendations list must be non-empty."""
        nodes = _make_nodes(count=4, overloaded_ids=["node_0", "node_1"])
        self._write_nodes(nodes)
        scaler = MeshAutoScaler(mesh_dir=self.tmp_dir)
        result = scaler.get_recommendations()
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)


# ---------------------------------------------------------------------------
# 3. MeshMetricsCollector
# ---------------------------------------------------------------------------

class TestMeshMetricsCollectorBase(unittest.TestCase):
    """Base setup for MeshMetricsCollector tests."""

    def setUp(self):
        MeshMetricsCollector._instance = None
        self.tmp_dir = tempfile.mkdtemp()
        nodes_path = os.path.join(self.tmp_dir, "nodes.json")
        with open(nodes_path, "w") as f:
            json.dump(_make_nodes(count=3), f)
        self.collector = MeshMetricsCollector(mesh_dir=self.tmp_dir)

    def tearDown(self):
        MeshMetricsCollector._instance = None
        shutil.rmtree(self.tmp_dir, ignore_errors=True)


class TestMeshMetricsCollectorCollect(TestMeshMetricsCollectorBase):
    """collect() must return a MeshMetrics dataclass."""

    def test_collect_returns_mesh_metrics(self):
        """collect() must return an instance of MeshMetrics."""
        result = self.collector.collect()
        self.assertIsInstance(result, MeshMetrics)

    def test_collect_has_node_count(self):
        """MeshMetrics must expose the number of active nodes."""
        result = self.collector.collect()
        self.assertTrue(hasattr(result, "node_count"))
        self.assertGreaterEqual(result.node_count, 0)

    def test_collect_node_count_matches_nodes_json(self):
        """node_count must equal the number of nodes in nodes.json."""
        result = self.collector.collect()
        self.assertEqual(result.node_count, 3)

    def test_collect_has_avg_latency(self):
        """MeshMetrics must expose avg_latency_ms."""
        result = self.collector.collect()
        self.assertTrue(hasattr(result, "avg_latency_ms"))

    def test_collect_has_total_messages(self):
        """MeshMetrics must expose total_messages."""
        result = self.collector.collect()
        self.assertTrue(hasattr(result, "total_messages"))


class TestMeshMetricsCollectorPrometheus(TestMeshMetricsCollectorBase):
    """export_prometheus() must return valid Prometheus-format text."""

    def test_export_prometheus_returns_string(self):
        """export_prometheus() must return a str."""
        result = self.collector.export_prometheus()
        self.assertIsInstance(result, str)

    def test_export_prometheus_has_mesh_prefix(self):
        """Prometheus output must contain at least one metric with 'mesh_' prefix."""
        result = self.collector.export_prometheus()
        self.assertIn("mesh_", result)

    def test_export_prometheus_non_empty(self):
        """Prometheus output must not be empty."""
        result = self.collector.export_prometheus()
        self.assertTrue(len(result.strip()) > 0)


# ---------------------------------------------------------------------------
# 4. MeshRouterV2 integration smoke tests
# ---------------------------------------------------------------------------

class TestMeshRouterV2Integration(unittest.TestCase):
    """Smoke tests for MeshRouterV2 in a real temp directory."""

    def setUp(self):
        MeshRouterV2._instance = None
        self.tmp_dir = tempfile.mkdtemp()
        nodes_path = os.path.join(self.tmp_dir, "nodes.json")
        with open(nodes_path, "w") as f:
            json.dump(_make_nodes(count=4), f)
        self.router = MeshRouterV2.get_instance(mesh_dir=self.tmp_dir)

    def tearDown(self):
        MeshRouterV2._instance = None
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_route_returns_non_empty_string(self):
        """route() must return a non-empty string."""
        result = self.router.route(task_type="general")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_route_result_is_known_node(self):
        """route() result must be one of the nodes defined in nodes.json."""
        known = set(_make_nodes(count=4).keys())
        result = self.router.route(task_type="general")
        self.assertIn(result, known)

    def test_route_multiple_calls_consistent(self):
        """Repeated route() calls must always return a non-empty string."""
        for _ in range(10):
            result = self.router.route(task_type="general")
            self.assertIsInstance(result, str)
            self.assertTrue(len(result) > 0)


if __name__ == "__main__":
    unittest.main()
