"""
Runtime Observer — Production metrics from real execution data.

Computes the 5 formal metrics (SS, PFI, RP, GCR, SSR) from actual
crew executions logged in logs/execution_log.jsonl.

Metrics (all ∈ [0,1]):
  SS  — Stability Score: fraction of runs completing without terminal failure
  PFI — Provider Fragility Index: mean provider failure count per run
  RP  — Retry Pressure: mean retry count per run
  GCR — Governance Compliance Rate: fraction of completed runs passing governance
  SSR — Supervisor Strictness Ratio: fraction of completed runs rejected by supervisor

Usage:
    python -m core.runtime_observer              # all metrics, last 100 runs
    python -m core.runtime_observer --window 50  # last 50 runs
"""

import json
import math
import os
import logging
from dataclasses import dataclass

logger = logging.getLogger("core.runtime_observer")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(BASE_DIR, "logs", "execution_log.jsonl")


@dataclass
class MetricResult:
    """A single metric with mean and Bessel-corrected std."""
    name: str
    mean: float
    std: float
    n: int

    def __repr__(self) -> str:
        return f"{self.name}: {self.mean:.4f} ± {self.std:.4f} (n={self.n})"


def _bessel_std(values: list[float]) -> float:
    """Bessel-corrected sample standard deviation (n-1 denominator)."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    return math.sqrt(variance)


def _mean(values: list[float]) -> float:
    """Arithmetic mean."""
    if not values:
        return 0.0
    return sum(values) / len(values)


class RuntimeObserver:
    """Compute formal metrics from production execution logs."""

    def __init__(self, log_path: str = LOG_PATH):
        self.log_path = log_path

    def load_runs(self, window: int = 100) -> list[dict]:
        """Load last N runs from execution_log.jsonl."""
        if not os.path.exists(self.log_path):
            logger.warning(f"Log file not found: {self.log_path}")
            return []

        runs = []
        with open(self.log_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    runs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        # Return last N runs
        return runs[-window:]

    def compute_ss(self, runs: list[dict]) -> tuple[float, float]:
        """Stability Score: fraction of runs completing without terminal failure.

        A run is "stable" if status is "success" or "escalated" (completed but
        low quality). Only "error" status counts as terminal failure.
        """
        if not runs:
            return 0.0, 0.0
        values = [1.0 if r.get("status") in ("success", "escalated") else 0.0 for r in runs]
        return _mean(values), _bessel_std(values)

    def compute_pfi(self, runs: list[dict]) -> tuple[float, float]:
        """Provider Fragility Index: mean provider failure indicator per run.

        A run exhibits provider fragility if it has retries > 0 (indicating
        at least one provider failure) or if the error contains rate limit
        or authentication errors.
        """
        if not runs:
            return 0.0, 0.0

        values = []
        for r in runs:
            retries = r.get("retries", 0)
            error = r.get("error") or ""
            error_lower = error.lower()

            # Count provider failure signals
            failure_count = 0
            if retries > 0:
                failure_count = retries
            elif r.get("status") == "error":
                # Detect provider-specific failures from error text
                provider_errors = ["ratelimit", "rate_limit", "exhausted",
                                   "authenticationerror", "quota", "resource_exhausted"]
                if any(pe in error_lower for pe in provider_errors):
                    failure_count = 1

            # Normalize: 0 = no failures, 1 = max (capped at max_retries=3)
            values.append(min(failure_count / 3.0, 1.0))

        return _mean(values), _bessel_std(values)

    def compute_rp(self, runs: list[dict]) -> tuple[float, float]:
        """Retry Pressure: mean retry count per run, normalized.

        Uses the 'retries' field from crew_runner. For older runs without
        this field, infers from 'attempts' or error patterns.
        """
        if not runs:
            return 0.0, 0.0

        values = []
        for r in runs:
            retries = r.get("retries", 0)
            if retries == 0:
                # Fallback: check 'attempts' field (telegram entries)
                attempts = r.get("attempts", 1)
                retries = max(0, attempts - 1)
            # Normalize over max_retries (3)
            values.append(min(retries / 3.0, 1.0))

        return _mean(values), _bessel_std(values)

    def compute_gcr(self, runs: list[dict]) -> tuple[float, float]:
        """Governance Compliance Rate: fraction of completed runs passing governance.

        Only considers runs that completed (have governance data). Runs that
        crashed before reaching governance are excluded.
        """
        if not runs:
            return 0.0, 0.0

        values = []
        for r in runs:
            gov = r.get("governance_passed")
            if gov is not None:
                values.append(1.0 if gov else 0.0)
            elif r.get("status") in ("success", "escalated"):
                # Pre-supervisor runs that succeeded: assume governance passed
                # (governance was not tracked in early versions)
                values.append(1.0)

        if not values:
            return 0.0, 0.0
        return _mean(values), _bessel_std(values)

    def compute_ssr(self, runs: list[dict]) -> tuple[float, float]:
        """Supervisor Strictness Ratio: fraction of completed runs rejected.

        A run is "rejected" if the supervisor decision is ESCALATE or RETRY
        on the final attempt. Only considers runs with supervisor data.
        """
        if not runs:
            return 0.0, 0.0

        values = []
        for r in runs:
            decision = r.get("supervisor_decision")
            if decision is not None:
                # ESCALATE = rejected, RETRY on final attempt = rejected
                values.append(1.0 if decision in ("ESCALATE",) else 0.0)
            elif r.get("status") == "success":
                # Pre-supervisor runs: accepted by definition
                values.append(0.0)

        if not values:
            return 0.0, 0.0
        return _mean(values), _bessel_std(values)

    def compute_all(self, window: int = 100) -> dict:
        """Compute all 5 metrics from the last N runs.

        Returns dict with metric names as keys, each containing:
            mean, std, n, domain
        """
        runs = self.load_runs(window)
        n = len(runs)

        if n == 0:
            return {"error": "No runs found", "n": 0}

        ss_m, ss_s = self.compute_ss(runs)
        pfi_m, pfi_s = self.compute_pfi(runs)
        rp_m, rp_s = self.compute_rp(runs)
        gcr_m, gcr_s = self.compute_gcr(runs)
        ssr_m, ssr_s = self.compute_ssr(runs)

        return {
            "n": n,
            "window": window,
            "SS": {"mean": round(ss_m, 4), "std": round(ss_s, 4), "domain": "[0,1]"},
            "PFI": {"mean": round(pfi_m, 4), "std": round(pfi_s, 4), "domain": "[0,1]"},
            "RP": {"mean": round(rp_m, 4), "std": round(rp_s, 4), "domain": "[0,1]"},
            "GCR": {"mean": round(gcr_m, 4), "std": round(gcr_s, 4), "domain": "[0,1]"},
            "SSR": {"mean": round(ssr_m, 4), "std": round(ssr_s, 4), "domain": "[0,1]"},
        }

    def detect_anomalies(self, window: int = 100) -> list[str]:
        """Flag metrics that deviate >2 std from expected baseline.

        Baselines (from parametric sweep at f=0):
            SS=1.0, PFI=0.0, RP=0.0, GCR=1.0, SSR=0.0
        """
        runs = self.load_runs(window)
        if len(runs) < 2:
            return ["Insufficient data for anomaly detection (n < 2)"]

        anomalies = []

        # SS: baseline = 1.0, anomaly if mean drops significantly
        ss_m, ss_s = self.compute_ss(runs)
        if ss_m < 1.0 - 2 * max(ss_s, 0.05):
            anomalies.append(f"SS={ss_m:.3f} is >2σ below baseline (expected ~1.0, σ={ss_s:.3f})")

        # PFI: baseline = 0.0, anomaly if elevated
        pfi_m, pfi_s = self.compute_pfi(runs)
        if pfi_m > 0.0 + 2 * max(pfi_s, 0.05):
            anomalies.append(f"PFI={pfi_m:.3f} is >2σ above baseline (expected ~0.0, σ={pfi_s:.3f})")

        # RP: baseline = 0.0, anomaly if elevated
        rp_m, rp_s = self.compute_rp(runs)
        if rp_m > 0.0 + 2 * max(rp_s, 0.05):
            anomalies.append(f"RP={rp_m:.3f} is >2σ above baseline (expected ~0.0, σ={rp_s:.3f})")

        # GCR: baseline = 1.0, anomaly if drops
        gcr_m, gcr_s = self.compute_gcr(runs)
        if gcr_m < 1.0 - 2 * max(gcr_s, 0.05):
            anomalies.append(f"GCR={gcr_m:.3f} is >2σ below baseline (expected ~1.0, σ={gcr_s:.3f})")

        # SSR: baseline = 0.0, anomaly if elevated
        ssr_m, ssr_s = self.compute_ssr(runs)
        if ssr_m > 0.0 + 2 * max(ssr_s, 0.05):
            anomalies.append(f"SSR={ssr_m:.3f} is >2σ above baseline (expected ~0.0, σ={ssr_s:.3f})")

        return anomalies if anomalies else ["No anomalies detected"]


# ═══════════════════════════════════════════════════════
# CLI ENTRY POINT: python -m core.runtime_observer
# ═══════════════════════════════════════════════════════

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Runtime Observer — Production metrics from real execution data"
    )
    parser.add_argument("--window", type=int, default=100,
                        help="Number of recent runs to analyze (default: 100)")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON instead of table")
    args = parser.parse_args()

    observer = RuntimeObserver()
    metrics = observer.compute_all(args.window)

    if args.json:
        print(json.dumps(metrics, indent=2))
        return

    n = metrics.get("n", 0)
    if n == 0:
        print("No execution data found.")
        return

    print(f"\n{'='*60}")
    print(f"  Runtime Observer — Production Metrics")
    print(f"  Runs analyzed: {n} (window: {args.window})")
    print(f"{'='*60}\n")
    print(f"  {'Metric':<8} {'Mean':>8} {'± Std':>10}  {'Domain':<8}")
    print(f"  {'─'*6:<8} {'─'*6:>8} {'─'*8:>10}  {'─'*6:<8}")

    for key in ("SS", "PFI", "RP", "GCR", "SSR"):
        m = metrics[key]
        std_str = f"± {m['std']:.4f}"
        print(f"  {key:<8} {m['mean']:>8.4f} {std_str:>10}  {m['domain']:<8}")

    # Anomaly detection
    anomalies = observer.detect_anomalies(args.window)
    print(f"\n  Anomaly Detection:")
    for a in anomalies:
        prefix = "  ⚠ " if "anomal" not in a.lower() and "no " not in a.lower()[:3] else "  ✓ "
        if a.startswith("No ") or a.startswith("Insufficient"):
            prefix = "  ✓ "
        print(f"{prefix}{a}")

    print()


if __name__ == "__main__":
    main()
