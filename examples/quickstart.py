# No API keys required. Run: python examples/quickstart.py
"""
DOF SDK — Quick Start Example

Demonstrates how to use dof as a pip-installable package.
Run with:
    pip install -e .
    python examples/quickstart.py
"""

import dof
from dof import register, Metrics, Constitution

# ── 1. Initialize governance from constitution YAML ──────────────────────────
print(f"DOF SDK v{dof.__version__}")
print()

constitution = register(constitution="dof.constitution.yml")
print("Governance loaded:")
print(f"  Project:     {constitution['metadata']['project']}")
print(f"  Hard rules:  {len(constitution['rules']['hard'])}")
print(f"  Soft rules:  {len(constitution['rules']['soft'])}")
print()

# ── 2. Run formal Z3 proofs ───────────────────────────────────────────────────
print("Running Z3 formal proofs…")
proofs = dof.verify()
for proof in proofs:
    status = proof.result
    theorem = proof.theorem_name
    marker = "✓" if status == "VERIFIED" else "✗"
    print(f"  {marker}  {theorem}: {status}")
print()

# ── 3. Access governance rules ────────────────────────────────────────────────
enforcer = Constitution()
sample = "The research findings indicate clear evidence of deterministic behavior across all test conditions."
allowed, message = enforcer.enforce(sample)
print(f"Governance check on sample output:")
print(f"  Allowed:     {allowed}")
print(f"  Message:     {message}")
print()

# ── 4. Access runtime metrics ─────────────────────────────────────────────────
metrics_observer = Metrics()

# Simulate a few mock steps for demonstration
from dof import RunTrace, StepTrace, ErrorClass
import time

trace = RunTrace(run_id="quickstart-demo", crew_name="research", mode="demo",
                start_epoch=time.time())
trace.steps = [
    StepTrace(step_index=0, agent="researcher", provider="groq",
              status="success", latency_ms=312.0),
    StepTrace(step_index=1, agent="writer", provider="groq",
              status="success", latency_ms=289.0),
    StepTrace(step_index=2, agent="reviewer", provider="cerebras",
              status="failure", latency_ms=0.0, error="Rate limit exceeded",
              error_class=ErrorClass.INFRA_FAILURE),
    StepTrace(step_index=3, agent="reviewer", provider="groq",
              status="success", latency_ms=401.0),
]
trace.end_epoch = time.time()

from dof import compute_derived_metrics
metrics = compute_derived_metrics(trace)

print("Derived metrics for demo run:")
print(f"  SS  (Stability Score):       {metrics.stability_score:.3f}   # target ≥ 0.70")
print(f"  PFI (Provider Fragility):    {metrics.provider_fragility_index:.3f}   # target ≤ 0.30")
print(f"  RP  (Retry Pressure):        {metrics.retry_pressure:.3f}   # target ≥ 0.50")
print(f"  GCR (Governance Compliance): {metrics.governance_compliance_rate:.3f}   # invariant = 1.0")
print()

# ── 5. Error classification ───────────────────────────────────────────────────
from dof import classify_error

class FakeRateLimit(Exception):
    pass

err_class = classify_error(FakeRateLimit("429 Too Many Requests — rate limit"), context={})
print(f"Error classification for rate-limit error: {err_class}")
print()

print("Quickstart complete.")
