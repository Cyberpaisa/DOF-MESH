"""Tests for TestGenerator and BenchmarkRunner in core/test_generator.py."""

import unittest

from core.test_generator import TestGenerator, BenchmarkRunner, BenchmarkResult, _compute_benchmark_result
from core.data_oracle import DataOracle
from core.ast_verifier import ASTVerifier


class TestGenerateHallucinationTests(unittest.TestCase):
    """generate_hallucination_tests retorna n tests con 50/50 split."""

    def test_hallucination_count_and_split(self):
        gen = TestGenerator(seed=42)
        tests = gen.generate_hallucination_tests(100)
        self.assertEqual(len(tests), 100)
        clean = sum(1 for t in tests if not t["has_hallucination"])
        bad = sum(1 for t in tests if t["has_hallucination"])
        self.assertEqual(clean, 50)
        self.assertEqual(bad, 50)

    def test_hallucination_keys(self):
        gen = TestGenerator(seed=42)
        tests = gen.generate_hallucination_tests(10)
        for t in tests:
            self.assertIn("text", t)
            self.assertIn("has_hallucination", t)
            self.assertIn("category", t)


class TestGenerateCodeSafetyTests(unittest.TestCase):
    """generate_code_safety_tests retorna código válido e inválido."""

    def test_code_safety_count_and_split(self):
        gen = TestGenerator(seed=42)
        tests = gen.generate_code_safety_tests(100)
        self.assertEqual(len(tests), 100)
        clean = sum(1 for t in tests if not t["is_unsafe"])
        bad = sum(1 for t in tests if t["is_unsafe"])
        self.assertEqual(clean, 50)
        self.assertEqual(bad, 50)

    def test_code_safety_categories(self):
        gen = TestGenerator(seed=42)
        tests = gen.generate_code_safety_tests(100)
        unsafe = [t for t in tests if t["is_unsafe"]]
        categories = {t["category"] for t in unsafe}
        self.assertTrue(categories.issubset({"eval", "import_os", "hardcoded_secret"}))


class TestGenerateGovernanceTests(unittest.TestCase):
    """generate_governance_tests retorna compliant y non-compliant."""

    def test_governance_count_and_split(self):
        gen = TestGenerator(seed=42)
        tests = gen.generate_governance_tests(100)
        self.assertEqual(len(tests), 100)
        passing = sum(1 for t in tests if t["should_pass"])
        failing = sum(1 for t in tests if not t["should_pass"])
        self.assertEqual(passing, 50)
        self.assertEqual(failing, 50)


class TestGenerateConsistencyTests(unittest.TestCase):
    """generate_consistency_tests retorna consistent y contradictory."""

    def test_consistency_count_and_split(self):
        gen = TestGenerator(seed=42)
        tests = gen.generate_consistency_tests(50)
        self.assertEqual(len(tests), 50)
        clean = sum(1 for t in tests if not t["has_contradiction"])
        bad = sum(1 for t in tests if t["has_contradiction"])
        self.assertEqual(clean, 25)
        self.assertEqual(bad, 25)


class TestGenerateFullDataset(unittest.TestCase):
    """generate_full_dataset retorna 4*n tests."""

    def test_full_dataset_count(self):
        gen = TestGenerator(seed=42)
        dataset = gen.generate_full_dataset(n_per_category=20)
        # 20 hallucination + 20 code_safety + 20 governance + 20 consistency
        self.assertEqual(dataset["total_tests"], 80)
        self.assertIn("path", dataset)
        self.assertEqual(len(dataset["hallucination"]), 20)
        self.assertEqual(len(dataset["code_safety"]), 20)
        self.assertEqual(len(dataset["governance"]), 20)
        self.assertEqual(len(dataset["consistency"]), 20)


class TestBenchmarkResultFDR(unittest.TestCase):
    """BenchmarkResult calcula FDR correctamente."""

    def test_fdr_calculation(self):
        result = _compute_benchmark_result("test", tp=40, tn=45, fp=5, fn=10, latencies=[1.0]*100)
        # FDR = TP / (TP + FN) = 40 / 50 = 0.8
        self.assertAlmostEqual(result.fdr, 0.8, places=4)


class TestBenchmarkResultFPR(unittest.TestCase):
    """BenchmarkResult calcula FPR correctamente."""

    def test_fpr_calculation(self):
        result = _compute_benchmark_result("test", tp=40, tn=45, fp=5, fn=10, latencies=[1.0]*100)
        # FPR = FP / (FP + TN) = 5 / 50 = 0.1
        self.assertAlmostEqual(result.fpr, 0.1, places=4)


class TestBenchmarkResultF1(unittest.TestCase):
    """BenchmarkResult calcula F1 correctamente."""

    def test_f1_calculation(self):
        result = _compute_benchmark_result("test", tp=40, tn=45, fp=5, fn=10, latencies=[1.0]*100)
        # Precision = 40/45 = 0.8889, Recall = 40/50 = 0.8
        # F1 = 2 * 0.8889 * 0.8 / (0.8889 + 0.8) = 0.8421
        self.assertAlmostEqual(result.f1, 0.8421, places=3)


class TestBenchmarkResultPerfect(unittest.TestCase):
    """Perfect detection → FDR=1.0, FPR=0.0."""

    def test_perfect_detection(self):
        result = _compute_benchmark_result("test", tp=50, tn=50, fp=0, fn=0, latencies=[1.0]*100)
        self.assertEqual(result.fdr, 1.0)
        self.assertEqual(result.fpr, 0.0)
        self.assertEqual(result.f1, 1.0)


class TestBenchmarkResultZero(unittest.TestCase):
    """Zero detection → FDR=0.0."""

    def test_zero_detection(self):
        result = _compute_benchmark_result("test", tp=0, tn=50, fp=0, fn=50, latencies=[1.0]*100)
        self.assertEqual(result.fdr, 0.0)
        self.assertEqual(result.recall, 0.0)


class TestRunHallucinationBenchmark(unittest.TestCase):
    """run_hallucination_benchmark with DataOracle."""

    def test_hallucination_benchmark_runs(self):
        gen = TestGenerator(seed=42)
        dataset = gen.generate_full_dataset(n_per_category=20)
        runner = BenchmarkRunner(dataset)
        oracle = DataOracle()
        result = runner.run_hallucination_benchmark(oracle)
        self.assertEqual(result.category, "hallucination")
        self.assertEqual(result.total_tests, 20)
        self.assertGreaterEqual(result.fdr, 0.0)
        self.assertLessEqual(result.fdr, 1.0)


class TestRunCodeSafetyBenchmark(unittest.TestCase):
    """run_code_safety_benchmark with ASTVerifier."""

    def test_code_safety_benchmark_runs(self):
        gen = TestGenerator(seed=42)
        dataset = gen.generate_full_dataset(n_per_category=20)
        runner = BenchmarkRunner(dataset)
        verifier = ASTVerifier()
        result = runner.run_code_safety_benchmark(verifier)
        self.assertEqual(result.category, "code_safety")
        self.assertEqual(result.total_tests, 20)
        self.assertGreaterEqual(result.fdr, 0.0)


if __name__ == "__main__":
    unittest.main()
