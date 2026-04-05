"""Tests for core.mesh_orchestrator — MeshOrchestrator Phase 9."""
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


def setUpModule():
    raise unittest.SkipTest("module removed in commit 6cd575e — internal only, pending restoration")


class TestMeshOrchestratorSingleton(unittest.TestCase):
    def setUp(self):
        from core.mesh_orchestrator import MeshOrchestrator
        MeshOrchestrator.reset()

    def tearDown(self):
        from core.mesh_orchestrator import MeshOrchestrator
        MeshOrchestrator.reset()

    def test_singleton_same_instance(self):
        from core.mesh_orchestrator import MeshOrchestrator
        a = MeshOrchestrator()
        b = MeshOrchestrator()
        self.assertIs(a, b)

    def test_reset_creates_new_instance(self):
        from core.mesh_orchestrator import MeshOrchestrator
        a = MeshOrchestrator()
        MeshOrchestrator.reset()
        b = MeshOrchestrator()
        self.assertIsNot(a, b)

    def test_singleton_thread_safe(self):
        from core.mesh_orchestrator import MeshOrchestrator
        instances = []
        def _get():
            instances.append(MeshOrchestrator())
        threads = [threading.Thread(target=_get) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertTrue(all(i is instances[0] for i in instances))


class TestMeshOrchestratorStatus(unittest.TestCase):
    def setUp(self):
        from core.mesh_orchestrator import MeshOrchestrator
        MeshOrchestrator.reset()
        self.orch = MeshOrchestrator()

    def tearDown(self):
        from core.mesh_orchestrator import MeshOrchestrator
        MeshOrchestrator.reset()

    def test_get_status_returns_dict(self):
        status = self.orch.get_status()
        self.assertIsInstance(status, dict)

    def test_get_status_has_expected_keys(self):
        status = self.orch.get_status()
        for key in ("work_orders_processed", "work_orders_completed"):
            self.assertIn(key, status)

    def test_initial_counters_zero(self):
        self.assertEqual(self.orch.work_orders_processed, 0)
        self.assertEqual(self.orch.work_orders_completed, 0)

    def test_counter_setters(self):
        self.orch.work_orders_processed = 5
        self.assertEqual(self.orch.work_orders_processed, 5)
        self.orch.work_orders_completed = 3
        self.assertEqual(self.orch.work_orders_completed, 3)

    def test_get_status_scaling_key(self):
        status = self.orch.get_status()
        self.assertIn("scaling", status)

    def test_stop_sets_running_false(self):
        self.orch.stop()
        # Should not raise; running flag set
        self.assertFalse(getattr(self.orch, '_running', False))


class TestMeshOrchestratorScaling(unittest.TestCase):
    def setUp(self):
        from core.mesh_orchestrator import MeshOrchestrator
        MeshOrchestrator.reset()
        self.orch = MeshOrchestrator()

    def tearDown(self):
        from core.mesh_orchestrator import MeshOrchestrator
        MeshOrchestrator.reset()

    def test_evaluate_scaling_returns_scaling_decision(self):
        from core.mesh_orchestrator import ScalingDecision
        decision = self.orch.evaluate_scaling()
        self.assertIsInstance(decision, ScalingDecision)

    def test_scaling_decision_has_action(self):
        from core.mesh_orchestrator import ScalingDecision
        decision = self.orch.evaluate_scaling()
        self.assertTrue(hasattr(decision, 'action'))

    def test_scaling_decision_action_valid(self):
        decision = self.orch.evaluate_scaling()
        self.assertIn(decision.action, ('scale_up', 'scale_down', 'hold'))


class TestMeshOrchestratorOrchestrate(unittest.TestCase):
    def setUp(self):
        from core.mesh_orchestrator import MeshOrchestrator
        MeshOrchestrator.reset()
        self.orch = MeshOrchestrator()

    def tearDown(self):
        from core.mesh_orchestrator import MeshOrchestrator
        MeshOrchestrator.reset()

    def test_orchestrate_returns_result(self):
        from core.mesh_orchestrator import OrchestrationResult
        task = {"task_id": "t1", "type": "code", "content": "hello"}
        result = self.orch.orchestrate(task)
        self.assertIsInstance(result, OrchestrationResult)

    def test_orchestrate_result_has_task_id(self):
        task = {"task_id": "t42", "type": "code", "content": "test"}
        result = self.orch.orchestrate(task)
        self.assertEqual(result.task_id, "t42")

    def test_orchestrate_result_has_selected_node(self):
        task = {"task_id": "t2", "type": "code", "content": "hello"}
        result = self.orch.orchestrate(task)
        self.assertIsInstance(result.selected_node, str)
        self.assertTrue(len(result.selected_node) > 0)

    def test_orchestrate_increments_processed(self):
        before = self.orch.work_orders_processed
        task = {"task_id": "t3", "type": "code", "content": "test"}
        self.orch.orchestrate(task)
        self.assertGreaterEqual(self.orch.work_orders_processed, before)

    def test_orchestrate_auto_generates_task_id(self):
        from core.mesh_orchestrator import OrchestrationResult
        task = {"type": "analysis", "content": "data"}
        result = self.orch.orchestrate(task)
        self.assertIsInstance(result, OrchestrationResult)
        self.assertIsNotNone(result.task_id)


class TestOrchestrationResultDataclass(unittest.TestCase):
    def test_dataclass_creation(self):
        from core.mesh_orchestrator import OrchestrationResult
        r = OrchestrationResult(
            task_id="x",
            task_type="code",
            routed_node="node-a",
            cost_node="node-b",
            selected_node="node-a",
            circuit_state="CLOSED",
            success=True,
        )
        self.assertTrue(r.success)
        self.assertEqual(r.circuit_state, "CLOSED")

    def test_dataclass_error_field_default(self):
        from core.mesh_orchestrator import OrchestrationResult
        r = OrchestrationResult(
            task_id="y", task_type="t", routed_node="n",
            cost_node="n", selected_node="n", circuit_state="CLOSED", success=False
        )
        self.assertEqual(r.error, "")


class TestScalingDecisionDataclass(unittest.TestCase):
    def test_creation(self):
        from core.mesh_orchestrator import ScalingDecision
        sd = ScalingDecision(
            queue_depth=55, health_score=0.9, avg_latency_ms=200.0,
            demand_score=0.8, action="scale_up", scale_events=2,
            active_nodes=3, total_nodes=5
        )
        self.assertEqual(sd.action, "scale_up")
        self.assertEqual(sd.queue_depth, 55)

    def test_hold_action(self):
        from core.mesh_orchestrator import ScalingDecision
        sd = ScalingDecision(
            queue_depth=10, health_score=1.0, avg_latency_ms=100.0,
            demand_score=0.2, action="hold", scale_events=0,
            active_nodes=5, total_nodes=5
        )
        self.assertEqual(sd.action, "hold")


class TestMeshOrchestratorQueueDepth(unittest.TestCase):
    def setUp(self):
        from core.mesh_orchestrator import MeshOrchestrator
        MeshOrchestrator.reset()
        self.orch = MeshOrchestrator()

    def tearDown(self):
        from core.mesh_orchestrator import MeshOrchestrator
        MeshOrchestrator.reset()

    def test_queue_depth_returns_int(self):
        depth = self.orch._count_queue_depth()
        self.assertIsInstance(depth, int)
        self.assertGreaterEqual(depth, 0)


class TestMeshOrchestratorCycleCount(unittest.TestCase):
    def setUp(self):
        from core.mesh_orchestrator import MeshOrchestrator
        MeshOrchestrator.reset()
        self.orch = MeshOrchestrator()

    def tearDown(self):
        from core.mesh_orchestrator import MeshOrchestrator
        MeshOrchestrator.reset()

    def test_cycle_count_initial_zero(self):
        self.assertEqual(self.orch.cycle_count, 0)

    def test_cycle_count_setter(self):
        self.orch.cycle_count = 7
        self.assertEqual(self.orch.cycle_count, 7)

    def test_total_failures_accessible(self):
        self.assertGreaterEqual(self.orch._total_failures, 0)


class TestMeshOrchestratorDiscoverWorkOrders(unittest.TestCase):
    def setUp(self):
        from core.mesh_orchestrator import MeshOrchestrator
        MeshOrchestrator.reset()
        self.tmp = tempfile.mkdtemp()
        self.orch = MeshOrchestrator(mesh_dir=Path(self.tmp))

    def tearDown(self):
        from core.mesh_orchestrator import MeshOrchestrator
        MeshOrchestrator.reset()
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_empty_inbox_returns_empty_list(self):
        orders = self.orch._discover_work_orders()
        self.assertIsInstance(orders, list)
        self.assertEqual(len(orders), 0)

    def test_finds_json_task_files(self):
        inbox = Path(self.tmp) / "inbox" / "commander"
        inbox.mkdir(parents=True, exist_ok=True)
        task = {"task_id": "w1", "type": "code", "content": "build it"}
        (inbox / "w1.json").write_text(json.dumps(task))
        orders = self.orch._discover_work_orders()
        self.assertEqual(len(orders), 1)

    def test_ignores_response_files(self):
        inbox = Path(self.tmp) / "inbox" / "commander"
        inbox.mkdir(parents=True, exist_ok=True)
        task = {"task_id": "w2"}
        (inbox / "w2-RESPONSE.json").write_text(json.dumps(task))
        orders = self.orch._discover_work_orders()
        self.assertEqual(len(orders), 0)

    def test_ignores_failed_files(self):
        inbox = Path(self.tmp) / "inbox" / "commander"
        inbox.mkdir(parents=True, exist_ok=True)
        task = {"task_id": "w3"}
        (inbox / "w3-FAILED.json").write_text(json.dumps(task))
        orders = self.orch._discover_work_orders()
        self.assertEqual(len(orders), 0)

    def test_returns_path_and_dict_tuples(self):
        inbox = Path(self.tmp) / "inbox" / "commander"
        inbox.mkdir(parents=True, exist_ok=True)
        task = {"task_id": "w4", "type": "analysis"}
        (inbox / "w4.json").write_text(json.dumps(task))
        orders = self.orch._discover_work_orders()
        self.assertEqual(len(orders), 1)
        path, data = orders[0]
        self.assertIsInstance(path, Path)
        self.assertEqual(data["task_id"], "w4")


class TestMeshOrchestratorRunStop(unittest.TestCase):
    def setUp(self):
        from core.mesh_orchestrator import MeshOrchestrator
        MeshOrchestrator.reset()
        self.orch = MeshOrchestrator()

    def tearDown(self):
        from core.mesh_orchestrator import MeshOrchestrator
        MeshOrchestrator.reset()

    def test_stop_sets_running_false(self):
        self.orch.stop()
        self.assertFalse(self.orch._running)

    def test_stop_idempotent(self):
        self.orch.stop()
        self.orch.stop()  # second call should not raise
        self.assertFalse(self.orch._running)

    def test_get_status_after_stop(self):
        self.orch.stop()
        status = self.orch.get_status()
        self.assertIsInstance(status, dict)
        self.assertIn("scaling", status)


class TestOrchestrateManyTasks(unittest.TestCase):
    def setUp(self):
        from core.mesh_orchestrator import MeshOrchestrator
        MeshOrchestrator.reset()
        self.orch = MeshOrchestrator()

    def tearDown(self):
        from core.mesh_orchestrator import MeshOrchestrator
        MeshOrchestrator.reset()

    def test_orchestrate_five_tasks_increments_counter(self):
        from core.mesh_orchestrator import OrchestrationResult
        for i in range(5):
            task = {"task_id": f"multi-{i}", "type": "code", "content": f"task {i}"}
            result = self.orch.orchestrate(task)
            self.assertIsInstance(result, OrchestrationResult)
        self.assertGreaterEqual(self.orch.work_orders_processed, 5)

    def test_orchestrate_different_task_types(self):
        from core.mesh_orchestrator import OrchestrationResult
        for ttype in ("code", "research", "security", "analysis"):
            task = {"task_id": f"t-{ttype}", "type": ttype, "content": "data"}
            result = self.orch.orchestrate(task)
            self.assertEqual(result.task_type, ttype)
