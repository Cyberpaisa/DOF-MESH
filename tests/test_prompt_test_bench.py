"""
Tests para PromptTestBench — batch testing de prompts con datasets JSONL.

Usa unittest (NO pytest). Solo stdlib.
"""

import csv
import json
import os
import shutil
import tempfile
import unittest
from dataclasses import asdict

from core.prompt_test_bench import (
    BenchReport,
    PromptTestBench,
    TestCase,
    TestResult,
)


class TestPromptTestBenchBase(unittest.TestCase):
    """Base con setUp/tearDown para tests de PromptTestBench."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="ptb_test_")
        self.datasets_dir = os.path.join(self.tmpdir, "datasets")
        self.results_file = os.path.join(self.tmpdir, "bench_results.jsonl")
        self.bench = PromptTestBench(
            datasets_dir=self.datasets_dir,
            results_file=self.results_file,
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_cases(self, n=3):
        """Crea N test cases de ejemplo."""
        return [
            TestCase(
                id=f"tc_{i}",
                input_vars={"name": f"Agent_{i}", "score": str(i * 10)},
                expected_output=f"Agent_{i} tiene score {i * 10}",
                expected_verdict="pass",
                tags=["basic"],
                metadata={"source": "test"},
            )
            for i in range(n)
        ]


class TestCreateLoadDataset(TestPromptTestBenchBase):
    """Tests para crear y cargar datasets."""

    def test_create_dataset_returns_name(self):
        cases = self._make_cases(2)
        ds_id = self.bench.create_dataset("mi_dataset", cases)
        self.assertEqual(ds_id, "mi_dataset")

    def test_create_and_load_dataset(self):
        cases = self._make_cases(3)
        self.bench.create_dataset("test_ds", cases)
        loaded = self.bench.load_dataset("test_ds")
        self.assertEqual(len(loaded), 3)
        self.assertEqual(loaded[0].id, "tc_0")
        self.assertEqual(loaded[1].input_vars["name"], "Agent_1")

    def test_load_nonexistent_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.bench.load_dataset("no_existe")

    def test_create_empty_name_raises(self):
        with self.assertRaises(ValueError):
            self.bench.create_dataset("", [])

    def test_dataset_persistence_across_instances(self):
        """Dataset persiste en disco entre instancias."""
        cases = self._make_cases(2)
        self.bench.create_dataset("persist", cases)

        bench2 = PromptTestBench(
            datasets_dir=self.datasets_dir,
            results_file=self.results_file,
        )
        loaded = bench2.load_dataset("persist")
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].id, "tc_0")

    def test_empty_dataset(self):
        """Crear y cargar dataset vacio."""
        self.bench.create_dataset("vacio", [])
        loaded = self.bench.load_dataset("vacio")
        self.assertEqual(len(loaded), 0)


class TestAddTestCase(TestPromptTestBenchBase):
    """Tests para agregar test cases a datasets existentes."""

    def test_add_test_case(self):
        self.bench.create_dataset("ds", self._make_cases(1))
        new_tc = TestCase(
            id="tc_new",
            input_vars={"name": "Nuevo"},
            tags=["added"],
            metadata={},
        )
        self.bench.add_test_case("ds", new_tc)
        loaded = self.bench.load_dataset("ds")
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[1].id, "tc_new")

    def test_add_to_nonexistent_raises(self):
        tc = TestCase(id="x", input_vars={}, tags=[], metadata={})
        with self.assertRaises(FileNotFoundError):
            self.bench.add_test_case("no_existe", tc)


class TestRenderPrompt(TestPromptTestBenchBase):
    """Tests para render_prompt."""

    def test_render_with_variables(self):
        template = "Hola {{name}}, tu score es {{score}}."
        result = PromptTestBench.render_prompt(
            template, {"name": "Apex", "score": "85"}
        )
        self.assertEqual(result, "Hola Apex, tu score es 85.")

    def test_render_missing_variable_raises(self):
        template = "Agente {{name}} con {{level}}"
        with self.assertRaises(ValueError) as ctx:
            PromptTestBench.render_prompt(template, {"name": "Test"})
        self.assertIn("level", str(ctx.exception))

    def test_render_no_variables(self):
        template = "Prompt sin variables"
        result = PromptTestBench.render_prompt(template, {})
        self.assertEqual(result, "Prompt sin variables")

    def test_render_extra_variables_ignored(self):
        template = "Hola {{name}}"
        result = PromptTestBench.render_prompt(
            template, {"name": "Test", "extra": "ignored"}
        )
        self.assertEqual(result, "Hola Test")


class TestRunBench(TestPromptTestBenchBase):
    """Tests para run_bench."""

    def test_run_bench_all_pass(self):
        """Bench donde todos los casos pasan (sin evaluator, output == rendered)."""
        cases = [
            TestCase(
                id="t1",
                input_vars={"x": "hello"},
                expected_output="Value: hello",
                tags=[],
                metadata={},
            ),
            TestCase(
                id="t2",
                input_vars={"x": "world"},
                expected_output="Value: world",
                tags=[],
                metadata={},
            ),
        ]
        self.bench.create_dataset("pass_ds", cases)
        report = self.bench.run_bench(
            dataset_name="pass_ds",
            prompt_name="test_prompt",
            prompt_content="Value: {{x}}",
        )
        self.assertEqual(report.total_cases, 2)
        self.assertEqual(report.passed, 2)
        self.assertEqual(report.failed, 0)
        self.assertEqual(report.pass_rate, 100.0)

    def test_run_bench_with_failures(self):
        """Bench con casos que fallan (expected != rendered)."""
        cases = [
            TestCase(
                id="t1",
                input_vars={"x": "a"},
                expected_output="Value: a",
                tags=[],
                metadata={},
            ),
            TestCase(
                id="t2",
                input_vars={"x": "b"},
                expected_output="WRONG OUTPUT",
                tags=[],
                metadata={},
            ),
        ]
        self.bench.create_dataset("fail_ds", cases)
        report = self.bench.run_bench(
            dataset_name="fail_ds",
            prompt_name="test_prompt",
            prompt_content="Value: {{x}}",
        )
        self.assertEqual(report.passed, 1)
        self.assertEqual(report.failed, 1)
        self.assertEqual(report.pass_rate, 50.0)

    def test_bench_report_metrics(self):
        """Verifica metricas del BenchReport."""
        cases = self._make_cases(5)
        self.bench.create_dataset("metrics_ds", cases)
        report = self.bench.run_bench(
            dataset_name="metrics_ds",
            prompt_name="metric_prompt",
            prompt_content="{{name}} tiene score {{score}}",
            prompt_version=3,
        )
        self.assertEqual(report.prompt_name, "metric_prompt")
        self.assertEqual(report.prompt_version, 3)
        self.assertEqual(report.total_cases, 5)
        self.assertIsInstance(report.bench_id, str)
        self.assertGreater(len(report.bench_id), 0)
        self.assertGreaterEqual(report.avg_duration_ms, 0)
        self.assertIsInstance(report.timestamp, str)

    def test_run_bench_with_evaluator(self):
        """Bench con evaluator custom."""

        class MockEvalReport:
            def __init__(self, verdict):
                self.verdict = verdict
                self.results = [{"rubric": "mock", "passed": verdict == "PASS"}]

        class MockEvaluator:
            def evaluate(self, output):
                # Pasa si tiene mas de 10 chars
                if len(output) > 10:
                    return MockEvalReport("PASS")
                return MockEvalReport("FAIL")

        cases = [
            TestCase(
                id="long",
                input_vars={"text": "contenido largo suficiente"},
                expected_output="contenido largo suficiente para pasar la prueba del evaluador",
                expected_verdict="pass",
                tags=[],
                metadata={},
            ),
            TestCase(
                id="short",
                input_vars={"text": "x"},
                expected_output="corto",
                expected_verdict="fail",
                tags=[],
                metadata={},
            ),
        ]
        self.bench.create_dataset("eval_ds", cases)
        report = self.bench.run_bench(
            dataset_name="eval_ds",
            prompt_name="eval_prompt",
            prompt_content="Output: {{text}}",
            evaluator=MockEvaluator(),
        )
        self.assertEqual(report.passed, 2)
        self.assertEqual(report.failed, 0)

    def test_bench_results_persisted(self):
        """Resultados se guardan en bench_results.jsonl."""
        cases = self._make_cases(1)
        self.bench.create_dataset("persist_ds", cases)
        self.bench.run_bench(
            dataset_name="persist_ds",
            prompt_name="p",
            prompt_content="{{name}} {{score}}",
        )
        self.assertTrue(os.path.exists(self.results_file))
        with open(self.results_file, "r") as f:
            lines = [l for l in f if l.strip()]
        self.assertEqual(len(lines), 1)
        data = json.loads(lines[0])
        self.assertEqual(data["prompt_name"], "p")


class TestRunComparison(TestPromptTestBenchBase):
    """Tests para run_comparison."""

    def test_comparison_two_prompts(self):
        """Compara 2 prompts contra el mismo dataset."""
        cases = [
            TestCase(
                id="c1",
                input_vars={"val": "42"},
                expected_output="Result: 42",
                tags=[],
                metadata={},
            ),
        ]
        self.bench.create_dataset("comp_ds", cases)

        prompts = [
            ("prompt_v1", "Result: {{val}}"),
            ("prompt_v2", "Output: {{val}}"),
        ]
        reports = self.bench.run_comparison("comp_ds", prompts)

        self.assertEqual(len(reports), 2)
        self.assertEqual(reports[0].prompt_name, "prompt_v1")
        self.assertEqual(reports[1].prompt_name, "prompt_v2")
        # v1 coincide con expected, v2 no
        self.assertEqual(reports[0].passed, 1)
        self.assertEqual(reports[1].passed, 0)


class TestImportCSV(TestPromptTestBenchBase):
    """Tests para import_from_csv."""

    def test_import_csv(self):
        csv_path = os.path.join(self.tmpdir, "test.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["question", "answer", "category"])
            writer.writerow(["What is DeFi?", "Decentralized Finance", "crypto"])
            writer.writerow(["What is DOF?", "Deterministic Observability", "framework"])

        mapping = {
            "question": "input_vars.question",
            "answer": "expected_output",
            "category": "metadata.category",
        }
        count = self.bench.import_from_csv("csv_ds", csv_path, mapping)
        self.assertEqual(count, 2)

        loaded = self.bench.load_dataset("csv_ds")
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].input_vars["question"], "What is DeFi?")
        self.assertEqual(loaded[0].expected_output, "Decentralized Finance")
        self.assertEqual(loaded[0].metadata["category"], "crypto")

    def test_import_csv_nonexistent_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.bench.import_from_csv("ds", "/no/existe.csv", {})


class TestGenerateReportSummary(TestPromptTestBenchBase):
    """Tests para generate_report_summary."""

    def test_summary_contains_key_info(self):
        cases = self._make_cases(3)
        self.bench.create_dataset("sum_ds", cases)
        report = self.bench.run_bench(
            dataset_name="sum_ds",
            prompt_name="summary_prompt",
            prompt_content="{{name}} tiene score {{score}}",
        )
        summary = self.bench.generate_report_summary(report)

        self.assertIn("summary_prompt", summary)
        self.assertIn("Total: 3 casos", summary)
        self.assertIn("Pass Rate:", summary)
        self.assertIn("Bench Report:", summary)

    def test_summary_shows_failures(self):
        cases = [
            TestCase(
                id="fail_1",
                input_vars={"x": "a"},
                expected_output="WRONG",
                tags=[],
                metadata={},
            ),
        ]
        self.bench.create_dataset("fail_sum", cases)
        report = self.bench.run_bench(
            dataset_name="fail_sum",
            prompt_name="fp",
            prompt_content="Value: {{x}}",
        )
        summary = self.bench.generate_report_summary(report)
        self.assertIn("Fallos", summary)
        self.assertIn("fail_1", summary)


class TestLargeDataset(TestPromptTestBenchBase):
    """Test con dataset grande."""

    def test_large_dataset_100_cases(self):
        cases = [
            TestCase(
                id=f"big_{i}",
                input_vars={"n": str(i)},
                expected_output=f"N={i}",
                tags=["bulk"],
                metadata={"index": i},
            )
            for i in range(100)
        ]
        self.bench.create_dataset("big", cases)
        loaded = self.bench.load_dataset("big")
        self.assertEqual(len(loaded), 100)

        report = self.bench.run_bench(
            dataset_name="big",
            prompt_name="big_prompt",
            prompt_content="N={{n}}",
        )
        self.assertEqual(report.total_cases, 100)
        self.assertEqual(report.passed, 100)
        self.assertEqual(report.pass_rate, 100.0)


class TestDataclasses(TestPromptTestBenchBase):
    """Tests para dataclasses."""

    def test_testcase_defaults(self):
        tc = TestCase(id="d", input_vars={"a": 1})
        self.assertIsNone(tc.expected_output)
        self.assertIsNone(tc.expected_verdict)
        self.assertEqual(tc.tags, [])
        self.assertEqual(tc.metadata, {})

    def test_testresult_fields(self):
        tr = TestResult(
            test_case_id="t1",
            prompt_name="p",
            prompt_version=2,
            output="out",
            passed=True,
            duration_ms=1.5,
            timestamp="2026-03-27T00:00:00Z",
        )
        self.assertEqual(tr.prompt_version, 2)
        self.assertTrue(tr.passed)

    def test_benchreport_asdict(self):
        br = BenchReport(
            bench_id="abc",
            prompt_name="p",
            prompt_version=1,
            total_cases=10,
            passed=8,
            failed=2,
            pass_rate=80.0,
            avg_duration_ms=5.0,
            results=[],
            timestamp="2026-03-27T00:00:00Z",
        )
        d = asdict(br)
        self.assertEqual(d["pass_rate"], 80.0)
        self.assertEqual(d["bench_id"], "abc")


if __name__ == "__main__":
    unittest.main()
