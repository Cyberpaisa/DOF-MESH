"""Tests for 4-Strategy Compaction — Item 6 Plan Abril 2026."""
import os
import time
import json
import tempfile
import unittest
from unittest.mock import patch
from core.memory_manager import MemoryManager, MemoryEntry


def _make_manager_with_tmpdir(tmp_dir):
    m = MemoryManager.__new__(MemoryManager)
    m._short_term = {}
    m._long_term_file = os.path.join(tmp_dir, "long_term.jsonl")
    m._episodic_file = os.path.join(tmp_dir, "episodic.jsonl")
    return m


class TestCompact(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.m = _make_manager_with_tmpdir(self.tmp)

    def _write_entries(self, filepath, entries):
        from dataclasses import asdict
        with open(filepath, "w") as f:
            for e in entries:
                f.write(json.dumps(asdict(e), default=str) + "\n")

    # ── ttl_evict ──────────────────────────────────────────────────────────────

    def test_ttl_evict_removes_expired(self):
        now = time.time()
        entries = [
            MemoryEntry(key="old", value="v", memory_type="long_term",
                        created_at=now - 7200, ttl_seconds=3600),  # expired
            MemoryEntry(key="fresh", value="v", memory_type="long_term",
                        created_at=now, ttl_seconds=3600),          # valid
            MemoryEntry(key="no_ttl", value="v", memory_type="long_term",
                        created_at=now - 9999, ttl_seconds=0),     # no TTL, keep
        ]
        self._write_entries(self.m._long_term_file, entries)
        result = self.m.compact("ttl_evict")
        self.assertEqual(result["before"], 3)
        self.assertEqual(result["after"], 2)
        self.assertEqual(result["removed"], 1)

    # ── score_evict ────────────────────────────────────────────────────────────

    def test_score_evict_removes_never_recalled(self):
        entries = [
            MemoryEntry(key="k1", value="v", memory_type="long_term",
                        created_at=time.time(), access_count=0),
            MemoryEntry(key="k2", value="v", memory_type="long_term",
                        created_at=time.time(), access_count=3),
        ]
        self._write_entries(self.m._long_term_file, entries)
        result = self.m.compact("score_evict")
        self.assertEqual(result["after"], 1)
        remaining = self.m._load_jsonl(self.m._long_term_file)
        self.assertEqual(remaining[0].key, "k2")

    # ── dedup_merge ────────────────────────────────────────────────────────────

    def test_dedup_merge_keeps_most_recent(self):
        now = time.time()
        entries = [
            MemoryEntry(key="dup", value="old", memory_type="long_term",
                        created_at=now - 100),
            MemoryEntry(key="dup", value="new", memory_type="long_term",
                        created_at=now),
            MemoryEntry(key="unique", value="only", memory_type="long_term",
                        created_at=now),
        ]
        self._write_entries(self.m._long_term_file, entries)
        result = self.m.compact("dedup_merge")
        self.assertEqual(result["after"], 2)
        remaining = self.m._load_jsonl(self.m._long_term_file)
        dup_entry = next(e for e in remaining if e.key == "dup")
        self.assertEqual(dup_entry.value, "new")

    # ── summary_compress ───────────────────────────────────────────────────────

    def test_summary_compress_truncates_episodic(self):
        entries = [
            MemoryEntry(key="ep1", value="x" * 1000, memory_type="episodic",
                        created_at=time.time()),
            MemoryEntry(key="lt1", value="y" * 1000, memory_type="long_term",
                        created_at=time.time()),
        ]
        self._write_entries(self.m._episodic_file, entries)
        result = self.m.compact("summary_compress", target_file="episodic")
        remaining = self.m._load_jsonl(self.m._episodic_file)
        ep = next(e for e in remaining if e.key == "ep1")
        self.assertLessEqual(len(ep.value), 520)  # 500 + "…[compacted]"
        self.assertIn("compacted", ep.value)

    def test_summary_compress_preserves_long_term(self):
        entries = [
            MemoryEntry(key="lt1", value="z" * 1000, memory_type="long_term",
                        created_at=time.time()),
        ]
        self._write_entries(self.m._long_term_file, entries)
        self.m.compact("summary_compress", target_file="long_term")
        remaining = self.m._load_jsonl(self.m._long_term_file)
        # long_term entries are not compressed by summary_compress
        self.assertEqual(len(remaining[0].value), 1000)

    # ── atomic write ───────────────────────────────────────────────────────────

    def test_compact_uses_atomic_write(self):
        entries = [MemoryEntry(key="k", value="v", memory_type="long_term",
                               created_at=time.time())]
        self._write_entries(self.m._long_term_file, entries)
        self.m.compact("ttl_evict")
        # tmp file must be gone after successful compact
        self.assertFalse(os.path.exists(self.m._long_term_file + ".compact_tmp"))

    def test_unknown_strategy_raises(self):
        with self.assertRaises(ValueError):
            self.m.compact("nonexistent_strategy")

    def test_compact_method_exists(self):
        self.assertTrue(hasattr(self.m, "compact"))
        self.assertTrue(callable(self.m.compact))


if __name__ == "__main__":
    unittest.main()
