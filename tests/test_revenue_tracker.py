"""
Tests for core/revenue_tracker.py — DOF revenue + API usage tracker.

All tests redirect JSONL files to a temp directory.
Zero LLM, zero network, fully deterministic.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.revenue_tracker as rt_mod
from core.revenue_tracker import (
    APIUsageEntry,
    RevenueEntry,
    RevenueTracker,
)


# ── Isolation mixin ──────────────────────────────────────────────────

class TmpRevenueMixin(unittest.TestCase):
    """Redirect REVENUE_LOG and USAGE_LOG to temp files."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._orig_dir  = rt_mod.REVENUE_DIR
        self._orig_rlog = rt_mod.REVENUE_LOG
        self._orig_ulog = rt_mod.USAGE_LOG

        rt_mod.REVENUE_DIR = self._tmpdir
        rt_mod.REVENUE_LOG = os.path.join(self._tmpdir, "revenue.jsonl")
        rt_mod.USAGE_LOG   = os.path.join(self._tmpdir, "api_usage.jsonl")

    def tearDown(self):
        rt_mod.REVENUE_DIR = self._orig_dir
        rt_mod.REVENUE_LOG = self._orig_rlog
        rt_mod.USAGE_LOG   = self._orig_ulog

    def _tracker(self) -> RevenueTracker:
        return RevenueTracker()

    def _read_jsonl(self, path: str) -> list[dict]:
        if not os.path.exists(path):
            return []
        with open(path) as f:
            return [json.loads(l) for l in f if l.strip()]


# ─────────────────────────────────────────────────────────────────────
# RevenueEntry dataclass
# ─────────────────────────────────────────────────────────────────────

class TestRevenueEntry(unittest.TestCase):

    def test_entry_id_auto_generated(self):
        e = RevenueEntry()
        self.assertTrue(len(e.entry_id) > 0)

    def test_entry_id_is_string(self):
        e = RevenueEntry()
        self.assertIsInstance(e.entry_id, str)

    def test_timestamp_auto_set(self):
        e = RevenueEntry()
        self.assertTrue(len(e.timestamp) > 0)
        self.assertIn("T", e.timestamp)   # ISO 8601 format

    def test_default_status_confirmed(self):
        e = RevenueEntry()
        self.assertEqual(e.status, "confirmed")

    def test_default_currency_usd(self):
        e = RevenueEntry()
        self.assertEqual(e.currency, "USD")

    def test_custom_fields_set(self):
        e = RevenueEntry(source="grant", amount=5000.0, client="Avalanche",
                         payment_method="crypto", agent="builder")
        self.assertEqual(e.source, "grant")
        self.assertEqual(e.amount, 5000.0)
        self.assertEqual(e.client, "Avalanche")

    def test_two_entries_have_different_ids(self):
        a, b = RevenueEntry(), RevenueEntry()
        self.assertNotEqual(a.entry_id, b.entry_id)


# ─────────────────────────────────────────────────────────────────────
# APIUsageEntry dataclass
# ─────────────────────────────────────────────────────────────────────

class TestAPIUsageEntry(unittest.TestCase):

    def test_call_id_auto_generated(self):
        e = APIUsageEntry()
        self.assertTrue(len(e.call_id) > 0)

    def test_timestamp_auto_set(self):
        e = APIUsageEntry()
        self.assertTrue(len(e.timestamp) > 0)

    def test_custom_fields(self):
        e = APIUsageEntry(endpoint="/verify", caller="agent_x",
                          tokens_used=1000, cost_estimate=0.01)
        self.assertEqual(e.endpoint, "/verify")
        self.assertEqual(e.tokens_used, 1000)
        self.assertAlmostEqual(e.cost_estimate, 0.01)


# ─────────────────────────────────────────────────────────────────────
# track()
# ─────────────────────────────────────────────────────────────────────

class TestTrack(TmpRevenueMixin):

    def test_returns_revenue_entry(self):
        e = self._tracker().track("grant", 1000.0)
        self.assertIsInstance(e, RevenueEntry)

    def test_source_stored(self):
        e = self._tracker().track("saas", 99.0)
        self.assertEqual(e.source, "saas")

    def test_amount_stored(self):
        e = self._tracker().track("bounty", 250.0)
        self.assertAlmostEqual(e.amount, 250.0)

    def test_persisted_to_jsonl(self):
        self._tracker().track("saas", 50.0, description="Monthly sub")
        rows = self._read_jsonl(rt_mod.REVENUE_LOG)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source"], "saas")

    def test_multiple_entries_appended(self):
        t = self._tracker()
        t.track("saas", 10.0)
        t.track("grant", 5000.0)
        t.track("bounty", 250.0)
        rows = self._read_jsonl(rt_mod.REVENUE_LOG)
        self.assertEqual(len(rows), 3)

    def test_all_fields_in_jsonl(self):
        self._tracker().track("consulting", 300.0, currency="EUR",
                              description="audit", client="acme",
                              payment_method="stripe", agent="builder")
        row = self._read_jsonl(rt_mod.REVENUE_LOG)[0]
        self.assertEqual(row["currency"], "EUR")
        self.assertEqual(row["client"], "acme")
        self.assertEqual(row["payment_method"], "stripe")
        self.assertEqual(row["agent"], "builder")

    def test_default_currency_usd(self):
        self._tracker().track("api", 1.0)
        row = self._read_jsonl(rt_mod.REVENUE_LOG)[0]
        self.assertEqual(row["currency"], "USD")


# ─────────────────────────────────────────────────────────────────────
# log_api_usage()
# ─────────────────────────────────────────────────────────────────────

class TestLogAPIUsage(TmpRevenueMixin):

    def test_returns_api_usage_entry(self):
        e = self._tracker().log_api_usage("/verify", caller="a1", tokens_used=500)
        self.assertIsInstance(e, APIUsageEntry)

    def test_cost_computed_from_tokens(self):
        e = self._tracker().log_api_usage("/verify", tokens_used=1000,
                                          cost_per_token=0.00002)
        self.assertAlmostEqual(e.cost_estimate, 0.02)

    def test_default_cost_per_token(self):
        e = self._tracker().log_api_usage("/v", tokens_used=10000)
        self.assertAlmostEqual(e.cost_estimate, 0.10)   # 10000 * 0.00001

    def test_persisted_to_usage_jsonl(self):
        self._tracker().log_api_usage("/prove", caller="agent_x", tokens_used=200)
        rows = self._read_jsonl(rt_mod.USAGE_LOG)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["endpoint"], "/prove")
        self.assertEqual(rows[0]["tokens_used"], 200)

    def test_zero_tokens_zero_cost(self):
        e = self._tracker().log_api_usage("/health", tokens_used=0)
        self.assertEqual(e.cost_estimate, 0.0)


# ─────────────────────────────────────────────────────────────────────
# report()
# ─────────────────────────────────────────────────────────────────────

class TestReport(TmpRevenueMixin):

    def test_empty_report(self):
        r = self._tracker().report()
        self.assertEqual(r["total_revenue"], 0.0)
        self.assertEqual(r["transactions"], 0)

    def test_required_keys(self):
        r = self._tracker().report()
        for k in ("period_days", "total_revenue", "transactions",
                  "by_source", "by_payment_method", "currency"):
            self.assertIn(k, r)

    def test_total_revenue_sum(self):
        t = self._tracker()
        t.track("saas", 100.0)
        t.track("grant", 5000.0)
        t.track("bounty", 250.0)
        r = t.report()
        self.assertAlmostEqual(r["total_revenue"], 5350.0)

    def test_transactions_count(self):
        t = self._tracker()
        for _ in range(4):
            t.track("saas", 10.0)
        self.assertEqual(t.report()["transactions"], 4)

    def test_by_source_aggregation(self):
        t = self._tracker()
        t.track("saas", 100.0)
        t.track("saas", 50.0)
        t.track("grant", 1000.0)
        r = t.report()
        self.assertAlmostEqual(r["by_source"]["saas"], 150.0)
        self.assertAlmostEqual(r["by_source"]["grant"], 1000.0)

    def test_by_payment_method_aggregation(self):
        t = self._tracker()
        t.track("saas", 100.0, payment_method="stripe")
        t.track("bounty", 200.0, payment_method="crypto")
        t.track("saas", 50.0, payment_method="stripe")
        r = t.report()
        self.assertAlmostEqual(r["by_payment_method"]["stripe"], 150.0)
        self.assertAlmostEqual(r["by_payment_method"]["crypto"], 200.0)

    def test_period_days_preserved(self):
        r = self._tracker().report(days=7)
        self.assertEqual(r["period_days"], 7)

    def test_currency_is_usd(self):
        r = self._tracker().report()
        self.assertEqual(r["currency"], "USD")

    def test_by_source_sorted_descending(self):
        t = self._tracker()
        t.track("saas", 10.0)
        t.track("grant", 5000.0)
        t.track("bounty", 250.0)
        r = t.report()
        values = list(r["by_source"].values())
        self.assertEqual(values, sorted(values, reverse=True))


# ─────────────────────────────────────────────────────────────────────
# usage_stats()
# ─────────────────────────────────────────────────────────────────────

class TestUsageStats(TmpRevenueMixin):

    def test_empty_stats(self):
        s = self._tracker().usage_stats()
        self.assertEqual(s["total_calls"], 0)
        self.assertEqual(s["total_tokens"], 0)

    def test_required_keys(self):
        s = self._tracker().usage_stats()
        for k in ("period_days", "total_calls", "total_tokens",
                  "total_cost_estimate", "by_endpoint"):
            self.assertIn(k, s)

    def test_total_calls(self):
        t = self._tracker()
        t.log_api_usage("/verify", tokens_used=100)
        t.log_api_usage("/prove",  tokens_used=200)
        t.log_api_usage("/verify", tokens_used=50)
        self.assertEqual(t.usage_stats()["total_calls"], 3)

    def test_total_tokens_sum(self):
        t = self._tracker()
        t.log_api_usage("/a", tokens_used=1000)
        t.log_api_usage("/b", tokens_used=500)
        self.assertEqual(t.usage_stats()["total_tokens"], 1500)

    def test_total_cost_estimate(self):
        t = self._tracker()
        t.log_api_usage("/a", tokens_used=10000, cost_per_token=0.00001)
        t.log_api_usage("/b", tokens_used=10000, cost_per_token=0.00001)
        s = t.usage_stats()
        self.assertAlmostEqual(s["total_cost_estimate"], 0.2, places=4)

    def test_by_endpoint_counts(self):
        t = self._tracker()
        t.log_api_usage("/verify", tokens_used=10)
        t.log_api_usage("/verify", tokens_used=10)
        t.log_api_usage("/prove",  tokens_used=10)
        s = t.usage_stats()
        self.assertEqual(s["by_endpoint"]["/verify"], 2)
        self.assertEqual(s["by_endpoint"]["/prove"],  1)


# ─────────────────────────────────────────────────────────────────────
# _append / _load static methods
# ─────────────────────────────────────────────────────────────────────

class TestAppendLoad(TmpRevenueMixin):

    def test_append_creates_file(self):
        path = os.path.join(self._tmpdir, "test.jsonl")
        RevenueTracker._append(path, {"x": 1})
        self.assertTrue(os.path.exists(path))

    def test_append_writes_valid_json(self):
        path = os.path.join(self._tmpdir, "test.jsonl")
        RevenueTracker._append(path, {"key": "value", "num": 42})
        with open(path) as f:
            data = json.loads(f.read().strip())
        self.assertEqual(data["key"], "value")

    def test_load_empty_file(self):
        path = os.path.join(self._tmpdir, "empty.jsonl")
        self.assertEqual(RevenueTracker._load(path), [])

    def test_load_nonexistent_file(self):
        path = os.path.join(self._tmpdir, "ghost.jsonl")
        self.assertEqual(RevenueTracker._load(path), [])

    def test_load_reads_all_entries(self):
        path = os.path.join(self._tmpdir, "multi.jsonl")
        for i in range(5):
            RevenueTracker._append(path, {"i": i})
        rows = RevenueTracker._load(path)
        self.assertEqual(len(rows), 5)
        self.assertEqual([r["i"] for r in rows], list(range(5)))


if __name__ == "__main__":
    unittest.main()
