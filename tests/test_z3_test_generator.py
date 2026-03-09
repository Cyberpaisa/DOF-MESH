"""
Tests for core.z3_test_generator — auto-generate unittest tests from Z3 results.

Verifies:
- GenerationReport dataclass
- generate_from_counterexample creates valid test files
- generate_boundary_cases creates boundary tests
- generate_threat_pattern_cases creates threat tests
- generate_all orchestrates everything
- Generated files are valid Python
"""

import os
import shutil
import unittest
import tempfile

from core.z3_test_generator import Z3TestGenerator, GenerationReport


class TestGenerationReport(unittest.TestCase):
    """Test GenerationReport dataclass."""

    def test_defaults(self):
        r = GenerationReport()
        self.assertEqual(r.tests_generated, 0)
        self.assertEqual(r.counterexample_tests, 0)
        self.assertEqual(r.boundary_tests, 0)
        self.assertEqual(r.threat_pattern_tests, 0)
        self.assertEqual(r.files_created, [])

    def test_mutable_default_list(self):
        """Each instance should get its own list."""
        r1 = GenerationReport()
        r2 = GenerationReport()
        r1.files_created.append("a.py")
        self.assertEqual(r2.files_created, [])


class TestGenerateFromCounterexample(unittest.TestCase):
    """Test generate_from_counterexample."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.gen = Z3TestGenerator(output_dir=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_creates_file(self):
        path = self.gen.generate_from_counterexample(
            "INV-6",
            {"pre": {"trust_score": 0.5}, "post": {"trust_score": 0.3}},
            "Governor trust too low",
        )
        self.assertTrue(os.path.exists(path))

    def test_file_contains_class(self):
        path = self.gen.generate_from_counterexample("INV-1", {}, "test")
        with open(path) as f:
            content = f.read()
        self.assertIn("class TestZ3AutoINV1", content)

    def test_file_is_valid_python(self):
        path = self.gen.generate_from_counterexample("INV-2", {}, "test")
        with open(path) as f:
            code = f.read()
        compile(code, path, "exec")  # raises SyntaxError if invalid

    def test_report_updated(self):
        self.gen.generate_from_counterexample("INV-3", {}, "test")
        self.assertEqual(self.gen._report.counterexample_tests, 1)
        self.assertEqual(self.gen._report.tests_generated, 1)

    def test_file_in_report(self):
        path = self.gen.generate_from_counterexample("INV-4", {}, "test")
        self.assertIn(path, self.gen._report.files_created)

    def test_init_py_created(self):
        self.gen.generate_from_counterexample("INV-5", {}, "test")
        init = os.path.join(self.tmpdir, "__init__.py")
        self.assertTrue(os.path.exists(init))


class TestGenerateBoundaryCases(unittest.TestCase):
    """Test generate_boundary_cases."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.gen = Z3TestGenerator(output_dir=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_creates_file(self):
        files = self.gen.generate_boundary_cases(
            "trust-low", "trust_score", 0.4
        )
        self.assertEqual(len(files), 1)
        self.assertTrue(os.path.exists(files[0]))

    def test_file_is_valid_python(self):
        files = self.gen.generate_boundary_cases(
            "trust-governor", "trust_score", 0.8
        )
        with open(files[0]) as f:
            code = f.read()
        compile(code, files[0], "exec")

    def test_contains_boundary_values(self):
        files = self.gen.generate_boundary_cases(
            "trust-low", "trust_score", 0.4
        )
        with open(files[0]) as f:
            content = f.read()
        self.assertIn("0.4", content)
        self.assertIn("0.39", content)
        self.assertIn("0.41", content)

    def test_report_counts(self):
        self.gen.generate_boundary_cases("test-constraint", "trust_score", 0.5)
        self.assertGreater(self.gen._report.boundary_tests, 0)
        self.assertGreater(self.gen._report.tests_generated, 0)


class TestGenerateThreatPatternCases(unittest.TestCase):
    """Test generate_threat_pattern_cases."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.gen = Z3TestGenerator(output_dir=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_creates_file(self):
        files = self.gen.generate_threat_pattern_cases()
        self.assertEqual(len(files), 1)
        self.assertTrue(os.path.exists(files[0]))

    def test_file_is_valid_python(self):
        files = self.gen.generate_threat_pattern_cases()
        with open(files[0]) as f:
            code = f.read()
        compile(code, files[0], "exec")

    def test_12_categories_covered(self):
        files = self.gen.generate_threat_pattern_cases()
        with open(files[0]) as f:
            content = f.read()
        categories = [
            "credential_leak", "supply_chain", "prompt_injection",
            "mcp_attack", "external_download", "exfiltration",
            "command_execution", "ssrf_cloud", "indirect_injection",
            "unicode_attack", "cross_context_injection", "composite_detection",
        ]
        for cat in categories:
            self.assertIn(f"test_{cat}_positive", content)
            self.assertIn(f"test_{cat}_negative", content)

    def test_report_threat_counts(self):
        self.gen.generate_threat_pattern_cases()
        # 12 categories × 2 (pos+neg) + 12 variant = 36
        self.assertEqual(self.gen._report.threat_pattern_tests, 36)


class TestGenerateAll(unittest.TestCase):
    """Test generate_all orchestration."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.gen = Z3TestGenerator(output_dir=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_returns_report(self):
        report = self.gen.generate_all()
        self.assertIsInstance(report, GenerationReport)

    def test_creates_multiple_files(self):
        report = self.gen.generate_all()
        self.assertGreater(len(report.files_created), 0)

    def test_total_tests_nonzero(self):
        report = self.gen.generate_all()
        self.assertGreater(report.tests_generated, 0)

    def test_boundary_and_threat_combined(self):
        report = self.gen.generate_all()
        self.assertGreater(report.boundary_tests, 0)
        self.assertGreater(report.threat_pattern_tests, 0)


if __name__ == "__main__":
    unittest.main()
