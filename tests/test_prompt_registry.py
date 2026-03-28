"""
Tests for core.prompt_registry — Prompt Version Control.

Minimum 15 tests covering: register, get, diff, rollback,
list_versions, list_prompts, hash determinism, duplicate detection,
evaluate_change, edge cases.
"""

import os
import json
import tempfile
import unittest

from core.prompt_registry import PromptRegistry, PromptVersion, PromptDiff


class TestPromptRegistry(unittest.TestCase):
    """Tests for PromptRegistry."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.storage = os.path.join(self.tmpdir, "registry.jsonl")
        self.reg = PromptRegistry(storage_path=self.storage)

    # ── register ─────────────────────────────────────────────────

    def test_register_creates_version_1(self):
        """First registration creates version 1."""
        pv = self.reg.register("greet", "Hello {name}", "alice")
        self.assertEqual(pv.version, 1)
        self.assertEqual(pv.name, "greet")
        self.assertTrue(pv.active)

    def test_register_auto_increments_version(self):
        """Successive registrations increment the version."""
        self.reg.register("greet", "Hello {name}", "alice")
        pv2 = self.reg.register("greet", "Hi {name}!", "bob")
        self.assertEqual(pv2.version, 2)

    def test_register_deactivates_previous(self):
        """Registering a new version deactivates old ones."""
        self.reg.register("greet", "Hello {name}", "alice")
        self.reg.register("greet", "Hi {name}!", "bob")
        v1 = self.reg.get("greet", version=1)
        v2 = self.reg.get("greet", version=2)
        self.assertFalse(v1.active)
        self.assertTrue(v2.active)

    def test_register_with_tags(self):
        """Tags are stored correctly."""
        pv = self.reg.register("greet", "Hello", "alice", tags=["prod", "v1"])
        self.assertEqual(pv.tags, ["prod", "v1"])

    def test_register_empty_name_raises(self):
        """Empty name raises ValueError."""
        with self.assertRaises(ValueError):
            self.reg.register("", "content", "alice")

    def test_register_empty_content_raises(self):
        """Empty content raises ValueError."""
        with self.assertRaises(ValueError):
            self.reg.register("x", "", "alice")

    # ── get ──────────────────────────────────────────────────────

    def test_get_latest_returns_active(self):
        """get(name) without version returns the active version."""
        self.reg.register("greet", "v1 content", "alice")
        self.reg.register("greet", "v2 content", "bob")
        pv = self.reg.get("greet")
        self.assertEqual(pv.version, 2)
        self.assertEqual(pv.content, "v2 content")

    def test_get_specific_version(self):
        """get(name, version) returns that exact version."""
        self.reg.register("greet", "v1 content", "alice")
        self.reg.register("greet", "v2 content", "bob")
        pv = self.reg.get("greet", version=1)
        self.assertEqual(pv.content, "v1 content")

    def test_get_nonexistent_raises(self):
        """Getting a nonexistent prompt raises KeyError."""
        with self.assertRaises(KeyError):
            self.reg.get("nope")

    def test_get_nonexistent_version_raises(self):
        """Getting a nonexistent version raises KeyError."""
        self.reg.register("greet", "Hello", "alice")
        with self.assertRaises(KeyError):
            self.reg.get("greet", version=99)

    # ── hash determinism ─────────────────────────────────────────

    def test_hash_determinism(self):
        """Same content always produces the same hash."""
        h1 = PromptRegistry._hash_content("Hello World")
        h2 = PromptRegistry._hash_content("Hello World")
        self.assertEqual(h1, h2)

    def test_hash_different_content(self):
        """Different content produces different hashes."""
        h1 = PromptRegistry._hash_content("Hello")
        h2 = PromptRegistry._hash_content("Goodbye")
        self.assertNotEqual(h1, h2)

    # ── duplicate detection ──────────────────────────────────────

    def test_duplicate_content_raises(self):
        """Registering identical content for same prompt raises ValueError."""
        self.reg.register("greet", "Hello {name}", "alice")
        with self.assertRaises(ValueError) as ctx:
            self.reg.register("greet", "Hello {name}", "bob")
        self.assertIn("Duplicate", str(ctx.exception))

    def test_same_content_different_prompt_ok(self):
        """Same content under different prompt names is allowed."""
        self.reg.register("greet", "Hello", "alice")
        pv = self.reg.register("farewell", "Hello", "alice")
        self.assertEqual(pv.version, 1)

    # ── diff ─────────────────────────────────────────────────────

    def test_diff_detects_changes(self):
        """Diff identifies added and removed lines."""
        self.reg.register("prompt", "line1\nline2\nline3", "alice")
        self.reg.register("prompt", "line1\nline2_modified\nline3\nline4", "bob")
        d = self.reg.diff("prompt", 1, 2)
        self.assertIsInstance(d, PromptDiff)
        self.assertEqual(d.name, "prompt")
        self.assertEqual(d.v1, 1)
        self.assertEqual(d.v2, 2)
        self.assertIn("line2_modified", d.added_lines)
        self.assertIn("line2", d.removed_lines)
        self.assertGreater(d.changed_pct, 0)

    def test_diff_identical_versions(self):
        """Diff of a version with itself yields no changes."""
        self.reg.register("prompt", "same content", "alice")
        d = self.reg.diff("prompt", 1, 1)
        self.assertEqual(d.added_lines, [])
        self.assertEqual(d.removed_lines, [])
        self.assertEqual(d.changed_pct, 0)

    # ── rollback ─────────────────────────────────────────────────

    def test_rollback_activates_old_version(self):
        """Rollback makes the specified version active."""
        self.reg.register("greet", "v1", "alice")
        self.reg.register("greet", "v2", "bob")
        rolled = self.reg.rollback("greet", 1)
        self.assertTrue(rolled.active)
        self.assertEqual(rolled.version, 1)
        # v2 should be inactive
        v2 = self.reg.get("greet", version=2)
        self.assertFalse(v2.active)

    def test_rollback_get_returns_rolled_version(self):
        """After rollback, get() returns the rolled-back version."""
        self.reg.register("greet", "v1", "alice")
        self.reg.register("greet", "v2", "bob")
        self.reg.rollback("greet", 1)
        pv = self.reg.get("greet")
        self.assertEqual(pv.version, 1)

    def test_rollback_nonexistent_raises(self):
        """Rollback to nonexistent version raises KeyError."""
        self.reg.register("greet", "v1", "alice")
        with self.assertRaises(KeyError):
            self.reg.rollback("greet", 99)

    # ── list_versions / list_prompts ─────────────────────────────

    def test_list_versions(self):
        """list_versions returns all versions in order."""
        self.reg.register("greet", "v1", "alice")
        self.reg.register("greet", "v2", "bob")
        self.reg.register("greet", "v3", "carol")
        versions = self.reg.list_versions("greet")
        self.assertEqual(len(versions), 3)
        self.assertEqual([pv.version for pv in versions], [1, 2, 3])

    def test_list_versions_nonexistent_raises(self):
        """list_versions for nonexistent prompt raises KeyError."""
        with self.assertRaises(KeyError):
            self.reg.list_versions("nope")

    def test_list_prompts(self):
        """list_prompts returns sorted prompt names."""
        self.reg.register("zebra", "z", "alice")
        self.reg.register("alpha", "a", "bob")
        self.reg.register("mid", "m", "carol")
        names = self.reg.list_prompts()
        self.assertEqual(names, ["alpha", "mid", "zebra"])

    def test_list_prompts_empty(self):
        """list_prompts on empty registry returns empty list."""
        self.assertEqual(self.reg.list_prompts(), [])

    # ── evaluate_change ──────────────────────────────────────────

    def test_evaluate_change_structure(self):
        """evaluate_change returns proper structure for each test case."""
        self.reg.register("sum", "Add {a} + {b}", "alice")
        self.reg.register("sum", "Calculate sum of {a} and {b}", "bob")
        cases = [
            {"input": "a=1, b=2", "expected_output": "3"},
            {"input": "a=10, b=20"},
        ]
        results = self.reg.evaluate_change("sum", 1, 2, cases)
        self.assertEqual(len(results), 2)
        r = results[0]
        self.assertEqual(r["test_input"], "a=1, b=2")
        self.assertEqual(r["expected_output"], "3")
        self.assertEqual(r["old_version"], 1)
        self.assertEqual(r["new_version"], 2)
        self.assertIn("old_prompt", r)
        self.assertIn("new_prompt", r)
        self.assertIsNone(r["old_result"])
        self.assertIsNone(r["new_result"])
        self.assertIsNone(r["comparison"])

    # ── persistence ──────────────────────────────────────────────

    def test_persistence_across_instances(self):
        """Data survives creating a new registry instance."""
        self.reg.register("greet", "Hello", "alice")
        reg2 = PromptRegistry(storage_path=self.storage)
        pv = reg2.get("greet")
        self.assertEqual(pv.content, "Hello")
        self.assertEqual(pv.version, 1)

    def test_storage_file_is_valid_jsonl(self):
        """Storage file contains valid JSONL."""
        self.reg.register("a", "content_a", "alice")
        self.reg.register("b", "content_b", "bob")
        with open(self.storage, "r") as f:
            lines = [l.strip() for l in f if l.strip()]
        self.assertEqual(len(lines), 2)
        for line in lines:
            data = json.loads(line)
            self.assertIn("name", data)
            self.assertIn("hash", data)

    # ── edge case: multiple prompts independent ──────────────────

    def test_independent_prompt_versioning(self):
        """Different prompts version independently."""
        self.reg.register("a", "a1", "alice")
        self.reg.register("a", "a2", "alice")
        self.reg.register("b", "b1", "bob")
        self.assertEqual(self.reg.get("a").version, 2)
        self.assertEqual(self.reg.get("b").version, 1)


if __name__ == "__main__":
    unittest.main()
