"""
Tests for core/ast_verifier.py — AST static analysis on agent-generated code.
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.ast_verifier import ASTVerifier


class TestASTVerifierClean(unittest.TestCase):
    """Clean code should pass verification."""

    def setUp(self):
        self.verifier = ASTVerifier()

    def test_clean_code_passes(self):
        code = '''
import json
import math

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

data = {"key": "value", "count": 42}
result = json.dumps(data)
print(result)
'''
        result = self.verifier.verify(code)
        self.assertTrue(result.passed)
        self.assertEqual(result.score, 1.0)
        self.assertEqual(len(result.violations), 0)

    def test_empty_code_passes(self):
        result = self.verifier.verify("x = 1\n")
        self.assertTrue(result.passed)
        self.assertEqual(result.score, 1.0)


class TestASTVerifierUnsafeCalls(unittest.TestCase):
    """Detect eval(), exec(), compile()."""

    def setUp(self):
        self.verifier = ASTVerifier()

    def test_eval_detected(self):
        code = 'result = eval("2 + 2")\n'
        result = self.verifier.verify(code)
        self.assertFalse(result.passed)
        rule_ids = [v["rule_id"] for v in result.violations]
        self.assertIn("UNSAFE_CALLS", rule_ids)

    def test_exec_detected(self):
        code = 'exec("import os")\n'
        result = self.verifier.verify(code)
        self.assertFalse(result.passed)
        rule_ids = [v["rule_id"] for v in result.violations]
        self.assertIn("UNSAFE_CALLS", rule_ids)

    def test_compile_detected(self):
        code = 'co = compile("x=1", "<string>", "exec")\n'
        result = self.verifier.verify(code)
        self.assertFalse(result.passed)
        rule_ids = [v["rule_id"] for v in result.violations]
        self.assertIn("UNSAFE_CALLS", rule_ids)


class TestASTVerifierBlockedImports(unittest.TestCase):
    """Detect blocked imports."""

    def setUp(self):
        self.verifier = ASTVerifier()

    def test_import_subprocess(self):
        code = "import subprocess\nsubprocess.run(['ls'])\n"
        result = self.verifier.verify(code)
        self.assertFalse(result.passed)
        rule_ids = [v["rule_id"] for v in result.violations]
        self.assertIn("BLOCKED_IMPORTS", rule_ids)

    def test_from_shutil_rmtree(self):
        code = "from shutil import rmtree\nrmtree('/tmp/test')\n"
        result = self.verifier.verify(code)
        self.assertFalse(result.passed)
        rule_ids = [v["rule_id"] for v in result.violations]
        self.assertIn("BLOCKED_IMPORTS", rule_ids)

    def test_dunder_import_call(self):
        code = "__import__('os').system('rm -rf /')\n"
        result = self.verifier.verify(code)
        self.assertFalse(result.passed)
        rule_ids = [v["rule_id"] for v in result.violations]
        self.assertIn("BLOCKED_IMPORTS", rule_ids)


class TestASTVerifierSecrets(unittest.TestCase):
    """Detect hardcoded API keys and tokens."""

    def setUp(self):
        self.verifier = ASTVerifier()

    def test_openai_key(self):
        code = 'API_KEY = "sk-abcdefghijklmnopqrstuvwxyz1234567890"\n'
        result = self.verifier.verify(code)
        self.assertFalse(result.passed)
        rule_ids = [v["rule_id"] for v in result.violations]
        self.assertIn("SECRET_PATTERNS", rule_ids)

    def test_github_pat(self):
        code = 'token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmn"\n'
        result = self.verifier.verify(code)
        self.assertFalse(result.passed)
        rule_ids = [v["rule_id"] for v in result.violations]
        self.assertIn("SECRET_PATTERNS", rule_ids)

    def test_aws_key(self):
        code = 'aws_key = "AKIAIOSFODNN7EXAMPLE"\n'
        result = self.verifier.verify(code)
        self.assertFalse(result.passed)
        rule_ids = [v["rule_id"] for v in result.violations]
        self.assertIn("SECRET_PATTERNS", rule_ids)

    def test_env_var_is_safe(self):
        code = 'import os\napi_key = os.getenv("OPENAI_API_KEY")\n'
        result = self.verifier.verify(code)
        self.assertTrue(result.passed)


class TestASTVerifierResourceRisks(unittest.TestCase):
    """Detect resource risk patterns (warn, not block)."""

    def setUp(self):
        self.verifier = ASTVerifier()

    def test_while_true_no_break(self):
        code = '''
def run():
    while True:
        do_something()
'''
        result = self.verifier.verify(code)
        # Should pass (warn only, not block)
        self.assertTrue(result.passed)
        rule_ids = [v["rule_id"] for v in result.violations]
        self.assertIn("RESOURCE_RISKS", rule_ids)
        # But severity is "warn"
        for v in result.violations:
            if v["rule_id"] == "RESOURCE_RISKS":
                self.assertEqual(v["severity"], "warn")

    def test_while_true_with_break_is_ok(self):
        code = '''
def run():
    while True:
        data = get_data()
        if data is None:
            break
'''
        result = self.verifier.verify(code)
        resource_violations = [v for v in result.violations if v["rule_id"] == "RESOURCE_RISKS"]
        self.assertEqual(len(resource_violations), 0)


class TestASTVerifierSyntaxError(unittest.TestCase):
    """Syntax errors should fail with SYNTAX_ERROR rule."""

    def setUp(self):
        self.verifier = ASTVerifier()

    def test_syntax_error(self):
        code = "def foo(\n"
        result = self.verifier.verify(code)
        self.assertFalse(result.passed)
        self.assertEqual(result.score, 0.0)
        rule_ids = [v["rule_id"] for v in result.violations]
        self.assertIn("SYNTAX_ERROR", rule_ids)


class TestASTVerifierScore(unittest.TestCase):
    """Score calculation: 1.0 - (violated_categories / 4)."""

    def setUp(self):
        self.verifier = ASTVerifier()

    def test_one_category_violated(self):
        code = 'result = eval("1+1")\n'
        result = self.verifier.verify(code)
        self.assertEqual(result.score, 0.75)  # 1 - 1/4

    def test_two_categories_violated(self):
        code = 'import subprocess\nresult = eval("1+1")\n'
        result = self.verifier.verify(code)
        self.assertEqual(result.score, 0.5)  # 1 - 2/4

    def test_clean_score_is_1(self):
        code = "x = 42\n"
        result = self.verifier.verify(code)
        self.assertEqual(result.score, 1.0)


class TestGovernanceIntegration(unittest.TestCase):
    """ConstitutionEnforcer triggers AST verification on code blocks."""

    def test_code_block_with_eval_fails_governance(self):
        from core.governance import ConstitutionEnforcer

        enforcer = ConstitutionEnforcer()
        output = '''Here is the solution:

```python
result = eval(user_input)
print(result)
```

This should work for your use case and provides the flexibility needed to
handle dynamic expressions from the user input with proper validation
and error handling mechanisms in place for production deployments.
'''
        result = enforcer.check(output)
        self.assertFalse(result.passed)
        ast_violations = [v for v in result.violations if "AST_VERIFY" in v]
        self.assertGreater(len(ast_violations), 0)

    def test_code_block_clean_passes_governance(self):
        from core.governance import ConstitutionEnforcer

        enforcer = ConstitutionEnforcer()
        output = '''Here is the implementation:

```python
import json

def process(data):
    return json.dumps(data, indent=2)
```

This function serializes the data to JSON format with proper indentation
for readability and can be used in production with confidence in the
output formatting and structure of the serialized data.
'''
        result = enforcer.check(output)
        # No AST violations (other rules may still fire, but not AST)
        ast_violations = [v for v in result.violations if "AST_VERIFY" in v]
        self.assertEqual(len(ast_violations), 0)


class TestViolationFields(unittest.TestCase):
    """Violation dataclass fields are fully populated on detection."""

    def setUp(self):
        from core.ast_verifier import ASTVerifier
        self.verifier = ASTVerifier()

    def test_violation_has_rule_id(self):
        result = self.verifier.verify("eval(user_input)")
        self.assertTrue(len(result.violations) > 0)
        self.assertIn("rule_id", result.violations[0])

    def test_violation_has_severity_block(self):
        result = self.verifier.verify("eval(x)")
        self.assertEqual(result.violations[0]["severity"], "block")

    def test_violation_has_line_number(self):
        result = self.verifier.verify("x = 1\neval(x)")
        v = result.violations[0]
        self.assertIsInstance(v["line_number"], int)
        self.assertGreaterEqual(v["line_number"], 1)

    def test_violation_has_message(self):
        result = self.verifier.verify("exec('rm -rf /')")
        self.assertIn("message", result.violations[0])
        self.assertIsInstance(result.violations[0]["message"], str)

    def test_violation_has_code_snippet(self):
        result = self.verifier.verify("import subprocess")
        self.assertIn("code_snippet", result.violations[0])

    def test_rule_id_matches_category(self):
        result = self.verifier.verify("import subprocess")
        self.assertEqual(result.violations[0]["rule_id"], "BLOCKED_IMPORTS")

    def test_eval_rule_id_unsafe_calls(self):
        result = self.verifier.verify("eval(x)")
        self.assertEqual(result.violations[0]["rule_id"], "UNSAFE_CALLS")


class TestSecretPatternsExtra(unittest.TestCase):
    """Additional SECRET_PATTERNS beyond OpenAI/GitHub/AWS."""

    def setUp(self):
        from core.ast_verifier import ASTVerifier
        self.verifier = ASTVerifier()

    def test_github_oauth_token(self):
        code = 'TOKEN = "gho_' + 'a' * 36 + '"'
        result = self.verifier.verify(code)
        self.assertFalse(result.passed)

    def test_gitlab_pat(self):
        code = 'KEY = "glpat-' + 'a' * 20 + '"'
        result = self.verifier.verify(code)
        self.assertFalse(result.passed)

    def test_slack_token(self):
        code = 'SLACK = "xoxb-' + 'a1b2c3d4e5-f6g7h8i9j0' + '"'
        result = self.verifier.verify(code)
        self.assertFalse(result.passed)

    def test_secret_violation_rule_id(self):
        code = 'K = "AKIA' + 'A' * 16 + '"'
        result = self.verifier.verify(code)
        secret_violations = [v for v in result.violations if v["rule_id"] == "SECRET_PATTERNS"]
        self.assertGreater(len(secret_violations), 0)


class TestVerificationResultStructure(unittest.TestCase):
    """VerificationResult fields and invariants."""

    def setUp(self):
        from core.ast_verifier import ASTVerifier
        self.verifier = ASTVerifier()

    def test_passed_true_means_no_violations(self):
        result = self.verifier.verify("x = 1 + 2")
        if result.passed:
            self.assertEqual(len(result.violations), 0)

    def test_failed_means_violations_non_empty(self):
        result = self.verifier.verify("eval(x)")
        self.assertFalse(result.passed)
        self.assertGreater(len(result.violations), 0)

    def test_score_1_when_clean(self):
        result = self.verifier.verify("x = [i for i in range(10)]")
        self.assertAlmostEqual(result.score, 1.0)

    def test_score_between_0_and_1(self):
        result = self.verifier.verify("eval(x)\nexec(y)")
        self.assertGreaterEqual(result.score, 0.0)
        self.assertLessEqual(result.score, 1.0)

    def test_violations_list_of_dicts(self):
        result = self.verifier.verify("import subprocess")
        self.assertIsInstance(result.violations, list)
        self.assertIsInstance(result.violations[0], dict)


if __name__ == "__main__":
    unittest.main()
