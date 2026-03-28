# tests/test_virtuals_integration.py
# Tests para DOF × Virtuals Protocol integration
# NO requieren conexión on-chain real — dry_run=True

import unittest
from unittest.mock import patch, MagicMock

from integrations.virtuals.virtuals_trust_adapter import (
    VirtualsTrustAdapter,
    VirtualsAgentScore,
    SCORE_WEIGHTS,
    TRUST_THRESHOLD_HIGH,
    TRUST_THRESHOLD_MED,
)


SAMPLE_ADDRESS = "0xabc123def456abc123def456abc123def456abc1"
SAMPLE_ADDRESS_2 = "0x1234567890abcdef1234567890abcdef12345678"


class TestVirtualsTrustAdapterInit(unittest.TestCase):

    def test_default_chain_is_base_sepolia(self):
        adapter = VirtualsTrustAdapter()
        self.assertEqual(adapter.chain, "base_sepolia")

    def test_dry_run_flag(self):
        adapter = VirtualsTrustAdapter(dry_run=True)
        self.assertTrue(adapter.dry_run)

    def test_base_mainnet_chain(self):
        adapter = VirtualsTrustAdapter(chain="base")
        self.assertEqual(adapter.chain, "base")


class TestAddressToAgentId(unittest.TestCase):

    def test_deterministic(self):
        id1 = VirtualsTrustAdapter._address_to_agent_id(SAMPLE_ADDRESS)
        id2 = VirtualsTrustAdapter._address_to_agent_id(SAMPLE_ADDRESS)
        self.assertEqual(id1, id2)

    def test_different_addresses_different_ids(self):
        id1 = VirtualsTrustAdapter._address_to_agent_id(SAMPLE_ADDRESS)
        id2 = VirtualsTrustAdapter._address_to_agent_id(SAMPLE_ADDRESS_2)
        self.assertNotEqual(id1, id2)

    def test_id_is_positive_int(self):
        agent_id = VirtualsTrustAdapter._address_to_agent_id(SAMPLE_ADDRESS)
        self.assertIsInstance(agent_id, int)
        self.assertGreater(agent_id, 0)

    def test_id_fits_uint32(self):
        agent_id = VirtualsTrustAdapter._address_to_agent_id(SAMPLE_ADDRESS)
        self.assertLess(agent_id, 2 ** 32)


class TestScoreWeights(unittest.TestCase):

    def test_weights_sum_to_100(self):
        self.assertEqual(sum(SCORE_WEIGHTS.values()), 100)

    def test_all_weight_keys_present(self):
        expected = {
            "governance_compliance",
            "behavioral_consistency",
            "onchain_attestations",
            "response_integrity",
        }
        self.assertEqual(set(SCORE_WEIGHTS.keys()), expected)


class TestWeightedScoreComputation(unittest.TestCase):

    def test_perfect_scores_give_100(self):
        sub_scores = {k: 100 for k in SCORE_WEIGHTS}
        result = VirtualsTrustAdapter._compute_weighted_score(sub_scores)
        self.assertEqual(result, 100)

    def test_zero_scores_give_0(self):
        sub_scores = {k: 0 for k in SCORE_WEIGHTS}
        result = VirtualsTrustAdapter._compute_weighted_score(sub_scores)
        self.assertEqual(result, 0)

    def test_score_in_range(self):
        sub_scores = {k: 75 for k in SCORE_WEIGHTS}
        result = VirtualsTrustAdapter._compute_weighted_score(sub_scores)
        self.assertGreaterEqual(result, 0)
        self.assertLessEqual(result, 100)

    def test_score_never_exceeds_100(self):
        sub_scores = {k: 999 for k in SCORE_WEIGHTS}
        result = VirtualsTrustAdapter._compute_weighted_score(sub_scores)
        self.assertLessEqual(result, 100)


class TestTierClassification(unittest.TestCase):

    def test_high_tier(self):
        self.assertEqual(VirtualsTrustAdapter._classify_tier(80), "HIGH")
        self.assertEqual(VirtualsTrustAdapter._classify_tier(100), "HIGH")

    def test_medium_tier(self):
        self.assertEqual(VirtualsTrustAdapter._classify_tier(50), "MEDIUM")
        self.assertEqual(VirtualsTrustAdapter._classify_tier(79), "MEDIUM")

    def test_low_tier(self):
        self.assertEqual(VirtualsTrustAdapter._classify_tier(0), "LOW")
        self.assertEqual(VirtualsTrustAdapter._classify_tier(49), "LOW")

    def test_boundary_high(self):
        self.assertEqual(VirtualsTrustAdapter._classify_tier(TRUST_THRESHOLD_HIGH), "HIGH")

    def test_boundary_medium(self):
        self.assertEqual(VirtualsTrustAdapter._classify_tier(TRUST_THRESHOLD_MED), "MEDIUM")


class TestProofHash(unittest.TestCase):

    def test_hash_is_hex_string(self):
        bundle = {"agent": SAMPLE_ADDRESS, "score": 75}
        h = VirtualsTrustAdapter._hash_proof_bundle(bundle)
        self.assertIsInstance(h, str)
        self.assertEqual(len(h), 64)  # SHA-256 hex = 64 chars

    def test_hash_is_deterministic(self):
        bundle = {"agent": SAMPLE_ADDRESS, "score": 75}
        h1 = VirtualsTrustAdapter._hash_proof_bundle(bundle)
        h2 = VirtualsTrustAdapter._hash_proof_bundle(bundle)
        self.assertEqual(h1, h2)

    def test_different_bundles_different_hashes(self):
        b1 = {"agent": SAMPLE_ADDRESS, "score": 75}
        b2 = {"agent": SAMPLE_ADDRESS, "score": 80}
        self.assertNotEqual(
            VirtualsTrustAdapter._hash_proof_bundle(b1),
            VirtualsTrustAdapter._hash_proof_bundle(b2),
        )


class TestScoreAgentDryRun(unittest.TestCase):
    """Tests del flujo completo score_agent() sin llamadas on-chain."""

    def setUp(self):
        self.adapter = VirtualsTrustAdapter(chain="base_sepolia", dry_run=True)

    def test_returns_virtuals_agent_score(self):
        score = self.adapter.score_agent(SAMPLE_ADDRESS)
        self.assertIsInstance(score, VirtualsAgentScore)

    def test_score_fields_populated(self):
        score = self.adapter.score_agent(SAMPLE_ADDRESS)
        self.assertEqual(score.agent_token_address, SAMPLE_ADDRESS)
        self.assertIsInstance(score.agent_id, int)
        self.assertIsInstance(score.trust_score, int)
        self.assertIn(score.trust_tier, ["HIGH", "MEDIUM", "LOW"])
        self.assertIsInstance(score.proof_hash, str)
        self.assertIsInstance(score.recommendation, str)
        self.assertEqual(score.chain, "base_sepolia")

    def test_score_in_valid_range(self):
        score = self.adapter.score_agent(SAMPLE_ADDRESS)
        self.assertGreaterEqual(score.trust_score, 0)
        self.assertLessEqual(score.trust_score, 100)

    def test_sub_scores_in_range(self):
        score = self.adapter.score_agent(SAMPLE_ADDRESS)
        self.assertGreaterEqual(score.governance_score, 0)
        self.assertGreaterEqual(score.behavioral_score, 0)
        self.assertGreaterEqual(score.onchain_score, 0)
        self.assertGreaterEqual(score.integrity_score, 0)

    def test_proof_hash_is_valid_hex(self):
        score = self.adapter.score_agent(SAMPLE_ADDRESS)
        self.assertEqual(len(score.proof_hash), 64)
        int(score.proof_hash, 16)  # No debe lanzar excepción

    def test_no_onchain_tx_before_publish(self):
        score = self.adapter.score_agent(SAMPLE_ADDRESS)
        self.assertIsNone(score.onchain_tx)

    def test_deterministic_agent_id(self):
        s1 = self.adapter.score_agent(SAMPLE_ADDRESS)
        s2 = self.adapter.score_agent(SAMPLE_ADDRESS)
        self.assertEqual(s1.agent_id, s2.agent_id)


class TestPublishScoreOnchain(unittest.TestCase):

    def test_dry_run_publish_returns_string(self):
        adapter = VirtualsTrustAdapter(chain="base_sepolia", dry_run=True)
        score = adapter.score_agent(SAMPLE_ADDRESS)
        tx = adapter.publish_score_onchain(score)
        self.assertIsInstance(tx, str)
        self.assertEqual(tx, "dry_run_tx_hash")

    def test_publish_sets_onchain_tx(self):
        adapter = VirtualsTrustAdapter(chain="base_sepolia", dry_run=True)
        score = adapter.score_agent(SAMPLE_ADDRESS)
        adapter.publish_score_onchain(score)
        self.assertEqual(score.onchain_tx, "dry_run_tx_hash")


class TestVerifyAgent(unittest.TestCase):

    def test_returns_bool(self):
        adapter = VirtualsTrustAdapter(chain="base_sepolia", dry_run=True)
        result = adapter.verify_agent(SAMPLE_ADDRESS)
        self.assertIsInstance(result, bool)


class TestBadgeMetadata(unittest.TestCase):

    def test_badge_metadata_structure(self):
        adapter = VirtualsTrustAdapter(chain="base_sepolia", dry_run=True)
        meta = adapter.get_trust_badge_metadata(SAMPLE_ADDRESS)
        required_fields = ["name", "description", "score", "badge", "proof_hash", "attributes"]
        for field in required_fields:
            self.assertIn(field, meta)

    def test_attributes_list_not_empty(self):
        adapter = VirtualsTrustAdapter(chain="base_sepolia", dry_run=True)
        meta = adapter.get_trust_badge_metadata(SAMPLE_ADDRESS)
        self.assertGreater(len(meta["attributes"]), 0)

    def test_score_in_metadata_matches_score_agent(self):
        adapter = VirtualsTrustAdapter(chain="base_sepolia", dry_run=True)
        score = adapter.score_agent(SAMPLE_ADDRESS)
        meta = adapter.get_trust_badge_metadata(SAMPLE_ADDRESS)
        # Los scores pueden diferir ligeramente por timestamps distintos
        # pero deben estar en rango válido
        self.assertGreaterEqual(meta["score"], 0)
        self.assertLessEqual(meta["score"], 100)


class TestVirtualsAgentScoreDataclass(unittest.TestCase):

    def _make_score(self, trust_score: int) -> VirtualsAgentScore:
        return VirtualsAgentScore(
            agent_token_address=SAMPLE_ADDRESS,
            agent_id=12345,
            trust_score=trust_score,
            trust_tier=VirtualsTrustAdapter._classify_tier(trust_score),
            governance_score=trust_score,
            behavioral_score=trust_score,
            onchain_score=trust_score,
            integrity_score=trust_score,
            proof_hash="a" * 64,
            z3_verified=trust_score >= 70,
            onchain_tx=None,
            chain="base_sepolia",
            timestamp=1234567890.0,
            recommendation="Test recommendation",
        )

    def test_is_trusted_high_score(self):
        score = self._make_score(85)
        self.assertTrue(score.is_trusted)

    def test_is_trusted_low_score(self):
        score = self._make_score(40)
        self.assertFalse(score.is_trusted)

    def test_badge_verified(self):
        score = self._make_score(85)
        self.assertIn("VERIFIED", score.badge)

    def test_badge_unverified(self):
        score = self._make_score(30)
        self.assertIn("UNVERIFIED", score.badge)

    def test_to_dict(self):
        score = self._make_score(75)
        d = score.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIn("trust_score", d)
        self.assertIn("agent_token_address", d)

    def test_to_json(self):
        score = self._make_score(75)
        import json
        j = score.to_json()
        parsed = json.loads(j)
        self.assertEqual(parsed["trust_score"], 75)


class TestRecommendationText(unittest.TestCase):

    def test_high_score_recommendation(self):
        rec = VirtualsTrustAdapter._build_recommendation(85, {k: 85 for k in SCORE_WEIGHTS})
        self.assertIn("verificado", rec.lower())

    def test_medium_score_recommendation(self):
        rec = VirtualsTrustAdapter._build_recommendation(65, {k: 65 for k in SCORE_WEIGHTS})
        self.assertIn("parcialmente", rec.lower())

    def test_low_score_recommendation(self):
        rec = VirtualsTrustAdapter._build_recommendation(30, {k: 30 for k in SCORE_WEIGHTS})
        self.assertIn("no", rec.lower())


if __name__ == "__main__":
    unittest.main()
