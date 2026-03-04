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


if __name__ == "__main__":
    unittest.main()
