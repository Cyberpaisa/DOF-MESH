"""
Tests for core/memory_manager.py — Cross-session memory with TTL.

All tests redirect MEMORY_DIR to a temp directory.
Zero LLM, zero network, fully deterministic.
"""

import json
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.memory_manager as mm_mod
from core.memory_manager import MemoryEntry, MemoryManager


# ── Isolation mixin ──────────────────────────────────────────────────

class TmpMemoryMixin(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._orig = mm_mod.MEMORY_DIR
        mm_mod.MEMORY_DIR = self._tmpdir

    def tearDown(self):
        mm_mod.MEMORY_DIR = self._orig

    def _mgr(self) -> MemoryManager:
        return MemoryManager()


# ─────────────────────────────────────────────────────────────────────
# MemoryEntry dataclass
# ─────────────────────────────────────────────────────────────────────

class TestMemoryEntry(unittest.TestCase):

    def test_fields_set(self):
        e = MemoryEntry(key="k", value="v", memory_type="short_term")
        self.assertEqual(e.key, "k")
        self.assertEqual(e.value, "v")
        self.assertEqual(e.memory_type, "short_term")

    def test_defaults(self):
        e = MemoryEntry(key="k", value="v", memory_type="long_term")
        self.assertEqual(e.ttl_seconds, 0.0)
        self.assertEqual(e.created_at, 0.0)
        self.assertIsNone(e.tags)


# ─────────────────────────────────────────────────────────────────────
# Short-term: remember / recall
# ─────────────────────────────────────────────────────────────────────

class TestShortTerm(TmpMemoryMixin):

    def test_remember_and_recall(self):
        m = self._mgr()
        m.remember("foo", "bar")
        self.assertEqual(m.recall("foo"), "bar")

    def test_recall_missing_key_returns_none(self):
        self.assertIsNone(self._mgr().recall("ghost"))

    def test_recall_within_ttl_returns_value(self):
        m = self._mgr()
        m.remember("k", "v", ttl=3600)
        self.assertEqual(m.recall("k"), "v")

    def test_recall_after_ttl_returns_none(self):
        m = self._mgr()
        m.remember("k", "v", ttl=0.001)
        time.sleep(0.01)
        self.assertIsNone(m.recall("k"))

    def test_expired_key_removed_from_store(self):
        m = self._mgr()
        m.remember("k", "v", ttl=0.001)
        time.sleep(0.01)
        m.recall("k")
        self.assertNotIn("k", m._short_term)

    def test_zero_ttl_never_expires(self):
        m = self._mgr()
        m.remember("k", "v", ttl=0)
        self.assertEqual(m.recall("k"), "v")

    def test_overwrite_key(self):
        m = self._mgr()
        m.remember("k", "first")
        m.remember("k", "second")
        self.assertEqual(m.recall("k"), "second")

    def test_source_stored(self):
        m = self._mgr()
        m.remember("k", "v", source="agent_x")
        self.assertEqual(m._short_term["k"].source, "agent_x")

    def test_tags_stored(self):
        m = self._mgr()
        m.remember("k", "v", tags=["z3", "proof"])
        self.assertEqual(m._short_term["k"].tags, ["z3", "proof"])


# ─────────────────────────────────────────────────────────────────────
# get_context()
# ─────────────────────────────────────────────────────────────────────

class TestGetContext(TmpMemoryMixin):

    def test_empty_context_when_no_memory(self):
        self.assertEqual(self._mgr().get_context(), "")

    def test_context_is_string(self):
        m = self._mgr()
        m.remember("topic", "DOF governance")
        ctx = m.get_context()
        self.assertIsInstance(ctx, str)

    def test_context_contains_keys(self):
        m = self._mgr()
        m.remember("run_id", "abc123")
        self.assertIn("run_id", m.get_context())

    def test_context_contains_values(self):
        m = self._mgr()
        m.remember("provider", "groq")
        self.assertIn("groq", m.get_context())

    def test_max_entries_respected(self):
        m = self._mgr()
        for i in range(20):
            m.remember(f"key_{i}", f"val_{i}")
        ctx = m.get_context(max_entries=3)
        # Each entry formats as "- **key**: value" → 2 ** tokens per entry
        self.assertLessEqual(ctx.count("- **"), 3)

    def test_expired_entries_excluded(self):
        m = self._mgr()
        m.remember("fresh", "yes", ttl=3600)
        m.remember("stale", "no",  ttl=0.001)
        time.sleep(0.01)
        ctx = m.get_context()
        self.assertIn("fresh", ctx)
        self.assertNotIn("stale", ctx)


# ─────────────────────────────────────────────────────────────────────
# Long-term: store_long_term / search_long_term
# ─────────────────────────────────────────────────────────────────────

class TestLongTerm(TmpMemoryMixin):

    def test_store_creates_file(self):
        m = self._mgr()
        m.store_long_term("fact_1", "Z3 verifies 8 invariants in 109ms")
        self.assertTrue(os.path.exists(m._long_term_file))

    def test_stored_entry_is_valid_jsonl(self):
        m = self._mgr()
        m.store_long_term("k", "v")
        with open(m._long_term_file) as f:
            row = json.loads(f.readline())
        self.assertEqual(row["key"], "k")
        self.assertEqual(row["value"], "v")
        self.assertEqual(row["memory_type"], "long_term")

    def test_search_returns_relevant_entry(self):
        m = self._mgr()
        m.store_long_term("z3_result", "Z3 theorem prover verified all invariants")
        m.store_long_term("perf",      "Qwen3 runs at 60 tok/s on M4 Max")
        results = m.search_long_term("Z3 theorem proof")
        self.assertTrue(len(results) > 0)
        keys = [r.key for r in results]
        self.assertIn("z3_result", keys)

    def test_search_empty_store_returns_empty(self):
        m = self._mgr()
        self.assertEqual(m.search_long_term("anything"), [])

    def test_search_max_results_respected(self):
        m = self._mgr()
        for i in range(10):
            m.store_long_term(f"fact_{i}", f"DOF fact number {i} about governance")
        results = m.search_long_term("DOF governance", max_results=3)
        self.assertLessEqual(len(results), 3)

    def test_search_returns_memory_entries(self):
        m = self._mgr()
        m.store_long_term("k", "some relevant knowledge about DOF")
        results = m.search_long_term("DOF knowledge")
        for r in results:
            self.assertIsInstance(r, MemoryEntry)

    def test_multiple_stores_appended(self):
        m = self._mgr()
        m.store_long_term("a", "alpha")
        m.store_long_term("b", "beta")
        m.store_long_term("c", "gamma")
        loaded = MemoryManager._load_jsonl(m._long_term_file)
        self.assertEqual(len(loaded), 3)


# ─────────────────────────────────────────────────────────────────────
# Episodic: store_episode / get_recent_episodes
# ─────────────────────────────────────────────────────────────────────

class TestEpisodic(TmpMemoryMixin):

    def test_store_episode_creates_file(self):
        m = self._mgr()
        m.store_episode("r1", "gov_crew", "input", "output", "ok")
        self.assertTrue(os.path.exists(m._episodic_file))

    def test_get_recent_episodes_returns_list(self):
        m = self._mgr()
        m.store_episode("r1", "gov_crew", "in", "out", "ok")
        eps = m.get_recent_episodes()
        self.assertIsInstance(eps, list)

    def test_episode_fields_present(self):
        m = self._mgr()
        m.store_episode("r1", "gov_crew", "question", "answer", "ok")
        ep = m.get_recent_episodes()[0]
        for field in ("crew", "input", "output", "status", "timestamp"):
            self.assertIn(field, ep)

    def test_episode_input_truncated_at_500(self):
        m = self._mgr()
        m.store_episode("r1", "c", "x" * 600, "out", "ok")
        ep = m.get_recent_episodes()[0]
        self.assertLessEqual(len(ep["input"]), 500)

    def test_episode_output_truncated_at_2000(self):
        m = self._mgr()
        m.store_episode("r1", "c", "in", "y" * 3000, "ok")
        ep = m.get_recent_episodes()[0]
        self.assertLessEqual(len(ep["output"]), 2000)

    def test_filter_by_crew_name(self):
        m = self._mgr()
        m.store_episode("r1", "crew_a", "in", "out", "ok")
        m.store_episode("r2", "crew_b", "in", "out", "ok")
        eps = m.get_recent_episodes(crew_name="crew_a")
        self.assertEqual(len(eps), 1)
        self.assertEqual(eps[0]["crew"], "crew_a")

    def test_n_limit_respected(self):
        m = self._mgr()
        for i in range(10):
            m.store_episode(f"r{i}", "crew_x", "in", "out", "ok")
        eps = m.get_recent_episodes(n=3)
        self.assertLessEqual(len(eps), 3)

    def test_empty_episodes_returns_empty_list(self):
        self.assertEqual(self._mgr().get_recent_episodes(), [])


# ─────────────────────────────────────────────────────────────────────
# _cleanup_expired()
# ─────────────────────────────────────────────────────────────────────

class TestCleanup(TmpMemoryMixin):

    def test_removes_expired_entries(self):
        m = self._mgr()
        m.remember("stale", "v", ttl=0.001)
        m.remember("fresh", "v", ttl=3600)
        time.sleep(0.01)
        m._cleanup_expired()
        self.assertNotIn("stale", m._short_term)
        self.assertIn("fresh", m._short_term)

    def test_no_expiry_when_ttl_zero(self):
        m = self._mgr()
        m.remember("permanent", "v", ttl=0)
        m._cleanup_expired()
        self.assertIn("permanent", m._short_term)


# ─────────────────────────────────────────────────────────────────────
# _append_jsonl / _load_jsonl static methods
# ─────────────────────────────────────────────────────────────────────

class TestJSONL(TmpMemoryMixin):

    def test_load_nonexistent_file_returns_empty(self):
        path = os.path.join(self._tmpdir, "ghost.jsonl")
        self.assertEqual(MemoryManager._load_jsonl(path), [])

    def test_roundtrip_single_entry(self):
        path = os.path.join(self._tmpdir, "test.jsonl")
        e = MemoryEntry(key="k", value="v", memory_type="long_term",
                        created_at=12345.0, source="test")
        MemoryManager._append_jsonl(path, e)
        loaded = MemoryManager._load_jsonl(path)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].key, "k")
        self.assertEqual(loaded[0].value, "v")

    def test_roundtrip_multiple_entries(self):
        path = os.path.join(self._tmpdir, "multi.jsonl")
        for i in range(5):
            MemoryManager._append_jsonl(
                path, MemoryEntry(key=f"k{i}", value=f"v{i}", memory_type="episodic")
            )
        loaded = MemoryManager._load_jsonl(path)
        self.assertEqual(len(loaded), 5)
        self.assertEqual([e.key for e in loaded], [f"k{i}" for i in range(5)])


class TestGetRecentEpisodesNonPositiveN(unittest.TestCase):
    """get_recent_episodes(n<=0) must return [] — Python -0 gotcha guard."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        mm_mod.MEMORY_DIR = self.tmpdir
        self.mm = MemoryManager()
        for i in range(5):
            self.mm.store_episode(f"r{i}", "crew", f"in{i}", f"out{i}", "ok")

    def test_n_zero_returns_empty(self):
        self.assertEqual(self.mm.get_recent_episodes(n=0), [])

    def test_n_negative_returns_empty(self):
        self.assertEqual(self.mm.get_recent_episodes(n=-1), [])

    def test_n_positive_returns_data(self):
        self.assertEqual(len(self.mm.get_recent_episodes(n=3)), 3)


if __name__ == "__main__":
    unittest.main()
