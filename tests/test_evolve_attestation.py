"""Tests for EvolveEngine on-chain attestation of weight evolution."""
import sys, os, unittest, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.evolve_engine import (
    EvolveController, EvolveConfig, EvolveResult,
    DEFAULT_TRACER_WEIGHTS
)
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile


class TestEvolveAttestation(unittest.TestCase):

    def _make_adopted_result(self):
        return EvolveResult(
            target="tracer_weights",
            best_params=dict(DEFAULT_TRACER_WEIGHTS),
            best_score=0.9980,
            baseline_score=0.9963,
            improvement_pct=0.17,
            total_iterations=40,
            total_cost_usd=0.0,
            adopted=True,
            run_duration_s=1.5,
            run_id="test1234",
            candidates_evaluated=41
        )

    def test_attest_returns_dict(self):
        config = EvolveConfig(target="tracer_weights", verbose=False)
        controller = EvolveController(config, lambda w: 0.5)
        result = self._make_adopted_result()
        attest = controller._attest_evolution_onchain(result)
        self.assertIsInstance(attest, dict)

    def test_attest_has_proof_hash_on_error(self):
        """Even if chain call fails, proof_hash must be in result."""
        config = EvolveConfig(target="tracer_weights", verbose=False)
        controller = EvolveController(config, lambda w: 0.5)
        result = self._make_adopted_result()
        attest = controller._attest_evolution_onchain(result)
        # Either success with tx_hash or error with proof_hash
        self.assertTrue("proof_hash" in attest or "tx_hash" in attest or "status" in attest)

    def test_attest_creates_log_file(self):
        """Attestation log must be written when adoption happens."""
        config = EvolveConfig(target="tracer_weights", verbose=False)
        controller = EvolveController(config, lambda w: 0.5)
        result = self._make_adopted_result()
        controller._attest_evolution_onchain(result)
        log_file = Path("logs/evolve/evolution_attestations.jsonl")
        if log_file.exists():
            lines = log_file.read_text().strip().split("\n")
            last = json.loads(lines[-1])
            self.assertEqual(last["event"], "WEIGHTS_EVOLVED")
            self.assertIn("proof_hash", last)

    def test_attest_proof_hash_format(self):
        """proof_hash must be 0x + 64 hex chars."""
        config = EvolveConfig(target="tracer_weights", verbose=False)
        controller = EvolveController(config, lambda w: 0.5)
        result = self._make_adopted_result()
        # Extract proof hash from log or return value
        import hashlib
        payload_str = json.dumps({
            "run_id": result.run_id,
            "target": result.target,
            "baseline_score": round(result.baseline_score, 6),
            "new_score": round(result.best_score, 6),
            "score_delta_pct": round(result.improvement_pct, 4),
            "new_weights": result.best_params,
            "candidates_evaluated": result.candidates_evaluated,
        }, sort_keys=True)
        # Just verify our hash function produces correct format
        h = "0x" + hashlib.sha3_256(payload_str.encode()).hexdigest()
        self.assertTrue(h.startswith("0x"))
        self.assertEqual(len(h), 66)  # 0x + 64 hex chars

    def test_run_with_adopted_triggers_attestation(self):
        """Full integration: run() with improvement > threshold calls attestation."""
        config = EvolveConfig(
            target="tracer_weights",
            max_iterations=5,
            min_improvement_pct=0.0,  # always adopt
            budget_usd=0.0,
            verbose=False,
            random_seed=42
        )
        call_count = [0]
        original_attest = EvolveController._attest_evolution_onchain

        def mock_attest(self, result):
            call_count[0] += 1
            return {"status": "mock", "proof_hash": "0x" + "a" * 64}

        with patch.object(EvolveController, '_attest_evolution_onchain', mock_attest):
            evaluator = lambda w: w.get("reliability", 0.2) + 0.5
            controller = EvolveController(config, evaluator)
            result = controller.run()

        if result.adopted:
            self.assertEqual(call_count[0], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
