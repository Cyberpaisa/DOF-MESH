"""
Tests for core/data_oracle.py — DataOracle deterministic fact-checking.

All tests are deterministic, no network or LLM calls.
"""

import json
import os
import sys
import tempfile
import unittest

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_oracle import DataOracle, FactClaim, Contradiction, OracleVerdict


class TestPatternCheckYear(unittest.TestCase):
    """Test year-based fact claims."""

    def setUp(self):
        self.oracle = DataOracle()

    def test_bitcoin_wrong_year(self):
        claims = self.oracle.pattern_check("Bitcoin was created in 2010")
        self.assertTrue(len(claims) >= 1)
        btc_claim = claims[0]
        self.assertEqual(btc_claim.status, "DISCREPANCY")
        self.assertEqual(btc_claim.extracted_value, 2010)
        self.assertEqual(btc_claim.verified_value, 2009)

    def test_bitcoin_correct_year(self):
        claims = self.oracle.pattern_check("Bitcoin was created in 2009")
        self.assertTrue(len(claims) >= 1)
        btc_claim = claims[0]
        self.assertEqual(btc_claim.status, "VERIFIED")
        self.assertEqual(btc_claim.extracted_value, 2009)

    def test_ethereum_correct_year(self):
        claims = self.oracle.pattern_check("Ethereum launched in 2015")
        self.assertTrue(len(claims) >= 1)
        eth_claim = claims[0]
        self.assertEqual(eth_claim.status, "VERIFIED")
        self.assertEqual(eth_claim.extracted_value, 2015)

    def test_avalanche_correct_year(self):
        claims = self.oracle.pattern_check("Avalanche was launched in 2020")
        self.assertTrue(len(claims) >= 1)
        avax_claim = claims[0]
        self.assertEqual(avax_claim.status, "VERIFIED")

    def test_unknown_entity_year(self):
        claims = self.oracle.pattern_check("Foochain was created in 2023")
        self.assertTrue(len(claims) >= 1)
        self.assertEqual(claims[0].status, "NO_REFERENCE")


class TestPatternCheckChainID(unittest.TestCase):
    """Test chain ID claims."""

    def setUp(self):
        self.oracle = DataOracle()

    def test_avalanche_chain_id_correct(self):
        claims = self.oracle.pattern_check("Avalanche chain ID 43114")
        self.assertTrue(len(claims) >= 1)
        chain_claim = claims[0]
        self.assertEqual(chain_claim.status, "VERIFIED")
        self.assertEqual(chain_claim.extracted_value, 43114)

    def test_chain_id_wrong(self):
        claims = self.oracle.pattern_check("Avalanche chain id: 99999")
        self.assertTrue(len(claims) >= 1)
        self.assertEqual(claims[0].status, "DISCREPANCY")


class TestPatternCheckNoClaimsText(unittest.TestCase):
    """Test text with no extractable claims."""

    def setUp(self):
        self.oracle = DataOracle()

    def test_no_claims(self):
        claims = self.oracle.pattern_check(
            "This is a simple paragraph about the weather today."
        )
        self.assertEqual(len(claims), 0)

    def test_plain_numbers_not_extracted(self):
        claims = self.oracle.pattern_check("The temperature is 72 degrees.")
        self.assertEqual(len(claims), 0)


class TestConsistencyCheck(unittest.TestCase):
    """Test intra-output contradiction detection."""

    def setUp(self):
        self.oracle = DataOracle()

    def test_contradiction_detected(self):
        text = (
            "The governance score is 85 out of 100. "
            "Later analysis confirmed the governance score is 92."
        )
        contradictions = self.oracle.consistency_check(text)
        self.assertTrue(len(contradictions) >= 1)
        c = contradictions[0]
        self.assertIn("85", [c.value_1, c.value_2])
        self.assertIn("92", [c.value_1, c.value_2])

    def test_consistent_text(self):
        text = (
            "The stability score is 0.90. The system achieved "
            "a perfect governance compliance rate."
        )
        contradictions = self.oracle.consistency_check(text)
        self.assertEqual(len(contradictions), 0)

    def test_same_entity_same_value_no_contradiction(self):
        text = "The score is 85. The score is 85."
        contradictions = self.oracle.consistency_check(text)
        self.assertEqual(len(contradictions), 0)


class TestCrossReferenceCheck(unittest.TestCase):
    """Test cross-reference verification against known facts."""

    def setUp(self):
        self.oracle = DataOracle()

    def test_agent_1687_verified(self):
        claims = self.oracle.cross_reference_check("Agent #1687 is active")
        self.assertTrue(len(claims) >= 1)
        agent_claim = [c for c in claims if c.extracted_value == 1687]
        self.assertTrue(len(agent_claim) >= 1)
        self.assertEqual(agent_claim[0].status, "VERIFIED")

    def test_agent_1686_verified(self):
        claims = self.oracle.cross_reference_check("Agent #1686 was deployed")
        agent_claim = [c for c in claims if c.extracted_value == 1686]
        self.assertTrue(len(agent_claim) >= 1)
        self.assertEqual(agent_claim[0].status, "VERIFIED")

    def test_unknown_agent(self):
        claims = self.oracle.cross_reference_check("Agent #9999 is running")
        agent_claim = [c for c in claims if c.extracted_value == 9999]
        self.assertTrue(len(agent_claim) >= 1)
        self.assertEqual(agent_claim[0].status, "NO_REFERENCE")


class TestOracleScore(unittest.TestCase):
    """Test oracle_score computation."""

    def setUp(self):
        self.oracle = DataOracle()

    def test_all_verified_score_1(self):
        verdict = self.oracle.verify("Bitcoin was created in 2009. Ethereum launched in 2015.")
        # Both should be VERIFIED
        verified = verdict.verified_count
        self.assertGreaterEqual(verified, 2)
        self.assertEqual(verdict.oracle_score, 1.0)

    def test_discrepancy_lowers_score(self):
        verdict = self.oracle.verify("Bitcoin was created in 2010")
        self.assertEqual(verdict.discrepancy_count, 1)
        self.assertLess(verdict.oracle_score, 1.0)

    def test_no_claims_score_1(self):
        verdict = self.oracle.verify("Hello world, nothing factual here.")
        self.assertEqual(verdict.oracle_score, 1.0)


class TestAddKnownFact(unittest.TestCase):
    """Test adding new facts to knowledge base."""

    def test_add_and_use_fact(self):
        # Use a temp file to avoid modifying real known_facts
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                         delete=False) as f:
            json.dump({"test": {}}, f)
            tmp_path = f.name

        try:
            oracle = DataOracle(known_facts_path=tmp_path)
            oracle.add_known_fact(
                category="test",
                key="solana_creation_year",
                value=2020,
                source="Solana docs",
                timestamp="2026-03-06T00:00:00Z",
            )

            # Verify fact was persisted
            self.assertIn("solana_creation_year", oracle.known_facts["test"])

            # Now verify against it
            claims = oracle.pattern_check("Solana was created in 2020")
            solana_claims = [c for c in claims if c.extracted_value == 2020]
            self.assertTrue(len(solana_claims) >= 1)
            self.assertEqual(solana_claims[0].status, "VERIFIED")
        finally:
            os.unlink(tmp_path)


class TestVerifyIntegration(unittest.TestCase):
    """Test full verify() integration."""

    def setUp(self):
        self.oracle = DataOracle()

    def test_clean_verdict(self):
        verdict = self.oracle.verify("Bitcoin was created in 2009. Agent #1687 is running.")
        self.assertEqual(verdict.overall_status, "CLEAN")
        self.assertGreaterEqual(verdict.verified_count, 1)
        self.assertEqual(verdict.discrepancy_count, 0)

    def test_discrepancy_verdict(self):
        verdict = self.oracle.verify("Bitcoin was created in 2010")
        self.assertEqual(verdict.overall_status, "DISCREPANCY_FOUND")
        self.assertEqual(verdict.discrepancy_count, 1)

    def test_contradiction_verdict(self):
        text = "The score is 85. Later the score is 92."
        verdict = self.oracle.verify(text)
        self.assertEqual(verdict.overall_status, "DISCREPANCY_FOUND")
        self.assertGreaterEqual(verdict.contradiction_count, 1)

    def test_processing_time_recorded(self):
        verdict = self.oracle.verify("Some text to verify")
        self.assertGreaterEqual(verdict.processing_time_ms, 0.0)


class TestNoEnigmaFallback(unittest.TestCase):
    """Test graceful behavior without Enigma connection."""

    def test_works_without_enigma(self):
        oracle = DataOracle(enigma_bridge=None)
        verdict = oracle.verify("Bitcoin was created in 2009")
        self.assertEqual(verdict.overall_status, "CLEAN")

    def test_no_facts_file(self):
        oracle = DataOracle(known_facts_path="/nonexistent/path/facts.json")
        verdict = oracle.verify("Some text")
        self.assertEqual(verdict.overall_status, "CLEAN")
        self.assertEqual(verdict.oracle_score, 1.0)


class TestFactClaimDataclass(unittest.TestCase):
    """Test FactClaim dataclass."""

    def test_default_values(self):
        claim = FactClaim(claim_text="test", claim_type="NUMERIC")
        self.assertEqual(claim.status, "NO_REFERENCE")
        self.assertEqual(claim.confidence, 0.0)
        self.assertIsNone(claim.extracted_value)

    def test_all_fields(self):
        claim = FactClaim(
            claim_text="Bitcoin created in 2009",
            claim_type="DATE",
            extracted_value=2009,
            verified_value=2009,
            status="VERIFIED",
            confidence=1.0,
            source="whitepaper",
            evidence="matches",
        )
        self.assertEqual(claim.status, "VERIFIED")
        self.assertEqual(claim.confidence, 1.0)


class TestContradictionDataclass(unittest.TestCase):
    """Test Contradiction dataclass."""

    def test_fields(self):
        c = Contradiction(
            entity="score",
            value_1="85",
            value_2="92",
            location_1=10,
            location_2=50,
        )
        self.assertEqual(c.entity, "score")
        self.assertEqual(c.value_1, "85")
        self.assertEqual(c.value_2, "92")


if __name__ == "__main__":
    unittest.main()
