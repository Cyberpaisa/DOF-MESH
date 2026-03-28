"""
Tests para core/prompt_eval_gate.py — Prompt Evaluation Gate para CI/CD.

Minimo 12 tests cubriendo: deteccion de cambios, extraccion de prompts,
gate pass/fail, reporte CI, secrets, threshold, edge cases.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from dataclasses import asdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.prompt_eval_gate import (
    PromptEvalGate, GateResult, PromptEvalResult, PromptInfo,
    PROMPT_PATTERNS, SECRET_PATTERNS,
)


class TestDetectPromptChanges(unittest.TestCase):
    """Tests para detect_prompt_changes."""

    def setUp(self):
        self.gate = PromptEvalGate(gate_dir=tempfile.mkdtemp())

    def test_detect_changes_in_python_file_with_prompts(self):
        """Detecta cambios en archivo Python con system_prompt."""
        diff = (
            "diff --git a/core/agent.py b/core/agent.py\n"
            "--- a/core/agent.py\n"
            "+++ b/core/agent.py\n"
            "@@ -10,3 +10,5 @@\n"
            '+system_prompt = "You are a helpful assistant that answers questions"\n'
            "+# some comment\n"
        )
        result = self.gate.detect_prompt_changes(diff)
        self.assertEqual(result, ["core/agent.py"])

    def test_detect_no_changes_in_non_prompt_file(self):
        """No detecta prompts en archivo sin patrones de prompt."""
        diff = (
            "diff --git a/utils/math.py b/utils/math.py\n"
            "--- a/utils/math.py\n"
            "+++ b/utils/math.py\n"
            "@@ -1,3 +1,4 @@\n"
            "+def add(a, b): return a + b\n"
        )
        result = self.gate.detect_prompt_changes(diff)
        self.assertEqual(result, [])

    def test_detect_template_string_changes(self):
        """Detecta cambios con template strings {{variable}}."""
        diff = (
            "diff --git a/prompts/main.py b/prompts/main.py\n"
            "--- a/prompts/main.py\n"
            "+++ b/prompts/main.py\n"
            "@@ -1,2 +1,3 @@\n"
            '+msg = "Hello {{user_name}}, please provide {{context}}"\n'
        )
        result = self.gate.detect_prompt_changes(diff)
        self.assertEqual(result, ["prompts/main.py"])

    def test_empty_diff(self):
        """Diff vacio retorna lista vacia."""
        self.assertEqual(self.gate.detect_prompt_changes(""), [])
        self.assertEqual(self.gate.detect_prompt_changes("   "), [])
        self.assertEqual(self.gate.detect_prompt_changes(None), [])

    def test_detect_multiple_files(self):
        """Detecta cambios en multiples archivos."""
        diff = (
            "diff --git a/a.py b/a.py\n"
            "--- a/a.py\n"
            "+++ b/a.py\n"
            "@@ -1 +1,2 @@\n"
            "+PROMPT = 'instrucciones'\n"
            "diff --git a/b.py b/b.py\n"
            "--- a/b.py\n"
            "+++ b/b.py\n"
            "@@ -1 +1,2 @@\n"
            '+instructions = "do something"\n'
        )
        result = self.gate.detect_prompt_changes(diff)
        self.assertEqual(len(result), 2)
        self.assertIn("a.py", result)
        self.assertIn("b.py", result)


class TestExtractPrompts(unittest.TestCase):
    """Tests para extract_prompts_from_file."""

    def setUp(self):
        self.gate = PromptEvalGate(gate_dir=tempfile.mkdtemp())

    def test_extract_prompts_from_python(self):
        """Extrae prompts de archivo Python con string multilinea."""
        content = '''
SYSTEM_PROMPT = """
You are a helpful assistant that must always respond with detailed analysis.
You should evaluate the input carefully and generate a structured output.
Follow these instructions step by step: first analyze, then summarize.
Always include examples and context in your response format.
"""
'''
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False
        ) as f:
            f.write(content)
            f.flush()
            result = self.gate.extract_prompts_from_file(f.name)

        os.unlink(f.name)
        self.assertGreaterEqual(len(result), 1)
        self.assertIn('content', result[0])
        self.assertIn('line', result[0])
        self.assertIn('file', result[0])

    def test_extract_nonexistent_file(self):
        """Archivo inexistente retorna lista vacia."""
        result = self.gate.extract_prompts_from_file("/nonexistent/path.py")
        self.assertEqual(result, [])

    def test_extract_short_strings_ignored(self):
        """Strings cortos (<100 chars) no se extraen como prompts."""
        content = 'prompt = "short"\ntemplate = "also short"\n'
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False
        ) as f:
            f.write(content)
            f.flush()
            result = self.gate.extract_prompts_from_file(f.name)

        os.unlink(f.name)
        self.assertEqual(result, [])


class TestRunGate(unittest.TestCase):
    """Tests para run_gate."""

    def setUp(self):
        self.gate = PromptEvalGate(gate_dir=tempfile.mkdtemp())

    @patch('core.prompt_eval_gate.PromptEvalGate._evaluate_single_prompt')
    def test_run_gate_all_pass(self, mock_eval):
        """Gate pasa cuando todos los prompts pasan."""
        mock_eval.return_value = PromptEvalResult(
            prompt_file="test.py", prompt_line=1,
            passed=True, eval_score=1.0,
            governance_passed=True, has_secrets=False,
            details="ALL_CHECKS_PASSED",
        )
        prompts = [
            {'content': 'prompt 1 ' * 20, 'line': 1, 'file': 'test.py'},
            {'content': 'prompt 2 ' * 20, 'line': 10, 'file': 'test.py'},
        ]
        result = self.gate.run_gate(prompts, threshold=0.7)
        self.assertTrue(result.passed)
        self.assertEqual(result.prompts_evaluated, 2)
        self.assertEqual(result.actual_pass_rate, 1.0)
        self.assertEqual(len(result.failures), 0)

    @patch('core.prompt_eval_gate.PromptEvalGate._evaluate_single_prompt')
    def test_run_gate_failures_below_threshold(self, mock_eval):
        """Gate falla cuando pass rate < threshold."""
        def side_effect(content, file_path, line):
            if 'fail' in content:
                return PromptEvalResult(
                    prompt_file=file_path, prompt_line=line,
                    passed=False, eval_score=0.3,
                    governance_passed=False, has_secrets=False,
                    details="GOVERNANCE_FAIL: violation",
                )
            return PromptEvalResult(
                prompt_file=file_path, prompt_line=line,
                passed=True, eval_score=1.0,
                governance_passed=True, has_secrets=False,
                details="ALL_CHECKS_PASSED",
            )

        mock_eval.side_effect = side_effect
        prompts = [
            {'content': 'fail prompt 1', 'line': 1, 'file': 'a.py'},
            {'content': 'fail prompt 2', 'line': 2, 'file': 'b.py'},
            {'content': 'good prompt', 'line': 3, 'file': 'c.py'},
        ]
        result = self.gate.run_gate(prompts, threshold=0.7)
        self.assertFalse(result.passed)
        self.assertAlmostEqual(result.actual_pass_rate, 1 / 3, places=2)
        self.assertEqual(len(result.failures), 2)

    def test_run_gate_empty_prompts(self):
        """Gate pasa con lista de prompts vacia."""
        result = self.gate.run_gate([], threshold=0.7)
        self.assertTrue(result.passed)
        self.assertEqual(result.prompts_evaluated, 0)
        self.assertEqual(result.actual_pass_rate, 1.0)

    @patch('core.prompt_eval_gate.PromptEvalGate._evaluate_single_prompt')
    def test_threshold_parameter(self, mock_eval):
        """Threshold alto hace que gate falle con un solo fallo."""
        call_count = [0]

        def side_effect(content, file_path, line):
            call_count[0] += 1
            if call_count[0] == 1:
                return PromptEvalResult(
                    prompt_file=file_path, prompt_line=line,
                    passed=False, eval_score=0.5,
                    governance_passed=False, has_secrets=False,
                    details="FAIL",
                )
            return PromptEvalResult(
                prompt_file=file_path, prompt_line=line,
                passed=True, eval_score=1.0,
                governance_passed=True, has_secrets=False,
                details="PASS",
            )

        mock_eval.side_effect = side_effect
        prompts = [
            {'content': 'p1', 'line': 1, 'file': 'a.py'},
            {'content': 'p2', 'line': 2, 'file': 'b.py'},
        ]

        # Con threshold 1.0, un fallo de 2 hace que falle (0.5 < 1.0)
        result = self.gate.run_gate(prompts, threshold=1.0)
        self.assertFalse(result.passed)

    @patch('core.prompt_eval_gate.PromptEvalGate._evaluate_single_prompt')
    def test_threshold_low_passes(self, mock_eval):
        """Threshold bajo permite pasar con fallos parciales."""
        call_count = [0]

        def side_effect(content, file_path, line):
            call_count[0] += 1
            if call_count[0] == 1:
                return PromptEvalResult(
                    prompt_file=file_path, prompt_line=line,
                    passed=False, eval_score=0.5,
                    governance_passed=False, has_secrets=False,
                    details="FAIL",
                )
            return PromptEvalResult(
                prompt_file=file_path, prompt_line=line,
                passed=True, eval_score=1.0,
                governance_passed=True, has_secrets=False,
                details="PASS",
            )

        mock_eval.side_effect = side_effect
        prompts = [
            {'content': 'p1', 'line': 1, 'file': 'a.py'},
            {'content': 'p2', 'line': 2, 'file': 'b.py'},
        ]

        # Con threshold 0.4, 1 de 2 pass (0.5) >= 0.4
        result = self.gate.run_gate(prompts, threshold=0.4)
        self.assertTrue(result.passed)


class TestSecretsDetection(unittest.TestCase):
    """Tests para deteccion de secrets en prompts."""

    def setUp(self):
        self.gate = PromptEvalGate(gate_dir=tempfile.mkdtemp())

    def test_secrets_in_prompt_detected(self):
        """Detecta private key en un prompt."""
        prompt_with_secret = (
            "You are a helpful assistant. Use this key: "
            "0x" + "a" * 64 + " to authenticate."
        )
        result = self.gate._evaluate_single_prompt(
            prompt_with_secret, "test.py", 1
        )
        self.assertTrue(result.has_secrets)
        self.assertFalse(result.passed)
        self.assertIn("SECRET_DETECTED", result.details)

    def test_no_secrets_in_clean_prompt(self):
        """Prompt limpio no dispara deteccion de secrets."""
        clean_prompt = (
            "You are a helpful assistant that answers questions about "
            "blockchain technology and smart contracts. Always be precise."
        )
        result = self.gate._evaluate_single_prompt(
            clean_prompt, "test.py", 1
        )
        self.assertFalse(result.has_secrets)

    def test_bearer_token_detected(self):
        """Detecta Bearer token en prompt."""
        prompt = (
            "Call the API with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            ".eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I"
        )
        result = self.gate._evaluate_single_prompt(prompt, "test.py", 1)
        self.assertTrue(result.has_secrets)


class TestGenerateCIReport(unittest.TestCase):
    """Tests para generate_ci_report."""

    def setUp(self):
        self.gate = PromptEvalGate(gate_dir=tempfile.mkdtemp())

    def test_generate_ci_report_pass(self):
        """Reporte de gate que pasa."""
        gate_result = GateResult(
            passed=True,
            threshold=0.7,
            actual_pass_rate=1.0,
            prompts_evaluated=3,
            failures=[],
            report="",
            timestamp="2026-03-27T00:00:00Z",
        )
        report = self.gate.generate_ci_report(gate_result)
        self.assertIn("PASS", report)
        self.assertIn("70%", report)
        self.assertIn("100%", report)
        self.assertIn("3", report)
        self.assertIn("All prompts passed", report)

    def test_generate_ci_report_fail(self):
        """Reporte de gate que falla incluye detalles de fallos."""
        gate_result = GateResult(
            passed=False,
            threshold=0.7,
            actual_pass_rate=0.3,
            prompts_evaluated=3,
            failures=[{
                'prompt_file': 'bad.py',
                'prompt_line': 42,
                'has_secrets': True,
                'details': 'SECRET_DETECTED: prompt contains sensitive data',
            }],
            report="",
            timestamp="2026-03-27T00:00:00Z",
        )
        report = self.gate.generate_ci_report(gate_result)
        self.assertIn("FAIL", report)
        self.assertIn("bad.py:42", report)
        self.assertIn("SECRET", report)
        self.assertIn("Failures", report)


class TestGateResultStructure(unittest.TestCase):
    """Tests para la estructura de GateResult."""

    def test_gate_result_dataclass_fields(self):
        """GateResult tiene todos los campos requeridos."""
        gr = GateResult()
        self.assertTrue(hasattr(gr, 'passed'))
        self.assertTrue(hasattr(gr, 'threshold'))
        self.assertTrue(hasattr(gr, 'actual_pass_rate'))
        self.assertTrue(hasattr(gr, 'prompts_evaluated'))
        self.assertTrue(hasattr(gr, 'failures'))
        self.assertTrue(hasattr(gr, 'report'))
        self.assertTrue(hasattr(gr, 'timestamp'))

    def test_gate_result_to_dict(self):
        """GateResult se serializa correctamente a dict."""
        gr = GateResult(
            passed=True, threshold=0.8,
            actual_pass_rate=0.9, prompts_evaluated=5,
            failures=[], report="ok", timestamp="2026-01-01",
        )
        d = gr.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d['passed'], True)
        self.assertEqual(d['threshold'], 0.8)
        self.assertEqual(d['prompts_evaluated'], 5)

    def test_gate_result_json_serializable(self):
        """GateResult.to_dict() es serializable a JSON."""
        gr = GateResult(
            passed=False, threshold=0.7,
            actual_pass_rate=0.5, prompts_evaluated=2,
            failures=[{'file': 'x.py', 'line': 1}],
            report="fail", timestamp="2026-01-01",
        )
        serialized = json.dumps(gr.to_dict())
        self.assertIsInstance(serialized, str)
        parsed = json.loads(serialized)
        self.assertEqual(parsed['passed'], False)


class TestPersistence(unittest.TestCase):
    """Tests para persistencia JSONL."""

    def test_persist_creates_file(self):
        """_persist crea el archivo JSONL."""
        tmpdir = tempfile.mkdtemp()
        gate = PromptEvalGate(gate_dir=tmpdir)
        gr = GateResult(
            passed=True, threshold=0.7,
            actual_pass_rate=1.0, prompts_evaluated=1,
            failures=[], report="ok",
            timestamp="2026-01-01T00:00:00Z",
        )
        gate._persist(gr)
        gate_file = os.path.join(tmpdir, "gate_results.jsonl")
        self.assertTrue(os.path.isfile(gate_file))
        with open(gate_file) as f:
            line = f.readline()
            data = json.loads(line)
            self.assertEqual(data['passed'], True)


if __name__ == '__main__':
    unittest.main()
