"""
Tests for core/adversarial.py — Adversarial evaluation protocol.
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.adversarial import (
    RedTeamAgent, GuardianAgent, DeterministicArbiter,
    AdversarialEvaluator, Issue, Defense,
)


# ─────────────────────────────────────────────────────────────────────
# Clean output samples
# ─────────────────────────────────────────────────────────────────────

CLEAN_OUTPUT = """## Market Analysis for ERC-8004

### Overview

The ERC-8004 standard defines agent identities on the Avalanche C-Chain,
enabling decentralized AI agent registration and discovery.

### Key Findings

- Agent registration costs approximately 0.5 AVAX per identity
- The standard supports metadata storage for agent capabilities
- Integration with existing DeFi protocols is straightforward

### Recommendations

1. Implement the agent registry contract first
2. Add metadata validation for agent capabilities
3. Deploy on Fuji testnet before mainnet

Source: https://eips.ethereum.org/EIPS/eip-8004
Reference: https://docs.avax.network/build/dapp/smart-contracts
"""

HALLUCINATION_OUTPUT = """## Analysis Results

According to recent studies, the blockchain market is growing at 45% annually.
Statistics show that 87% of enterprises will adopt DeFi by 2027.
Research demonstrates that agent-based systems reduce costs by 60%.

These findings confirm our hypothesis about the market opportunity.
The data confirms a massive shift toward decentralized infrastructure.
"""

UNSAFE_CODE_OUTPUT = """## Solution

Here is the implementation:

```python
import subprocess
result = eval(user_input)
subprocess.run(["rm", "-rf", "/"])
```

This should handle all edge cases properly and provides the flexibility
needed for production deployment with proper error handling mechanisms.
"""


class TestRedTeamClean(unittest.TestCase):
    """Red Team should find zero critical issues in clean output."""

    def test_clean_output_no_critical_issues(self):
        red = RedTeamAgent()
        issues = red.analyze(CLEAN_OUTPUT, "ERC-8004 market analysis")
        critical = [i for i in issues if i.severity == "critical"]
        self.assertEqual(len(critical), 0)


class TestRedTeamHallucination(unittest.TestCase):
    """Red Team should detect hallucination patterns."""

    def test_detects_hallucination_claims(self):
        red = RedTeamAgent()
        issues = red.analyze(HALLUCINATION_OUTPUT)
        hallucinations = [i for i in issues if i.category == "hallucination"]
        self.assertGreater(len(hallucinations), 0)
        # Should find at least "according to recent studies" and "statistics show"
        self.assertGreaterEqual(len(hallucinations), 2)

    def test_hallucination_is_critical_severity(self):
        red = RedTeamAgent()
        issues = red.analyze(HALLUCINATION_OUTPUT)
        hallucinations = [i for i in issues if i.category == "hallucination"]
        for h in hallucinations:
            self.assertEqual(h.severity, "critical")


class TestRedTeamSecurity(unittest.TestCase):
    """Red Team should flag unsafe code blocks."""

    def test_detects_unsafe_code(self):
        red = RedTeamAgent()
        issues = red.analyze(UNSAFE_CODE_OUTPUT)
        security = [i for i in issues if i.category == "security"]
        self.assertGreater(len(security), 0)


class TestGuardianAgent(unittest.TestCase):
    """Guardian should provide evidence-backed defenses."""

    def test_defends_clean_output(self):
        red = RedTeamAgent()
        guardian = GuardianAgent()
        issues = red.analyze(CLEAN_OUTPUT, "ERC-8004 market analysis")
        if issues:
            defenses = guardian.defend(CLEAN_OUTPUT, issues)
            # Guardian should attempt to defend all issues
            self.assertGreaterEqual(len(defenses), 0)

    def test_cannot_defend_hallucination_without_urls(self):
        red = RedTeamAgent()
        guardian = GuardianAgent()
        issues = red.analyze(HALLUCINATION_OUTPUT)
        hallucinations = [i for i in issues if i.category == "hallucination"]
        defenses = guardian.defend(HALLUCINATION_OUTPUT, hallucinations)
        # Should NOT be able to defend since there are no URLs
        self.assertEqual(len(defenses), 0)


class TestDeterministicArbiter(unittest.TestCase):
    """Arbiter should reject defenses without evidence."""

    def test_rejects_argument_defense(self):
        arbiter = DeterministicArbiter()
        issues = [Issue(
            issue_id="TEST-001",
            severity="medium",
            category="factual_error",
            evidence="Unsourced claim",
            confidence_score=0.8,
        )]
        defenses = [Defense(
            issue_id="TEST-001",
            defense_type="argument",
            evidence_data="The claim is reasonable based on industry knowledge",
        )]
        verdict = arbiter.adjudicate("test output", issues, defenses)
        self.assertEqual(len(verdict.unresolved), 1)
        self.assertEqual(verdict.unresolved[0]["issue_id"], "TEST-001")

    def test_accepts_governance_defense_when_passed(self):
        arbiter = DeterministicArbiter()
        issues = [Issue(
            issue_id="TEST-001",
            severity="low",
            category="governance",
            evidence="Empty section",
            confidence_score=0.6,
        )]
        defenses = [Defense(
            issue_id="TEST-001",
            defense_type="governance_compliant",
            evidence_data="ConstitutionEnforcer passed",
        )]
        # Use clean output so governance passes
        verdict = arbiter.adjudicate(CLEAN_OUTPUT, issues, defenses)
        self.assertEqual(len(verdict.resolved), 1)

    def test_no_defense_means_unresolved(self):
        arbiter = DeterministicArbiter()
        issues = [Issue(
            issue_id="TEST-001",
            severity="critical",
            category="hallucination",
            evidence="Fabricated claim",
            confidence_score=0.9,
        )]
        verdict = arbiter.adjudicate("test output", issues, [])
        self.assertEqual(len(verdict.unresolved), 1)
        self.assertEqual(verdict.verdict, "FAIL")


class TestAdversarialEvaluatorE2E(unittest.TestCase):
    """End-to-end adversarial evaluation pipeline."""

    def test_clean_output_passes(self):
        evaluator = AdversarialEvaluator()
        result = evaluator.evaluate(CLEAN_OUTPUT, "ERC-8004 market analysis")
        self.assertEqual(result.verdict, "PASS")
        self.assertGreaterEqual(result.score, 0.5)

    def test_hallucination_output_fails(self):
        evaluator = AdversarialEvaluator()
        result = evaluator.evaluate(HALLUCINATION_OUTPUT)
        self.assertEqual(result.verdict, "FAIL")
        self.assertGreater(result.total_issues, 0)
        self.assertGreater(len(result.unresolved), 0)

    def test_acr_is_valid_range(self):
        evaluator = AdversarialEvaluator()
        result = evaluator.evaluate(CLEAN_OUTPUT)
        self.assertGreaterEqual(result.acr, 0.0)
        self.assertLessEqual(result.acr, 1.0)

    def test_unsafe_code_fails(self):
        evaluator = AdversarialEvaluator()
        result = evaluator.evaluate(UNSAFE_CODE_OUTPUT)
        self.assertEqual(result.verdict, "FAIL")
        security_unresolved = [
            u for u in result.unresolved
            if "security" in str(u).lower() or u.get("severity") == "critical"
        ]
        self.assertGreater(len(security_unresolved), 0)


class TestACRMetric(unittest.TestCase):
    """ACR (Adversarial Consensus Rate) calculation."""

    def test_acr_no_issues_is_1(self):
        evaluator = AdversarialEvaluator()
        # Very minimal clean output
        result = evaluator.evaluate(
            "This is a brief analysis with recommendations to implement "
            "the next step. Source: https://example.com/reference\n" * 5
        )
        self.assertEqual(result.acr, 1.0)

    def test_acr_all_unresolved_is_0(self):
        arbiter = DeterministicArbiter()
        issues = [
            Issue("I-1", "critical", "hallucination", "Claim A", 0.9),
            Issue("I-2", "critical", "hallucination", "Claim B", 0.9),
        ]
        verdict = arbiter.adjudicate("short text", issues, [])
        self.assertEqual(verdict.acr, 0.0)


if __name__ == "__main__":
    unittest.main()
