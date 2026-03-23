"""Tests for core/test_generator.py — BenchmarkResult, _compute_benchmark_result, TestGenerator."""

import os
import tempfile
import unittest

from core.test_generator import (
    BenchmarkResult,
    BenchmarkRunner,
    TestGenerator,
    _compute_benchmark_result,
)


# ─────────────────────────────────────────────────────────
# _compute_benchmark_result — pure math
# ─────────────────────────────────────────────────────────

class TestComputeBenchmarkResult(unittest.TestCase):

    def _run(self, tp, tn, fp, fn, latencies=None):
        return _compute_benchmark_result("cat", tp, tn, fp, fn, latencies or [1.0, 2.0])

    def test_returns_benchmark_result(self):
        self.assertIsInstance(self._run(5, 5, 0, 0), BenchmarkResult)

    def test_category_preserved(self):
        r = _compute_benchmark_result("hallucination", 1, 1, 0, 0, [1.0])
        self.assertEqual(r.category, "hallucination")

    def test_total_tests(self):
        r = self._run(3, 4, 1, 2)
        self.assertEqual(r.total_tests, 10)

    def test_perfect_precision_recall(self):
        r = self._run(tp=10, tn=10, fp=0, fn=0)
        self.assertAlmostEqual(r.precision, 1.0)
        self.assertAlmostEqual(r.recall, 1.0)
        self.assertAlmostEqual(r.f1, 1.0)

    def test_zero_precision_zero_recall(self):
        # tp=0, fp=0 → precision=0; tp=0, fn=10 → recall=0
        r = self._run(tp=0, tn=5, fp=0, fn=10)
        self.assertAlmostEqual(r.precision, 0.0)
        self.assertAlmostEqual(r.recall, 0.0)
        self.assertAlmostEqual(r.f1, 0.0)

    def test_f1_harmonic_mean(self):
        # tp=1, fp=1, fn=1 → precision=0.5, recall=0.5, F1=0.5
        r = self._run(tp=1, tn=0, fp=1, fn=1)
        self.assertAlmostEqual(r.f1, 0.5, places=3)

    def test_all_zeros_safe(self):
        r = self._run(tp=0, tn=0, fp=0, fn=0)
        self.assertAlmostEqual(r.f1, 0.0)
        self.assertAlmostEqual(r.fdr, 0.0)

    def test_fdr_formula(self):
        # FDR = fp / (fp + tp) — False Discovery Rate
        r = self._run(tp=8, tn=2, fp=2, fn=0)
        self.assertAlmostEqual(r.fdr, 2 / 10)  # 2 FP out of 10 positive predictions

    def test_fdr_distinct_from_recall(self):
        # FDR and recall must be different metrics when fp > 0
        r = self._run(tp=8, tn=2, fp=2, fn=2)
        self.assertNotAlmostEqual(r.fdr, r.recall)

    def test_fpr_formula(self):
        # FPR = fp / (fp + tn)
        r = self._run(tp=5, tn=8, fp=2, fn=5)
        self.assertAlmostEqual(r.fpr, 2 / 10)

    def test_latency_mean(self):
        r = _compute_benchmark_result("c", 1, 1, 0, 0, [10.0, 20.0, 30.0])
        self.assertAlmostEqual(r.latency_mean_ms, 20.0)

    def test_latency_p99_single(self):
        r = _compute_benchmark_result("c", 1, 0, 0, 0, [42.0])
        self.assertAlmostEqual(r.latency_p99_ms, 42.0)

    def test_metrics_rounded_to_4dp(self):
        r = self._run(tp=1, tn=2, fp=1, fn=1)
        for attr in ("fdr", "fpr", "precision", "recall", "f1"):
            v = getattr(r, attr)
            self.assertEqual(v, round(v, 4))

    def test_empty_latencies_safe(self):
        r = _compute_benchmark_result("c", 1, 1, 0, 0, [])
        self.assertGreaterEqual(r.latency_mean_ms, 0.0)


# ─────────────────────────────────────────────────────────
# BenchmarkResult.to_dict
# ─────────────────────────────────────────────────────────

class TestBenchmarkResult(unittest.TestCase):

    def _make(self):
        return BenchmarkResult(
            category="test", total_tests=10,
            true_positives=5, true_negatives=4,
            false_positives=1, false_negatives=0,
            fdr=0.9, fpr=0.2, precision=0.83,
            recall=0.9, f1=0.86,
            latency_mean_ms=5.0, latency_p99_ms=12.0,
        )

    def test_to_dict_returns_dict(self):
        self.assertIsInstance(self._make().to_dict(), dict)

    def test_to_dict_keys(self):
        d = self._make().to_dict()
        for key in ("category", "total_tests", "true_positives", "f1",
                     "latency_mean_ms", "latency_p99_ms"):
            self.assertIn(key, d)

    def test_to_dict_values_match(self):
        r = self._make()
        d = r.to_dict()
        self.assertEqual(d["category"], "test")
        self.assertAlmostEqual(d["f1"], 0.86)


# ─────────────────────────────────────────────────────────
# TestGenerator — generation methods
# ─────────────────────────────────────────────────────────

class TestGeneratorTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.gen = TestGenerator(seed=42)

    # generate_hallucination_tests
    def test_hallucination_count(self):
        tests = self.gen.generate_hallucination_tests(20)
        self.assertEqual(len(tests), 20)

    def test_hallucination_keys(self):
        tests = self.gen.generate_hallucination_tests(10)
        for t in tests:
            self.assertIn("text", t)
            self.assertIn("has_hallucination", t)
            self.assertIn("category", t)

    def test_hallucination_bool_labels(self):
        tests = self.gen.generate_hallucination_tests(10)
        for t in tests:
            self.assertIsInstance(t["has_hallucination"], bool)

    def test_hallucination_roughly_balanced(self):
        tests = self.gen.generate_hallucination_tests(100)
        pos = sum(1 for t in tests if t["has_hallucination"])
        self.assertGreater(pos, 30)
        self.assertLess(pos, 70)

    def test_hallucination_deterministic(self):
        t1 = TestGenerator(seed=42).generate_hallucination_tests(20)
        t2 = TestGenerator(seed=42).generate_hallucination_tests(20)
        self.assertEqual([t["text"] for t in t1], [t["text"] for t in t2])

    def test_hallucination_different_seeds_differ(self):
        t1 = TestGenerator(seed=1).generate_hallucination_tests(20)
        t2 = TestGenerator(seed=2).generate_hallucination_tests(20)
        self.assertNotEqual([t["text"] for t in t1], [t["text"] for t in t2])

    # generate_code_safety_tests
    def test_code_safety_count(self):
        self.assertEqual(len(self.gen.generate_code_safety_tests(20)), 20)

    def test_code_safety_keys(self):
        for t in self.gen.generate_code_safety_tests(10):
            self.assertIn("code", t)
            self.assertIn("is_unsafe", t)
            self.assertIn("category", t)

    def test_code_safety_balanced(self):
        tests = self.gen.generate_code_safety_tests(100)
        unsafe = sum(1 for t in tests if t["is_unsafe"])
        self.assertGreater(unsafe, 30)
        self.assertLess(unsafe, 70)

    def test_code_safety_deterministic(self):
        t1 = TestGenerator(seed=42).generate_code_safety_tests(20)
        t2 = TestGenerator(seed=42).generate_code_safety_tests(20)
        self.assertEqual([t["code"] for t in t1], [t["code"] for t in t2])

    # generate_governance_tests
    def test_governance_count(self):
        self.assertEqual(len(self.gen.generate_governance_tests(20)), 20)

    def test_governance_keys(self):
        for t in self.gen.generate_governance_tests(10):
            self.assertIn("text", t)
            self.assertIn("should_pass", t)
            self.assertIn("violation_type", t)

    def test_governance_balanced(self):
        tests = self.gen.generate_governance_tests(100)
        violations = sum(1 for t in tests if not t["should_pass"])
        self.assertGreater(violations, 30)
        self.assertLess(violations, 70)

    # generate_consistency_tests
    def test_consistency_count(self):
        self.assertEqual(len(self.gen.generate_consistency_tests(20)), 20)

    def test_consistency_keys(self):
        for t in self.gen.generate_consistency_tests(10):
            self.assertIn("text", t)
            self.assertIn("has_contradiction", t)

    def test_consistency_balanced(self):
        tests = self.gen.generate_consistency_tests(50)
        contradictions = sum(1 for t in tests if t["has_contradiction"])
        self.assertGreater(contradictions, 10)
        self.assertLess(contradictions, 40)

    # generate_full_dataset
    def test_full_dataset_keys(self):
        dataset = self.gen.generate_full_dataset(n_per_category=10)
        for key in ("hallucination", "code_safety", "governance", "consistency",
                     "total_tests", "seed", "timestamp"):
            self.assertIn(key, dataset)

    def test_full_dataset_total_tests(self):
        dataset = self.gen.generate_full_dataset(n_per_category=10)
        expected = sum(len(dataset[k]) for k in
                       ["hallucination", "code_safety", "governance", "consistency"])
        self.assertEqual(dataset["total_tests"], expected)

    def test_full_dataset_seed_preserved(self):
        dataset = TestGenerator(seed=99).generate_full_dataset(n_per_category=10)
        self.assertEqual(dataset["seed"], 99)

    def test_full_dataset_file_written(self):
        dataset = self.gen.generate_full_dataset(n_per_category=10)
        self.assertIn("path", dataset)
        self.assertTrue(os.path.exists(dataset["path"]))


# ─────────────────────────────────────────────────────────
# BenchmarkRunner — run_code_safety_benchmark (self-contained)
# ─────────────────────────────────────────────────────────

class TestBenchmarkRunner(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        gen = TestGenerator(seed=42)
        cls.dataset = {
            "hallucination": gen.generate_hallucination_tests(20),
            "code_safety": gen.generate_code_safety_tests(20),
            "governance": gen.generate_governance_tests(20),
            "consistency": gen.generate_consistency_tests(20),
        }
        cls.runner = BenchmarkRunner(cls.dataset)

    def test_code_safety_returns_benchmark_result(self):
        from core.ast_verifier import ASTVerifier
        result = self.runner.run_code_safety_benchmark(ASTVerifier())
        self.assertIsInstance(result, BenchmarkResult)

    def test_code_safety_category(self):
        from core.ast_verifier import ASTVerifier
        result = self.runner.run_code_safety_benchmark(ASTVerifier())
        self.assertEqual(result.category, "code_safety")

    def test_code_safety_total_tests(self):
        from core.ast_verifier import ASTVerifier
        result = self.runner.run_code_safety_benchmark(ASTVerifier())
        self.assertEqual(result.total_tests, 20)

    def test_code_safety_f1_in_range(self):
        from core.ast_verifier import ASTVerifier
        result = self.runner.run_code_safety_benchmark(ASTVerifier())
        self.assertGreaterEqual(result.f1, 0.0)
        self.assertLessEqual(result.f1, 1.0)

    def test_governance_returns_benchmark_result(self):
        from core.governance import ConstitutionEnforcer
        result = self.runner.run_governance_benchmark(ConstitutionEnforcer())
        self.assertIsInstance(result, BenchmarkResult)

    def test_governance_total_tests(self):
        from core.governance import ConstitutionEnforcer
        result = self.runner.run_governance_benchmark(ConstitutionEnforcer())
        self.assertEqual(result.total_tests, 20)

    def test_governance_latency_positive(self):
        from core.governance import ConstitutionEnforcer
        result = self.runner.run_governance_benchmark(ConstitutionEnforcer())
        self.assertGreater(result.latency_mean_ms, 0.0)

    def test_run_full_benchmark_returns_dict(self):
        result = self.runner.run_full_benchmark()
        self.assertIsInstance(result, dict)

    def test_run_full_benchmark_has_all_keys(self):
        result = self.runner.run_full_benchmark()
        for key in ("hallucination", "code_safety", "governance",
                    "consistency", "overall_f1", "total_tests"):
            self.assertIn(key, result)

    def test_run_full_benchmark_overall_f1_in_range(self):
        result = self.runner.run_full_benchmark()
        self.assertGreaterEqual(result["overall_f1"], 0.0)
        self.assertLessEqual(result["overall_f1"], 1.0)

    def test_run_full_benchmark_total_tests(self):
        result = self.runner.run_full_benchmark()
        # 4 categories × 20 tests each
        self.assertEqual(result["total_tests"], 80)

    def test_run_full_benchmark_each_category_is_dict(self):
        result = self.runner.run_full_benchmark()
        for key in ("hallucination", "code_safety", "governance", "consistency"):
            self.assertIsInstance(result[key], dict)
            self.assertIn("f1", result[key])

    def test_dataset_stored_on_runner(self):
        self.assertEqual(len(self.runner.dataset["code_safety"]), 20)


if __name__ == "__main__":
    unittest.main()
