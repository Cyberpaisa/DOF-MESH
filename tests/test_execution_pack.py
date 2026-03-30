"""
Tests for DOFExecutionPack — Layer 4 Execution Tier.

Validates that:
1. Complete packs build successfully
2. Incomplete packs raise IncompletePackError (not silently pass)
3. Governance-failed packs are rejected
4. Layer boundary hashes are computed correctly
5. Pack serialization round-trips
6. Default agent pack builds correctly
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.execution_pack import (
    ExecutionPackBuilder,
    ExecutionPack,
    PolicyConfig,
    SentinelReport,
    StateMachineSpec,
    APIEndpoint,
    APIContract,
    build_default_agent_pack,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def complete_builder(agent_id="test_agent", version="1.0.0") -> ExecutionPackBuilder:
    """Returns a fully configured builder that produces a COMPLETE pack."""
    return (
        ExecutionPackBuilder(agent_id=agent_id, version=version)
        .set_policy(violations=[], warnings=[], score=80)
        .set_sentinel(checks_passed=27, score=85, verdict="PASS")
        .set_state_machine(
            states=["idle", "governed", "executing", "done"],
            governance_checkpoints=["governed"],
            transitions=[
                {"from": "idle",      "to": "governed",   "trigger": "start",    "guard": "always"},
                {"from": "governed",  "to": "executing",  "trigger": "approved", "guard": "score>=60"},
                {"from": "executing", "to": "done",       "trigger": "complete", "guard": "always"},
            ]
        )
        .set_base_url("https://test-agent.railway.app")
        .add_api_endpoint("POST", "/api/interact/task", "Execute task",
                          request_schema={"task": "string"},
                          response_schema={"result": "object"})
        .add_api_endpoint("GET", "/api/health", "Health check",
                          governance_required=False)
    )


# ── Build Tests ───────────────────────────────────────────────────────────────

class TestExecutionPackBuild(unittest.TestCase):

    def test_complete_pack_builds_successfully(self):
        pack = complete_builder().build()
        self.assertEqual(pack.status, "COMPLETE")
        self.assertEqual(pack.completeness_errors, [])

    def test_pack_has_all_required_artifacts(self):
        pack = complete_builder().build()
        self.assertIsNotNone(pack.policy_config)
        self.assertIsNotNone(pack.sentinel_report)
        self.assertIsNotNone(pack.state_machine)
        self.assertIsNotNone(pack.api_contract)

    def test_pack_has_unique_id(self):
        pack1 = complete_builder().build()
        pack2 = complete_builder().build()
        self.assertNotEqual(pack1.pack_id, pack2.pack_id)

    def test_pack_delivery_layer_is_execution(self):
        pack = complete_builder().build()
        self.assertEqual(pack.delivery_layer, "execution")

    def test_pack_has_created_timestamp(self):
        pack = complete_builder().build()
        self.assertNotEqual(pack.created_at, "")
        self.assertTrue("2026" in pack.created_at or "2025" in pack.created_at)


# ── Incompleteness Tests ──────────────────────────────────────────────────────

class TestIncompletePackRejection(unittest.TestCase):
    """Core rule: incomplete packs MUST be sent back."""

    def test_missing_policy_raises_error(self):
        builder = (
            ExecutionPackBuilder("agent", "1.0")
            .set_sentinel(checks_passed=27, score=85, verdict="PASS")
            .set_state_machine(states=["idle", "done"])
            .add_api_endpoint("GET", "/api/health", "health")
        )
        with self.assertRaises(ExecutionPackBuilder.IncompletePackError) as ctx:
            builder.build()
        self.assertIn("policy_config", str(ctx.exception))

    def test_missing_sentinel_raises_error(self):
        builder = (
            ExecutionPackBuilder("agent", "1.0")
            .set_policy(violations=[], warnings=[], score=80)
            .set_state_machine(states=["idle", "done"])
            .add_api_endpoint("GET", "/api/health", "health")
        )
        with self.assertRaises(ExecutionPackBuilder.IncompletePackError) as ctx:
            builder.build()
        self.assertIn("sentinel_report", str(ctx.exception))

    def test_missing_state_machine_raises_error(self):
        builder = (
            ExecutionPackBuilder("agent", "1.0")
            .set_policy(violations=[], warnings=[], score=80)
            .set_sentinel(checks_passed=27, score=85, verdict="PASS")
            .add_api_endpoint("GET", "/api/health", "health")
        )
        with self.assertRaises(ExecutionPackBuilder.IncompletePackError) as ctx:
            builder.build()
        self.assertIn("state_machine", str(ctx.exception))

    def test_missing_api_contract_raises_error(self):
        builder = (
            ExecutionPackBuilder("agent", "1.0")
            .set_policy(violations=[], warnings=[], score=80)
            .set_sentinel(checks_passed=27, score=85, verdict="PASS")
            .set_state_machine(states=["idle", "done"])
        )
        with self.assertRaises(ExecutionPackBuilder.IncompletePackError) as ctx:
            builder.build()
        self.assertIn("api_contract", str(ctx.exception))


# ── Governance Rejection Tests ────────────────────────────────────────────────

class TestGovernanceRejection(unittest.TestCase):

    def test_policy_with_violations_is_rejected(self):
        builder = (
            ExecutionPackBuilder("agent", "1.0")
            .set_policy(violations=["SELF_MODIFICATION_DETECTED"], warnings=[], score=30)
            .set_sentinel(checks_passed=27, score=85, verdict="PASS")
            .set_state_machine(states=["idle", "done"])
            .add_api_endpoint("GET", "/api/health", "health")
        )
        with self.assertRaises(ExecutionPackBuilder.IncompletePackError) as ctx:
            builder.build()
        msg = str(ctx.exception).lower()
        self.assertTrue("governance" in msg or "REJECTED" in str(ctx.exception))

    def test_sentinel_fail_is_rejected(self):
        builder = (
            ExecutionPackBuilder("agent", "1.0")
            .set_policy(violations=[], warnings=[], score=80)
            .set_sentinel(checks_passed=10, score=20, verdict="FAIL")
            .set_state_machine(states=["idle", "done"])
            .add_api_endpoint("GET", "/api/health", "health")
        )
        with self.assertRaises(ExecutionPackBuilder.IncompletePackError) as ctx:
            builder.build()
        msg = str(ctx.exception).lower()
        self.assertTrue("sentinel" in msg or "FAIL" in str(ctx.exception))

    def test_low_governance_score_rejected(self):
        builder = (
            ExecutionPackBuilder("agent", "1.0")
            .set_policy(violations=[], warnings=[], score=40)  # below threshold
            .set_sentinel(checks_passed=27, score=85, verdict="PASS")
            .set_state_machine(states=["idle", "done"])
            .add_api_endpoint("GET", "/api/health", "health")
        )
        with self.assertRaises(ExecutionPackBuilder.IncompletePackError):
            builder.build()


# ── Layer Hash Tests ──────────────────────────────────────────────────────────

class TestLayerHashes(unittest.TestCase):

    def test_all_four_hashes_computed(self):
        pack = complete_builder().build()
        self.assertTrue(pack.foundation_hash.startswith("0x"))
        self.assertTrue(pack.design_hash.startswith("0x"))
        self.assertTrue(pack.alignment_hash.startswith("0x"))
        self.assertTrue(pack.execution_hash.startswith("0x"))

    def test_different_agents_produce_different_hashes(self):
        pack1 = complete_builder(agent_id="agent_a").build()
        pack2 = complete_builder(agent_id="agent_b").build()
        self.assertNotEqual(pack1.execution_hash, pack2.execution_hash)

    def test_same_config_produces_same_hashes(self):
        pack1 = complete_builder().build()
        pack2 = complete_builder().build()
        self.assertEqual(pack1.foundation_hash, pack2.foundation_hash)
        self.assertEqual(pack1.design_hash, pack2.design_hash)
        self.assertEqual(pack1.alignment_hash, pack2.alignment_hash)


# ── State Machine Tests ───────────────────────────────────────────────────────

class TestStateMachine(unittest.TestCase):

    def test_invalid_initial_state_detected(self):
        sm = StateMachineSpec(
            states=["idle", "done"],
            initial="nonexistent",
            terminal=["done"],
            transitions=[],
            governance_checkpoints=[],
        )
        errors = sm.validate()
        self.assertTrue(any("initial" in e for e in errors))

    def test_invalid_terminal_state_detected(self):
        sm = StateMachineSpec(
            states=["idle", "done"],
            initial="idle",
            terminal=["ghost_state"],
            transitions=[],
            governance_checkpoints=[],
        )
        errors = sm.validate()
        self.assertTrue(any("terminal" in e for e in errors))

    def test_transition_to_unknown_state_detected(self):
        sm = StateMachineSpec(
            states=["idle", "done"],
            initial="idle",
            terminal=["done"],
            transitions=[{"from": "idle", "to": "limbo", "trigger": "x", "guard": "always"}],
            governance_checkpoints=[],
        )
        errors = sm.validate()
        self.assertTrue(any("limbo" in e for e in errors))

    def test_valid_state_machine_has_no_errors(self):
        sm = StateMachineSpec(
            states=["idle", "governed", "done"],
            initial="idle",
            terminal=["done"],
            transitions=[
                {"from": "idle",     "to": "governed", "trigger": "start",    "guard": "always"},
                {"from": "governed", "to": "done",     "trigger": "complete", "guard": "always"},
            ],
            governance_checkpoints=["governed"],
        )
        errors = sm.validate()
        self.assertEqual(errors, [])


# ── API Contract Tests ────────────────────────────────────────────────────────

class TestAPIContract(unittest.TestCase):

    def test_openapi_output_structure(self):
        contract = APIContract(
            base_url="https://agent.railway.app",
            version="1.0.0",
            endpoints=[
                APIEndpoint("POST", "/api/interact/task", "task",
                            {"task": "string"}, {"result": "object"}),
                APIEndpoint("GET", "/api/health", "health", {}, {}),
            ]
        )
        openapi = contract.to_openapi()
        self.assertEqual(openapi["openapi"], "3.1.0")
        self.assertIn("/api/interact/task", openapi["paths"])
        self.assertIn("/api/health", openapi["paths"])

    def test_governance_header_in_security_schemes(self):
        contract = APIContract(
            base_url="https://agent.railway.app",
            version="1.0.0",
            endpoints=[],
        )
        openapi = contract.to_openapi()
        schemes = openapi["components"]["securitySchemes"]
        self.assertIn("dofGovernance", schemes)


# ── Serialization Tests ───────────────────────────────────────────────────────

class TestSerialization(unittest.TestCase):

    def test_pack_saves_to_json(self):
        pack = complete_builder().build()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = pack.save(os.path.join(tmpdir, "test_pack.json"))
            self.assertTrue(os.path.exists(path))
            with open(path) as f:
                data = json.load(f)
            self.assertEqual(data["status"], "COMPLETE")
            self.assertEqual(data["agent_id"], "test_agent")

    def test_pack_to_dict_has_all_keys(self):
        pack = complete_builder().build()
        d = pack.to_dict()
        self.assertIn("layer_hashes", d)
        self.assertIn("policy_config", d)
        self.assertIn("state_machine", d)
        self.assertIn("api_contract", d)
        self.assertIn("sentinel_report", d)

    def test_pack_api_contract_is_valid_openapi(self):
        pack = complete_builder().build()
        d = pack.to_dict()
        openapi = d["api_contract"]
        self.assertEqual(openapi["openapi"], "3.1.0")
        self.assertIn("paths", openapi)


# ── Default Pack Tests ────────────────────────────────────────────────────────

class TestDefaultAgentPack(unittest.TestCase):

    def test_build_default_pack(self):
        pack = build_default_agent_pack("apex_1687")
        self.assertEqual(pack.status, "COMPLETE")
        self.assertEqual(pack.agent_id, "apex_1687")

    def test_default_pack_has_governance_checkpoints(self):
        pack = build_default_agent_pack("apex_1687")
        self.assertIn("governed", pack.state_machine.governance_checkpoints)

    def test_default_pack_has_standard_endpoints(self):
        pack = build_default_agent_pack("apex_1687")
        paths = [ep.path for ep in pack.api_contract.endpoints]
        self.assertIn("/api/health", paths)
        self.assertIn("/api/interact/task", paths)
        self.assertIn("/api/interactions", paths)

    def test_default_pack_hard_rules_present(self):
        pack = build_default_agent_pack("apex_1687")
        rules = pack.policy_config.hard_rules_enforced
        self.assertIn("GOVERNANCE_BEFORE_EXECUTION", rules)
        self.assertIn("SENTINEL_REQUIRED", rules)

    def test_default_pack_sentinel_passes(self):
        pack = build_default_agent_pack("apex_1687")
        self.assertEqual(pack.sentinel_report.verdict, "PASS")
        self.assertEqual(pack.sentinel_report.checks_passed, 27)


if __name__ == "__main__":
    unittest.main()
