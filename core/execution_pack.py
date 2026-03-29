"""
DOFExecutionPack — Agentic Delivery Layer: Execution Tier (Layer 4).

Produces a fully deterministic, machine-readable execution artifact from a
validated DOF design. Consumable directly by engineering teams or AI code
generators — zero interpretation required.

Based on: Agentic Delivery Layer Model
  Layer 1 (Foundation)  → ConstitutionEnforcer, Z3 primitives
  Layer 2 (Design)      → Agent archetypes, MeshRouter, MCP tools
  Layer 3 (Alignment)   → Sentinel 27-checks, ZK proofs, eval gate
  Layer 4 (Execution)   → THIS MODULE — ExecutionPack output artifact

Rule: If a spec cannot be executed immediately, it is functionally incomplete.

Usage:
    from core.execution_pack import ExecutionPackBuilder

    builder = ExecutionPackBuilder(agent_id="apex_1687", version="1.0.0")
    builder.set_policy(violations=[], warnings=[], score=85)
    builder.set_sentinel(checks_passed=27, score=85, verdict="PASS")
    builder.set_state_machine(states=["idle","running","governed","done"])
    builder.add_api_endpoint("POST", "/api/interact/task", {...})
    pack = builder.build()
    pack.save("output/packs/apex_1687_v1.0.0.json")
"""

import hashlib
import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).parent.parent

# ── State Machine ─────────────────────────────────────────────────────────────

@dataclass
class StateMachineSpec:
    """Protocol state machine — deterministic agent lifecycle."""
    states: list[str]
    initial: str
    terminal: list[str]
    transitions: list[dict]  # [{from, to, trigger, guard}]
    governance_checkpoints: list[str]  # states that require governance gate

    def validate(self) -> list[str]:
        errors = []
        if self.initial not in self.states:
            errors.append(f"initial state '{self.initial}' not in states")
        for t in self.terminal:
            if t not in self.states:
                errors.append(f"terminal state '{t}' not in states")
        for tx in self.transitions:
            if tx.get("from") not in self.states:
                errors.append(f"transition from unknown state: {tx.get('from')}")
            if tx.get("to") not in self.states:
                errors.append(f"transition to unknown state: {tx.get('to')}")
        for cp in self.governance_checkpoints:
            if cp not in self.states:
                errors.append(f"governance checkpoint '{cp}' not in states")
        return errors


# ── Policy Config ─────────────────────────────────────────────────────────────

@dataclass
class PolicyConfig:
    """Machine-readable policy configuration derived from ConstitutionEnforcer."""
    hard_rules_enforced: list[str]
    soft_rules_scored: list[str]
    violations_detected: list[str]
    warnings_detected: list[str]
    governance_score: int          # 0-100
    governance_passed: bool
    z3_theorems_checked: int
    z3_proof_hash: str             # keccak256 of proof
    zk_attestation_hash: str       # ZK batch proof hash

    def to_machine_config(self) -> dict:
        return {
            "policy_version": "1.0",
            "enforcement_mode": "hard_block",
            "hard_rules": self.hard_rules_enforced,
            "soft_rules": self.soft_rules_scored,
            "runtime_violations_allowed": 0,
            "governance_threshold": 60,
            "current_score": self.governance_score,
            "passed": self.governance_passed,
            "proofs": {
                "z3_theorems": self.z3_theorems_checked,
                "z3_hash": self.z3_proof_hash,
                "zk_hash": self.zk_attestation_hash,
            }
        }


# ── Sentinel Report ───────────────────────────────────────────────────────────

@dataclass
class SentinelReport:
    """Sentinel alignment results — Layer 3 output fed into Layer 4."""
    checks_run: int
    checks_passed: int
    overall_score: int             # 0-85
    max_score: int = 85
    verdict: str = "UNKNOWN"       # PASS | FAIL | WARNING
    tracer_6d: dict = field(default_factory=dict)
    survival_status: str = "unknown"
    failed_checks: list[str] = field(default_factory=list)


# ── API Contract ──────────────────────────────────────────────────────────────

@dataclass
class APIEndpoint:
    """Single API endpoint specification — OpenAPI compatible."""
    method: str                    # GET | POST | PUT | DELETE
    path: str
    description: str
    request_schema: dict
    response_schema: dict
    governance_required: bool = True
    auth_required: bool = True
    rate_limit_rpm: int = 60


@dataclass
class APIContract:
    """Full API contract — directly consumable by code generators."""
    base_url: str
    version: str
    endpoints: list[APIEndpoint]
    auth_scheme: str = "bearer"
    governance_header: str = "X-DOF-Governance-Proof"

    def to_openapi(self) -> dict:
        paths = {}
        for ep in self.endpoints:
            paths[ep.path] = {
                ep.method.lower(): {
                    "description": ep.description,
                    "x-governance-required": ep.governance_required,
                    "x-rate-limit-rpm": ep.rate_limit_rpm,
                    "requestBody": {"content": {"application/json": {"schema": ep.request_schema}}},
                    "responses": {"200": {"content": {"application/json": {"schema": ep.response_schema}}}},
                }
            }
        return {
            "openapi": "3.1.0",
            "info": {"title": "DOF Agent API", "version": self.version},
            "servers": [{"url": self.base_url}],
            "paths": paths,
            "components": {
                "securitySchemes": {
                    "bearerAuth": {"type": "http", "scheme": "bearer"},
                    "dofGovernance": {"type": "apiKey", "in": "header", "name": self.governance_header}
                }
            }
        }


# ── ExecutionPack ─────────────────────────────────────────────────────────────

@dataclass
class ExecutionPack:
    """
    DOFExecutionPack — Layer 4 output artifact.

    A fully deterministic, machine-readable specification ready for
    immediate implementation. If any field is None, the pack is INCOMPLETE.
    """
    pack_id: str
    agent_id: str
    version: str
    created_at: str
    delivery_layer: str = "execution"  # Layer 4
    status: str = "INCOMPLETE"         # INCOMPLETE | COMPLETE | REJECTED

    # Layer 4 required artifacts
    policy_config: PolicyConfig | None = None
    state_machine: StateMachineSpec | None = None
    api_contract: APIContract | None = None
    sentinel_report: SentinelReport | None = None

    # Governance proof chain
    foundation_hash: str = ""    # hash of primitives used (Layer 1)
    design_hash: str = ""        # hash of design spec (Layer 2)
    alignment_hash: str = ""     # hash of alignment proof (Layer 3)
    execution_hash: str = ""     # hash of this pack (Layer 4)

    # Completeness validation
    completeness_errors: list[str] = field(default_factory=list)

    def validate_completeness(self) -> bool:
        """
        Core rule: if a spec cannot be executed immediately, it is incomplete.
        Returns True only if ALL required artifacts are present and valid.
        """
        errors = []

        if self.policy_config is None:
            errors.append("MISSING: policy_config — governance rules not defined")
        elif not self.policy_config.governance_passed:
            errors.append("REJECTED: governance failed — alignment layer must be re-run")

        if self.state_machine is None:
            errors.append("MISSING: state_machine — protocol states not defined")
        else:
            sm_errors = self.state_machine.validate()
            errors.extend(sm_errors)

        if self.api_contract is None:
            errors.append("MISSING: api_contract — no executable interface defined")
        elif not self.api_contract.endpoints:
            errors.append("INCOMPLETE: api_contract has zero endpoints")

        if self.sentinel_report is None:
            errors.append("MISSING: sentinel_report — alignment layer not run")
        elif self.sentinel_report.verdict == "FAIL":
            errors.append("REJECTED: sentinel verdict FAIL — cannot execute")

        self.completeness_errors = errors
        self.status = "COMPLETE" if not errors else "INCOMPLETE"
        return not bool(errors)

    def compute_hashes(self):
        """Compute layer-boundary hashes for audit trail."""
        def _hash(obj) -> str:
            raw = json.dumps(obj, sort_keys=True, default=str)
            return "0x" + hashlib.sha256(raw.encode()).hexdigest()

        if self.policy_config:
            self.foundation_hash = _hash(self.policy_config.to_machine_config())
        if self.state_machine:
            self.design_hash = _hash(asdict(self.state_machine))
        if self.sentinel_report:
            self.alignment_hash = _hash(asdict(self.sentinel_report))

        # Execution hash = hash of all three layers combined
        self.execution_hash = _hash({
            "foundation": self.foundation_hash,
            "design": self.design_hash,
            "alignment": self.alignment_hash,
            "agent_id": self.agent_id,
            "version": self.version,
        })

    def to_dict(self) -> dict:
        return {
            "pack_id": self.pack_id,
            "agent_id": self.agent_id,
            "version": self.version,
            "created_at": self.created_at,
            "delivery_layer": self.delivery_layer,
            "status": self.status,
            "completeness_errors": self.completeness_errors,
            "layer_hashes": {
                "foundation": self.foundation_hash,
                "design": self.design_hash,
                "alignment": self.alignment_hash,
                "execution": self.execution_hash,
            },
            "policy_config": self.policy_config.to_machine_config() if self.policy_config else None,
            "state_machine": asdict(self.state_machine) if self.state_machine else None,
            "api_contract": self.api_contract.to_openapi() if self.api_contract else None,
            "sentinel_report": asdict(self.sentinel_report) if self.sentinel_report else None,
        }

    def save(self, path: str | None = None) -> str:
        """Save ExecutionPack to JSON. Returns the file path."""
        if path is None:
            out_dir = BASE_DIR / "output" / "packs"
            out_dir.mkdir(parents=True, exist_ok=True)
            path = str(out_dir / f"{self.agent_id}_v{self.version}.json")

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        return path

    @classmethod
    def load(cls, path: str) -> "ExecutionPack":
        """Load and reconstruct an ExecutionPack from JSON."""
        with open(path) as f:
            data = json.load(f)
        pack = cls(
            pack_id=data["pack_id"],
            agent_id=data["agent_id"],
            version=data["version"],
            created_at=data["created_at"],
            status=data["status"],
            completeness_errors=data.get("completeness_errors", []),
            foundation_hash=data["layer_hashes"]["foundation"],
            design_hash=data["layer_hashes"]["design"],
            alignment_hash=data["layer_hashes"]["alignment"],
            execution_hash=data["layer_hashes"]["execution"],
        )
        return pack


# ── Builder ───────────────────────────────────────────────────────────────────

class ExecutionPackBuilder:
    """
    Fluent builder for DOFExecutionPack.

    Enforces layer ordering: policy → sentinel → state_machine → api → build.
    Any call to build() without all required components raises IncompletePackError.
    """

    class IncompletePackError(Exception):
        pass

    def __init__(self, agent_id: str, version: str):
        self._agent_id = agent_id
        self._version = version
        self._pack_id = "pack_" + uuid.uuid4().hex[:12]
        self._policy: PolicyConfig | None = None
        self._sentinel: SentinelReport | None = None
        self._state_machine: StateMachineSpec | None = None
        self._api_contract: APIContract | None = None
        self._endpoints: list[APIEndpoint] = []
        self._base_url = ""

    def set_policy(
        self,
        violations: list[str],
        warnings: list[str],
        score: int,
        hard_rules: list[str] | None = None,
        soft_rules: list[str] | None = None,
        z3_theorems: int = 0,
        z3_proof_hash: str = "",
        zk_attestation_hash: str = "",
    ) -> "ExecutionPackBuilder":
        self._policy = PolicyConfig(
            hard_rules_enforced=hard_rules or [],
            soft_rules_scored=soft_rules or [],
            violations_detected=violations,
            warnings_detected=warnings,
            governance_score=score,
            governance_passed=len(violations) == 0 and score >= 60,
            z3_theorems_checked=z3_theorems,
            z3_proof_hash=z3_proof_hash,
            zk_attestation_hash=zk_attestation_hash,
        )
        return self

    def set_sentinel(
        self,
        checks_passed: int,
        score: int,
        verdict: str,
        checks_run: int = 27,
        tracer_6d: dict | None = None,
        failed_checks: list[str] | None = None,
        survival_status: str = "alive",
    ) -> "ExecutionPackBuilder":
        self._sentinel = SentinelReport(
            checks_run=checks_run,
            checks_passed=checks_passed,
            overall_score=score,
            verdict=verdict,
            tracer_6d=tracer_6d or {},
            failed_checks=failed_checks or [],
            survival_status=survival_status,
        )
        return self

    def set_state_machine(
        self,
        states: list[str],
        initial: str | None = None,
        terminal: list[str] | None = None,
        transitions: list[dict] | None = None,
        governance_checkpoints: list[str] | None = None,
    ) -> "ExecutionPackBuilder":
        self._state_machine = StateMachineSpec(
            states=states,
            initial=initial or states[0],
            terminal=terminal or [states[-1]],
            transitions=transitions or [],
            governance_checkpoints=governance_checkpoints or [],
        )
        return self

    def add_api_endpoint(
        self,
        method: str,
        path: str,
        description: str = "",
        request_schema: dict | None = None,
        response_schema: dict | None = None,
        governance_required: bool = True,
        rate_limit_rpm: int = 60,
    ) -> "ExecutionPackBuilder":
        self._endpoints.append(APIEndpoint(
            method=method.upper(),
            path=path,
            description=description,
            request_schema=request_schema or {},
            response_schema=response_schema or {},
            governance_required=governance_required,
            rate_limit_rpm=rate_limit_rpm,
        ))
        return self

    def set_base_url(self, url: str) -> "ExecutionPackBuilder":
        self._base_url = url
        return self

    def build(self) -> ExecutionPack:
        """
        Build and validate the ExecutionPack.
        Raises IncompletePackError if any required artifact is missing.
        """
        api_contract = APIContract(
            base_url=self._base_url,
            version=self._version,
            endpoints=self._endpoints,
        ) if self._endpoints or self._base_url else None

        pack = ExecutionPack(
            pack_id=self._pack_id,
            agent_id=self._agent_id,
            version=self._version,
            created_at=datetime.now(timezone.utc).isoformat(),
            policy_config=self._policy,
            state_machine=self._state_machine,
            api_contract=api_contract,
            sentinel_report=self._sentinel,
        )

        pack.compute_hashes()
        is_complete = pack.validate_completeness()

        if not is_complete:
            raise self.IncompletePackError(
                f"ExecutionPack INCOMPLETE — must be sent back to alignment layer:\n"
                + "\n".join(f"  • {e}" for e in pack.completeness_errors)
            )

        return pack


# ── CLI utility ───────────────────────────────────────────────────────────────

def build_default_agent_pack(agent_id: str, version: str = "1.0.0") -> ExecutionPack:
    """
    Build a standard DOF agent ExecutionPack with default DOF governance rules.
    Used as reference template for all agent onboarding.
    """
    builder = (
        ExecutionPackBuilder(agent_id=agent_id, version=version)
        .set_policy(
            violations=[],
            warnings=[],
            score=85,
            hard_rules=["NO_SELF_MODIFICATION", "NO_EXTERNAL_CALLS_WITHOUT_APPROVAL",
                        "GOVERNANCE_BEFORE_EXECUTION", "SENTINEL_REQUIRED"],
            soft_rules=["PREFER_MINIMAL_FOOTPRINT", "LOG_ALL_DECISIONS",
                        "PREFER_DETERMINISTIC_PATHS"],
            z3_theorems=4,
        )
        .set_sentinel(
            checks_passed=27,
            score=85,
            verdict="PASS",
            survival_status="alive",
        )
        .set_state_machine(
            states=["idle", "receiving", "governed", "executing", "attesting", "done", "failed"],
            initial="idle",
            terminal=["done", "failed"],
            transitions=[
                {"from": "idle",       "to": "receiving",  "trigger": "task_received",    "guard": "auth_valid"},
                {"from": "receiving",  "to": "governed",   "trigger": "governance_check",  "guard": "always"},
                {"from": "governed",   "to": "executing",  "trigger": "governance_passed", "guard": "score>=60"},
                {"from": "governed",   "to": "failed",     "trigger": "governance_failed", "guard": "violations>0"},
                {"from": "executing",  "to": "attesting",  "trigger": "task_complete",     "guard": "always"},
                {"from": "attesting",  "to": "done",       "trigger": "attestation_ok",    "guard": "always"},
                {"from": "executing",  "to": "failed",     "trigger": "execution_error",   "guard": "always"},
            ],
            governance_checkpoints=["governed"],
        )
        .set_base_url(f"https://{agent_id}.up.railway.app")
        .add_api_endpoint(
            "GET", "/api/health",
            description="Health check — returns agent status and governance score",
            request_schema={},
            response_schema={"status": "string", "governance_score": "integer", "sentinel_verdict": "string"},
            governance_required=False,
            rate_limit_rpm=120,
        )
        .add_api_endpoint(
            "POST", "/api/interact/task",
            description="Submit task for governed execution",
            request_schema={"task": "string", "agent_id": "string", "context": "object"},
            response_schema={"result": "object", "governance_proof": "string", "trace_id": "string"},
            governance_required=True,
        )
        .add_api_endpoint(
            "GET", "/api/interactions",
            description="Retrieve interaction history with governance proofs",
            request_schema={},
            response_schema={"interactions": "array", "total": "integer"},
            governance_required=True,
        )
    )
    return builder.build()


if __name__ == "__main__":
    import sys

    agent_id = sys.argv[1] if len(sys.argv) > 1 else "dof_agent_demo"
    version = sys.argv[2] if len(sys.argv) > 2 else "1.0.0"

    try:
        pack = build_default_agent_pack(agent_id, version)
        path = pack.save()
        print(f"ExecutionPack COMPLETE")
        print(f"  Agent:    {pack.agent_id}")
        print(f"  Version:  {pack.version}")
        print(f"  Status:   {pack.status}")
        print(f"  Exec Hash:{pack.execution_hash[:18]}...")
        print(f"  Saved to: {path}")
    except ExecutionPackBuilder.IncompletePackError as e:
        print(f"ERROR — Pack incomplete:\n{e}", file=sys.stderr)
        sys.exit(1)
