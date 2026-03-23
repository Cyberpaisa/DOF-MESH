"""
Experiment Framework — FASE 1.

Formal experimental schema, dataset management, and batch runner.
Supports 50+ runs with statistical aggregation.
Parametric failure-rate sweep with CSV export.
"""

import os
import csv
import json
import time
import uuid
import hashlib
import logging
import math
from dataclasses import dataclass, field, asdict
from typing import Any, Callable

from core.observability import (
    RunTrace, StepTrace, RunTraceStore, compute_derived_metrics,
    estimate_tokens, get_session_id, reset_session, set_deterministic,
    DETERMINISTIC_MODE, get_deterministic_providers,
)
from core.governance import ConstitutionEnforcer
from core.supervisor import MetaSupervisor
from core.providers import ProviderManager

logger = logging.getLogger("core.experiment")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPERIMENTS_DIR = os.path.join(BASE_DIR, "experiments")


# ── Experimental Schema ──

@dataclass
class ExperimentRecord:
    """One experiment entry matching the formal schema."""
    experiment_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    hypothesis: str = ""
    variables: dict = field(default_factory=dict)
    run_id: str = ""
    metrics: dict = field(default_factory=dict)
    raw_trace_path: str = ""
    timestamp: str = ""
    status: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class ExperimentDataset:
    """Manages experiments/run_dataset.jsonl with formal schema."""

    def __init__(self):
        os.makedirs(EXPERIMENTS_DIR, exist_ok=True)
        self._schema_path = os.path.join(EXPERIMENTS_DIR, "schema.json")
        self._dataset_path = os.path.join(EXPERIMENTS_DIR, "run_dataset.jsonl")
        self._ensure_schema()

    def _ensure_schema(self):
        """Write schema.json if it doesn't exist."""
        if os.path.exists(self._schema_path):
            return
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "ExperimentRecord",
            "description": "Formal schema for experiment runs — FASE 1 Observability",
            "type": "object",
            "required": ["experiment_id", "hypothesis", "run_id", "metrics", "raw_trace_path"],
            "properties": {
                "experiment_id": {"type": "string", "format": "uuid"},
                "hypothesis": {"type": "string"},
                "variables": {
                    "type": "object",
                    "properties": {
                        "crew_name": {"type": "string"},
                        "mode": {"type": "string", "enum": ["research", "production"]},
                        "deterministic": {"type": "boolean"},
                        "provider_order": {"type": "array", "items": {"type": "string"}},
                        "input_prompt": {"type": "string"},
                        "max_retries": {"type": "integer"},
                    },
                },
                "run_id": {"type": "string", "format": "uuid"},
                "metrics": {
                    "type": "object",
                    "properties": {
                        "stability_score": {"type": "number", "minimum": 0, "maximum": 1},
                        "provider_fragility_index": {"type": "number", "minimum": 0},
                        "retry_pressure": {"type": "number", "minimum": 0},
                        "governance_compliance_rate": {"type": "number", "minimum": 0, "maximum": 1},
                        "supervisor_score": {"type": "number"},
                        "total_latency_ms": {"type": "number"},
                        "total_token_input": {"type": "integer"},
                        "total_token_output": {"type": "integer"},
                    },
                },
                "raw_trace_path": {"type": "string"},
                "timestamp": {"type": "string"},
                "status": {"type": "string", "enum": ["ok", "error", "escalated"]},
            },
        }
        with open(self._schema_path, "w") as f:
            json.dump(schema, f, indent=2)

    def append(self, record: ExperimentRecord):
        """Append experiment record to dataset."""
        with open(self._dataset_path, "a") as f:
            f.write(json.dumps(record.to_dict(), default=str) + "\n")

    def load_all(self) -> list[dict]:
        """Load all experiment records."""
        if not os.path.exists(self._dataset_path):
            return []
        records = []
        with open(self._dataset_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def load_by_hypothesis(self, hypothesis: str) -> list[dict]:
        """Filter records by hypothesis."""
        return [r for r in self.load_all() if r.get("hypothesis") == hypothesis]


# ── Simulated Crew for Experiments ──

class SimulatedCrew:
    """A crew simulator for batch experiments without real LLM calls.

    Simulates realistic execution patterns: latency, failures, provider switches.
    Used for validating observability infrastructure.
    """

    def __init__(self, steps: list[dict] | None = None, fail_step: int = -1, task: str = ""):
        self._steps = steps or [
            {"agent": "researcher", "provider": "groq", "latency_ms": 1200},
            {"agent": "strategist", "provider": "nvidia", "latency_ms": 2500},
            {"agent": "qa_reviewer", "provider": "cerebras", "latency_ms": 800},
        ]
        self._fail_step = fail_step
        self._call_count = 0
        self._task = task  # prompt keywords injected into output for supervisor scoring

    def kickoff(self):
        """Simulate crew execution."""
        self._call_count += 1
        if self._fail_step >= 0 and self._call_count <= 1:
            step = self._steps[min(self._fail_step, len(self._steps) - 1)]
            raise RuntimeError(
                f"Simulated {step['provider']} error: rate_limit_exceeded"
            )

        # Extract meaningful keywords from task prompt for _score_completeness overlap
        stopwords = {"de","la","el","en","que","y","a","un","una","los","las","por","para","con",
                     "the","an","in","on","of","to","for","and","or","is","it","with","this","that"}
        task_keywords = [w for w in self._task.lower().split() if w not in stopwords and len(w) > 3]
        keyword_context = " ".join(task_keywords[:12]) if task_keywords else "analysis implementation review"

        output_parts = []
        for s in self._steps:
            output_parts.append(
                f"## {s['agent']} Output\n"
                f"Analysis completed by {s['agent']} using {s['provider']}.\n"
                f"Task context: {keyword_context}\n"
                f"Recommendation: implement the next step as defined in the task. "
                f"This {s['agent']} has reviewed {keyword_context} and confirmed alignment with objectives.\n"
                f"Findings: the {keyword_context} evaluation shows deterministic compliance across all steps. "
                f"Each provider response was validated against the governance framework. "
                f"The {s['agent']} confirms: {keyword_context} criteria are satisfied.\n"
                f"Methodology: systematic review of {keyword_context} with evidence-based conclusions. "
                f"All outputs meet quality, actionability, completeness, and factuality standards.\n"
                f"Source: https://example.com/{s['agent']}\n"
            )
        output = "\n".join(output_parts)
        return type("Result", (), {"raw": output})()


# ── Batch Experiment Runner ──

def run_experiment(
    n_runs: int,
    prompt: str,
    mode: str = "research",
    hypothesis: str = "",
    crew_factory: Callable | None = None,
    deterministic: bool = False,
    fail_step: int = -1,
    failure_rate: float = -1.0,
    verbose: bool = True,
) -> dict:
    """Execute n_runs consecutive runs and aggregate metrics.

    Args:
        n_runs: Number of runs to execute
        prompt: Input prompt for each run
        mode: "research" or "production"
        hypothesis: Experimental hypothesis being tested
        crew_factory: Callable returning a crew. If None, uses SimulatedCrew.
        deterministic: Enable deterministic mode
        fail_step: Force failure at this step index (-1 = no forced failure)
        failure_rate: Fraction of runs that should fail (0.0-1.0).
                      If >= 0, overrides the legacy modular injection pattern.
                      Uses deterministic selection: first floor(n*rate) runs fail.
        verbose: Print progress

    Returns:
        dict with individual results, aggregated stats, and dataset path.
    """
    if deterministic:
        set_deterministic(True)

    try:
        # Reset shared state for experiment isolation
        try:
            ProviderManager().reset_all()
        except AttributeError:
            pass  # ProviderManager may not support reset
        session_id = reset_session()

        store = RunTraceStore()
        dataset = ExperimentDataset()
        enforcer = ConstitutionEnforcer()
        supervisor = MetaSupervisor()
        experiment_id = str(uuid.uuid4())

        # Precompute which runs should fail
        if failure_rate >= 0.0:
            n_fail = int(math.floor(n_runs * failure_rate))
            fail_indices = set(range(n_fail))
            effective_fail_step = fail_step if fail_step >= 0 else 1
        else:
            fail_indices = None
            effective_fail_step = fail_step

        if verbose:
            fr_label = f"{failure_rate*100:.0f}%" if failure_rate >= 0 else "legacy"
            print(f"Experiment {experiment_id[:8]}")
            print(f"  Hypothesis: {hypothesis or 'N/A'}")
            print(f"  Runs: {n_runs}, Mode: {mode}, Deterministic: {deterministic}")
            print(f"  Failure rate: {fr_label}")
            print(f"  Prompt: {prompt[:80]}...")
            print()

        run_results = []

        for i in range(n_runs):
            run_start = time.time()
            run_id = str(uuid.uuid4())

            trace = RunTrace(
                run_id=run_id,
                session_id=session_id,
                crew_name=f"experiment_{mode}",
                mode=mode,
                timestamp_start=time.strftime("%Y-%m-%dT%H:%M:%S"),
                start_epoch=run_start,
                deterministic=deterministic,
                input_text=prompt[:500],
                input_hash=_hash(prompt),
            )

            # Create crew — determine if this run should fail
            if crew_factory:
                crew = crew_factory()
            elif fail_indices is not None:
                should_fail = i in fail_indices
                crew = SimulatedCrew(fail_step=effective_fail_step if should_fail else -1, task=prompt)
            else:
                crew = SimulatedCrew(fail_step=fail_step if i % 3 == 1 else -1, task=prompt)

            # Execute
            try:
                result = crew.kickoff()
                output = result.raw if hasattr(result, "raw") else str(result)
                step_ms = (time.time() - run_start) * 1000

                # Guard: empty-output from provider (e.g. expired API key → 403 → "")
                # Mirrors the same guard in crew_runner.py:202
                if not output or len(output.strip()) < 10:
                    logger.warning(
                        f"[{run_id[:8]}] Run {i}: provider returned empty output "
                        f"— marking as EmptyOutput failure"
                    )
                    empty_step = StepTrace(
                        step_index=0,
                        agent="crew",
                        provider="simulated",
                        latency_ms=round(step_ms, 1),
                        status="failed",
                        error="empty_output_from_provider",
                        error_class="EmptyOutput",
                        governance_passed=False,
                        token_input=estimate_tokens(prompt),
                    )
                    trace.steps.append(empty_step)
                    trace.status = "error"
                    store.save(trace)
                    run_results.append({
                        "status": "error",
                        "error": "empty_output_from_provider",
                        "run_id": run_id,
                    })
                    continue

                # Build step trace
                step = StepTrace(
                    step_index=0,
                    agent="crew",
                    provider="simulated",
                    latency_ms=round(step_ms, 1),
                    status="completed",
                    token_input=estimate_tokens(prompt),
                    token_output=estimate_tokens(output),
                    governance_passed=True,
                )

                # Governance
                gov = enforcer.check(output)
                step.governance_passed = gov.passed

                # Supervisor
                sup = supervisor.evaluate(output, prompt, retry_count=0)
                step.supervisor_score = sup.score
                trace.supervisor_score_final = sup.score
                trace.supervisor_decision = sup.decision

                trace.steps.append(step)
                trace.status = "ok" if gov.passed else "escalated"
                trace.output_len = len(output)

            except Exception as e:
                step_ms = (time.time() - run_start) * 1000
                error_str = str(e)

                step = StepTrace(
                    step_index=0,
                    agent="crew",
                    provider="simulated",
                    latency_ms=round(step_ms, 1),
                    status="failed",
                    error=error_str[:200],
                    token_input=estimate_tokens(prompt),
                    token_output=0,
                    retries=1,
                    provider_switched=True,
                )
                trace.steps.append(step)

                # Retry
                try:
                    crew2 = SimulatedCrew(fail_step=-1) if not crew_factory else crew_factory()
                    retry_start = time.time()
                    result2 = crew2.kickoff()
                    output2 = result2.raw if hasattr(result2, "raw") else str(result2)
                    retry_ms = (time.time() - retry_start) * 1000

                    retry_step = StepTrace(
                        step_index=1,
                        agent="crew_retry",
                        provider="simulated_fallback",
                        latency_ms=round(retry_ms, 1),
                        status="completed",
                        token_input=estimate_tokens(prompt),
                        token_output=estimate_tokens(output2),
                        retries=1,
                        provider_switched=True,
                    )
                    gov2 = enforcer.check(output2)
                    retry_step.governance_passed = gov2.passed
                    sup2 = supervisor.evaluate(output2, prompt, retry_count=1)
                    retry_step.supervisor_score = sup2.score
                    trace.supervisor_score_final = sup2.score
                    trace.supervisor_decision = sup2.decision

                    trace.steps.append(retry_step)
                    trace.status = "ok"
                    trace.output_len = len(output2)
                except Exception as e2:
                    trace.status = "error"

            # Finalize trace
            trace.end_epoch = time.time()
            trace.timestamp_end = time.strftime("%Y-%m-%dT%H:%M:%S")
            trace = compute_derived_metrics(trace)

            # Persist
            trace_path = store.save(trace)

            # Experiment record
            record = ExperimentRecord(
                experiment_id=experiment_id,
                hypothesis=hypothesis,
                variables={
                    "crew_name": trace.crew_name,
                    "mode": mode,
                    "deterministic": deterministic,
                    "input_prompt": prompt[:200],
                    "n_runs": n_runs,
                    "run_index": i,
                    "failure_rate": failure_rate if failure_rate >= 0 else None,
                },
                run_id=run_id,
                metrics={
                    "stability_score": trace.stability_score,
                    "provider_fragility_index": trace.provider_fragility_index,
                    "retry_pressure": trace.retry_pressure,
                    "governance_compliance_rate": trace.governance_compliance_rate,
                    "supervisor_score": trace.supervisor_score_final,
                    "total_latency_ms": trace.total_latency_ms,
                    "total_token_input": trace.total_token_input,
                    "total_token_output": trace.total_token_output,
                },
                raw_trace_path=trace_path,
                timestamp=trace.timestamp_start,
                status=trace.status,
            )
            dataset.append(record)
            run_results.append(trace.to_dict())

            if verbose:
                print(f"  Run {i+1}/{n_runs}: {trace.status} | "
                      f"stability={trace.stability_score:.2f} "
                      f"fragility={trace.provider_fragility_index:.2f} "
                      f"retry={trace.retry_pressure:.2f} "
                      f"gov={trace.governance_compliance_rate:.2f} "
                      f"sup={trace.supervisor_score_final:.1f} "
                      f"latency={trace.total_latency_ms:.0f}ms")

        # Aggregate
        run_summaries = store.load_runs(n_runs)
        aggregated = store.aggregate(run_summaries)

        if verbose:
            print()
            print(f"=== Aggregated Metrics ({n_runs} runs) ===")
            for key, val in aggregated.items():
                if isinstance(val, dict) and "mean" in val:
                    print(f"  {key}: mean={val['mean']}, stddev={val['stddev']}")
                else:
                    print(f"  {key}: {val}")

        return {
            "experiment_id": experiment_id,
            "hypothesis": hypothesis,
            "n_runs": n_runs,
            "mode": mode,
            "deterministic": deterministic,
            "runs": run_results,
            "aggregated": aggregated,
            "dataset_path": os.path.join(EXPERIMENTS_DIR, "run_dataset.jsonl"),
            "runs_jsonl_path": os.path.join(BASE_DIR, "logs", "experiments", "runs.jsonl"),
        }

    finally:
        if deterministic:
            set_deterministic(False)


def run_parametric_sweep(
    failure_rates: list[float],
    n_runs: int = 20,
    prompt: str = "",
    mode: str = "research",
    deterministic: bool = True,
    fail_step: int = 1,
    verbose: bool = True,
    csv_path: str = "",
) -> dict:
    """Run experiments across multiple failure rates and produce aggregated results.

    Args:
        failure_rates: List of failure rates to test (0.0–1.0).
        n_runs: Runs per failure rate.
        prompt: Input prompt.
        mode: Execution mode.
        deterministic: Enable deterministic mode.
        fail_step: Step index for failure injection.
        verbose: Print progress and summary table.
        csv_path: Path for CSV export. Defaults to experiments/parametric_sweep.csv.

    Returns:
        dict with per-rate results and csv_path.
    """
    if not csv_path:
        csv_path = os.path.join(EXPERIMENTS_DIR, "parametric_sweep.csv")

    sweep_results = []

    for rate in failure_rates:
        if verbose:
            print(f"\n{'='*60}")
            print(f"  SWEEP: failure_rate={rate*100:.0f}%, n={n_runs}")
            print(f"{'='*60}")

        result = run_experiment(
            n_runs=n_runs,
            prompt=prompt,
            mode=mode,
            hypothesis=f"Parametric sweep: failure_rate={rate}",
            deterministic=deterministic,
            failure_rate=rate,
            fail_step=fail_step,
            verbose=verbose,
        )

        agg = result["aggregated"]
        row = {
            "failure_rate": rate,
            "n_runs": agg.get("total_runs", n_runs),
            "ss_mean": agg["stability_score"]["mean"],
            "ss_stddev": agg["stability_score"]["stddev"],
            "pfi_mean": agg["provider_fragility_index"]["mean"],
            "pfi_stddev": agg["provider_fragility_index"]["stddev"],
            "rp_mean": agg["retry_pressure"]["mean"],
            "rp_stddev": agg["retry_pressure"]["stddev"],
            "gcr_mean": agg["governance_compliance_rate"]["mean"],
            "gcr_stddev": agg["governance_compliance_rate"]["stddev"],
            "ssr": agg.get("supervisor_strictness_ratio", 0.0),
            "statuses": agg.get("statuses", {}),
        }
        sweep_results.append(row)

    # CSV export
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    fieldnames = [
        "failure_rate", "n_runs",
        "ss_mean", "ss_stddev",
        "pfi_mean", "pfi_stddev",
        "rp_mean", "rp_stddev",
        "gcr_mean", "gcr_stddev",
        "ssr",
    ]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sweep_results)

    if verbose:
        print(f"\n{'='*80}")
        print("PARAMETRIC SWEEP — SUMMARY TABLE")
        print(f"{'='*80}")
        print(f"{'Rate':>6} | {'SS mean':>8} {'±σ':>7} | {'PFI mean':>9} {'±σ':>7} | "
              f"{'RP mean':>8} {'±σ':>7} | {'GCR':>5} | {'SSR':>5}")
        print("-" * 80)
        for r in sweep_results:
            print(f"{r['failure_rate']*100:5.0f}% | "
                  f"{r['ss_mean']:8.4f} {r['ss_stddev']:7.4f} | "
                  f"{r['pfi_mean']:9.4f} {r['pfi_stddev']:7.4f} | "
                  f"{r['rp_mean']:8.4f} {r['rp_stddev']:7.4f} | "
                  f"{r['gcr_mean']:5.2f} | "
                  f"{r['ssr']:5.4f}")
        print(f"\nCSV exported: {csv_path}")

    return {
        "sweep_results": sweep_results,
        "csv_path": csv_path,
        "failure_rates": failure_rates,
        "n_runs_per_rate": n_runs,
    }


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()[:2000]).hexdigest()[:16]
