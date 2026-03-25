"""
Tests for MetaSupervisor.orchestrate_swarm() in core.supervisor.
Uses only stdlib: unittest.
"""
import os
import sys
import unittest

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.supervisor import MetaSupervisor

_VALID_DECISIONS = {"ACCEPT", "RETRY", "ESCALATE"}


class TestOrchestrateSwarmReturnShape(unittest.TestCase):
    """orchestrate_swarm() return value structure."""

    @classmethod
    def setUpClass(cls):
        cls.supervisor = MetaSupervisor()
        cls.result = cls.supervisor.orchestrate_swarm("build feature X")

    def test_returns_dict(self):
        self.assertIsInstance(self.result, dict)

    def test_has_key_objective(self):
        self.assertIn("objective", self.result)

    def test_has_key_subtasks(self):
        self.assertIn("subtasks", self.result)

    def test_has_key_results(self):
        self.assertIn("results", self.result)

    def test_has_key_verdict(self):
        self.assertIn("verdict", self.result)

    def test_has_key_integrated_output(self):
        self.assertIn("integrated_output", self.result)


class TestOrchestrateSwarmSubtasks(unittest.TestCase):
    """subtasks dict contains exactly the 6 expected agent roles."""

    @classmethod
    def setUpClass(cls):
        cls.supervisor = MetaSupervisor()
        cls.result = cls.supervisor.orchestrate_swarm("build feature X")
        cls.subtasks = cls.result["subtasks"]

    def test_subtasks_has_six_keys(self):
        self.assertEqual(len(self.subtasks), 6)

    def test_subtasks_has_architect(self):
        self.assertIn("architect", self.subtasks)

    def test_subtasks_has_researcher(self):
        self.assertIn("researcher", self.subtasks)

    def test_subtasks_has_guardian(self):
        self.assertIn("guardian", self.subtasks)

    def test_subtasks_has_verifier(self):
        self.assertIn("verifier", self.subtasks)

    def test_subtasks_has_narrator(self):
        self.assertIn("narrator", self.subtasks)

    def test_subtasks_has_devops(self):
        self.assertIn("devops", self.subtasks)

    def test_subtask_values_are_strings(self):
        for role, task in self.subtasks.items():
            with self.subTest(role=role):
                self.assertIsInstance(task, str)

    def test_subtask_values_contain_objective(self):
        objective = self.result["objective"]
        for role, task in self.subtasks.items():
            with self.subTest(role=role):
                self.assertIn(objective, task)


class TestOrchestrateSwarmVerdict(unittest.TestCase):
    """verdict dict structure and valid decision values."""

    @classmethod
    def setUpClass(cls):
        cls.supervisor = MetaSupervisor()
        cls.result = cls.supervisor.orchestrate_swarm("build feature X")
        cls.verdict = cls.result["verdict"]

    def test_verdict_has_key_decision(self):
        self.assertIn("decision", self.verdict)

    def test_verdict_has_key_score(self):
        self.assertIn("score", self.verdict)

    def test_verdict_decision_valid_value(self):
        self.assertIn(self.verdict["decision"], _VALID_DECISIONS)

    def test_verdict_score_is_numeric(self):
        self.assertIsInstance(self.verdict["score"], (int, float))

    def test_verdict_score_in_range(self):
        self.assertGreaterEqual(self.verdict["score"], 0.0)
        self.assertLessEqual(self.verdict["score"], 10.0)


class TestOrchestrateSwarmIntegratedOutput(unittest.TestCase):
    """integrated_output is a non-empty string that references the objective."""

    @classmethod
    def setUpClass(cls):
        cls.supervisor = MetaSupervisor()
        cls.objective = "build feature X"
        cls.result = cls.supervisor.orchestrate_swarm(cls.objective)

    def test_integrated_output_is_string(self):
        self.assertIsInstance(self.result["integrated_output"], str)

    def test_integrated_output_is_non_empty(self):
        self.assertTrue(len(self.result["integrated_output"]) > 0)

    def test_integrated_output_contains_objective(self):
        self.assertIn(self.objective, self.result["integrated_output"])


class TestOrchestrateSwarmObjectiveField(unittest.TestCase):
    """objective field echoes back the input exactly."""

    def setUp(self):
        self.supervisor = MetaSupervisor()

    def test_objective_echoed_back(self):
        obj = "deploy zero-trust mesh encryption layer"
        result = self.supervisor.orchestrate_swarm(obj)
        self.assertEqual(result["objective"], obj)


class TestOrchestrateSwarmEdgeCases(unittest.TestCase):
    """Edge cases: empty string and very long objective."""

    def setUp(self):
        self.supervisor = MetaSupervisor()

    def test_empty_string_objective_does_not_raise(self):
        try:
            result = self.supervisor.orchestrate_swarm("")
            self.assertIsInstance(result, dict)
        except Exception as exc:
            self.fail(f"orchestrate_swarm('') raised unexpectedly: {exc}")

    def test_empty_string_returns_valid_decision(self):
        result = self.supervisor.orchestrate_swarm("")
        self.assertIn(result["verdict"]["decision"], _VALID_DECISIONS)

    def test_long_objective_does_not_raise(self):
        long_obj = "implement secure autonomous governance layer " * 23  # ~1000 chars
        try:
            result = self.supervisor.orchestrate_swarm(long_obj)
            self.assertIsInstance(result, dict)
        except Exception as exc:
            self.fail(f"orchestrate_swarm(long) raised unexpectedly: {exc}")

    def test_long_objective_returns_valid_decision(self):
        long_obj = "build and deploy distributed mesh node " * 26
        result = self.supervisor.orchestrate_swarm(long_obj)
        self.assertIn(result["verdict"]["decision"], _VALID_DECISIONS)


if __name__ == "__main__":
    unittest.main()
