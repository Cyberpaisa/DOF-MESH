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
import pytest

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

class TestExecutionPackBuild:

    def test_complete_pack_builds_successfully(self):
        pack = complete_builder().build()
        assert pack.status == "COMPLETE"
        assert pack.completeness_errors == []

    def test_pack_has_all_required_artifacts(self):
        pack = complete_builder().build()
        assert pack.policy_config is not None
        assert pack.sentinel_report is not None
        assert pack.state_machine is not None
        assert pack.api_contract is not None

    def test_pack_has_unique_id(self):
        pack1 = complete_builder().build()
        pack2 = complete_builder().build()
        assert pack1.pack_id != pack2.pack_id

    def test_pack_delivery_layer_is_execution(self):
        pack = complete_builder().build()
        assert pack.delivery_layer == "execution"

    def test_pack_has_created_timestamp(self):
        pack = complete_builder().build()
        assert pack.created_at != ""
        assert "2026" in pack.created_at or "2025" in pack.created_at


# ── Incompleteness Tests ──────────────────────────────────────────────────────

class TestIncompletePackRejection:
    """Core rule: incomplete packs MUST be sent back."""

    def test_missing_policy_raises_error(self):
        builder = (
            ExecutionPackBuilder("agent", "1.0")
            .set_sentinel(checks_passed=27, score=85, verdict="PASS")
            .set_state_machine(states=["idle", "done"])
            .add_api_endpoint("GET", "/api/health", "health")
        )
        with pytest.raises(ExecutionPackBuilder.IncompletePackError) as exc:
            builder.build()
        assert "policy_config" in str(exc.value)

    def test_missing_sentinel_raises_error(self):
        builder = (
            ExecutionPackBuilder("agent", "1.0")
            .set_policy(violations=[], warnings=[], score=80)
            .set_state_machine(states=["idle", "done"])
            .add_api_endpoint("GET", "/api/health", "health")
        )
        with pytest.raises(ExecutionPackBuilder.IncompletePackError) as exc:
            builder.build()
        assert "sentinel_report" in str(exc.value)

    def test_missing_state_machine_raises_error(self):
        builder = (
            ExecutionPackBuilder("agent", "1.0")
            .set_policy(violations=[], warnings=[], score=80)
            .set_sentinel(checks_passed=27, score=85, verdict="PASS")
            .add_api_endpoint("GET", "/api/health", "health")
        )
        with pytest.raises(ExecutionPackBuilder.IncompletePackError) as exc:
            builder.build()
        assert "state_machine" in str(exc.value)

    def test_missing_api_contract_raises_error(self):
        builder = (
            ExecutionPackBuilder("agent", "1.0")
            .set_policy(violations=[], warnings=[], score=80)
            .set_sentinel(checks_passed=27, score=85, verdict="PASS")
            .set_state_machine(states=["idle", "done"])
        )
        with pytest.raises(ExecutionPackBuilder.IncompletePackError) as exc:
            builder.build()
        assert "api_contract" in str(exc.value)


# ── Governance Rejection Tests ────────────────────────────────────────────────

class TestGovernanceRejection:

    def test_policy_with_violations_is_rejected(self):
        builder = (
            ExecutionPackBuilder("agent", "1.0")
            .set_policy(violations=["SELF_MODIFICATION_DETECTED"], warnings=[], score=30)
            .set_sentinel(checks_passed=27, score=85, verdict="PASS")
            .set_state_machine(states=["idle", "done"])
            .add_api_endpoint("GET", "/api/health", "health")
        )
        with pytest.raises(ExecutionPackBuilder.IncompletePackError) as exc:
            builder.build()
        assert "governance" in str(exc.value).lower() or "REJECTED" in str(exc.value)

    def test_sentinel_fail_is_rejected(self):
        builder = (
            ExecutionPackBuilder("agent", "1.0")
            .set_policy(violations=[], warnings=[], score=80)
            .set_sentinel(checks_passed=10, score=20, verdict="FAIL")
            .set_state_machine(states=["idle", "done"])
            .add_api_endpoint("GET", "/api/health", "health")
        )
        with pytest.raises(ExecutionPackBuilder.IncompletePackError) as exc:
            builder.build()
        assert "sentinel" in str(exc.value).lower() or "FAIL" in str(exc.value)

    def test_low_governance_score_rejected(self):
        builder = (
            ExecutionPackBuilder("agent", "1.0")
            .set_policy(violations=[], warnings=[], score=40)  # below threshold
            .set_sentinel(checks_passed=27, score=85, verdict="PASS")
            .set_state_machine(states=["idle", "done"])
            .add_api_endpoint("GET", "/api/health", "health")
        )
        with pytest.raises(ExecutionPackBuilder.IncompletePackError):
            builder.build()


# ── Layer Hash Tests ──────────────────────────────────────────────────────────

class TestLayerHashes:

    def test_all_four_hashes_computed(self):
        pack = complete_builder().build()
        assert pack.foundation_hash.startswith("0x")
        assert pack.design_hash.startswith("0x")
        assert pack.alignment_hash.startswith("0x")
        assert pack.execution_hash.startswith("0x")

    def test_different_agents_produce_different_hashes(self):
        pack1 = complete_builder(agent_id="agent_a").build()
        pack2 = complete_builder(agent_id="agent_b").build()
        assert pack1.execution_hash != pack2.execution_hash

    def test_same_config_produces_same_hashes(self):
        pack1 = complete_builder().build()
        pack2 = complete_builder().build()
        # Foundation, design, alignment hashes are deterministic
        assert pack1.foundation_hash == pack2.foundation_hash
        assert pack1.design_hash == pack2.design_hash
        assert pack1.alignment_hash == pack2.alignment_hash


# ── State Machine Tests ───────────────────────────────────────────────────────

class TestStateMachine:

    def test_invalid_initial_state_detected(self):
        sm = StateMachineSpec(
            states=["idle", "done"],
            initial="nonexistent",
            terminal=["done"],
            transitions=[],
            governance_checkpoints=[],
        )
        errors = sm.validate()
        assert any("initial" in e for e in errors)

    def test_invalid_terminal_state_detected(self):
        sm = StateMachineSpec(
            states=["idle", "done"],
            initial="idle",
            terminal=["ghost_state"],
            transitions=[],
            governance_checkpoints=[],
        )
        errors = sm.validate()
        assert any("terminal" in e for e in errors)

    def test_transition_to_unknown_state_detected(self):
        sm = StateMachineSpec(
            states=["idle", "done"],
            initial="idle",
            terminal=["done"],
            transitions=[{"from": "idle", "to": "limbo", "trigger": "x", "guard": "always"}],
            governance_checkpoints=[],
        )
        errors = sm.validate()
        assert any("limbo" in e for e in errors)

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
        assert errors == []


# ── API Contract Tests ────────────────────────────────────────────────────────

class TestAPIContract:

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
        assert openapi["openapi"] == "3.1.0"
        assert "/api/interact/task" in openapi["paths"]
        assert "/api/health" in openapi["paths"]

    def test_governance_header_in_security_schemes(self):
        contract = APIContract(
            base_url="https://agent.railway.app",
            version="1.0.0",
            endpoints=[],
        )
        openapi = contract.to_openapi()
        schemes = openapi["components"]["securitySchemes"]
        assert "dofGovernance" in schemes


# ── Serialization Tests ───────────────────────────────────────────────────────

class TestSerialization:

    def test_pack_saves_to_json(self):
        pack = complete_builder().build()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = pack.save(os.path.join(tmpdir, "test_pack.json"))
            assert os.path.exists(path)
            with open(path) as f:
                data = json.load(f)
            assert data["status"] == "COMPLETE"
            assert data["agent_id"] == "test_agent"

    def test_pack_to_dict_has_all_keys(self):
        pack = complete_builder().build()
        d = pack.to_dict()
        assert "layer_hashes" in d
        assert "policy_config" in d
        assert "state_machine" in d
        assert "api_contract" in d
        assert "sentinel_report" in d

    def test_pack_api_contract_is_valid_openapi(self):
        pack = complete_builder().build()
        d = pack.to_dict()
        openapi = d["api_contract"]
        assert openapi["openapi"] == "3.1.0"
        assert "paths" in openapi


# ── Default Pack Tests ────────────────────────────────────────────────────────

class TestDefaultAgentPack:

    def test_build_default_pack(self):
        pack = build_default_agent_pack("apex_1687")
        assert pack.status == "COMPLETE"
        assert pack.agent_id == "apex_1687"

    def test_default_pack_has_governance_checkpoints(self):
        pack = build_default_agent_pack("apex_1687")
        assert "governed" in pack.state_machine.governance_checkpoints

    def test_default_pack_has_standard_endpoints(self):
        pack = build_default_agent_pack("apex_1687")
        paths = [ep.path for ep in pack.api_contract.endpoints]
        assert "/api/health" in paths
        assert "/api/interact/task" in paths
        assert "/api/interactions" in paths

    def test_default_pack_hard_rules_present(self):
        pack = build_default_agent_pack("apex_1687")
        rules = pack.policy_config.hard_rules_enforced
        assert "GOVERNANCE_BEFORE_EXECUTION" in rules
        assert "SENTINEL_REQUIRED" in rules

    def test_default_pack_sentinel_passes(self):
        pack = build_default_agent_pack("apex_1687")
        assert pack.sentinel_report.verdict == "PASS"
        assert pack.sentinel_report.checks_passed == 27
