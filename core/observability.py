"""
Run-Level Observability — FASE 1.

Full run traces with UUID v4, session tracking, ordered steps,
token counting, derived metrics, deterministic mode, and causal
error classification.

Every execution generates a complete RunTrace exported as JSON.
Derived metrics saved to logs/experiments/runs.jsonl.
"""

import os
import re
import json
import time
import uuid
import hashlib
import logging
import math
import functools
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Any

logger = logging.getLogger("core.observability")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPERIMENTS_DIR = os.path.join(BASE_DIR, "logs", "experiments")
TRACES_DIR = os.path.join(BASE_DIR, "logs", "traces")

# ── Deterministic Mode ──
DETERMINISTIC_MODE = bool(os.getenv("DETERMINISTIC_MODE", ""))
_DETERMINISTIC_SEED = 42
_DETERMINISTIC_PROVIDER_ORDER = ["nvidia", "cerebras", "groq", "zhipu"]  # nvidia first: cerebras+groq keys expired


def set_deterministic(enabled: bool):
    """Toggle deterministic mode at runtime."""
    global DETERMINISTIC_MODE
    DETERMINISTIC_MODE = enabled
    if enabled:
        import random
        random.seed(_DETERMINISTIC_SEED)
        logger.info(f"Deterministic mode ON (seed={_DETERMINISTIC_SEED})")
    else:
        logger.info("Deterministic mode OFF")


def get_deterministic_providers() -> list[str] | None:
    """Return fixed provider order if deterministic mode is on."""
    if DETERMINISTIC_MODE:
        return list(_DETERMINISTIC_PROVIDER_ORDER)
    return None


# ── Session Management ──

_SESSION_ID: str = ""


def get_session_id() -> str:
    global _SESSION_ID
    if not _SESSION_ID:
        _SESSION_ID = str(uuid.uuid4())
    return _SESSION_ID


def reset_session():
    global _SESSION_ID
    _SESSION_ID = str(uuid.uuid4())
    return _SESSION_ID


# ── Error Classification ──

class ErrorClass(str, Enum):
    """Causal classification for execution errors."""
    MODEL_FAILURE = "MODEL_FAILURE"
    INFRA_FAILURE = "INFRA_FAILURE"
    GOVERNANCE_FAILURE = "GOVERNANCE_FAILURE"
    LLM_FAILURE = "LLM_FAILURE"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    MEMORY_FAILURE = "MEMORY_FAILURE"
    HASH_FAILURE = "HASH_FAILURE"
    Z3_FAILURE = "Z3_FAILURE"
    AGENT_FAILURE = "AGENT_FAILURE"
    UNKNOWN = "UNKNOWN"


def classify_error(exception: str | Exception, context: dict | None = None) -> ErrorClass:
    """Classify an error into a causal category.

    Args:
        exception: Error message string or Exception object.
        context: Optional dict with keys:
            - governance_violations: list of governance violation strings
            - retry_provider_different: bool, True if retry used a different provider
            - retry_succeeded: bool, True if retry with different provider succeeded
            - retry_same_failure: bool, True if retry with different provider had same error

    Returns:
        ErrorClass enum value.
    """
    context = context or {}
    error_str = str(exception).lower()

    # 1. Governance failure — check context first (most specific)
    if context.get("governance_violations"):
        return ErrorClass.GOVERNANCE_FAILURE

    # Check error message for governance keywords
    gov_keywords = ["governance", "constitution", "blocked", "hallucination",
                     "language_compliance", "no_empty_output", "ast_verify"]
    if any(kw in error_str for kw in gov_keywords):
        return ErrorClass.GOVERNANCE_FAILURE

    # 2. Agent failure — agent-level execution problems (before INFRA to avoid
    #    "timeout" in infra_patterns matching "reflexion_timeout" / "agent_timeout")
    agent_keywords = ["tool_call_failed", "function_calling_error",
                      "planning_loop_detected", "reflexion_timeout",
                      "agent_timeout", "max_iterations",
                      "agent_loop", "tool_execution_error",
                      "tool_not_found", "tool_timeout",
                      "invalid_json_schema", "missing_required_param",
                      "max_iterations_exceeded", "reasoning_failed",
                      "agent_stuck", "no_progress_detected"]
    if any(kw in error_str for kw in agent_keywords):
        return ErrorClass.AGENT_FAILURE

    # 3. Infrastructure failure — HTTP errors, rate limits, timeouts
    infra_patterns = [
        r"429", r"500", r"502", r"503", r"504",
        r"rate.?limit", r"rate_limit", r"resource.?exhausted",
        r"timeout", r"timed?.?out", r"connection.?error",
        r"connection.?refused", r"connection.?reset",
        r"ssl.?error", r"dns.?resolution", r"network",
        r"econnrefused", r"econnreset", r"epipe",
        r"service.?unavailable", r"gateway.?timeout",
        r"too.?many.?requests",
    ]
    for pattern in infra_patterns:
        if re.search(pattern, error_str):
            return ErrorClass.INFRA_FAILURE

    # 3. Cross-provider analysis: retry with different provider succeeded → INFRA
    if context.get("retry_provider_different") and context.get("retry_succeeded"):
        return ErrorClass.INFRA_FAILURE

    # 4. Cross-provider analysis: retry with different provider had same failure → MODEL
    if context.get("retry_provider_different") and context.get("retry_same_failure"):
        return ErrorClass.MODEL_FAILURE

    # 5. Model-specific failure patterns
    model_keywords = ["invalid grammar", "not supported", "bad request",
                      "model_incompatible", "parse_error", "pydantic",
                      "validation error", "output format",
                      "content_filter", "content filter"]
    if any(kw in error_str for kw in model_keywords):
        return ErrorClass.MODEL_FAILURE

    # 6. LLM failure — response quality, token limits, empty outputs
    llm_keywords = ["max_tokens", "token limit", "context_length",
                     "context length exceeded", "empty response",
                     "no response", "truncated", "finish_reason"]
    if any(kw in error_str for kw in llm_keywords):
        return ErrorClass.LLM_FAILURE

    # 7. Provider failure — API key, auth, quota, billing
    provider_keywords = ["api_key", "api key", "invalid key",
                         "authentication", "unauthorized", "401",
                         "403", "quota", "billing", "credits",
                         "permission denied", "access denied"]
    if any(kw in error_str for kw in provider_keywords):
        return ErrorClass.PROVIDER_FAILURE

    # 8. Memory failure — ChromaDB, embeddings, vector store
    memory_keywords = ["chromadb", "embedding", "vector", "memory_manager",
                       "collection", "chroma", "similarity_search"]
    if any(kw in error_str for kw in memory_keywords):
        return ErrorClass.MEMORY_FAILURE

    # 9. Hash/Merkle failure — hex, hash, merkle
    hash_keywords = ["hex", "hash", "merkle", "fromhex",
                     "non-hexadecimal", "blake3", "sha256"]
    if any(kw in error_str for kw in hash_keywords):
        return ErrorClass.HASH_FAILURE

    # 10. Z3/SMT failure — solver, verification
    z3_keywords = ["z3", "smt", "proof failed", "theorem", "z3exception"]
    if any(kw in error_str for kw in z3_keywords):
        return ErrorClass.Z3_FAILURE

    return ErrorClass.UNKNOWN


# ── Step Trace ──

@dataclass
class StepTrace:
    """One step in a run trace."""
    step_index: int
    agent: str
    provider: str
    latency_ms: float = 0.0
    retries: int = 0
    status: str = "pending"
    supervisor_score: float = 0.0
    governance_passed: bool = True
    token_input: int = 0
    token_output: int = 0
    error: str = ""
    provider_switched: bool = False
    error_class: str = ""
    causal_chain: list[dict] = field(default_factory=list)


# ── Run Trace ──

@dataclass
class RunTrace:
    """Complete trace for one execution run."""
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = field(default_factory=get_session_id)
    crew_name: str = ""
    mode: str = "production"  # research | production
    timestamp_start: str = ""
    timestamp_end: str = ""
    start_epoch: float = 0.0
    end_epoch: float = 0.0
    total_latency_ms: float = 0.0
    status: str = "pending"  # ok | error | escalated
    deterministic: bool = False
    input_text: str = ""
    input_hash: str = ""
    output_len: int = 0
    steps: list[StepTrace] = field(default_factory=list)
    # Derived metrics
    stability_score: float = 0.0
    provider_fragility_index: float = 0.0
    retry_pressure: float = 0.0
    governance_compliance_rate: float = 0.0
    supervisor_score_final: float = 0.0
    supervisor_decision: str = ""
    total_retries: int = 0
    total_token_input: int = 0
    total_token_output: int = 0
    # Causal error tracking
    error_distribution: dict = field(default_factory=dict)
    provider_reliability: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["steps"] = [asdict(s) for s in self.steps]
        return d

    def export_dashboard(self) -> dict:
        """Export data structured for dashboard visualization.

        Returns:
            error_class_distribution: {ErrorClass: count} for pie chart
            provider_reliability_over_time: {provider: {success: N, fail: N, rate: float}} for heatmap
            causal_chains: list of step causal chains for debugging
        """
        # Error class distribution
        error_dist: dict[str, int] = {}
        for step in self.steps:
            if step.error_class:
                error_dist[step.error_class] = error_dist.get(step.error_class, 0) + 1

        # Provider reliability
        provider_stats: dict[str, dict] = {}
        for step in self.steps:
            provider = step.provider
            if provider not in provider_stats:
                provider_stats[provider] = {"success": 0, "fail": 0}
            if step.status in ("completed", "ok"):
                provider_stats[provider]["success"] += 1
            elif step.status == "failed":
                provider_stats[provider]["fail"] += 1

        for provider, stats in provider_stats.items():
            total = stats["success"] + stats["fail"]
            stats["rate"] = round(stats["success"] / total, 4) if total > 0 else 0.0

        # Causal chains (only steps that have them)
        chains = []
        for step in self.steps:
            if step.causal_chain:
                chains.append({
                    "step_index": step.step_index,
                    "agent": step.agent,
                    "provider": step.provider,
                    "error_class": step.error_class,
                    "chain": step.causal_chain,
                })

        return {
            "error_class_distribution": error_dist,
            "provider_reliability_over_time": provider_stats,
            "causal_chains": chains,
        }


# ── Token Estimation ──

def estimate_tokens(text: str) -> int:
    """Estimate token count (~4 chars per token for multilingual).

    Returns 0 for empty or whitespace-only strings (no real tokens).
    """
    if not text or not text.strip():
        return 0
    return max(1, len(text) // 4)


# ── Derived Metrics Calculator ──

def compute_derived_metrics(trace: RunTrace) -> RunTrace:
    """Compute all derived metrics from a completed RunTrace."""
    steps = trace.steps
    n = len(steps) if steps else 1

    # Stability Score = 1 - (step_failures / total_steps)
    failures = sum(1 for s in steps if s.status == "failed")
    trace.stability_score = round(1.0 - (failures / n), 4)

    # Provider Fragility Index = provider_switches / total_steps
    switches = sum(1 for s in steps if s.provider_switched)
    trace.provider_fragility_index = round(switches / n, 4)

    # Retry Pressure = retries / total_steps
    total_retries = sum(s.retries for s in steps)
    trace.retry_pressure = round(total_retries / n, 4)
    trace.total_retries = total_retries

    # Governance Compliance Rate = governance_passed_steps / total_steps
    gov_passed = sum(1 for s in steps if s.governance_passed)
    trace.governance_compliance_rate = round(gov_passed / n, 4)

    # Token totals
    trace.total_token_input = sum(s.token_input for s in steps)
    trace.total_token_output = sum(s.token_output for s in steps)

    # Total latency
    trace.total_latency_ms = round(sum(s.latency_ms for s in steps), 1)

    # Error distribution
    error_dist: dict[str, int] = {}
    provider_stats: dict[str, dict] = {}
    for s in steps:
        if s.error_class:
            error_dist[s.error_class] = error_dist.get(s.error_class, 0) + 1
        provider = s.provider
        if provider not in provider_stats:
            provider_stats[provider] = {"success": 0, "fail": 0}
        if s.status in ("completed", "ok"):
            provider_stats[provider]["success"] += 1
        elif s.status == "failed":
            provider_stats[provider]["fail"] += 1
    for stats in provider_stats.values():
        total = stats["success"] + stats["fail"]
        stats["rate"] = round(stats["success"] / total, 4) if total > 0 else 0.0

    trace.error_distribution = error_dist
    trace.provider_reliability = provider_stats

    return trace


# ── Causal Trace Decorator ──

# Thread-local storage for the active RunTrace
_active_trace: RunTrace | None = None


def get_active_trace() -> RunTrace | None:
    """Return the currently active RunTrace (set by @causal_trace)."""
    return _active_trace


def causal_trace(task_id: str = "", provider: str = ""):
    """Decorator that wraps a function with automatic causal error tracking.

    Captures exceptions, classifies them, and appends StepTrace entries
    to the active RunTrace.

    Usage:
        @causal_trace(task_id="research-001")
        def run_research(topic):
            return crew.kickoff()
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            global _active_trace
            trace = _active_trace
            own_trace = False

            if trace is None:
                trace = RunTrace(
                    crew_name=task_id or func.__name__,
                    timestamp_start=time.strftime("%Y-%m-%dT%H:%M:%S"),
                    start_epoch=time.time(),
                )
                _active_trace = trace
                own_trace = True

            step_start = time.time()
            step = StepTrace(
                step_index=len(trace.steps),
                agent=task_id or func.__name__,
                provider=provider or "unknown",
            )

            try:
                result = func(*args, **kwargs)
                step_ms = (time.time() - step_start) * 1000
                step.latency_ms = round(step_ms, 1)
                step.status = "completed"
                step.causal_chain.append({
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "event": "completed",
                    "classification": "",
                })
                trace.steps.append(step)
                return result

            except Exception as e:
                step_ms = (time.time() - step_start) * 1000
                step.latency_ms = round(step_ms, 1)
                step.status = "failed"
                step.error = str(e)[:200]

                error_class = classify_error(e)
                step.error_class = error_class.value
                step.causal_chain.append({
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "event": f"error: {str(e)[:100]}",
                    "classification": error_class.value,
                })
                trace.steps.append(step)
                raise

            finally:
                if own_trace:
                    trace.end_epoch = time.time()
                    trace.timestamp_end = time.strftime("%Y-%m-%dT%H:%M:%S")
                    _active_trace = None

        return wrapper
    return decorator


# ── Persistence ──

class RunTraceStore:
    """Persists RunTraces as JSON files and aggregates to runs.jsonl."""

    def __init__(self):
        os.makedirs(EXPERIMENTS_DIR, exist_ok=True)
        os.makedirs(TRACES_DIR, exist_ok=True)
        self._runs_file = os.path.join(EXPERIMENTS_DIR, "runs.jsonl")

    def save(self, trace: RunTrace) -> str:
        """Save trace as individual JSON + append to runs.jsonl. Returns trace path."""
        trace = compute_derived_metrics(trace)

        # Individual JSON trace
        trace_path = os.path.join(TRACES_DIR, f"{trace.run_id}.json")
        with open(trace_path, "w") as f:
            json.dump(trace.to_dict(), f, indent=2, default=str)

        # Append summary to runs.jsonl
        summary = {
            "run_id": trace.run_id,
            "session_id": trace.session_id,
            "crew_name": trace.crew_name,
            "mode": trace.mode,
            "timestamp_start": trace.timestamp_start,
            "timestamp_end": trace.timestamp_end,
            "total_latency_ms": trace.total_latency_ms,
            "status": trace.status,
            "deterministic": trace.deterministic,
            "steps_count": len(trace.steps),
            "stability_score": trace.stability_score,
            "provider_fragility_index": trace.provider_fragility_index,
            "retry_pressure": trace.retry_pressure,
            "governance_compliance_rate": trace.governance_compliance_rate,
            "supervisor_score_final": trace.supervisor_score_final,
            "supervisor_decision": trace.supervisor_decision,
            "total_retries": trace.total_retries,
            "total_token_input": trace.total_token_input,
            "total_token_output": trace.total_token_output,
            "output_len": trace.output_len,
            "raw_trace_path": trace_path,
        }
        with open(self._runs_file, "a") as f:
            f.write(json.dumps(summary, default=str) + "\n")

        logger.info(f"Trace saved: {trace_path}")
        return trace_path

    def load_runs(self, n: int = 0) -> list[dict]:
        """Load run summaries from runs.jsonl."""
        if not os.path.exists(self._runs_file):
            return []
        runs = []
        with open(self._runs_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    runs.append(json.loads(line))
        if n > 0:
            return runs[-n:]
        return runs

    def load_trace(self, run_id: str) -> dict | None:
        """Load full trace JSON by run_id."""
        path = os.path.join(TRACES_DIR, f"{run_id}.json")
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return json.load(f)

    def aggregate(self, runs: list[dict] | None = None) -> dict:
        """Compute aggregated statistics across runs."""
        if runs is None:
            runs = self.load_runs()
        if not runs:
            return {"total_runs": 0}

        n = len(runs)

        def _mean(values: list[float]) -> float:
            return sum(values) / len(values) if values else 0.0

        def _stddev(values: list[float]) -> float:
            if len(values) < 2:
                return 0.0
            m = _mean(values)
            variance = sum((x - m) ** 2 for x in values) / (len(values) - 1)
            return math.sqrt(variance)

        stability = [r["stability_score"] for r in runs]
        fragility = [r["provider_fragility_index"] for r in runs]
        retry_p = [r["retry_pressure"] for r in runs]
        gov_rate = [r["governance_compliance_rate"] for r in runs]
        latency = [r["total_latency_ms"] for r in runs]
        sup_scores = [r["supervisor_score_final"] for r in runs if r.get("supervisor_score_final", 0) > 0]
        tok_in = [r.get("total_token_input", 0) for r in runs]
        tok_out = [r.get("total_token_output", 0) for r in runs]

        statuses = {}
        for r in runs:
            s = r.get("status", "unknown")
            statuses[s] = statuses.get(s, 0) + 1

        # Supervisor Strictness Ratio = escalations / total_runs
        escalations = statuses.get("escalated", 0)
        strictness = escalations / n if n > 0 else 0.0

        return {
            "total_runs": n,
            "statuses": statuses,
            "stability_score": {"mean": round(_mean(stability), 4), "stddev": round(_stddev(stability), 4)},
            "provider_fragility_index": {"mean": round(_mean(fragility), 4), "stddev": round(_stddev(fragility), 4)},
            "retry_pressure": {"mean": round(_mean(retry_p), 4), "stddev": round(_stddev(retry_p), 4)},
            "governance_compliance_rate": {"mean": round(_mean(gov_rate), 4), "stddev": round(_stddev(gov_rate), 4)},
            "supervisor_strictness_ratio": round(strictness, 4),
            "supervisor_score": {"mean": round(_mean(sup_scores), 2), "stddev": round(_stddev(sup_scores), 2)} if sup_scores else {"mean": 0, "stddev": 0},
            "latency_ms": {"mean": round(_mean(latency), 1), "stddev": round(_stddev(latency), 1)},
            "tokens": {"input_total": sum(tok_in), "output_total": sum(tok_out)},
        }


# ─────────────────────────────────────────────────────────────────────
# Token Tracker — per-call LLM token flow observability
# ─────────────────────────────────────────────────────────────────────

class TokenTracker:
    """Tracks token usage, latency, and cost across LLM calls.

    Each log_call() records provider, model, token counts, latency, and
    estimated cost. Aggregation methods provide totals, per-provider
    breakdowns, and serialization for audit trails.

    Zero external dependencies — pure Python.

    Usage:
        tracker = TokenTracker()
        tracker.log_call("groq", "llama-3.3-70b", 500, 200, 1200.0, 0.0)
        tracker.log_call("minimax", "m2.1", 300, 150, 800.0, 0.0)
        print(tracker.total_tokens())   # 1150
        print(tracker.calls_by_provider())  # {'groq': 1, 'minimax': 1}
    """

    def __init__(self):
        self.calls = []

    def log_call(self, provider, model, prompt_tokens, completion_tokens,
                 latency_ms, cost_estimate=0.0):
        """Record a single LLM call."""
        self.calls.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": provider,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "latency_ms": latency_ms,
            "cost_estimate": cost_estimate,
        })

    def total_tokens(self):
        """Total tokens across all logged calls."""
        return sum(c["total_tokens"] for c in self.calls)

    def total_cost(self):
        """Total estimated cost in USD."""
        return sum(c["cost_estimate"] for c in self.calls)

    def calls_by_provider(self):
        """Count of calls per provider."""
        from collections import Counter
        return dict(Counter(c["provider"] for c in self.calls))

    def average_latency(self):
        """Average latency per call in milliseconds."""
        if not self.calls:
            return 0
        return sum(c["latency_ms"] for c in self.calls) / len(self.calls)

    def to_dict(self):
        """Serialize tracker state for persistence/audit."""
        return {
            "calls": self.calls,
            "total_tokens": self.total_tokens(),
            "total_cost": self.total_cost(),
            "total_calls": len(self.calls),
            "calls_by_provider": self.calls_by_provider(),
            "average_latency_ms": self.average_latency(),
        }

    def reset(self):
        """Clear all recorded calls."""
        self.calls = []
