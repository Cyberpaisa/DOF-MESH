#!/usr/bin/env python3
"""
DOF-EvolveEngine runner — optimize TRACER weights using historical data.

Usage:
    python3 scripts/run_evolve.py                     # default run
    python3 scripts/run_evolve.py --iterations 60     # more iterations
    python3 scripts/run_evolve.py --budget 2.0        # higher LLM budget
    python3 scripts/run_evolve.py --dry-run           # evaluate baseline only
    python3 scripts/run_evolve.py --show-adopted      # show current adopted weights

Output:
    logs/evolve/runs.jsonl     — full history of evaluated candidates
    logs/evolve/adopted.json   — best weights (auto-loaded by SentinelEngine)
"""

import sys
import os
import argparse
import json
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)

VALIDATIONS_LOG = "logs/sentinel/validations.jsonl"
ADOPTED_FILE = "logs/evolve/adopted.json"


def cmd_run(args):
    from core.evolve_engine import EvolveConfig, EvolveController, build_tracer_evaluator

    print("\n" + "="*60)
    print(" DOF-EvolveEngine — TRACER Weight Optimization")
    print("="*60)

    config = EvolveConfig(
        target="tracer_weights",
        max_iterations=args.iterations,
        budget_usd=args.budget,
        mutation_temperature=args.temperature,
        verbose=True,
    )
    evaluator = build_tracer_evaluator(VALIDATIONS_LOG)
    engine = EvolveController(config, evaluator)

    print(f"\nTarget:         {config.target}")
    print(f"Max iterations: {config.max_iterations}")
    print(f"LLM budget:     ${config.budget_usd:.2f}")
    print(f"Model:          {config.llm_model}")
    print(f"Validations:    {VALIDATIONS_LOG}")
    print()

    result = engine.run()

    print("\n" + "="*60)
    print(f" RESULT: {result.summary}")
    print("="*60)
    print(f"\nBaseline weights (current):")
    from core.evolve_engine import DEFAULT_TRACER_WEIGHTS
    for k, v in DEFAULT_TRACER_WEIGHTS.items():
        print(f"  {k:12s}: {v:.3f}")

    print(f"\nBest weights found (score={result.best_score:.4f}):")
    for k, v in result.best_params.items():
        delta = v - DEFAULT_TRACER_WEIGHTS.get(k, 0)
        arrow = f" ({'↑' if delta > 0 else '↓'}{abs(delta):.3f})" if abs(delta) > 0.001 else ""
        print(f"  {k:12s}: {v:.3f}{arrow}")

    print(f"\nImprovement:    +{result.improvement_pct:.2f}%")
    print(f"Cost:           ${result.total_cost_usd:.4f}")
    print(f"Duration:       {result.run_duration_s:.1f}s")
    print(f"Candidates:     {result.candidates_evaluated}")

    if result.adopted:
        print(f"\n✅ New weights ADOPTED → {ADOPTED_FILE}")
        print("   SentinelEngine will load these automatically on next run.")
    else:
        print(f"\n⏭  Improvement below threshold ({config.min_improvement_pct}%) — keeping current weights.")

    return result


def cmd_dry_run(args):
    from core.evolve_engine import build_tracer_evaluator, DEFAULT_TRACER_WEIGHTS

    print("\n[DRY RUN] Evaluating baseline weights only...\n")
    evaluator = build_tracer_evaluator(VALIDATIONS_LOG)
    score = evaluator(DEFAULT_TRACER_WEIGHTS)
    print(f"Baseline TRACER weights:")
    for k, v in DEFAULT_TRACER_WEIGHTS.items():
        print(f"  {k:12s}: {v:.3f}")
    print(f"\nBaseline score: {score:.4f}")
    print("\nNo changes made.")


def cmd_show_adopted(args):
    from pathlib import Path
    adopted = Path(ADOPTED_FILE)
    if not adopted.exists():
        print("No adopted weights found. Run without --show-adopted to optimize.")
        return

    data = json.loads(adopted.read_text())
    print("\n" + "="*60)
    print(" Currently Adopted TRACER Weights")
    print("="*60)
    print(f"\nAdopted at:   {data.get('adopted_at', 'unknown')}")
    print(f"Score:        {data.get('score', '?'):.4f} (baseline: {data.get('baseline_score', '?'):.4f})")
    print(f"Improvement:  +{data.get('score_delta', 0):.2f}%")
    print(f"Run ID:       {data.get('run_id', '?')}")
    print(f"\nWeights:")
    for k, v in data.get("params", {}).items():
        print(f"  {k:12s}: {v:.4f}")


def main():
    parser = argparse.ArgumentParser(description="DOF-EvolveEngine — TRACER weight optimizer")
    parser.add_argument("--iterations", type=int, default=40, help="Max evolution iterations (default: 40)")
    parser.add_argument("--budget", type=float, default=0.50, help="Max LLM spend in USD (default: 0.50)")
    parser.add_argument("--temperature", type=float, default=0.25, help="Mutation temperature (default: 0.25)")
    parser.add_argument("--dry-run", action="store_true", help="Evaluate baseline only, no optimization")
    parser.add_argument("--show-adopted", action="store_true", help="Show currently adopted weights")

    args = parser.parse_args()

    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    if args.show_adopted:
        cmd_show_adopted(args)
    elif args.dry_run:
        cmd_dry_run(args)
    else:
        cmd_run(args)


if __name__ == "__main__":
    main()
