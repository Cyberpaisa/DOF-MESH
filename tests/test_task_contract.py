"""
Tests for core/task_contract.py — Formal task contract enforcement.
"""

import os
import sys
import unittest
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.task_contract import TaskContract, ContractResult, _parse_contract_md


# ─────────────────────────────────────────────────────────────────────
# Sample contracts
# ─────────────────────────────────────────────────────────────────────

MINIMAL_CONTRACT = """# Test Contract

## PRECONDITIONS

- topic_provided: True
- providers_available: True

## DELIVERABLES

- output: research analysis in markdown format

## QUALITY_GATES

- governance_compliant: True

## POSTCONDITIONS

- output logged to JSONL: logs/execution_log.jsonl

## FORBIDDEN_ACTIONS

- no expose API keys in raw output
"""

FULL_CONTRACT = """# Full Research Contract

## PRECONDITIONS

- topic_provided: True
- providers_available: True

## DELIVERABLES

- output: research analysis in markdown format

## QUALITY_GATES

- governance_compliant: True
- supervisor_score>=7.0

## POSTCONDITIONS

- output logged to JSONL: logs/execution_log.jsonl

## FORBIDDEN_ACTIONS

- no expose API keys in raw output
- no unauthorized web requests
"""

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

OUTPUT_WITH_SECRET = """## Analysis

Here is the API configuration:

API_KEY = sk-abcdefghijklmnopqrstuvwxyz1234567890ABCDE

Use this key to connect to the service and retrieve analysis results
from the provider endpoint with proper authentication headers in place.
"""


# ─────────────────────────────────────────────────────────────────────
# Tests: Parsing
# ─────────────────────────────────────────────────────────────────────

class TestContractParsing(unittest.TestCase):
    """Contract markdown parsing."""

    def test_parse_all_sections(self):
        sections = _parse_contract_md(MINIMAL_CONTRACT)
        self.assertIn("PRECONDITIONS", sections)
        self.assertIn("DELIVERABLES", sections)
        self.assertIn("QUALITY_GATES", sections)
        self.assertIn("POSTCONDITIONS", sections)
        self.assertIn("FORBIDDEN_ACTIONS", sections)

    def test_parse_precondition_items(self):
        sections = _parse_contract_md(MINIMAL_CONTRACT)
        self.assertEqual(len(sections["PRECONDITIONS"]), 2)
        self.assertIn("topic_provided: True", sections["PRECONDITIONS"])

    def test_parse_from_string(self):
        contract = TaskContract.from_string(MINIMAL_CONTRACT)
        self.assertEqual(len(contract.preconditions), 2)
        self.assertEqual(len(contract.deliverables), 1)
        self.assertEqual(len(contract.quality_gates), 1)

    def test_parse_ignores_unknown_sections(self):
        text = "## UNKNOWN_SECTION\n\n- item1\n- item2\n"
        sections = _parse_contract_md(text)
        self.assertNotIn("UNKNOWN_SECTION", sections)


# ─────────────────────────────────────────────────────────────────────
# Tests: Load from file
# ─────────────────────────────────────────────────────────────────────

class TestContractFromFile(unittest.TestCase):
    """Loading contract from markdown file."""

    def test_load_from_file(self):
        contract = TaskContract.from_file("contracts/RESEARCH_CONTRACT.md")
        self.assertGreater(len(contract.preconditions), 0)
        self.assertGreater(len(contract.quality_gates), 0)
        self.assertIn("contracts/RESEARCH_CONTRACT.md", contract.source)

    def test_load_nonexistent_raises(self):
        with self.assertRaises(FileNotFoundError):
            TaskContract.from_file("contracts/NONEXISTENT.md")


# ─────────────────────────────────────────────────────────────────────
# Tests: Preconditions
# ─────────────────────────────────────────────────────────────────────

class TestPreconditions(unittest.TestCase):
    """Precondition verification."""

    def test_preconditions_met(self):
        contract = TaskContract.from_string(MINIMAL_CONTRACT)
        ok, failures = contract.check_preconditions({
            "topic_provided": True,
            "providers_available": True,
        })
        self.assertTrue(ok)
        self.assertEqual(len(failures), 0)

    def test_preconditions_missing_topic(self):
        contract = TaskContract.from_string(MINIMAL_CONTRACT)
        ok, failures = contract.check_preconditions({
            "topic_provided": False,
            "providers_available": True,
        })
        self.assertFalse(ok)
        self.assertEqual(len(failures), 1)

    def test_preconditions_missing_key(self):
        contract = TaskContract.from_string(MINIMAL_CONTRACT)
        ok, failures = contract.check_preconditions({})
        self.assertFalse(ok)
        self.assertEqual(len(failures), 2)


# ─────────────────────────────────────────────────────────────────────
# Tests: Deliverables
# ─────────────────────────────────────────────────────────────────────

class TestDeliverables(unittest.TestCase):
    """Deliverable verification."""

    def test_output_deliverable_met(self):
        contract = TaskContract.from_string(MINIMAL_CONTRACT)
        ok, failures, evidence = contract.check_deliverables(CLEAN_OUTPUT, {})
        self.assertTrue(ok)
        self.assertEqual(len(failures), 0)

    def test_output_deliverable_empty(self):
        contract = TaskContract.from_string(MINIMAL_CONTRACT)
        ok, failures, evidence = contract.check_deliverables("", {})
        self.assertFalse(ok)
        self.assertGreater(len(failures), 0)


# ─────────────────────────────────────────────────────────────────────
# Tests: Quality gates
# ─────────────────────────────────────────────────────────────────────

class TestQualityGates(unittest.TestCase):
    """Quality gate verification."""

    def test_governance_gate_passes_clean_output(self):
        contract = TaskContract.from_string(MINIMAL_CONTRACT)
        ok, passed, failed, evidence = contract.check_quality_gates(CLEAN_OUTPUT, {})
        self.assertTrue(ok)
        self.assertIn("governance_compliant", passed)

    def test_supervisor_score_gate_passes(self):
        contract = TaskContract.from_string(FULL_CONTRACT)
        ok, passed, failed, evidence = contract.check_quality_gates(
            CLEAN_OUTPUT, {"supervisor_score": 8.5}
        )
        self.assertTrue(ok)
        self.assertTrue(any("supervisor_score" in g for g in passed))

    def test_supervisor_score_gate_fails(self):
        contract = TaskContract.from_string(FULL_CONTRACT)
        ok, passed, failed, evidence = contract.check_quality_gates(
            CLEAN_OUTPUT, {"supervisor_score": 5.0}
        )
        self.assertFalse(ok)
        self.assertTrue(any("supervisor_score" in g for g in failed))


# ─────────────────────────────────────────────────────────────────────
# Tests: Forbidden actions
# ─────────────────────────────────────────────────────────────────────

class TestForbiddenActions(unittest.TestCase):
    """Forbidden action scanning."""

    def test_clean_output_no_violations(self):
        contract = TaskContract.from_string(MINIMAL_CONTRACT)
        ok, violations = contract.check_forbidden_actions(CLEAN_OUTPUT, {})
        self.assertTrue(ok)
        self.assertEqual(len(violations), 0)

    def test_detects_api_key_in_output(self):
        contract = TaskContract.from_string(MINIMAL_CONTRACT)
        ok, violations = contract.check_forbidden_actions(OUTPUT_WITH_SECRET, {})
        self.assertFalse(ok)
        self.assertGreater(len(violations), 0)
        self.assertTrue(any("API key" in v for v in violations))


# ─────────────────────────────────────────────────────────────────────
# Tests: Full contract (is_fulfilled)
# ─────────────────────────────────────────────────────────────────────

class TestContractFulfilled(unittest.TestCase):
    """End-to-end contract fulfillment."""

    def test_fulfilled_contract(self):
        contract = TaskContract.from_string(MINIMAL_CONTRACT)
        result = contract.is_fulfilled(
            output=CLEAN_OUTPUT,
            context={"supervisor_score": 8.0},
        )
        self.assertTrue(result.fulfilled)
        self.assertGreater(len(result.passed_gates), 0)
        self.assertEqual(len(result.failed_gates), 0)

    def test_breached_contract_secret_in_output(self):
        contract = TaskContract.from_string(MINIMAL_CONTRACT)
        result = contract.is_fulfilled(
            output=OUTPUT_WITH_SECRET,
            context={"supervisor_score": 8.0},
        )
        self.assertFalse(result.fulfilled)
        self.assertGreater(len(result.failed_gates), 0)
        # Should have forbidden action violation
        has_forbidden = any("FORBIDDEN" in g or "API key" in g for g in result.failed_gates)
        self.assertTrue(has_forbidden)

    def test_breached_contract_quality_gate_failed(self):
        contract = TaskContract.from_string(FULL_CONTRACT)
        result = contract.is_fulfilled(
            output=CLEAN_OUTPUT,
            context={"supervisor_score": 3.0},
        )
        self.assertFalse(result.fulfilled)
        # supervisor_score should be in failed_gates
        has_sup = any("supervisor_score" in g for g in result.failed_gates)
        self.assertTrue(has_sup)

    def test_evidence_includes_details(self):
        contract = TaskContract.from_string(MINIMAL_CONTRACT)
        result = contract.is_fulfilled(
            output=CLEAN_OUTPUT,
            context={"supervisor_score": 8.0},
        )
        self.assertIn("deliverables", result.evidence)
        self.assertIn("quality_gates", result.evidence)
        self.assertIn("forbidden_actions", result.evidence)

    def test_contract_result_repr(self):
        result = ContractResult(fulfilled=True, passed_gates=["a", "b"])
        self.assertIn("FULFILLED", repr(result))
        result2 = ContractResult(fulfilled=False, failed_gates=["x"])
        self.assertIn("BREACHED", repr(result2))


# ─────────────────────────────────────────────────────────────────────
# Tests: AST gate
# ─────────────────────────────────────────────────────────────────────

class TestASTGate(unittest.TestCase):
    """AST clean gate on code blocks."""

    def test_ast_gate_passes_clean_code(self):
        contract_md = """# Test
## QUALITY_GATES
- ast_clean: True
"""
        contract = TaskContract.from_string(contract_md)
        output = """Here is the code:

```python
import json
data = json.dumps({"key": "value"})
```

This handles the serialization properly with correct formatting
and error handling for production deployment scenarios.
"""
        ok, passed, failed, evidence = contract.check_quality_gates(output, {})
        self.assertTrue(ok)
        self.assertIn("ast_clean", passed)

    def test_ast_gate_fails_unsafe_code(self):
        contract_md = """# Test
## QUALITY_GATES
- ast_clean: True
"""
        contract = TaskContract.from_string(contract_md)
        output = """Here is the code:

```python
result = eval(user_input)
```

This provides the dynamic evaluation capability needed for the
production deployment with proper error handling in place.
"""
        ok, passed, failed, evidence = contract.check_quality_gates(output, {})
        self.assertFalse(ok)
        self.assertTrue(any("ast_clean" in g for g in failed))


class TestFromStringNoneInput(unittest.TestCase):
    """from_string(None) must not raise — treat None as empty contract."""

    def test_none_does_not_raise(self):
        try:
            TaskContract.from_string(None)
        except (AttributeError, TypeError) as e:
            self.fail(f"from_string(None) raised {type(e).__name__}: {e}")

    def test_none_returns_task_contract(self):
        tc = TaskContract.from_string(None)
        self.assertIsInstance(tc, TaskContract)

    def test_none_has_empty_sections(self):
        tc = TaskContract.from_string(None)
        self.assertEqual(tc.sections, {})

    def test_empty_string_same_as_none(self):
        tc_none = TaskContract.from_string(None)
        tc_empty = TaskContract.from_string("")
        self.assertEqual(tc_none.sections, tc_empty.sections)


if __name__ == "__main__":
    unittest.main()
