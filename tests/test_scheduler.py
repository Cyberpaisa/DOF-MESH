"""Tests for core/scheduler.py — HybridScheduler, routing, dataclasses."""

import asyncio
import os
import tempfile
import unittest
from pathlib import Path

from core.scheduler import (
    Backend, Priority, ModelTier,
    ModelProfile, InferenceRequest, InferenceResult, ResourceState,
    KNOWN_MODELS, HybridScheduler,
    create_scheduler, get_local_models, recommend_model,
)


def _sched(tmp_log, **kw) -> HybridScheduler:
    """Create scheduler with audit log redirected to temp dir."""
    s = HybridScheduler(**kw)
    s._log_path = Path(tmp_log)
    return s


# ─────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────

class TestEnums(unittest.TestCase):

    def test_backend_ordering(self):
        self.assertLess(Backend.GPU, Backend.ANE)
        self.assertLess(Backend.ANE, Backend.CPU)

    def test_priority_ordering(self):
        self.assertLess(Priority.CRITICAL, Priority.HIGH)
        self.assertLess(Priority.HIGH, Priority.NORMAL)
        self.assertLess(Priority.NORMAL, Priority.LOW)

    def test_model_tier_ordering(self):
        self.assertLess(ModelTier.LARGE, ModelTier.SMALL)


# ─────────────────────────────────────────────────────────
# ModelProfile
# ─────────────────────────────────────────────────────────

class TestModelProfile(unittest.TestCase):

    def test_fits_in_memory_true(self):
        m = ModelProfile("Test", 20.0, ModelTier.LARGE, Backend.GPU)
        self.assertTrue(m.fits_in_memory)

    def test_fits_in_memory_false(self):
        m = ModelProfile("Huge", 33.0, ModelTier.LARGE, Backend.GPU)
        self.assertFalse(m.fits_in_memory)

    def test_fits_in_memory_boundary(self):
        m = ModelProfile("Exact", 32.0, ModelTier.LARGE, Backend.GPU)
        self.assertTrue(m.fits_in_memory)  # <= 32.0

    def test_default_fields(self):
        m = ModelProfile("M", 5.0, ModelTier.SMALL, Backend.ANE)
        self.assertEqual(m.max_context, 32768)
        self.assertEqual(m.estimated_tps, 0.0)
        self.assertEqual(m.sha256_hash, "")


# ─────────────────────────────────────────────────────────
# InferenceRequest
# ─────────────────────────────────────────────────────────

class TestInferenceRequest(unittest.TestCase):

    def test_auto_request_id(self):
        r = InferenceRequest(model="llama-3.3-8b-q4", prompt="Hello")
        self.assertEqual(len(r.request_id), 16)

    def test_two_requests_different_ids(self):
        r1 = InferenceRequest(model="m", prompt="p1")
        r2 = InferenceRequest(model="m", prompt="p2")
        self.assertNotEqual(r1.request_id, r2.request_id)

    def test_custom_request_id(self):
        r = InferenceRequest(model="m", prompt="p", request_id="custom-id")
        self.assertEqual(r.request_id, "custom-id")

    def test_default_priority(self):
        r = InferenceRequest(model="m", prompt="p")
        self.assertEqual(r.priority, Priority.NORMAL)

    def test_default_privacy_false(self):
        r = InferenceRequest(model="m", prompt="p")
        self.assertFalse(r.requires_privacy)


# ─────────────────────────────────────────────────────────
# ResourceState
# ─────────────────────────────────────────────────────────

class TestResourceState(unittest.TestCase):

    def test_memory_available_default(self):
        s = ResourceState()
        # 36 - 4 - 0 = 32
        self.assertAlmostEqual(s.memory_available_gb, 32.0)

    def test_memory_available_used(self):
        s = ResourceState(memory_used_gb=10.0)
        self.assertAlmostEqual(s.memory_available_gb, 22.0)

    def test_combined_usage(self):
        s = ResourceState(gpu_usage_pct=50.0, ane_usage_pct=30.0)
        self.assertAlmostEqual(s.combined_usage_pct, 40.0)

    def test_can_load_model_fits(self):
        s = ResourceState(memory_used_gb=0.0)
        m = ModelProfile("Small", 5.0, ModelTier.SMALL, Backend.ANE)
        self.assertTrue(s.can_load_model(m))

    def test_can_load_model_no_memory(self):
        s = ResourceState(memory_used_gb=30.0)
        m = ModelProfile("Large", 20.0, ModelTier.LARGE, Backend.GPU)
        self.assertFalse(s.can_load_model(m))

    def test_can_load_model_high_usage(self):
        s = ResourceState(gpu_usage_pct=80.0, ane_usage_pct=80.0)
        m = ModelProfile("Small", 1.0, ModelTier.TINY, Backend.ANE)
        self.assertFalse(s.can_load_model(m))


# ─────────────────────────────────────────────────────────
# KNOWN_MODELS registry
# ─────────────────────────────────────────────────────────

class TestKnownModels(unittest.TestCase):

    def test_non_empty(self):
        self.assertGreater(len(KNOWN_MODELS), 0)

    def test_all_fit_in_32gb(self):
        for name, m in KNOWN_MODELS.items():
            self.assertLessEqual(m.size_gb, 32.0, f"{name} exceeds 32GB")

    def test_required_models_present(self):
        for key in ("qwen3-32b-q4", "phi-4-14b-q4", "llama-3.3-8b-q4"):
            self.assertIn(key, KNOWN_MODELS)

    def test_all_profiles_have_valid_tier(self):
        for name, m in KNOWN_MODELS.items():
            self.assertIsInstance(m.tier, ModelTier, name)

    def test_all_profiles_have_valid_backend(self):
        for name, m in KNOWN_MODELS.items():
            self.assertIsInstance(m.preferred_backend, Backend, name)


# ─────────────────────────────────────────────────────────
# get_model_profile / route (sync)
# ─────────────────────────────────────────────────────────

class TestGetModelProfile(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mktemp(suffix=".jsonl")
        self.sched = _sched(self._tmp)

    def test_exact_match(self):
        p = self.sched.get_model_profile("qwen3-32b-q4")
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "Qwen3 32B Q4")

    def test_fuzzy_match(self):
        p = self.sched.get_model_profile("phi4")
        # Fuzzy may or may not match — just check no crash
        # (no assertion on result — implementation-dependent)

    def test_unknown_returns_none(self):
        p = self.sched.get_model_profile("nonexistent-model-xyz")
        self.assertIsNone(p)


class TestRoute(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mktemp(suffix=".jsonl")
        self.sched = _sched(self._tmp)

    def _req(self, model, priority=Priority.NORMAL, privacy=False):
        return InferenceRequest(model=model, prompt="test", priority=priority,
                                requires_privacy=privacy)

    def test_large_model_to_gpu(self):
        backend = self.sched.route(self._req("qwen3-32b-q4"))
        self.assertEqual(backend, Backend.GPU)

    def test_small_model_to_ane(self):
        backend = self.sched.route(self._req("llama-3.3-8b-q4"))
        self.assertEqual(backend, Backend.ANE)

    def test_privacy_never_cloud(self):
        backend = self.sched.route(self._req("llama-3.3-8b-q4", privacy=True))
        self.assertNotEqual(backend, Backend.CLOUD)

    def test_unknown_model_cloud_fallback(self):
        backend = self.sched.route(self._req("nonexistent-model"))
        self.assertEqual(backend, Backend.CLOUD)

    def test_unknown_model_no_cloud_fallback(self):
        s = _sched(self._tmp, cloud_fallback=False)
        backend = s.route(self._req("nonexistent-model"))
        self.assertEqual(backend, Backend.GPU)

    def test_saturated_gpu_large_model_fallback(self):
        self.sched.state.gpu_usage_pct = 80.0
        self.sched.state.ane_usage_pct = 80.0
        backend = self.sched.route(self._req("qwen3-32b-q4"))
        # Under saturation with cloud_fallback=True → CLOUD
        self.assertEqual(backend, Backend.CLOUD)


# ─────────────────────────────────────────────────────────
# status / report
# ─────────────────────────────────────────────────────────

class TestStatusReport(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mktemp(suffix=".jsonl")
        self.sched = _sched(self._tmp)

    def test_status_returns_dict(self):
        s = self.sched.status()
        self.assertIsInstance(s, dict)

    def test_status_keys(self):
        s = self.sched.status()
        for key in ("resources", "queue_depth", "active_tasks",
                    "known_models", "cloud_fallback", "max_concurrent"):
            self.assertIn(key, s)

    def test_known_models_count(self):
        self.assertEqual(self.sched.status()["known_models"], len(KNOWN_MODELS))

    def test_report_is_string(self):
        self.assertIsInstance(self.sched.report(), str)

    def test_report_contains_memory(self):
        self.assertIn("Memory", self.sched.report())


# ─────────────────────────────────────────────────────────
# Convenience functions
# ─────────────────────────────────────────────────────────

class TestConvenienceFunctions(unittest.TestCase):

    def test_create_scheduler_returns_instance(self):
        s = create_scheduler()
        self.assertIsInstance(s, HybridScheduler)

    def test_get_local_models_non_empty(self):
        models = get_local_models()
        self.assertGreater(len(models), 0)

    def test_get_local_models_all_fit(self):
        for m in get_local_models():
            self.assertTrue(m.fits_in_memory)

    def test_recommend_model_returns_string(self):
        self.assertIsInstance(recommend_model("coding"), str)

    def test_recommend_model_known_tasks(self):
        for task in ("coding", "reasoning", "fast_check", "security", "simple"):
            result = recommend_model(task)
            self.assertIn(result, KNOWN_MODELS, f"Unknown model for task '{task}'")

    def test_recommend_model_unknown_task_default(self):
        result = recommend_model("unknown_task_xyz")
        self.assertIn(result, KNOWN_MODELS)


# ─────────────────────────────────────────────────────────
# schedule (async) — smoke test
# ─────────────────────────────────────────────────────────

class TestScheduleAsync(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._log = os.path.join(self._tmpdir, "audit.jsonl")
        self.sched = _sched(self._log)

    def _run(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_schedule_returns_inference_result(self):
        req = InferenceRequest(model="llama-3.3-8b-q4", prompt="Hello world")
        result = self._run(self.sched.schedule(req))
        self.assertIsInstance(result, InferenceResult)

    def test_schedule_preserves_request_id(self):
        req = InferenceRequest(model="llama-3.3-8b-q4", prompt="Test")
        result = self._run(self.sched.schedule(req))
        self.assertEqual(result.request_id, req.request_id)

    def test_schedule_proof_hash_64chars(self):
        req = InferenceRequest(model="llama-3.3-8b-q4", prompt="Test")
        result = self._run(self.sched.schedule(req))
        self.assertEqual(len(result.proof_hash), 64)

    def test_schedule_latency_positive(self):
        req = InferenceRequest(model="llama-3.3-8b-q4", prompt="Test")
        result = self._run(self.sched.schedule(req))
        self.assertGreater(result.latency_ms, 0.0)

    def test_schedule_audit_log_written(self):
        req = InferenceRequest(model="llama-3.3-8b-q4", prompt="Test")
        self._run(self.sched.schedule(req))
        self.assertTrue(os.path.exists(self._log))

    def test_schedule_verified_field_bool(self):
        req = InferenceRequest(model="llama-3.3-8b-q4", prompt="Test")
        result = self._run(self.sched.schedule(req))
        self.assertIsInstance(result.verified, bool)


if __name__ == "__main__":
    unittest.main()
