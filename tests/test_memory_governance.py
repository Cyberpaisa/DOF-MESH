"""
Tests for core/memory_governance.py — GovernedMemoryStore + TemporalGraph +
MemoryClassifier + ConstitutionalDecay.

Session 9:  GovernedMemoryStore (~25 tests)
Session 10: TemporalGraph (~15 tests)
Session 11: MemoryClassifier + ConstitutionalDecay (~15 tests)
"""

import os
import sys
import unittest
import tempfile
import shutil
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.memory_governance import (
    GovernedMemoryStore, MemoryEntry, TemporalGraph, VALID_CATEGORIES,
    MemoryClassifier, ConstitutionalDecay,
)


# ─────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────

# Passes ALL governance rules (has URL, structure, actionable, English, >50 chars)
APPROVED_CONTENT = (
    "## Formal Verification\n\n"
    "- Implement the Z3 theorem prover for invariant checking.\n"
    "- See https://z3prover.github.io/ for documentation.\n\n"
    "Next step: deploy the verification module to production."
)

# Passes HARD rules but fails SOFT rules (no URL, no structure, no actionable)
WARNING_CONTENT = (
    "The primary component encountered significant delays during standard "
    "procedures in the test environment. The measurements were recorded "
    "for comprehensive monitoring of the system state."
)

# Violates NO_HALLUCINATION_CLAIM (contains 'statistics show' without URL)
REJECTED_CONTENT = (
    "Statistics show the results are definitive and clear across all "
    "experimental test domains in the primary system evaluation context."
)


def make_store(tmpdir: str) -> GovernedMemoryStore:
    store_file = os.path.join(tmpdir, "governed_store.jsonl")
    log_file = os.path.join(tmpdir, "memory_governance.jsonl")
    return GovernedMemoryStore(_store_file=store_file, _log_file=log_file)


class TestGovernanceStatus(unittest.TestCase):
    """Tests for governance status assignment in add()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = make_store(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_approved_content_gets_approved_status(self):
        entry = self.store.add(APPROVED_CONTENT, category="knowledge")
        self.assertEqual(entry.governance_status, "approved")

    def test_warning_content_gets_warning_status(self):
        entry = self.store.add(WARNING_CONTENT, category="knowledge")
        self.assertEqual(entry.governance_status, "warning")

    def test_warning_entry_is_stored_as_active(self):
        entry = self.store.add(WARNING_CONTENT, category="context")
        self.assertIsNone(entry.valid_to)
        active = self.store.query()
        self.assertTrue(any(e.id == entry.id for e in active))

    def test_rejected_content_gets_rejected_status(self):
        entry = self.store.add(REJECTED_CONTENT, category="knowledge")
        self.assertEqual(entry.governance_status, "rejected")

    def test_rejected_entry_not_returned_by_query(self):
        entry = self.store.add(REJECTED_CONTENT, category="knowledge")
        active = self.store.query()
        self.assertFalse(any(e.id == entry.id for e in active))

    def test_rejected_entry_is_persisted_for_audit(self):
        """Rejected entries must be in self._entries for audit trail."""
        entry = self.store.add(REJECTED_CONTENT, category="knowledge")
        all_ids = [e.id for e in self.store._entries]
        self.assertIn(entry.id, all_ids)


class TestAdd(unittest.TestCase):
    """Tests for add() basic behavior."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = make_store(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_add_returns_memory_entry(self):
        entry = self.store.add(APPROVED_CONTENT, category="knowledge")
        self.assertIsInstance(entry, MemoryEntry)

    def test_add_sets_version_1(self):
        entry = self.store.add(APPROVED_CONTENT, category="knowledge")
        self.assertEqual(entry.version, 1)

    def test_add_sets_relevance_1(self):
        entry = self.store.add(APPROVED_CONTENT, category="knowledge")
        self.assertEqual(entry.relevance_score, 1.0)

    def test_add_sets_valid_to_none(self):
        entry = self.store.add(APPROVED_CONTENT, category="knowledge")
        self.assertIsNone(entry.valid_to)

    def test_add_sets_no_parent_id(self):
        entry = self.store.add(APPROVED_CONTENT, category="knowledge")
        self.assertIsNone(entry.parent_id)

    def test_add_invalid_category_defaults_to_knowledge(self):
        entry = self.store.add(APPROVED_CONTENT, category="nonsense_category")
        self.assertEqual(entry.category, "knowledge")

    def test_add_metadata_stored(self):
        meta = {"source": "crew_runner", "run_id": "test-001"}
        entry = self.store.add(APPROVED_CONTENT, category="knowledge", metadata=meta)
        self.assertEqual(entry.metadata["source"], "crew_runner")


class TestUpdate(unittest.TestCase):
    """Tests for update() versioning."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = make_store(self.tmpdir)
        self.original = self.store.add(APPROVED_CONTENT, category="knowledge")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_update_creates_new_version(self):
        new_entry = self.store.update(self.original.id, WARNING_CONTENT)
        self.assertEqual(new_entry.version, 2)

    def test_update_sets_parent_id(self):
        new_entry = self.store.update(self.original.id, WARNING_CONTENT)
        self.assertEqual(new_entry.parent_id, self.original.id)

    def test_update_preserves_category(self):
        new_entry = self.store.update(self.original.id, WARNING_CONTENT)
        self.assertEqual(new_entry.category, self.original.category)

    def test_update_marks_old_version_expired(self):
        self.store.update(self.original.id, WARNING_CONTENT)
        old = next(e for e in self.store._entries if e.id == self.original.id)
        self.assertIsNotNone(old.valid_to)

    def test_update_new_version_is_active(self):
        new_entry = self.store.update(self.original.id, WARNING_CONTENT)
        self.assertIsNone(new_entry.valid_to)

    def test_update_chain_has_two_versions(self):
        new_entry = self.store.update(self.original.id, WARNING_CONTENT)
        history = self.store.get_history(self.original.id)
        self.assertEqual(len(history), 2)

    def test_update_parent_id_chain_is_intact(self):
        v2 = self.store.update(self.original.id, WARNING_CONTENT)
        v3_content = (
            "## Updated Recommendation\n\n"
            "- Use Bayesian selection. See https://example.com/\n\n"
            "Next step: deploy new provider selector."
        )
        v3 = self.store.update(v2.id, v3_content)
        history = self.store.get_history(self.original.id)
        # Should be v1, v2, v3 in chronological order
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0].id, self.original.id)
        self.assertEqual(history[1].id, v2.id)
        self.assertEqual(history[2].id, v3.id)


class TestDelete(unittest.TestCase):
    """Tests for delete() soft-delete behavior."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = make_store(self.tmpdir)
        self.entry = self.store.add(APPROVED_CONTENT, category="knowledge")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_delete_returns_true_for_existing(self):
        result = self.store.delete(self.entry.id, reason="test cleanup")
        self.assertTrue(result)

    def test_delete_returns_false_for_nonexistent(self):
        result = self.store.delete("nonexistent-id-000", reason="test")
        self.assertFalse(result)

    def test_delete_sets_valid_to(self):
        self.store.delete(self.entry.id)
        e = next(x for x in self.store._entries if x.id == self.entry.id)
        self.assertIsNotNone(e.valid_to)

    def test_delete_does_not_remove_entry(self):
        self.store.delete(self.entry.id)
        all_ids = [e.id for e in self.store._entries]
        self.assertIn(self.entry.id, all_ids)

    def test_deleted_entry_not_in_query_results(self):
        self.store.delete(self.entry.id)
        active = self.store.query()
        self.assertFalse(any(e.id == self.entry.id for e in active))


class TestQuery(unittest.TestCase):
    """Tests for query() filtering."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = make_store(self.tmpdir)
        self.k1 = self.store.add(APPROVED_CONTENT, category="knowledge")
        # Enough English markers so LANGUAGE_COMPLIANCE passes
        self.k2 = self.store.add(
            "The provider failed in the request. See https://groq.com/ for the error.\n\n"
            "- Retry is recommended with exponential backoff.\n\n"
            "Next step: implement the retry logic in the runner.",
            category="errors",
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_query_by_category_filters_correctly(self):
        results = self.store.query(category="knowledge")
        self.assertTrue(all(e.category == "knowledge" for e in results))
        self.assertEqual(len(results), 1)

    def test_query_by_category_errors(self):
        results = self.store.query(category="errors")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, self.k2.id)

    def test_query_no_filter_returns_all_active(self):
        results = self.store.query()
        active_ids = {e.id for e in results}
        self.assertIn(self.k1.id, active_ids)
        self.assertIn(self.k2.id, active_ids)

    def test_query_keyword_match(self):
        results = self.store.query(query="Z3")
        self.assertTrue(any(e.id == self.k1.id for e in results))

    def test_query_ordered_by_relevance_descending(self):
        self.k1.relevance_score = 0.5
        self.k2.relevance_score = 0.9
        results = self.store.query()
        self.assertGreaterEqual(results[0].relevance_score, results[-1].relevance_score)


class TestTemporalQuery(unittest.TestCase):
    """Tests for query() with as_of (point-in-time) filter."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = make_store(self.tmpdir)
        # Add entry and record the time before it
        self.before = datetime.utcnow()
        self.entry = self.store.add(APPROVED_CONTENT, category="knowledge")
        self.after = datetime.utcnow()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_query_as_of_before_entry_returns_empty(self):
        results = self.store.query(as_of=self.before)
        self.assertFalse(any(e.id == self.entry.id for e in results))

    def test_query_as_of_after_entry_returns_it(self):
        results = self.store.query(as_of=self.after)
        self.assertTrue(any(e.id == self.entry.id for e in results))

    def test_query_as_of_after_delete_returns_empty(self):
        self.store.delete(self.entry.id)
        future = datetime.utcnow() + timedelta(seconds=1)
        results = self.store.query(as_of=future)
        self.assertFalse(any(e.id == self.entry.id for e in results))


class TestGetHistory(unittest.TestCase):
    """Tests for get_history()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = make_store(self.tmpdir)
        self.v1 = self.store.add(APPROVED_CONTENT, category="decisions")
        self.v2 = self.store.update(self.v1.id, WARNING_CONTENT)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_history_returns_all_versions(self):
        history = self.store.get_history(self.v1.id)
        self.assertEqual(len(history), 2)

    def test_history_is_chronological(self):
        history = self.store.get_history(self.v1.id)
        self.assertEqual(history[0].id, self.v1.id)
        self.assertEqual(history[1].id, self.v2.id)

    def test_history_from_any_version_returns_full_chain(self):
        """get_history(v2.id) should return the same chain as get_history(v1.id)."""
        history_from_v2 = self.store.get_history(self.v2.id)
        self.assertEqual(len(history_from_v2), 2)

    def test_history_nonexistent_id_returns_empty(self):
        self.assertEqual(self.store.get_history("nonexistent"), [])


class TestPersistence(unittest.TestCase):
    """Tests that state survives across store instances."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_entries_survive_reload(self):
        store1 = make_store(self.tmpdir)
        e = store1.add(APPROVED_CONTENT, category="knowledge")
        entry_id = e.id

        store2 = make_store(self.tmpdir)
        loaded_ids = [x.id for x in store2._entries]
        self.assertIn(entry_id, loaded_ids)

    def test_deleted_entry_survives_as_inactive_after_reload(self):
        store1 = make_store(self.tmpdir)
        e = store1.add(APPROVED_CONTENT, category="knowledge")
        store1.delete(e.id, reason="test")

        store2 = make_store(self.tmpdir)
        active = store2.query()
        self.assertFalse(any(x.id == e.id for x in active))
        # But entry still present (soft delete)
        self.assertTrue(any(x.id == e.id for x in store2._entries))

    def test_version_chain_survives_reload(self):
        store1 = make_store(self.tmpdir)
        v1 = store1.add(APPROVED_CONTENT, category="decisions")
        v2 = store1.update(v1.id, WARNING_CONTENT)

        store2 = make_store(self.tmpdir)
        history = store2.get_history(v1.id)
        self.assertEqual(len(history), 2)


class TestSimilarityDetection(unittest.TestCase):
    """Tests for similar-memory detection triggering update instead of add."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = make_store(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_similar_content_triggers_update(self):
        # Use plain prose with enough English markers so LANGUAGE_COMPLIANCE passes,
        # and high keyword overlap between the two strings (>70%).
        base = (
            "The system uses formal verification with the Z3 theorem prover "
            "to verify the GCR invariant. We recommend the approach for all "
            "implementations. See https://z3prover.github.io/ for the details."
        )
        similar = (
            "The system uses formal verification with the Z3 theorem prover "
            "to verify the GCR invariant value. We recommend the approach for all "
            "implementations. See https://z3prover.github.io/ for the details."
        )
        v1 = self.store.add(base, category="knowledge")
        v2 = self.store.add(similar, category="knowledge")

        # Second add should have returned an update (version 2, parent = v1)
        self.assertEqual(v2.version, 2)
        self.assertEqual(v2.parent_id, v1.id)

    def test_dissimilar_content_creates_new_entry(self):
        self.store.add(APPROVED_CONTENT, category="knowledge")
        entry2 = self.store.add(
            "## Error Classification\n\n"
            "- Rate limit exceeded on Groq provider. See https://console.groq.com/\n\n"
            "Next step: implement exponential backoff.",
            category="errors",
        )
        # Different category + different content → new entry, version 1
        self.assertEqual(entry2.version, 1)
        self.assertIsNone(entry2.parent_id)


class TestGetStats(unittest.TestCase):
    """Tests for get_stats()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = make_store(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_stats_has_required_keys(self):
        stats = self.store.get_stats()
        for key in ("total_memories", "active_memories", "by_category", "by_status", "avg_relevance"):
            self.assertIn(key, stats)

    def test_stats_counts_active_correctly(self):
        self.store.add(APPROVED_CONTENT, category="knowledge")
        stats = self.store.get_stats()
        self.assertEqual(stats["active_memories"], 1)

    def test_stats_rejected_not_counted_in_active(self):
        self.store.add(REJECTED_CONTENT, category="knowledge")
        stats = self.store.get_stats()
        self.assertEqual(stats["active_memories"], 0)

    def test_stats_by_category(self):
        self.store.add(APPROVED_CONTENT, category="knowledge")
        stats = self.store.get_stats()
        self.assertEqual(stats["by_category"].get("knowledge", 0), 1)


# ═════════════════════════════════════════════════════════════════════
# Session 10: TemporalGraph tests
# ═════════════════════════════════════════════════════════════════════

class TestSnapshot(unittest.TestCase):
    """Tests for TemporalGraph.snapshot()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = make_store(self.tmpdir)
        self.graph = TemporalGraph(self.store)
        self.before_add = datetime.utcnow()
        self.e1 = self.store.add(APPROVED_CONTENT, category="knowledge")
        self.after_add = datetime.utcnow()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_snapshot_before_add_is_empty(self):
        snap = self.graph.snapshot(as_of=self.before_add)
        self.assertEqual(len(snap), 0)

    def test_snapshot_after_add_contains_entry(self):
        snap = self.graph.snapshot(as_of=self.after_add)
        ids = [e.id for e in snap]
        self.assertIn(self.e1.id, ids)

    def test_snapshot_after_delete_excludes_entry(self):
        self.store.delete(self.e1.id)
        future = datetime.utcnow() + timedelta(seconds=1)
        snap = self.graph.snapshot(as_of=future)
        ids = [e.id for e in snap]
        self.assertNotIn(self.e1.id, ids)

    def test_snapshot_returns_correct_version(self):
        """After update, snapshot before the update returns v1, after returns v2."""
        v2 = self.store.update(self.e1.id, WARNING_CONTENT)
        after_update = datetime.utcnow()

        # Snapshot between original add and update → v1
        snap_before = self.graph.snapshot(as_of=self.after_add)
        snap_ids_before = [e.id for e in snap_before]
        self.assertIn(self.e1.id, snap_ids_before)
        self.assertNotIn(v2.id, snap_ids_before)

        # Snapshot after update → v2
        snap_after = self.graph.snapshot(as_of=after_update)
        snap_ids_after = [e.id for e in snap_after]
        self.assertIn(v2.id, snap_ids_after)
        self.assertNotIn(self.e1.id, snap_ids_after)

    def test_snapshot_excludes_rejected(self):
        self.store.add(REJECTED_CONTENT, category="knowledge")
        snap = self.graph.snapshot(as_of=datetime.utcnow() + timedelta(seconds=1))
        for e in snap:
            self.assertNotEqual(e.governance_status, "rejected")


class TestTimeline(unittest.TestCase):
    """Tests for TemporalGraph.timeline()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = make_store(self.tmpdir)
        self.graph = TemporalGraph(self.store)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_timeline_add_event(self):
        self.store.add(APPROVED_CONTENT, category="knowledge")
        events = self.graph.timeline()
        self.assertTrue(any(ev["action"] == "ADD" for ev in events))

    def test_timeline_update_event(self):
        e = self.store.add(APPROVED_CONTENT, category="knowledge")
        self.store.update(e.id, WARNING_CONTENT)
        events = self.graph.timeline()
        actions = [ev["action"] for ev in events]
        self.assertIn("ADD", actions)
        self.assertIn("UPDATE", actions)

    def test_timeline_delete_event(self):
        e = self.store.add(APPROVED_CONTENT, category="knowledge")
        self.store.delete(e.id)
        events = self.graph.timeline()
        actions = [ev["action"] for ev in events]
        self.assertIn("DELETE", actions)

    def test_timeline_is_chronological(self):
        self.store.add(APPROVED_CONTENT, category="knowledge")
        events = self.graph.timeline()
        timestamps = [ev["timestamp"] for ev in events]
        self.assertEqual(timestamps, sorted(timestamps))

    def test_timeline_filtered_by_category(self):
        self.store.add(APPROVED_CONTENT, category="knowledge")
        self.store.add(
            "The provider failed in the request. See https://groq.com/ for the error.\n\n"
            "- Retry is recommended with exponential backoff.\n\n"
            "Next step: implement the retry logic in the runner.",
            category="errors",
        )
        events = self.graph.timeline(category="knowledge")
        for ev in events:
            self.assertEqual(ev["category"], "knowledge")

    def test_timeline_content_summary_max_100_chars(self):
        self.store.add(APPROVED_CONTENT, category="knowledge")
        events = self.graph.timeline()
        for ev in events:
            self.assertLessEqual(len(ev["content_summary"]), 100)


class TestDiff(unittest.TestCase):
    """Tests for TemporalGraph.diff()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = make_store(self.tmpdir)
        self.graph = TemporalGraph(self.store)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_diff_detects_added_entry(self):
        before = datetime.utcnow()
        self.store.add(APPROVED_CONTENT, category="knowledge")
        after = datetime.utcnow()
        d = self.graph.diff(before, after)
        self.assertEqual(len(d["added"]), 1)
        self.assertEqual(len(d["deleted"]), 0)
        self.assertEqual(d["unchanged"], 0)

    def test_diff_detects_deleted_entry(self):
        e = self.store.add(APPROVED_CONTENT, category="knowledge")
        after_add = datetime.utcnow()
        self.store.delete(e.id)
        after_delete = datetime.utcnow() + timedelta(seconds=1)
        d = self.graph.diff(after_add, after_delete)
        self.assertEqual(len(d["deleted"]), 1)

    def test_diff_detects_updated_entry(self):
        e = self.store.add(APPROVED_CONTENT, category="decisions")
        after_add = datetime.utcnow()
        self.store.update(e.id, WARNING_CONTENT)
        after_update = datetime.utcnow()
        d = self.graph.diff(after_add, after_update)
        self.assertEqual(len(d["updated"]), 1)

    def test_diff_unchanged_count(self):
        self.store.add(APPROVED_CONTENT, category="knowledge")
        t1 = datetime.utcnow()
        t2 = datetime.utcnow()
        d = self.graph.diff(t1, t2)
        self.assertEqual(d["unchanged"], 1)

    def test_diff_has_required_keys(self):
        d = self.graph.diff(datetime.utcnow(), datetime.utcnow())
        for key in ("added", "updated", "deleted", "unchanged"):
            self.assertIn(key, d)


class TestAgeDistribution(unittest.TestCase):
    """Tests for TemporalGraph.memory_age_distribution()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = make_store(self.tmpdir)
        self.graph = TemporalGraph(self.store)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_distribution_has_all_buckets(self):
        dist = self.graph.memory_age_distribution()
        for bucket in ("<1h", "1h-24h", "1d-7d", "7d-30d", ">30d"):
            self.assertIn(bucket, dist)

    def test_new_entry_in_less_than_1h_bucket(self):
        self.store.add(APPROVED_CONTENT, category="knowledge")
        dist = self.graph.memory_age_distribution()
        self.assertEqual(dist["<1h"], 1)

    def test_empty_store_all_buckets_zero(self):
        dist = self.graph.memory_age_distribution()
        self.assertEqual(sum(dist.values()), 0)


# ═════════════════════════════════════════════════════════════════════
# Session 11: MemoryClassifier + ConstitutionalDecay tests
# ═════════════════════════════════════════════════════════════════════

class TestMemoryClassifier(unittest.TestCase):
    """Tests for MemoryClassifier.classify() and classify_with_confidence()."""

    def setUp(self):
        self.classifier = MemoryClassifier()

    def test_classify_error_in_provider(self):
        self.assertEqual(self.classifier.classify("error in provider"), "errors")

    def test_classify_decided_to_use_z3(self):
        self.assertEqual(self.classifier.classify("we decided to use Z3"), "decisions")

    def test_classify_api_key_configuration(self):
        self.assertEqual(self.classifier.classify("API key configuration setting"), "preferences")

    def test_classify_working_on_research_task(self):
        self.assertEqual(self.classifier.classify("working on research task"), "context")

    def test_classify_framework_uses_five_metrics(self):
        self.assertEqual(self.classifier.classify("the framework uses 5 metrics"), "knowledge")

    def test_classify_with_confidence_low_returns_uncategorized(self):
        """Content with no matching keywords → low confidence → uncategorized."""
        category, confidence = self.classifier.classify_with_confidence(
            "the framework uses 5 metrics for observability"
        )
        self.assertEqual(category, "uncategorized")
        self.assertLess(confidence, 0.3)

    def test_classify_with_confidence_high_returns_category(self):
        """Content with multiple matching keywords → high confidence."""
        # 5 errors keywords + "decided" = 6/18 = 0.333 → ≥ 0.3
        category, confidence = self.classifier.classify_with_confidence(
            "error crash exception fail bug and we decided to fix"
        )
        self.assertEqual(category, "errors")
        self.assertGreaterEqual(confidence, 0.3)


class TestConstitutionalDecay(unittest.TestCase):
    """Tests for ConstitutionalDecay."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = make_store(self.tmpdir)
        decay_log = os.path.join(self.tmpdir, "memory_decay.jsonl")
        self.decay = ConstitutionalDecay(
            self.store, decay_lambda=0.99, threshold=0.1,
            _decay_log_file=decay_log,
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_decay_reduces_relevance_score(self):
        """Decay cycle should reduce score for old memories."""
        entry = self.store.add(APPROVED_CONTENT, category="knowledge")
        # Simulate aging: set valid_from to 100 hours ago
        entry.valid_from = (datetime.utcnow() - timedelta(hours=100)).isoformat()
        original_score = entry.relevance_score

        self.decay.decay_cycle()
        self.assertLess(entry.relevance_score, original_score)

    def test_protected_categories_do_not_decay(self):
        """Decisions and errors categories must never decay."""
        entry = self.store.add(
            "## Decision Record\n\n"
            "- We decided to use the Z3 theorem prover. See https://z3prover.github.io/\n\n"
            "Next step: integrate with the governance module.",
            category="decisions",
        )
        entry.valid_from = (datetime.utcnow() - timedelta(hours=500)).isoformat()
        original_score = entry.relevance_score

        result = self.decay.decay_cycle()
        self.assertEqual(entry.relevance_score, original_score)
        self.assertGreater(result["protected"], 0)

    def test_reinforce_increments_score(self):
        entry = self.store.add(APPROVED_CONTENT, category="knowledge")
        entry.relevance_score = 0.5
        new_score = self.decay.reinforce(entry.id, boost=0.2)
        self.assertAlmostEqual(new_score, 0.7)

    def test_reinforce_capped_at_1(self):
        entry = self.store.add(APPROVED_CONTENT, category="knowledge")
        entry.relevance_score = 0.95
        new_score = self.decay.reinforce(entry.id, boost=0.2)
        self.assertEqual(new_score, 1.0)

    def test_reinforce_nonexistent_returns_negative(self):
        self.assertEqual(self.decay.reinforce("nonexistent-id"), -1.0)

    def test_archived_when_below_threshold(self):
        """Memory with score below threshold should be archived (valid_to set)."""
        entry = self.store.add(APPROVED_CONTENT, category="knowledge")
        # Set score just above threshold, then age enough so decay drops it below
        entry.relevance_score = 0.12
        entry.valid_from = (datetime.utcnow() - timedelta(hours=200)).isoformat()

        result = self.decay.decay_cycle()
        self.assertGreater(result["archived"], 0)
        self.assertIsNotNone(entry.valid_to)

    def test_get_decay_status_sorted_ascending(self):
        e1 = self.store.add(APPROVED_CONTENT, category="knowledge")
        e2 = self.store.add(
            "The provider failed in the request. See https://groq.com/ for the error.\n\n"
            "- Retry is recommended with exponential backoff.\n\n"
            "Next step: implement the retry logic in the runner.",
            category="errors",
        )
        e1.relevance_score = 0.3
        e2.relevance_score = 0.9

        status = self.decay.get_decay_status()
        scores = [s["relevance_score"] for s in status]
        self.assertEqual(scores, sorted(scores))

    def test_decay_cycle_returns_required_keys(self):
        result = self.decay.decay_cycle()
        for key in ("processed", "decayed", "archived", "protected"):
            self.assertIn(key, result)


class TestAutoClassifyIntegration(unittest.TestCase):
    """Tests for auto-classify when add() receives no category."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = make_store(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_auto_classify_errors(self):
        """add() without category should auto-classify 'error' content as errors."""
        entry = self.store.add(
            "The system encountered an error in the provider chain. "
            "See https://groq.com/ for the error details.\n\n"
            "- Retry is recommended with exponential backoff.\n\n"
            "Next step: implement the retry logic in the runner."
        )
        self.assertEqual(entry.category, "errors")

    def test_auto_classify_knowledge_default(self):
        """add() without category should default to knowledge for generic content."""
        entry = self.store.add(APPROVED_CONTENT)
        self.assertEqual(entry.category, "knowledge")


class TestQueryReinforcement(unittest.TestCase):
    """Tests for query() reinforcing memories via decay."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = make_store(self.tmpdir)
        decay_log = os.path.join(self.tmpdir, "memory_decay.jsonl")
        self.decay = ConstitutionalDecay(
            self.store, _decay_log_file=decay_log,
        )
        # Wire decay into store
        self.store._decay = self.decay

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_query_reinforces_returned_memories(self):
        entry = self.store.add(APPROVED_CONTENT, category="knowledge")
        entry.relevance_score = 0.5

        self.store.query(query="Z3")
        # After query, score should have been boosted by 0.1
        self.assertAlmostEqual(entry.relevance_score, 0.6)


# ═════════════════════════════════════════════════════════════════════
# Session 12: Integration tests
# ═════════════════════════════════════════════════════════════════════

class TestConstitutionMemoryConfig(unittest.TestCase):
    """Test that dof.constitution.yml memory config loads correctly."""

    def test_constitution_has_memory_section(self):
        import yaml
        constitution_path = os.path.join(PROJECT_ROOT, "dof.constitution.yml")
        with open(constitution_path, "r") as f:
            data = yaml.safe_load(f)
        self.assertIn("memory", data)
        mem = data["memory"]
        self.assertIn("categories", mem)
        self.assertIn("decay", mem)
        self.assertIn("limits", mem)
        self.assertIn("governance", mem)

    def test_constitution_memory_categories_match(self):
        import yaml
        constitution_path = os.path.join(PROJECT_ROOT, "dof.constitution.yml")
        with open(constitution_path, "r") as f:
            data = yaml.safe_load(f)
        categories = set(data["memory"]["categories"])
        self.assertEqual(categories, VALID_CATEGORIES)

    def test_store_loads_memory_config_from_constitution(self):
        tmpdir = tempfile.mkdtemp()
        try:
            store = make_store(tmpdir)
            cfg = store._memory_config
            self.assertIn("categories", cfg)
            self.assertIn("decay", cfg)
            self.assertIn("limits", cfg)
            self.assertIn("governance", cfg)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_decay_config_values(self):
        import yaml
        constitution_path = os.path.join(PROJECT_ROOT, "dof.constitution.yml")
        with open(constitution_path, "r") as f:
            data = yaml.safe_load(f)
        decay = data["memory"]["decay"]
        self.assertEqual(decay["lambda"], 0.99)
        self.assertEqual(decay["threshold"], 0.1)
        self.assertIn("decisions", decay["protected_categories"])
        self.assertIn("errors", decay["protected_categories"])


class TestDashboardData(unittest.TestCase):
    """Test that dashboard-related methods return valid data."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = make_store(self.tmpdir)
        self.store.add(APPROVED_CONTENT, category="knowledge")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_stats_returns_valid_structure(self):
        stats = self.store.get_stats()
        self.assertIsInstance(stats["total_memories"], int)
        self.assertIsInstance(stats["active_memories"], int)
        self.assertIsInstance(stats["by_category"], dict)
        self.assertIsInstance(stats["by_status"], dict)
        self.assertIsInstance(stats["avg_relevance"], float)

    def test_temporal_graph_age_distribution_works(self):
        from core.memory_governance import TemporalGraph
        graph = TemporalGraph(self.store)
        dist = graph.memory_age_distribution()
        self.assertGreater(sum(dist.values()), 0)

    def test_decay_status_returns_list(self):
        decay_log = os.path.join(self.tmpdir, "memory_decay.jsonl")
        decay = ConstitutionalDecay(self.store, _decay_log_file=decay_log)
        status = decay.get_decay_status()
        self.assertIsInstance(status, list)
        self.assertGreater(len(status), 0)


class TestDofExports(unittest.TestCase):
    """Test that dof/__init__.py exports memory governance classes."""

    def test_import_governed_memory_store(self):
        from dof import GovernedMemoryStore
        self.assertTrue(callable(GovernedMemoryStore))

    def test_import_temporal_graph(self):
        from dof import TemporalGraph
        self.assertTrue(callable(TemporalGraph))

    def test_import_memory_classifier(self):
        from dof import MemoryClassifier
        self.assertTrue(callable(MemoryClassifier))

    def test_import_constitutional_decay(self):
        from dof import ConstitutionalDecay
        self.assertTrue(callable(ConstitutionalDecay))

    def test_import_memory_entry(self):
        from dof import MemoryEntry
        self.assertTrue(callable(MemoryEntry))


if __name__ == "__main__":
    unittest.main(verbosity=2)
