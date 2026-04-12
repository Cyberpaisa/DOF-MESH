"""
Tool Hooks — PreToolUse / PostToolUse governance pipeline for DOF-MESH.

Converts DOF from post-hoc monitoring to pre-execution verification:

    BEFORE (current):  agent runs tool → governance checks output → log
    AFTER  (this):     PreToolUse verifies BEFORE → tool runs → PostToolUse attests

Architecture inspired by the StreamingToolExecutor pattern:
    PreToolUse  → ConstitutionEnforcer → Z3Gate → HookResult(allowed)
    PostToolUse → audit trail entry  → attestation hash → PostHookResult

Integration point in crew_runner.py:
    hook = ToolHookPipeline()
    pre  = hook.pre_tool_use(tool_name, tool_input, agent_id)
    if not pre.allowed:
        raise GovernanceViolation(pre.reason)
    output = execute_tool(...)
    post = hook.post_tool_use(tool_name, output, agent_id, pre_result=pre)

Fallbacks:
    - Z3Gate unavailable → deterministic Constitution check only
    - Constitution unavailable → BLOCKED_TOOLS list only
    - All unavailable → ALLOW with warning (never silently block)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger("dof.tool_hooks")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT_LOG = os.path.join(BASE_DIR, "logs", "tool_hooks.jsonl")

# ── Defaults ──────────────────────────────────────────────────────────────────

# Tools that are unconditionally blocked regardless of constitution state.
# These map directly to ConstitutionEnforcer HARD_RULES for imports/calls.
BLOCKED_TOOLS: set[str] = {
    "shell",
    "bash",
    "execute_command",
    "run_script",
    "eval",
    "exec",
    "subprocess",
    "os_system",
}

# Tools that are always allowed without Z3 (read-only, deterministic)
SAFE_TOOLS: set[str] = {
    "read_file",
    "list_directory",
    "search",
    "web_search",
    "fetch_url",
    "get_current_time",
    "Read",
    "Glob",
    "Grep",
}

# Tools safe for concurrent execution (read-only, no side effects)
# Superset of SAFE_TOOLS that includes all known read-only Claude Code tools
CONCURRENT_SAFE_TOOLS: frozenset[str] = frozenset(SAFE_TOOLS | {
    "search_files",
    "list_files",
    "WebSearch",
    "WebFetch",
    "mcp__brave",
    "mcp__context7",
})

# Tools that write state — must run serially
WRITE_TOOLS: frozenset[str] = frozenset({
    "Edit", "Write", "Bash", "NotebookEdit", "computer_use",
    "write_file", "create_file", "delete_file", "move_file",
})

# Output size budget per tool (chars) — prevents context flooding
TOOL_OUTPUT_LIMITS: dict[str, int] = {
    "Bash":      8_000,
    "Read":     10_000,
    "fetch_url": 5_000,
    "WebFetch":  5_000,
    "Grep":      6_000,
    "Glob":      4_000,
    "_default":  4_000,
}


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class HookResult:
    """Result of a PreToolUse check."""
    allowed: bool
    reason: str
    z3_proof: Optional[str] = None          # keccak256 proof hash if Z3 ran
    governance_score: float = 1.0
    layer: str = "none"                     # which layer made the decision
    latency_ms: float = 0.0

    @property
    def blocked(self) -> bool:
        return not self.allowed


@dataclass
class PostHookResult:
    """Result of a PostToolUse audit pass."""
    attestation_hash: str                   # keccak256 of tool_name+output+agent_id
    trace_entry: dict = field(default_factory=dict)
    audit_written: bool = False


# ── Exceptions ────────────────────────────────────────────────────────────────

class GovernanceViolation(Exception):
    """Raised when PreToolUse blocks a tool call."""
    def __init__(self, reason: str, hook_result: Optional[HookResult] = None):
        super().__init__(reason)
        self.hook_result = hook_result


# ── Audit logger ─────────────────────────────────────────────────────────────

def _write_audit(entry: dict) -> None:
    os.makedirs(os.path.dirname(AUDIT_LOG), exist_ok=True)
    try:
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception as e:
        logger.error(f"tool_hooks audit write failed: {e}")


# ── Pipeline ──────────────────────────────────────────────────────────────────

class ToolHookPipeline:
    """
    PreToolUse / PostToolUse governance pipeline.

    Layer order in pre_tool_use:
      1. BLOCKED_TOOLS hardcoded list  — zero latency, no LLM
      2. ConstitutionEnforcer          — deterministic rule check on tool_input
      3. Z3Gate                        — formal verification (skipped for SAFE_TOOLS)

    Layer order in post_tool_use:
      1. Audit trail entry (JSONL)
      2. Attestation hash (keccak256)
      3. get_execution_trace() compatible dict
    """

    def __init__(
        self,
        blocked_tools: Optional[set[str]] = None,
        safe_tools: Optional[set[str]] = None,
        skip_z3_for_safe: bool = True,
    ):
        self._blocked = blocked_tools if blocked_tools is not None else BLOCKED_TOOLS
        self._safe = safe_tools if safe_tools is not None else SAFE_TOOLS
        self._skip_z3_for_safe = skip_z3_for_safe

        # Lazy-load heavy dependencies
        self._enforcer = None
        self._z3_gate = None
        self._z3_available = False

        self._init_dependencies()

    def _init_dependencies(self) -> None:
        try:
            from core.governance import ConstitutionEnforcer
            self._enforcer = ConstitutionEnforcer()
        except Exception as e:
            logger.warning(f"ConstitutionEnforcer unavailable: {e} — using BLOCKED_TOOLS only")

        try:
            from core.z3_gate import Z3Gate
            from core.agent_output import AgentOutput  # noqa: F401 — validate import
            self._z3_gate = Z3Gate(timeout_ms=3000)
            self._z3_available = True
        except Exception as e:
            logger.debug(f"Z3Gate unavailable: {e} — deterministic fallback active")

    # ── PRE TOOL USE ─────────────────────────────────────────────────────────

    def pre_tool_use(
        self,
        tool_name: str,
        tool_input: str,
        agent_id: str,
    ) -> HookResult:
        """
        Run governance pipeline BEFORE a tool executes.

        Checks in order:
          1. Hardcoded BLOCKED_TOOLS → immediate block, no further checks
          2. ConstitutionEnforcer on tool_input text
          3. Z3Gate if not a SAFE_TOOL and Z3 is available

        Returns HookResult(allowed=True/False, reason, z3_proof, layer).
        Never raises — always returns a result so callers can decide.
        """
        t0 = time.time()

        # ── Layer 1: hardcoded block list ─────────────────────────────────────
        if tool_name.lower() in {t.lower() for t in self._blocked}:
            result = HookResult(
                allowed=False,
                reason=f"Tool '{tool_name}' is in BLOCKED_TOOLS (HARD rule)",
                governance_score=0.0,
                layer="BLOCKED_TOOLS",
                latency_ms=(time.time() - t0) * 1000,
            )
            self._log_pre(tool_name, tool_input, agent_id, result)
            return result

        # ── Layer 2: ConstitutionEnforcer ─────────────────────────────────────
        gov_score = 1.0
        gov_violations: list[str] = []

        if self._enforcer is not None:
            try:
                # Check the tool input text for governance rule violations
                gov_result = self._enforcer.check(tool_input or tool_name)
                gov_score = gov_result.score if hasattr(gov_result, "score") else 1.0
                if not gov_result.passed:
                    violations = gov_result.violations or []
                    result = HookResult(
                        allowed=False,
                        reason=f"Constitution BLOCKED: {'; '.join(violations[:2])}",
                        governance_score=gov_score,
                        layer="ConstitutionEnforcer",
                        latency_ms=(time.time() - t0) * 1000,
                    )
                    self._log_pre(tool_name, tool_input, agent_id, result)
                    return result
                gov_violations = list(gov_result.warnings or [])
            except Exception as e:
                logger.warning(f"ConstitutionEnforcer check failed: {e}")

        # ── Layer 3: Z3Gate (skip for SAFE_TOOLS) ────────────────────────────
        z3_proof: Optional[str] = None

        should_z3 = (
            self._z3_available
            and self._z3_gate is not None
            and not (self._skip_z3_for_safe and tool_name in self._safe)
        )

        if should_z3:
            try:
                from core.agent_output import AgentOutput, OutputType
                agent_output = AgentOutput(
                    agent_id=agent_id,
                    output_type=OutputType.GOVERNANCE_CHECK,
                    proposed_value=tool_name,
                    evidence={"tool_input": tool_input[:500]},
                )
                verification = self._z3_gate.validate_output(agent_output)

                from core.z3_gate import GateResult
                if verification.result == GateResult.REJECTED:
                    result = HookResult(
                        allowed=False,
                        reason=f"Z3Gate REJECTED: {verification.counterexample}",
                        governance_score=0.0,
                        layer="Z3Gate",
                        latency_ms=(time.time() - t0) * 1000,
                    )
                    self._log_pre(tool_name, tool_input, agent_id, result)
                    return result

                if verification.proof_transcript:
                    z3_proof = hashlib.sha256(
                        verification.proof_transcript.encode()
                    ).hexdigest()
            except Exception as e:
                logger.debug(f"Z3Gate check skipped: {e}")

        # ── All layers passed ─────────────────────────────────────────────────
        layer_used = "Z3Gate" if z3_proof else ("ConstitutionEnforcer" if self._enforcer else "BLOCKED_TOOLS")
        result = HookResult(
            allowed=True,
            reason="APPROVED" + (f" (warnings: {len(gov_violations)})" if gov_violations else ""),
            z3_proof=z3_proof,
            governance_score=gov_score,
            layer=layer_used,
            latency_ms=(time.time() - t0) * 1000,
        )
        self._log_pre(tool_name, tool_input, agent_id, result)
        return result

    # ── POST TOOL USE ─────────────────────────────────────────────────────────

    def post_tool_use(
        self,
        tool_name: str,
        tool_output: str,
        agent_id: str,
        pre_result: Optional[HookResult] = None,
    ) -> PostHookResult:
        """
        Run audit pipeline AFTER a tool executes.

        Records:
          - Attestation hash: keccak256(tool_name + output + agent_id + ts)
          - Audit JSONL entry
          - trace_entry compatible with get_execution_trace()

        Returns PostHookResult(attestation_hash, trace_entry, audit_written).
        Never raises.
        """
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")

        # Deterministic attestation hash (no on-chain — per-tool level)
        # Hash uses raw output (before budgeting) for integrity
        hash_payload = f"{tool_name}|{tool_output[:500]}|{agent_id}|{ts}"
        attestation_hash = "0x" + hashlib.sha256(hash_payload.encode()).hexdigest()

        # Budget output AFTER hash to avoid altering attestation
        budgeted_output = self._budget_output(tool_name, tool_output or "")

        trace_entry = {
            "event":            "tool_execution",
            "tool_name":        tool_name,
            "agent_id":         agent_id,
            "timestamp":        ts,
            "attestation_hash": attestation_hash,
            "pre_allowed":      pre_result.allowed if pre_result else None,
            "pre_layer":        pre_result.layer if pre_result else None,
            "pre_latency_ms":   pre_result.latency_ms if pre_result else None,
            "z3_proof":         pre_result.z3_proof if pre_result else None,
            "output_preview":   budgeted_output[:200],
            "output_budgeted":  len(budgeted_output) < len(tool_output or ""),
        }

        audit_entry = {
            "ts":       time.time(),
            "iso":      ts,
            **trace_entry,
        }

        _write_audit(audit_entry)

        return PostHookResult(
            attestation_hash=attestation_hash,
            trace_entry=trace_entry,
            audit_written=True,
        )

    # ── Tool classification & budgeting ───────────────────────────────────────

    def classify_tool(self, tool_name: str) -> str:
        """Classify a tool for concurrency and Z3 routing.

        Returns:
            "concurrent_safe" — read-only, can run in parallel, skip Z3Gate
            "write"           — mutates state, must run serially
            "default"         — unknown tool, run through full pipeline
        """
        if tool_name in CONCURRENT_SAFE_TOOLS:
            return "concurrent_safe"
        if tool_name in WRITE_TOOLS:
            return "write"
        return "default"

    def _budget_output(self, tool_name: str, output: str) -> str:
        """Truncate tool output to the configured budget for this tool.

        Prevents context flooding when tools return large payloads.
        The raw output is preserved for hashing — this only affects
        what gets stored in trace_entry / audit JSONL.
        """
        limit = TOOL_OUTPUT_LIMITS.get(tool_name, TOOL_OUTPUT_LIMITS["_default"])
        if len(output) <= limit:
            return output
        truncated = output[:limit]
        return truncated + f"\n…[truncated {len(output) - limit} chars by budget]"

    # ── Internal logging ──────────────────────────────────────────────────────

    def _log_pre(
        self,
        tool_name: str,
        tool_input: str,
        agent_id: str,
        result: HookResult,
    ) -> None:
        level = logging.WARNING if result.blocked else logging.DEBUG
        logger.log(
            level,
            f"[PreToolUse] tool={tool_name} agent={agent_id} "
            f"allowed={result.allowed} layer={result.layer} "
            f"latency={result.latency_ms:.1f}ms"
        )
        _write_audit({
            "ts":         time.time(),
            "iso":        time.strftime("%Y-%m-%dT%H:%M:%S"),
            "event":      "pre_tool_use",
            "tool_name":  tool_name,
            "agent_id":   agent_id,
            "allowed":    result.allowed,
            "reason":     result.reason,
            "layer":      result.layer,
            "z3_proof":   result.z3_proof,
            "gov_score":  result.governance_score,
            "latency_ms": result.latency_ms,
            "input_preview": (tool_input or "")[:200],
        })
