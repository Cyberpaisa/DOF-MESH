#!/usr/bin/env python3
"""
DOF AutoResearch — Self-optimization loop inspired by Karpathy's autoresearch.

Autonomously optimizes DOF configs by:
1. Reading current config (supervisor weights, retry count, governance thresholds)
2. Making ONE modification
3. Running experiment with formal metrics
4. If dof_score improves → KEEP (commit to autoresearch branch)
5. If not → DISCARD (revert)
6. Repeat forever

Usage:
    python3 scripts/dof_autoresearch.py                  # Run forever
    python3 scripts/dof_autoresearch.py --max-cycles 5   # Run 5 cycles
    python3 scripts/dof_autoresearch.py --dry-run        # Show what would change
"""

import os
import sys
import json
import time
import random
import subprocess
import logging
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.observability import set_deterministic, RunTrace, compute_derived_metrics, reset_session
from core.governance import ConstitutionEnforcer
from core.supervisor import MetaSupervisor
from core.experiment import run_experiment

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("dof.autoresearch")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_FILE = os.path.join(BASE_DIR, "logs", "autoresearch", "results.tsv")
CONFIG_FILE = os.path.join(BASE_DIR, "logs", "autoresearch", "config_history.jsonl")

# Tunable parameters and their ranges
TUNABLE_PARAMS = {
    "supervisor_weight_quality": {"min": 0.20, "max": 0.60, "step": 0.05, "default": 0.40},
    "supervisor_weight_actionability": {"min": 0.10, "max": 0.40, "step": 0.05, "default": 0.25},
    "supervisor_weight_completeness": {"min": 0.10, "max": 0.35, "step": 0.05, "default": 0.20},
    "supervisor_weight_factuality": {"min": 0.05, "max": 0.25, "step": 0.05, "default": 0.15},
    "max_retries": {"min": 1, "max": 5, "step": 1, "default": 3},
    "supervisor_accept_threshold": {"min": 5.0, "max": 9.0, "step": 0.5, "default": 7.0},
    "supervisor_retry_threshold": {"min": 3.0, "max": 7.0, "step": 0.5, "default": 5.0},
}


def compute_dof_score(metrics: dict) -> float:
    """Compute composite DOF score from experiment metrics.

    Formula: 0.3*SS + 0.25*(1-PFI) + 0.2*RP_inv + 0.15*GCR + 0.1*SSR
    Returns score in [0, 1]. Higher = better.
    """
    ss = metrics.get("stability_score", {}).get("mean", 0.0)
    pfi = metrics.get("provider_fragility_index", {}).get("mean", 0.0)
    rp = metrics.get("retry_pressure", {}).get("mean", 0.0)
    gcr = metrics.get("governance_compliance_rate", {}).get("mean", 0.0)
    sup = metrics.get("supervisor_score", {}).get("mean", 0.0) / 10.0  # Normalize to 0-1

    score = (
        0.30 * ss +
        0.25 * max(0, 1.0 - pfi) +
        0.20 * max(0, 1.0 - rp) +
        0.15 * gcr +
        0.10 * sup
    )
    return round(score, 6)


def run_baseline(n_runs: int = 10) -> float:
    """Run baseline experiment and return dof_score."""
    logger.info(f"Running baseline ({n_runs} runs)...")
    set_deterministic(True)
    result = run_experiment(
        n_runs=n_runs,
        prompt="Baseline DOF autoresearch evaluation",
        mode="research",
        hypothesis="baseline",
        deterministic=True,
    )
    score = compute_dof_score(result.get("aggregated", {}))
    logger.info(f"Baseline dof_score: {score:.6f}")
    return score


def propose_modification(current_config: dict) -> tuple[str, float, float]:
    """Propose ONE random modification to a tunable parameter.

    Returns: (param_name, old_value, new_value)
    """
    param = random.choice(list(TUNABLE_PARAMS.keys()))
    spec = TUNABLE_PARAMS[param]
    old_val = current_config.get(param, spec["default"])

    # Random direction: up or down by one step
    direction = random.choice([-1, 1])
    if isinstance(spec["step"], int):
        new_val = int(old_val + direction * spec["step"])
    else:
        new_val = round(old_val + direction * spec["step"], 4)

    # Clamp to range
    new_val = max(spec["min"], min(spec["max"], new_val))

    # If clamped to same value, try other direction
    if new_val == old_val:
        new_val = round(old_val - direction * spec["step"], 4)
        new_val = max(spec["min"], min(spec["max"], new_val))

    return param, old_val, new_val


def apply_modification(param: str, value: float):
    """Apply parameter modification to the running config.

    Writes to a JSON config file that core modules can read.
    """
    config_path = os.path.join(BASE_DIR, "config", "autoresearch_overrides.json")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    overrides = {}
    if os.path.exists(config_path):
        with open(config_path) as f:
            overrides = json.load(f)

    overrides[param] = value
    with open(config_path, "w") as f:
        json.dump(overrides, f, indent=2)


def revert_modification(param: str, old_value: float):
    """Revert a parameter to its previous value."""
    apply_modification(param, old_value)


def log_result(cycle: int, param: str, old_val: float, new_val: float,
               score: float, baseline: float, status: str):
    """Log experiment result to TSV."""
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)

    # Write header if new file
    if not os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "w") as f:
            f.write("cycle\tparam\told_val\tnew_val\tscore\tbaseline\tdelta\tstatus\ttimestamp\n")

    delta = round(score - baseline, 6)
    ts = datetime.now(timezone.utc).isoformat()
    with open(RESULTS_FILE, "a") as f:
        f.write(f"{cycle}\t{param}\t{old_val}\t{new_val}\t{score:.6f}\t{baseline:.6f}\t{delta:+.6f}\t{status}\t{ts}\n")


def log_config(cycle: int, config: dict, score: float, status: str):
    """Log config state to JSONL."""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    entry = {
        "cycle": cycle,
        "config": config,
        "dof_score": score,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(CONFIG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def run_loop(max_cycles: int = 0, n_runs: int = 5, dry_run: bool = False):
    """Main autoresearch loop.

    Args:
        max_cycles: 0 = run forever
        n_runs: experiments per evaluation
        dry_run: show what would change without executing
    """
    logger.info("=" * 60)
    logger.info("DOF AutoResearch Loop — Starting")
    logger.info(f"Max cycles: {'infinite' if max_cycles == 0 else max_cycles}")
    logger.info(f"Runs per eval: {n_runs}")
    logger.info("=" * 60)

    # Current config state
    current_config = {k: v["default"] for k, v in TUNABLE_PARAMS.items()}

    # Load existing overrides
    overrides_path = os.path.join(BASE_DIR, "config", "autoresearch_overrides.json")
    if os.path.exists(overrides_path):
        with open(overrides_path) as f:
            current_config.update(json.load(f))

    # Get baseline score
    baseline_score = run_baseline(n_runs)
    best_score = baseline_score
    kept = 0
    discarded = 0

    cycle = 0
    while True:
        cycle += 1
        if max_cycles > 0 and cycle > max_cycles:
            break

        logger.info(f"\n--- Cycle {cycle} (best: {best_score:.6f}) ---")

        # Propose modification
        param, old_val, new_val = propose_modification(current_config)
        logger.info(f"Proposal: {param} = {old_val} → {new_val}")

        if dry_run:
            logger.info(f"[DRY RUN] Would modify {param}: {old_val} → {new_val}")
            continue

        # Apply modification
        apply_modification(param, new_val)
        current_config[param] = new_val

        # Run experiment
        try:
            set_deterministic(True)
            result = run_experiment(
                n_runs=n_runs,
                prompt=f"AutoResearch cycle {cycle}: {param}={new_val}",
                mode="research",
                hypothesis=f"autoresearch_c{cycle}_{param}",
                deterministic=True,
            )
            new_score = compute_dof_score(result.get("aggregated", {}))
        except Exception as e:
            logger.error(f"Experiment failed: {e}")
            revert_modification(param, old_val)
            current_config[param] = old_val
            log_result(cycle, param, old_val, new_val, 0.0, best_score, "crash")
            continue

        # Decision: KEEP or DISCARD
        if new_score > best_score:
            status = "KEEP"
            kept += 1
            logger.info(f"  KEEP: {new_score:.6f} > {best_score:.6f} (+{new_score - best_score:.6f})")
            best_score = new_score
        else:
            status = "DISCARD"
            discarded += 1
            logger.info(f"  DISCARD: {new_score:.6f} <= {best_score:.6f}")
            revert_modification(param, old_val)
            current_config[param] = old_val

        log_result(cycle, param, old_val, new_val, new_score, best_score, status)
        log_config(cycle, current_config, new_score if status == "KEEP" else best_score, status)

        # Brief pause between cycles
        time.sleep(1)

    # Summary
    total = kept + discarded
    logger.info(f"\n{'=' * 60}")
    logger.info(f"AutoResearch Complete")
    pct = (kept/total*100) if total > 0 else 0.0
    logger.info(f"Cycles: {total} | Kept: {kept} ({pct:.1f}%) | Discarded: {discarded}")
    logger.info(f"Baseline: {baseline_score:.6f} → Best: {best_score:.6f} (Δ{best_score - baseline_score:+.6f})")
    logger.info(f"Results: {RESULTS_FILE}")
    logger.info(f"{'=' * 60}")

    return {
        "cycles": total,
        "kept": kept,
        "discarded": discarded,
        "baseline_score": baseline_score,
        "best_score": best_score,
        "improvement": best_score - baseline_score,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="DOF AutoResearch Loop")
    parser.add_argument("--max-cycles", type=int, default=0, help="Max cycles (0=infinite)")
    parser.add_argument("--n-runs", type=int, default=5, help="Experiment runs per cycle")
    parser.add_argument("--dry-run", action="store_true", help="Show proposals without executing")
    args = parser.parse_args()

    run_loop(max_cycles=args.max_cycles, n_runs=args.n_runs, dry_run=args.dry_run)
