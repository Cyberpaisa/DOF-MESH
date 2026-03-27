"""
Tests para core/self_improvement.py — Motor de auto-mejora DOF.

Usa datos mock en tmpdir — NO lee logs reales.
"""

import json
import os
import shutil
import tempfile
import unittest

from core.self_improvement import (
    GovernanceAnalysis,
    ImprovementCycle,
    Lesson,
    MeshAnalysis,
    SelfImprover,
    TestAnalysis,
)


class TestGovernanceAnalysis(unittest.TestCase):
    """Tests para analyze_governance_logs."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.improver = SelfImprover(improvement_dir=os.path.join(self.tmpdir, "improvement"))

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_governance_analysis_empty(self):
        """Sin logs, retorna zeros."""
        result = self.improver.analyze_governance_logs(
            os.path.join(self.tmpdir, "nonexistent.jsonl")
        )
        self.assertIsInstance(result, GovernanceAnalysis)
        self.assertEqual(result.total_decisions, 0)
        self.assertEqual(result.pass_count, 0)
        self.assertEqual(result.fail_count, 0)
        self.assertEqual(result.pass_rate, 0.0)
        self.assertEqual(result.fail_rate, 0.0)
        self.assertEqual(result.top_failing_rules, [])
        self.assertEqual(result.trend, "unknown")

    def test_governance_analysis_with_data(self):
        """Con datos mock, calcula correctamente."""
        log_path = os.path.join(self.tmpdir, "gov.jsonl")
        entries = [
            {"verdict": "PASS", "rule": "NO_HALLUCINATION_CLAIM"},
            {"verdict": "PASS", "rule": "LANGUAGE_COMPLIANCE"},
            {"verdict": "FAIL", "rule": "NO_EMPTY_OUTPUT"},
            {"verdict": "PASS", "rule": "MAX_LENGTH"},
            {"verdict": "FAIL", "rule": "NO_EMPTY_OUTPUT"},
            {"verdict": "PASS", "rule": "NO_HALLUCINATION_CLAIM"},
            {"verdict": "FAIL", "rule": "LANGUAGE_COMPLIANCE"},
            {"verdict": "PASS", "rule": "MAX_LENGTH"},
            {"verdict": "PASS", "rule": "NO_HALLUCINATION_CLAIM"},
            {"verdict": "PASS", "rule": "MAX_LENGTH"},
        ]
        with open(log_path, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

        result = self.improver.analyze_governance_logs(log_path)
        self.assertEqual(result.total_decisions, 10)
        self.assertEqual(result.pass_count, 7)
        self.assertEqual(result.fail_count, 3)
        self.assertAlmostEqual(result.pass_rate, 70.0)
        self.assertAlmostEqual(result.fail_rate, 30.0)
        # NO_EMPTY_OUTPUT falla 2 veces, LANGUAGE_COMPLIANCE 1 vez
        self.assertEqual(result.top_failing_rules[0][0], "NO_EMPTY_OUTPUT")
        self.assertEqual(result.top_failing_rules[0][1], 2)

    def test_governance_trend_improving(self):
        """Trend mejorando cuando segunda mitad tiene menos fallos."""
        log_path = os.path.join(self.tmpdir, "gov_trend.jsonl")
        # Primera mitad: 4 FAIL de 5
        # Segunda mitad: 1 FAIL de 5
        entries = (
            [{"verdict": "FAIL", "rule": "R1"}] * 4
            + [{"verdict": "PASS", "rule": "R1"}]
            + [{"verdict": "PASS", "rule": "R1"}] * 4
            + [{"verdict": "FAIL", "rule": "R1"}]
        )
        with open(log_path, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

        result = self.improver.analyze_governance_logs(log_path)
        self.assertEqual(result.trend, "improving")

    def test_governance_trend_worsening(self):
        """Trend empeorando cuando segunda mitad tiene más fallos."""
        log_path = os.path.join(self.tmpdir, "gov_bad.jsonl")
        entries = (
            [{"verdict": "PASS", "rule": "R1"}] * 4
            + [{"verdict": "FAIL", "rule": "R1"}]
            + [{"verdict": "FAIL", "rule": "R1"}] * 4
            + [{"verdict": "PASS", "rule": "R1"}]
        )
        with open(log_path, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

        result = self.improver.analyze_governance_logs(log_path)
        self.assertEqual(result.trend, "worsening")


class TestMeshAnalysis(unittest.TestCase):
    """Tests para analyze_mesh_performance."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.improver = SelfImprover(improvement_dir=os.path.join(self.tmpdir, "improvement"))

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_mesh_analysis_with_data(self):
        """Con orchestrator data mock, calcula métricas correctamente."""
        log_path = os.path.join(self.tmpdir, "orch.jsonl")
        entries = [
            {"selected_node": "groq", "latency_ms": 100.0, "success": True, "circuit_state": "CLOSED"},
            {"selected_node": "groq", "latency_ms": 150.0, "success": True, "circuit_state": "CLOSED"},
            {"selected_node": "nvidia", "latency_ms": 500.0, "success": True, "circuit_state": "CLOSED"},
            {"selected_node": "nvidia", "latency_ms": 600.0, "success": False, "circuit_state": "OPEN"},
            {"selected_node": "cerebras", "latency_ms": 200.0, "success": True, "circuit_state": "CLOSED"},
        ]
        with open(log_path, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

        result = self.improver.analyze_mesh_performance(log_path)
        self.assertEqual(result.total_events, 5)
        self.assertAlmostEqual(result.avg_latency_by_node["groq"], 125.0)
        self.assertAlmostEqual(result.avg_latency_by_node["nvidia"], 550.0)
        self.assertAlmostEqual(result.success_rate_by_node["groq"], 100.0)
        self.assertAlmostEqual(result.success_rate_by_node["nvidia"], 50.0)
        self.assertIn("nvidia", result.circuit_breaker_open_nodes)
        self.assertTrue(result.most_efficient_node != "")

    def test_mesh_analysis_empty(self):
        """Sin archivo, retorna vacío."""
        result = self.improver.analyze_mesh_performance(
            os.path.join(self.tmpdir, "nope.jsonl")
        )
        self.assertEqual(result.total_events, 0)
        self.assertEqual(result.avg_latency_by_node, {})


class TestTestAnalysis(unittest.TestCase):
    """Tests para analyze_test_results."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.improver = SelfImprover(improvement_dir=os.path.join(self.tmpdir, "improvement"))

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_test_analysis_parse(self):
        """Parsea output de unittest correctamente."""
        output = """test_a (tests.test_governance) ... ok
test_b (tests.test_governance) ... ok
test_c (tests.test_supervisor) ... FAIL
test_d (tests.test_z3) ... ERROR

======================================================================
FAIL: test_c (tests.test_supervisor)
----------------------------------------------------------------------
Traceback (most recent call last):
  ...
AssertionError: ...

======================================================================
ERROR: test_d (tests.test_z3)
----------------------------------------------------------------------
Traceback (most recent call last):
  ...

----------------------------------------------------------------------
Ran 4 tests in 0.5s

FAILED (failures=1, errors=1)"""

        result = self.improver.analyze_test_results(output)
        self.assertEqual(result.total, 4)
        self.assertEqual(result.passed, 2)
        self.assertEqual(result.failed, 1)
        self.assertEqual(result.errors, 1)

    def test_test_analysis_all_pass(self):
        """Output sin fallos."""
        output = """test_a ... ok
test_b ... ok
test_c ... ok

----------------------------------------------------------------------
Ran 3 tests in 0.1s

OK"""
        result = self.improver.analyze_test_results(output)
        self.assertEqual(result.total, 3)
        self.assertEqual(result.passed, 3)
        self.assertEqual(result.failed, 0)
        self.assertEqual(result.errors, 0)

    def test_test_analysis_empty(self):
        """Output vacío retorna zeros."""
        result = self.improver.analyze_test_results("")
        self.assertEqual(result.total, 0)
        self.assertEqual(result.passed, 0)

    def test_test_analysis_with_skipped(self):
        """Parsea tests saltados."""
        output = """----------------------------------------------------------------------
Ran 10 tests in 1.2s

FAILED (failures=2, errors=1, skipped=3)"""
        result = self.improver.analyze_test_results(output)
        self.assertEqual(result.total, 10)
        self.assertEqual(result.skipped, 3)
        self.assertEqual(result.failed, 2)
        self.assertEqual(result.errors, 1)
        self.assertEqual(result.passed, 4)  # 10 - 2 - 1 - 3


class TestExtractLessons(unittest.TestCase):
    """Tests para extract_lessons."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.improver = SelfImprover(improvement_dir=os.path.join(self.tmpdir, "improvement"))

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_extract_lessons_high_fail_rate(self):
        """>10% fail genera lesson de governance."""
        gov = GovernanceAnalysis(
            total_decisions=100,
            pass_count=80,
            fail_count=20,
            pass_rate=80.0,
            fail_rate=20.0,
            top_failing_rules=[("NO_EMPTY_OUTPUT", 12), ("LANGUAGE_COMPLIANCE", 8)],
            trend="stable",
        )
        mesh = MeshAnalysis()
        tests = TestAnalysis()

        lessons = self.improver.extract_lessons(gov, mesh, tests)
        gov_lessons = [l for l in lessons if l.category == "governance"]
        self.assertTrue(len(gov_lessons) >= 1)
        self.assertEqual(gov_lessons[0].severity, "high")
        self.assertIn("20.0%", gov_lessons[0].finding)

    def test_extract_lessons_slow_latency(self):
        """>2000ms genera lesson de performance."""
        gov = GovernanceAnalysis()
        mesh = MeshAnalysis(
            total_events=50,
            overall_avg_latency=3500.0,
            avg_latency_by_node={"slow-node": 5000.0, "ok-node": 2000.0},
            success_rate_by_node={"slow-node": 80.0, "ok-node": 95.0},
        )
        tests = TestAnalysis()

        lessons = self.improver.extract_lessons(gov, mesh, tests)
        perf_lessons = [l for l in lessons if l.category == "performance"]
        self.assertTrue(len(perf_lessons) >= 1)
        self.assertEqual(perf_lessons[0].severity, "high")
        self.assertIn("3500", perf_lessons[0].finding)

    def test_extract_lessons_positive_trend(self):
        """Mejora en governance genera lesson positiva."""
        gov = GovernanceAnalysis(
            total_decisions=100,
            pass_count=95,
            fail_count=5,
            pass_rate=95.0,
            fail_rate=5.0,
            trend="improving",
            first_half_fail_rate=10.0,
            second_half_fail_rate=2.0,
        )
        mesh = MeshAnalysis()
        tests = TestAnalysis()

        lessons = self.improver.extract_lessons(gov, mesh, tests)
        positive = [l for l in lessons if "positivo" in l.finding.lower() or "mantener" in l.recommendation.lower()]
        self.assertTrue(len(positive) >= 1)
        self.assertEqual(positive[0].severity, "low")

    def test_extract_lessons_no_issues(self):
        """Sistema sano genera pocas o cero lessons."""
        gov = GovernanceAnalysis(
            total_decisions=100,
            pass_count=98,
            fail_count=2,
            pass_rate=98.0,
            fail_rate=2.0,
            trend="stable",
        )
        mesh = MeshAnalysis(
            total_events=50,
            overall_avg_latency=500.0,
            avg_latency_by_node={"node-a": 500.0},
            success_rate_by_node={"node-a": 99.0},
        )
        tests = TestAnalysis(total=100, passed=100, failed=0, errors=0, trend="stable")

        lessons = self.improver.extract_lessons(gov, mesh, tests)
        # No debería haber lessons de alta severidad
        high = [l for l in lessons if l.severity == "high"]
        self.assertEqual(len(high), 0)

    def test_extract_lessons_circuit_breaker(self):
        """Nodo con circuit breaker OPEN genera lesson."""
        gov = GovernanceAnalysis()
        mesh = MeshAnalysis(
            total_events=10,
            circuit_breaker_open_nodes=["broken-node"],
        )
        tests = TestAnalysis()

        lessons = self.improver.extract_lessons(gov, mesh, tests)
        cb_lessons = [l for l in lessons if "circuit breaker" in l.finding.lower()]
        self.assertTrue(len(cb_lessons) >= 1)
        self.assertEqual(cb_lessons[0].severity, "high")

    def test_lesson_structure(self):
        """Lesson tiene todos los campos requeridos."""
        lesson = Lesson(
            id="L-001",
            category="governance",
            finding="Test finding",
            recommendation="Test recommendation",
            severity="medium",
            timestamp="2026-03-27T00:00:00+00:00",
        )
        d = lesson.to_dict()
        required_fields = ["id", "category", "finding", "recommendation", "severity", "timestamp"]
        for field_name in required_fields:
            self.assertIn(field_name, d)
            self.assertNotEqual(d[field_name], "")


class TestImprovementCycle(unittest.TestCase):
    """Tests para run_improvement_cycle y storage."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.improvement_dir = os.path.join(self.tmpdir, "improvement")
        self.improver = SelfImprover(improvement_dir=self.improvement_dir)

        # Crear logs mock
        self.gov_path = os.path.join(self.tmpdir, "gov.jsonl")
        self.mesh_path = os.path.join(self.tmpdir, "orch.jsonl")

        with open(self.gov_path, "w") as f:
            for i in range(20):
                verdict = "PASS" if i % 3 != 0 else "FAIL"
                f.write(json.dumps({"verdict": verdict, "rule": f"RULE_{i % 4}"}) + "\n")

        with open(self.mesh_path, "w") as f:
            for i in range(10):
                f.write(json.dumps({
                    "selected_node": f"node-{i % 3}",
                    "latency_ms": 100.0 + i * 50,
                    "success": i != 7,
                    "circuit_state": "OPEN" if i == 7 else "CLOSED",
                }) + "\n")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_improvement_cycle(self):
        """Ciclo completo funciona y retorna ImprovementCycle."""
        test_output = "Ran 50 tests in 2.0s\n\nFAILED (failures=3, errors=1)"

        cycle = self.improver.run_improvement_cycle(
            cycle_id="test-001",
            governance_log=self.gov_path,
            mesh_log=self.mesh_path,
            test_output=test_output,
        )

        self.assertIsInstance(cycle, ImprovementCycle)
        self.assertEqual(cycle.cycle_id, "test-001")
        self.assertIsNotNone(cycle.governance)
        self.assertIsNotNone(cycle.mesh)
        self.assertIsNotNone(cycle.tests)
        self.assertTrue(cycle.timestamp != "")
        self.assertEqual(cycle.recommendations_count, len(cycle.lessons))

    def test_cycle_storage(self):
        """Ciclo se guarda en JSONL."""
        self.improver.run_improvement_cycle(
            cycle_id="store-001",
            governance_log=self.gov_path,
            mesh_log=self.mesh_path,
        )

        # Verificar cycles.jsonl
        cycles_file = os.path.join(self.improvement_dir, "cycles.jsonl")
        self.assertTrue(os.path.exists(cycles_file))

        with open(cycles_file) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)

        data = json.loads(lines[0])
        self.assertEqual(data["cycle_id"], "store-001")

    def test_get_improvement_history(self):
        """Historia retorna ciclos previos."""
        self.improver.run_improvement_cycle(
            cycle_id="hist-001",
            governance_log=self.gov_path,
            mesh_log=self.mesh_path,
        )
        self.improver.run_improvement_cycle(
            cycle_id="hist-002",
            governance_log=self.gov_path,
            mesh_log=self.mesh_path,
        )

        history = self.improver.get_improvement_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["cycle_id"], "hist-001")
        self.assertEqual(history[1]["cycle_id"], "hist-002")

    def test_compare_cycles(self):
        """Comparar dos ciclos retorna delta."""
        self.improver.run_improvement_cycle(
            cycle_id="cmp-001",
            governance_log=self.gov_path,
            mesh_log=self.mesh_path,
            test_output="Ran 50 tests in 1.0s\n\nOK",
        )
        self.improver.run_improvement_cycle(
            cycle_id="cmp-002",
            governance_log=self.gov_path,
            mesh_log=self.mesh_path,
            test_output="Ran 55 tests in 1.2s\n\nOK",
        )

        comparison = self.improver.compare_cycles("cmp-001", "cmp-002")
        self.assertIn("governance_delta", comparison)
        self.assertIn("mesh_delta", comparison)
        self.assertIn("tests_delta", comparison)
        self.assertIn("verdict", comparison)
        self.assertIn(comparison["verdict"], ("IMPROVED", "REGRESSED", "STABLE"))

    def test_compare_cycles_not_found(self):
        """Comparar ciclos inexistentes retorna error."""
        result = self.improver.compare_cycles("nope-1", "nope-2")
        self.assertIn("error", result)

    def test_cycle_auto_id(self):
        """Ciclo sin ID genera uno automáticamente."""
        cycle = self.improver.run_improvement_cycle(
            governance_log=self.gov_path,
            mesh_log=self.mesh_path,
        )
        self.assertTrue(len(cycle.cycle_id) > 0)


if __name__ == "__main__":
    unittest.main()
