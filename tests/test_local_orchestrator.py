"""Tests for core.local_orchestrator — LocalOrchestrator zero-token routing."""
import json
import time
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestLocalOrchestratorSingleton(unittest.TestCase):
    def setUp(self):
        from core.local_orchestrator import LocalOrchestrator
        LocalOrchestrator.reset()

    def test_singleton_same_instance(self):
        from core.local_orchestrator import LocalOrchestrator
        a = LocalOrchestrator()
        b = LocalOrchestrator()
        self.assertIs(a, b)

    def test_instance_is_orchestrator(self):
        from core.local_orchestrator import LocalOrchestrator
        o = LocalOrchestrator()
        self.assertIsInstance(o, LocalOrchestrator)


class TestOrchestratorRouting(unittest.TestCase):
    def setUp(self):
        from core.local_orchestrator import LocalOrchestrator
        LocalOrchestrator.reset()
        self.orch = LocalOrchestrator()

    def test_route_code_task(self):
        model = self.orch.route("write a python function to sort a list")
        self.assertIn("coder", model.lower())

    def test_route_reasoning_task(self):
        model = self.orch.route("analyze the security architecture and design a plan")
        self.assertIsInstance(model, str)
        self.assertGreater(len(model), 0)

    def test_route_returns_string(self):
        model = self.orch.route("some task")
        self.assertIsInstance(model, str)

    def test_route_unknown_returns_default(self):
        model = self.orch.route("xyzzy frobble snorkel")
        from core.local_orchestrator import LOCAL_MODELS
        self.assertEqual(model, LOCAL_MODELS["default"])

    def test_route_task_type_detection_code(self):
        task_type = self.orch._route_task("implement a binary search tree")
        self.assertEqual(task_type, "code")

    def test_route_task_type_detection_reasoning(self):
        task_type = self.orch._route_task("analyze and evaluate the system design")
        self.assertEqual(task_type, "reasoning")

    def test_route_task_type_detection_fast(self):
        task_type = self.orch._route_task("classify this item quickly")
        self.assertEqual(task_type, "fast")

    def test_select_model_returns_string(self):
        model = self.orch._select_model("code")
        self.assertIsInstance(model, str)

    def test_select_model_unknown_returns_default(self):
        from core.local_orchestrator import LOCAL_MODELS
        model = self.orch._select_model("nonexistent_type")
        self.assertEqual(model, LOCAL_MODELS["default"])


class TestOrchestratorResultDataclass(unittest.TestCase):
    def test_creation(self):
        from core.local_orchestrator import OrchestratorResult
        r = OrchestratorResult(
            task_id="LOCAL-001",
            objective="test",
            model_used="qwen2.5-coder:14b",
            output="result text",
            success=True,
        )
        self.assertEqual(r.task_id, "LOCAL-001")
        self.assertTrue(r.success)

    def test_default_fields(self):
        from core.local_orchestrator import OrchestratorResult
        r = OrchestratorResult(
            task_id="t", objective="o", model_used="m", output="x"
        )
        self.assertEqual(r.subtasks, [])
        self.assertEqual(r.dispatched_nodes, [])
        self.assertEqual(r.error, "")
        self.assertGreater(r.timestamp, 0)

    def test_failure_result(self):
        from core.local_orchestrator import OrchestratorResult
        r = OrchestratorResult(
            task_id="t", objective="o", model_used="none", output="",
            success=False, error="No models available"
        )
        self.assertFalse(r.success)
        self.assertIn("No models", r.error)


class TestOrchestratorStats(unittest.TestCase):
    def setUp(self):
        from core.local_orchestrator import LocalOrchestrator
        LocalOrchestrator.reset()
        self.orch = LocalOrchestrator()

    def test_get_stats_returns_dict(self):
        stats = self.orch.get_stats()
        self.assertIsInstance(stats, dict)

    def test_get_stats_has_required_keys(self):
        stats = self.orch.get_stats()
        for key in ("tasks_run", "tasks_succeeded", "tasks_failed",
                    "success_rate", "avg_duration_ms", "models_used"):
            self.assertIn(key, stats)

    def test_initial_stats_zero(self):
        stats = self.orch.get_stats()
        self.assertEqual(stats["tasks_run"], 0)
        self.assertEqual(stats["success_rate"], 0.0)

    def test_update_stats_increments(self):
        self.orch._update_stats("test-model", 100.0, True)
        stats = self.orch.get_stats()
        self.assertEqual(stats["tasks_run"], 1)
        self.assertEqual(stats["tasks_succeeded"], 1)
        self.assertIn("test-model", stats["models_used"])

    def test_update_stats_failure(self):
        self.orch._update_stats("test-model", 50.0, False)
        stats = self.orch.get_stats()
        self.assertEqual(stats["tasks_failed"], 1)
        self.assertEqual(stats["tasks_succeeded"], 0)


class TestOrchestratorDecompose(unittest.TestCase):
    def setUp(self):
        from core.local_orchestrator import LocalOrchestrator
        LocalOrchestrator.reset()
        self.orch = LocalOrchestrator()

    def test_decompose_with_mock_ollama(self):
        with patch.object(self.orch, "_call_ollama",
                          return_value='["task1", "task2", "task3"]'):
            result = self.orch._decompose("build a complex system", "test-model")
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_decompose_empty_ollama_returns_list(self):
        with patch.object(self.orch, "_call_ollama", return_value=""):
            result = self.orch._decompose("anything", "test-model")
        self.assertIsInstance(result, list)

    def test_decompose_invalid_json_fallback(self):
        with patch.object(self.orch, "_call_ollama",
                          return_value="1. Do this task\n2. Do that task\n3. Final task"):
            result = self.orch._decompose("build something", "test-model")
        self.assertIsInstance(result, list)

    def test_decompose_max_5_subtasks(self):
        long_json = '["t1","t2","t3","t4","t5","t6","t7"]'
        with patch.object(self.orch, "_call_ollama", return_value=long_json):
            result = self.orch._decompose("big task", "test-model")
        self.assertLessEqual(len(result), 5)


class TestOrchestratorDispatch(unittest.TestCase):
    def setUp(self):
        from core.local_orchestrator import LocalOrchestrator
        LocalOrchestrator.reset()
        self.tmp = tempfile.mkdtemp()
        self.orch = LocalOrchestrator()
        self.orch._inbox_root = Path(self.tmp)

    def test_dispatch_creates_files(self):
        subtasks = ["task1", "task2"]
        dispatched = self.orch._dispatch_subtasks("TEST-001", subtasks)
        self.assertEqual(len(dispatched), 2)
        # Check that files were created
        files_created = list(Path(self.tmp).rglob("*.json"))
        self.assertGreaterEqual(len(files_created), 2)

    def test_dispatch_returns_node_names(self):
        dispatched = self.orch._dispatch_subtasks("TEST-002", ["subtask"])
        self.assertIsInstance(dispatched, list)
        self.assertGreater(len(dispatched), 0)

    def test_dispatch_file_content_valid_json(self):
        self.orch._dispatch_subtasks("TEST-003", ["do something important"])
        files = list(Path(self.tmp).rglob("*.json"))
        for f in files:
            data = json.loads(f.read_text())
            self.assertIn("msg_id", data)
            self.assertIn("msg_type", data)
            self.assertEqual(data["msg_type"], "subtask")


class TestOrchestratorRunWithMock(unittest.TestCase):
    def setUp(self):
        from core.local_orchestrator import LocalOrchestrator
        LocalOrchestrator.reset()
        self.orch = LocalOrchestrator()

    def test_run_no_models_returns_failure(self):
        with patch.object(self.orch, "get_available_models", return_value=[]):
            result = self.orch.run("build something")
        self.assertFalse(result.success)
        self.assertIn("No local models", result.error)

    def test_run_with_mock_ollama_success(self):
        with patch.object(self.orch, "get_available_models",
                          return_value=["qwen2.5-coder:14b"]):
            with patch.object(self.orch, "_call_ollama",
                              return_value="Here is the implementation"):
                result = self.orch.run("write a simple function", decompose=False)
        self.assertTrue(result.success)
        self.assertEqual(result.output, "Here is the implementation")

    def test_run_with_mock_empty_response_fails(self):
        with patch.object(self.orch, "get_available_models",
                          return_value=["qwen2.5-coder:14b"]):
            with patch.object(self.orch, "_call_ollama", return_value=""):
                result = self.orch.run("do something", decompose=False)
        self.assertFalse(result.success)

    def test_run_result_has_task_id(self):
        with patch.object(self.orch, "get_available_models",
                          return_value=["qwen2.5-coder:14b"]):
            with patch.object(self.orch, "_call_ollama", return_value="ok"):
                result = self.orch.run("test", decompose=False)
        self.assertTrue(result.task_id.startswith("LOCAL-"))

    def test_run_records_model_in_stats(self):
        with patch.object(self.orch, "get_available_models",
                          return_value=["qwen2.5-coder:14b"]):
            with patch.object(self.orch, "_call_ollama", return_value="done"):
                self.orch.run("implement something", decompose=False)
        stats = self.orch.get_stats()
        self.assertEqual(stats["tasks_run"], 1)

    def test_run_with_fallback_model(self):
        # preferred model not available, fallback to available
        with patch.object(self.orch, "get_available_models",
                          return_value=["qwen2.5-coder:14b"]):
            with patch.object(self.orch, "_call_ollama", return_value="fallback ok"):
                result = self.orch.run("reason about this complex problem",
                                       decompose=False)
        self.assertIsNotNone(result)


class TestLocalModelsDict(unittest.TestCase):
    def test_deepseek_is_reasoning_model(self):
        from core.local_orchestrator import LOCAL_MODELS
        self.assertIn("deepseek", LOCAL_MODELS["reasoning"])

    def test_qwen_coder_is_code_model(self):
        from core.local_orchestrator import LOCAL_MODELS
        self.assertIn("qwen", LOCAL_MODELS["code"])

    def test_all_required_keys_present(self):
        from core.local_orchestrator import LOCAL_MODELS
        for key in ("reasoning", "code", "orchestration", "fast", "default"):
            self.assertIn(key, LOCAL_MODELS)
