"""
Tests for core/sem_analyzer.py — Semantic diff layer for DOF-MESH.

All tests degrade gracefully when sem is not installed:
  - sem_diff() returns available=False
  - sem_verify_entities() returns (True, []) — neutral pass
  - sem_audit_entry() returns a "not available" note

When sem IS installed, tests verify entity-level detection and constitution
enforcement.
"""

import unittest
from unittest.mock import patch

from core.sem_analyzer import (
    sem_available,
    sem_audit_entry,
    sem_diff,
    sem_verify_entities,
)
from core.ast_verifier import ASTVerifier


# ─── helpers ──────────────────────────────────────────────────────────────────

BEFORE = """\
def calculate(x, y):
    return x + y

class Config:
    debug = False
"""

AFTER_MODIFIED = """\
def calculate(x, y):
    return x * y

class Config:
    debug = True
"""

AFTER_NEW_FUNC = """\
def calculate(x, y):
    return x + y

def send_data(url):
    pass

class Config:
    debug = False
"""

AFTER_BLOCKED_FUNC = """\
def calculate(x, y):
    return x + y

def exec(cmd):
    pass

class Config:
    debug = False
"""

IDENTICAL = BEFORE


# ─── sem_available ────────────────────────────────────────────────────────────

class TestSemAvailable(unittest.TestCase):
    def test_returns_bool(self):
        result = sem_available()
        self.assertIsInstance(result, bool)


# ─── sem_diff ─────────────────────────────────────────────────────────────────

class TestSemDiff(unittest.TestCase):

    def test_returns_required_keys(self):
        result = sem_diff(BEFORE, AFTER_MODIFIED)
        self.assertIn("available", result)
        self.assertIn("changes", result)
        self.assertIn("summary", result)
        self.assertIn("error", result)

    def test_identical_code_returns_no_changes(self):
        result = sem_diff(BEFORE, IDENTICAL)
        self.assertEqual(result["changes"], [])

    @unittest.skipUnless(sem_available(), "sem not installed")
    def test_detects_modified_function(self):
        result = sem_diff(BEFORE, AFTER_MODIFIED)
        self.assertIsNone(result["error"])
        entity_ids = [c["entityId"] for c in result["changes"]]
        self.assertTrue(
            any("calculate" in eid for eid in entity_ids),
            f"Expected 'calculate' in entity changes, got: {entity_ids}",
        )

    @unittest.skipUnless(sem_available(), "sem not installed")
    def test_detects_added_function(self):
        result = sem_diff(BEFORE, AFTER_NEW_FUNC)
        self.assertIsNone(result["error"])
        added = [c for c in result["changes"] if c["changeType"] == "added"]
        names = [c["entityName"] for c in added]
        self.assertIn("send_data", names)

    @unittest.skipUnless(sem_available(), "sem not installed")
    def test_change_type_values(self):
        result = sem_diff(BEFORE, AFTER_MODIFIED)
        for change in result["changes"]:
            self.assertIn(
                change["changeType"],
                {"added", "modified", "deleted", "renamed"},
            )

    @unittest.skipUnless(sem_available(), "sem not installed")
    def test_entity_type_values(self):
        result = sem_diff(BEFORE, AFTER_MODIFIED)
        for change in result["changes"]:
            self.assertIn(change["entityType"], {"function", "class", "method", "variable"})

    def test_fallback_when_sem_unavailable(self):
        with patch("core.sem_analyzer._SEM_AVAILABLE", False):
            result = sem_diff(BEFORE, AFTER_MODIFIED)
        self.assertFalse(result["available"])
        self.assertEqual(result["changes"], [])
        self.assertIsNone(result["error"])


# ─── sem_verify_entities ─────────────────────────────────────────────────────

class TestSemVerifyEntities(unittest.TestCase):

    def test_neutral_pass_when_unavailable(self):
        diff = {"available": False, "changes": []}
        passed, violations = sem_verify_entities(diff)
        self.assertTrue(passed)
        self.assertEqual(violations, [])

    def test_neutral_pass_when_no_changes(self):
        diff = {"available": True, "changes": [], "summary": {}}
        passed, violations = sem_verify_entities(diff)
        self.assertTrue(passed)
        self.assertEqual(violations, [])

    @unittest.skipUnless(sem_available(), "sem not installed")
    def test_blocked_entity_name_fails(self):
        """Function named 'exec' added — must be blocked by constitution."""
        diff = sem_diff(BEFORE, AFTER_BLOCKED_FUNC)
        rules = {"blocked_entities": ["exec"]}
        passed, violations = sem_verify_entities(diff, rules)
        self.assertFalse(passed)
        block_violations = [v for v in violations if v["severity"] == "block"]
        self.assertTrue(len(block_violations) > 0)
        rule_ids = [v["rule_id"] for v in block_violations]
        self.assertIn("SEM_BLOCKED_ENTITY", rule_ids)

    @unittest.skipUnless(sem_available(), "sem not installed")
    def test_allowed_modification_passes(self):
        """Modifying an existing function is allowed by default rules."""
        diff = sem_diff(BEFORE, AFTER_MODIFIED)
        rules = {"allowed_change_types": ["modified"]}
        passed, violations = sem_verify_entities(diff, rules)
        block_violations = [v for v in violations if v["severity"] == "block"]
        self.assertEqual(block_violations, [])

    @unittest.skipUnless(sem_available(), "sem not installed")
    def test_added_function_blocked_when_not_in_allowed(self):
        """Adding a new function is a warning when only 'modified' is allowed."""
        diff = sem_diff(BEFORE, AFTER_NEW_FUNC)
        rules = {"allowed_change_types": ["modified"]}
        passed, violations = sem_verify_entities(diff, rules)
        warn_violations = [v for v in violations if v["change"] == "added"]
        self.assertTrue(len(warn_violations) > 0)

    @unittest.skipUnless(sem_available(), "sem not installed")
    def test_empty_blocked_list_allows_everything(self):
        diff = sem_diff(BEFORE, AFTER_BLOCKED_FUNC)
        rules = {"blocked_entities": []}
        passed, violations = sem_verify_entities(diff, rules)
        block_violations = [v for v in violations if v["severity"] == "block"]
        self.assertEqual(block_violations, [])


# ─── sem_audit_entry ─────────────────────────────────────────────────────────

class TestSemAuditEntry(unittest.TestCase):

    def test_unavailable_returns_note(self):
        diff = {"available": False, "changes": []}
        entry = sem_audit_entry(diff, "agent-1687", "code_gen")
        self.assertIn("semantic_diff", entry)
        self.assertFalse(entry["semantic_diff"]["available"])

    def test_entry_contains_required_fields(self):
        diff = {
            "available": True,
            "changes": [
                {
                    "entityId": "f.py::function::foo",
                    "entityName": "foo",
                    "entityType": "function",
                    "changeType": "modified",
                }
            ],
            "summary": {"modified": 1, "total": 1},
        }
        entry = sem_audit_entry(diff, "apex-1687", "code_gen")
        sd = entry["semantic_diff"]
        self.assertEqual(sd["agent_id"], "apex-1687")
        self.assertEqual(sd["action"], "code_gen")
        self.assertIn("timestamp", sd)
        self.assertIn("entities", sd)
        self.assertIn("by_type", sd)

    def test_by_type_groups_correctly(self):
        diff = {
            "available": True,
            "changes": [
                {"entityId": "f.py::function::foo", "entityName": "foo",
                 "entityType": "function", "changeType": "modified"},
                {"entityId": "f.py::function::bar", "entityName": "bar",
                 "entityType": "function", "changeType": "added"},
            ],
            "summary": {},
        }
        entry = sem_audit_entry(diff, "agent", "action")
        by_type = entry["semantic_diff"]["by_type"]
        self.assertIn("modified", by_type)
        self.assertIn("added", by_type)
        self.assertEqual(len(by_type["modified"]), 1)
        self.assertEqual(len(by_type["added"]), 1)


# ─── ASTVerifier.verify_diff integration ──────────────────────────────────────

class TestASTVerifierDiff(unittest.TestCase):

    def setUp(self):
        self.verifier = ASTVerifier()

    def test_verify_diff_returns_verification_result(self):
        from core.ast_verifier import VerificationResult
        result = self.verifier.verify_diff(BEFORE, AFTER_MODIFIED)
        self.assertIsInstance(result, VerificationResult)

    def test_verify_diff_passes_clean_code(self):
        result = self.verifier.verify_diff(BEFORE, AFTER_MODIFIED)
        self.assertTrue(result.passed)

    def test_verify_diff_blocks_unsafe_code(self):
        after_unsafe = """\
def calculate(x, y):
    eval("rm -rf /")
    return x + y
"""
        result = self.verifier.verify_diff(BEFORE, after_unsafe)
        self.assertFalse(result.passed)

    def test_verify_diff_has_semantic_diff_field(self):
        result = self.verifier.verify_diff(BEFORE, AFTER_MODIFIED)
        self.assertIsInstance(result.semantic_diff, dict)

    @unittest.skipUnless(sem_available(), "sem not installed")
    def test_verify_diff_blocks_blocked_entity_via_constitution(self):
        """Adding a function named 'exec' — blocked by constitution rule."""
        rules = {"blocked_entities": ["exec"]}
        result = self.verifier.verify_diff(BEFORE, AFTER_BLOCKED_FUNC, constitution_rules=rules)
        self.assertFalse(result.passed)
        rule_ids = [v.get("rule_id") for v in result.violations]
        self.assertIn("SEM_BLOCKED_ENTITY", rule_ids)

    @unittest.skipUnless(sem_available(), "sem not installed")
    def test_verify_diff_semantic_diff_has_entities(self):
        result = self.verifier.verify_diff(BEFORE, AFTER_MODIFIED)
        if result.semantic_diff.get("available") is not False:
            self.assertIn("entities", result.semantic_diff)

    def test_verify_diff_falls_back_when_sem_unavailable(self):
        with patch("core.sem_analyzer._SEM_AVAILABLE", False):
            result = self.verifier.verify_diff(BEFORE, AFTER_MODIFIED)
        self.assertTrue(result.passed)  # clean code still passes


if __name__ == "__main__":
    unittest.main()
