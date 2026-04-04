"""
tests/test_cost_tracker.py
───────────────────────────
Tests para core/cost_tracker.py.

Suite:
    TestCalculateCost       — método estático calculate_cost()
    TestCallRecord          — dataclass CallRecord (serialización, propiedades)
    TestRoleSummary         — dataclass RoleSummary (propiedades, to_dict)
    TestCostTrackerRecord   — record() acumula correctamente
    TestCostTrackerQueries  — total_cost_usd, total_calls, by_role, most_expensive_role
    TestCostTrackerSummary  — summary_dict()
    TestCostTrackerReset    — reset() aísla estado entre tests
    TestCostTrackerPersist  — persistencia JSONL en disco
    TestCostTrackerWithMock — integración con patch_provider() de tests.mocks
"""

import json
import os
import sys
import tempfile
import time
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.cost_tracker import (
    PRICE_TABLE,
    CallRecord,
    CostTracker,
    RoleSummary,
)
from tests.mocks import patch_provider


# ─────────────────────────────────────────────────────────────────────────────
# TestCalculateCost
# ─────────────────────────────────────────────────────────────────────────────

class TestCalculateCost(unittest.TestCase):
    """calculate_cost() calcula correctamente para distintos modelos."""

    def test_known_model_deepseek(self):
        cost = CostTracker.calculate_cost(
            model="deepseek/deepseek-chat",
            prompt_tokens=1_000_000,
            completion_tokens=0,
        )
        self.assertAlmostEqual(cost, 0.27, places=4)

    def test_known_model_output_only(self):
        cost = CostTracker.calculate_cost(
            model="deepseek/deepseek-chat",
            prompt_tokens=0,
            completion_tokens=1_000_000,
        )
        self.assertAlmostEqual(cost, 1.10, places=4)

    def test_known_model_combined(self):
        # 1200 prompt + 400 completion con deepseek
        # (1200 * 0.27 + 400 * 1.10) / 1_000_000
        expected = (1200 * 0.27 + 400 * 1.10) / 1_000_000
        cost = CostTracker.calculate_cost(
            model="deepseek/deepseek-chat",
            prompt_tokens=1200,
            completion_tokens=400,
        )
        self.assertAlmostEqual(cost, expected, places=8)

    def test_mock_model_is_free(self):
        cost = CostTracker.calculate_cost(
            model="mock/model",
            prompt_tokens=100_000,
            completion_tokens=100_000,
        )
        self.assertEqual(cost, 0.0)

    def test_unknown_model_uses_default(self):
        cost = CostTracker.calculate_cost(
            model="unknown/model-xyz",
            prompt_tokens=1_000_000,
            completion_tokens=0,
        )
        # _default input = 1.00 $/1M
        self.assertAlmostEqual(cost, 1.00, places=4)

    def test_zero_tokens_returns_zero(self):
        cost = CostTracker.calculate_cost(
            model="deepseek/deepseek-chat",
            prompt_tokens=0,
            completion_tokens=0,
        )
        self.assertEqual(cost, 0.0)

    def test_custom_price_table(self):
        custom = {"test/model": {"input": 2.00, "output": 4.00}, "_default": {"input": 1.0, "output": 1.0}}
        cost = CostTracker.calculate_cost(
            model="test/model",
            prompt_tokens=500_000,
            completion_tokens=500_000,
            price_table=custom,
        )
        expected = (500_000 * 2.00 + 500_000 * 4.00) / 1_000_000
        self.assertAlmostEqual(cost, expected, places=6)

    def test_nvidia_nim_is_free(self):
        cost = CostTracker.calculate_cost(
            model="nvidia_nim/qwen3.5-397b",
            prompt_tokens=500_000,
            completion_tokens=500_000,
        )
        self.assertEqual(cost, 0.0)

    def test_returns_float(self):
        cost = CostTracker.calculate_cost(
            model="groq/llama-3.3-70b-versatile",
            prompt_tokens=100,
            completion_tokens=100,
        )
        self.assertIsInstance(cost, float)

    def test_price_table_has_default_key(self):
        self.assertIn("_default", PRICE_TABLE)

    def test_price_table_default_has_input_output(self):
        default = PRICE_TABLE["_default"]
        self.assertIn("input", default)
        self.assertIn("output", default)


# ─────────────────────────────────────────────────────────────────────────────
# TestCallRecord
# ─────────────────────────────────────────────────────────────────────────────

class TestCallRecord(unittest.TestCase):
    """CallRecord — propiedades y serialización."""

    def _make_record(self, **overrides) -> CallRecord:
        defaults = dict(
            timestamp=time.time(),
            role="architect",
            model="deepseek/deepseek-chat",
            prompt_tokens=1000,
            completion_tokens=300,
            cost_usd=0.0006,
        )
        defaults.update(overrides)
        return CallRecord(**defaults)

    def test_total_tokens_property(self):
        rec = self._make_record(prompt_tokens=800, completion_tokens=200)
        self.assertEqual(rec.total_tokens, 1000)

    def test_to_dict_has_all_fields(self):
        rec = self._make_record()
        d = rec.to_dict()
        for key in ("timestamp", "role", "model", "prompt_tokens",
                    "completion_tokens", "cost_usd"):
            self.assertIn(key, d)

    def test_from_dict_roundtrip(self):
        original = self._make_record()
        restored = CallRecord.from_dict(original.to_dict())
        self.assertEqual(restored.role, original.role)
        self.assertEqual(restored.model, original.model)
        self.assertEqual(restored.prompt_tokens, original.prompt_tokens)
        self.assertEqual(restored.completion_tokens, original.completion_tokens)
        self.assertAlmostEqual(restored.cost_usd, original.cost_usd, places=8)

    def test_from_dict_raises_on_missing_field(self):
        d = self._make_record().to_dict()
        del d["role"]
        with self.assertRaises(KeyError):
            CallRecord.from_dict(d)

    def test_repr_includes_role_and_cost(self):
        rec = self._make_record()
        r = repr(rec)
        self.assertIn("architect", r)
        self.assertIn("cost=", r)


# ─────────────────────────────────────────────────────────────────────────────
# TestRoleSummary
# ─────────────────────────────────────────────────────────────────────────────

class TestRoleSummary(unittest.TestCase):
    """RoleSummary — propiedades y to_dict."""

    def _make_summary(self, **overrides) -> RoleSummary:
        defaults = dict(
            role="researcher",
            total_calls=3,
            total_prompt_tokens=3000,
            total_completion_tokens=900,
            total_cost_usd=0.002,
        )
        defaults.update(overrides)
        return RoleSummary(**defaults)

    def test_total_tokens_property(self):
        s = self._make_summary(total_prompt_tokens=3000, total_completion_tokens=900)
        self.assertEqual(s.total_tokens, 3900)

    def test_to_dict_has_total_tokens(self):
        s = self._make_summary()
        d = s.to_dict()
        self.assertIn("total_tokens", d)
        self.assertEqual(d["total_tokens"], s.total_tokens)

    def test_to_dict_rounds_cost(self):
        s = self._make_summary(total_cost_usd=0.000123456789)
        d = s.to_dict()
        self.assertEqual(d["total_cost_usd"], round(0.000123456789, 6))

    def test_repr_includes_role(self):
        s = self._make_summary()
        self.assertIn("researcher", repr(s))


# ─────────────────────────────────────────────────────────────────────────────
# TestCostTrackerRecord
# ─────────────────────────────────────────────────────────────────────────────

class TestCostTrackerRecord(unittest.TestCase):
    """record() acumula registros correctamente."""

    def setUp(self):
        self.tracker = CostTracker(session_id="test-session")

    def test_record_returns_call_record(self):
        rec = self.tracker.record("architect", "mock/model", 100, 50)
        self.assertIsInstance(rec, CallRecord)

    def test_record_stores_role_correctly(self):
        rec = self.tracker.record("researcher", "mock/model", 200, 100)
        self.assertEqual(rec.role, "researcher")

    def test_record_stores_model_correctly(self):
        rec = self.tracker.record("architect", "deepseek/deepseek-chat", 100, 50)
        self.assertEqual(rec.model, "deepseek/deepseek-chat")

    def test_record_calculates_cost(self):
        rec = self.tracker.record("architect", "deepseek/deepseek-chat", 1_000_000, 0)
        self.assertAlmostEqual(rec.cost_usd, 0.27, places=4)

    def test_record_mock_model_zero_cost(self):
        rec = self.tracker.record("architect", "mock/model", 999_999, 999_999)
        self.assertEqual(rec.cost_usd, 0.0)

    def test_record_increments_call_count(self):
        self.tracker.record("architect", "mock/model", 100, 50)
        self.tracker.record("researcher", "mock/model", 200, 100)
        self.assertEqual(self.tracker.total_calls(), 2)

    def test_record_sets_timestamp(self):
        before = time.time()
        rec = self.tracker.record("architect", "mock/model", 100, 50)
        after = time.time()
        self.assertGreaterEqual(rec.timestamp, before)
        self.assertLessEqual(rec.timestamp, after)

    def test_multiple_records_accumulate(self):
        for i in range(5):
            self.tracker.record("architect", "mock/model", 100, 50)
        self.assertEqual(self.tracker.total_calls(), 5)


# ─────────────────────────────────────────────────────────────────────────────
# TestCostTrackerQueries
# ─────────────────────────────────────────────────────────────────────────────

class TestCostTrackerQueries(unittest.TestCase):
    """Consultas de agregación sobre registros acumulados."""

    def setUp(self):
        self.tracker = CostTracker()
        # architect: 2 llamadas con deepseek
        self.tracker.record("architect", "deepseek/deepseek-chat", 1_000_000, 0)
        self.tracker.record("architect", "deepseek/deepseek-chat", 0, 1_000_000)
        # researcher: 1 llamada con mock (gratis)
        self.tracker.record("researcher", "mock/model", 500_000, 200_000)

    def test_total_cost_includes_all_records(self):
        # architect input: 0.27 + architect output: 1.10 + researcher: 0.0
        expected = 0.27 + 1.10
        self.assertAlmostEqual(self.tracker.total_cost_usd(), expected, places=4)

    def test_total_calls_is_three(self):
        self.assertEqual(self.tracker.total_calls(), 3)

    def test_total_tokens_counts_all(self):
        # 1M + 1M + (500K + 200K) = 2_700_000
        self.assertEqual(self.tracker.total_tokens(), 2_700_000)

    def test_by_role_has_both_roles(self):
        summaries = self.tracker.by_role()
        self.assertIn("architect", summaries)
        self.assertIn("researcher", summaries)

    def test_by_role_architect_has_two_calls(self):
        summaries = self.tracker.by_role()
        self.assertEqual(summaries["architect"].total_calls, 2)

    def test_by_role_researcher_has_one_call(self):
        summaries = self.tracker.by_role()
        self.assertEqual(summaries["researcher"].total_calls, 1)

    def test_by_role_architect_cost(self):
        summaries = self.tracker.by_role()
        self.assertAlmostEqual(summaries["architect"].total_cost_usd, 1.37, places=4)

    def test_by_role_researcher_cost_is_zero(self):
        summaries = self.tracker.by_role()
        self.assertEqual(summaries["researcher"].total_cost_usd, 0.0)

    def test_most_expensive_role_is_architect(self):
        self.assertEqual(self.tracker.most_expensive_role(), "architect")

    def test_most_expensive_role_none_when_empty(self):
        tracker = CostTracker()
        self.assertIsNone(tracker.most_expensive_role())

    def test_by_role_empty_when_no_records(self):
        tracker = CostTracker()
        self.assertEqual(tracker.by_role(), {})

    def test_total_cost_zero_when_no_records(self):
        tracker = CostTracker()
        self.assertEqual(tracker.total_cost_usd(), 0.0)

    def test_total_calls_zero_when_no_records(self):
        tracker = CostTracker()
        self.assertEqual(tracker.total_calls(), 0)


# ─────────────────────────────────────────────────────────────────────────────
# TestCostTrackerSummary
# ─────────────────────────────────────────────────────────────────────────────

class TestCostTrackerSummary(unittest.TestCase):
    """summary_dict() produce estructura JSON-serializable completa."""

    def setUp(self):
        self.tracker = CostTracker(session_id="session-xyz")
        self.tracker.record("architect", "mock/model", 1000, 500)
        self.tracker.record("researcher", "mock/model", 800, 300)

    def test_summary_has_required_keys(self):
        s = self.tracker.summary_dict()
        for key in ("session_id", "total_calls", "total_cost_usd",
                    "total_tokens", "by_role"):
            self.assertIn(key, s)

    def test_summary_session_id(self):
        s = self.tracker.summary_dict()
        self.assertEqual(s["session_id"], "session-xyz")

    def test_summary_total_calls(self):
        s = self.tracker.summary_dict()
        self.assertEqual(s["total_calls"], 2)

    def test_summary_by_role_is_dict(self):
        s = self.tracker.summary_dict()
        self.assertIsInstance(s["by_role"], dict)

    def test_summary_is_json_serializable(self):
        s = self.tracker.summary_dict()
        serialized = json.dumps(s)
        restored = json.loads(serialized)
        self.assertEqual(restored["total_calls"], 2)

    def test_summary_empty_tracker(self):
        tracker = CostTracker(session_id="empty")
        s = tracker.summary_dict()
        self.assertEqual(s["total_calls"], 0)
        self.assertEqual(s["total_cost_usd"], 0.0)
        self.assertEqual(s["by_role"], {})


# ─────────────────────────────────────────────────────────────────────────────
# TestCostTrackerReset
# ─────────────────────────────────────────────────────────────────────────────

class TestCostTrackerReset(unittest.TestCase):
    """reset() limpia el estado en memoria (patrón singleton DOF)."""

    def test_reset_zeroes_call_count(self):
        tracker = CostTracker()
        tracker.record("architect", "mock/model", 100, 50)
        tracker.record("architect", "mock/model", 100, 50)
        tracker.reset()
        self.assertEqual(tracker.total_calls(), 0)

    def test_reset_zeroes_cost(self):
        tracker = CostTracker()
        tracker.record("architect", "deepseek/deepseek-chat", 1_000_000, 0)
        tracker.reset()
        self.assertEqual(tracker.total_cost_usd(), 0.0)

    def test_reset_clears_by_role(self):
        tracker = CostTracker()
        tracker.record("architect", "mock/model", 100, 50)
        tracker.reset()
        self.assertEqual(tracker.by_role(), {})

    def test_reset_idempotent(self):
        tracker = CostTracker()
        tracker.reset()
        tracker.reset()
        self.assertEqual(tracker.total_calls(), 0)

    def test_record_after_reset_works(self):
        tracker = CostTracker()
        tracker.record("architect", "mock/model", 100, 50)
        tracker.reset()
        tracker.record("researcher", "mock/model", 200, 100)
        self.assertEqual(tracker.total_calls(), 1)
        self.assertIn("researcher", tracker.by_role())


# ─────────────────────────────────────────────────────────────────────────────
# TestCostTrackerPersist
# ─────────────────────────────────────────────────────────────────────────────

class TestCostTrackerPersist(unittest.TestCase):
    """Persistencia JSONL — record() hace append a disco cuando persist_path está set."""

    def _make_tracker(self) -> "tuple[CostTracker, str]":
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "costs.jsonl")
        tracker = CostTracker(session_id="persist-test", persist_path=path)
        return tracker, path

    def test_persist_creates_file(self):
        tracker, path = self._make_tracker()
        tracker.record("architect", "mock/model", 100, 50)
        self.assertTrue(os.path.exists(path))

    def test_persist_writes_valid_jsonl(self):
        tracker, path = self._make_tracker()
        tracker.record("architect", "mock/model", 100, 50)
        tracker.record("researcher", "mock/model", 200, 100)
        with open(path, "r") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 2)
        for line in lines:
            data = json.loads(line)
            self.assertIn("role", data)
            self.assertIn("cost_usd", data)

    def test_persist_appends_not_overwrites(self):
        tracker, path = self._make_tracker()
        for i in range(5):
            tracker.record("architect", "mock/model", 100, 50)
        with open(path, "r") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 5)

    def test_no_persist_when_path_is_none(self):
        tracker = CostTracker(persist_path=None)
        tracker.record("architect", "mock/model", 100, 50)
        # Sin persist_path no debe haber ningún side-effect en disco
        # (solo verificamos que no lanza excepción)

    def test_reset_does_not_delete_jsonl(self):
        tracker, path = self._make_tracker()
        tracker.record("architect", "mock/model", 100, 50)
        tracker.reset()
        self.assertTrue(os.path.exists(path), "reset() no debe borrar el archivo JSONL")


# ─────────────────────────────────────────────────────────────────────────────
# TestCostTrackerWithMock
# ─────────────────────────────────────────────────────────────────────────────

class TestCostTrackerWithMock(unittest.TestCase):
    """
    Integración con patch_provider() de tests.mocks.

    Simula un flujo real donde se obtiene un LLM via ProviderManager,
    se hace la llamada, y se registra el costo en CostTracker.
    """

    def test_record_with_mock_provider_zero_cost(self):
        """Un MockLLM tiene costo cero — el tracker refleja eso."""
        tracker = CostTracker(session_id="mock-test")
        with patch_provider("respuesta simulada") as mock_llm:
            response = mock_llm.call([{"role": "user", "content": "hola"}])
            # Simular tokens estimados (en prod vendrían del provider)
            prompt_tokens = len(response.split()) * 4  # aproximación
            completion_tokens = 50
            tracker.record(
                role="architect",
                model=mock_llm.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
        self.assertEqual(tracker.total_calls(), 1)
        self.assertEqual(tracker.total_cost_usd(), 0.0)

    def test_multiple_roles_with_mock(self):
        """Múltiples roles usando el mismo mock."""
        tracker = CostTracker(session_id="multi-role-test")
        with patch_provider("ok") as mock_llm:
            for role in ("architect", "researcher", "guardian"):
                mock_llm.call([])
                tracker.record(
                    role=role,
                    model=mock_llm.model,
                    prompt_tokens=100,
                    completion_tokens=50,
                )
        self.assertEqual(tracker.total_calls(), 3)
        summaries = tracker.by_role()
        self.assertEqual(len(summaries), 3)
        for role in ("architect", "researcher", "guardian"):
            self.assertIn(role, summaries)

    def test_tracker_independent_of_mock_call_count(self):
        """call_count del mock y total_calls del tracker son independientes."""
        tracker = CostTracker()
        with patch_provider() as mock_llm:
            mock_llm.call([])  # llamada que NO registra en tracker
            mock_llm.call([])  # llamada que NO registra en tracker
            tracker.record("architect", mock_llm.model, 100, 50)  # solo esta
        self.assertEqual(mock_llm.call_count, 2)
        self.assertEqual(tracker.total_calls(), 1)

    def test_reset_tracker_inside_mock_context(self):
        """reset() dentro del contexto del mock funciona correctamente."""
        tracker = CostTracker()
        with patch_provider() as mock_llm:
            tracker.record("architect", mock_llm.model, 100, 50)
            tracker.record("researcher", mock_llm.model, 200, 100)
            self.assertEqual(tracker.total_calls(), 2)
            tracker.reset()
            self.assertEqual(tracker.total_calls(), 0)


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
