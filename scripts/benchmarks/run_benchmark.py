#!/usr/bin/env python3
"""
DOF Benchmark Runner — Automated adversarial testing with FDR/FPR metrics.

Generates 400 test cases (100 per category) and benchmarks DOF components:
  - DataOracle (hallucination detection + consistency)
  - ASTVerifier (code safety)
  - ConstitutionEnforcer (governance compliance)

Usage:
    python3 scripts/run_benchmark.py
"""

import json
import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.test_generator import TestGenerator, BenchmarkRunner

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    print("=" * 60)
    print("DOF Benchmark Runner")
    print("=" * 60)
    print()

    # Generate dataset
    print("[1/3] Generating test dataset (400 tests)...")
    gen = TestGenerator(seed=42)
    dataset = gen.generate_full_dataset(n_per_category=100)
    print(f"  Dataset saved: {dataset['path']}")
    print(f"  Total tests: {dataset['total_tests']}")
    print()

    # Run benchmarks
    print("[2/3] Running benchmarks...")
    start = time.time()
    runner = BenchmarkRunner(dataset)
    results = runner.run_full_benchmark()
    elapsed = time.time() - start
    print(f"  Completed in {elapsed:.2f}s")
    print()

    # Print results table
    print("[3/3] Results")
    print()
    print(f"{'Category':<20} {'FDR':>8} {'FPR':>8} {'Prec':>8} {'Recall':>8} {'F1':>8} {'TP':>5} {'TN':>5} {'FP':>5} {'FN':>5} {'Lat(ms)':>8}")
    print("-" * 100)
    for cat in ["hallucination", "code_safety", "governance", "consistency"]:
        r = results[cat]
        print(f"{cat:<20} {r['fdr']:>7.1%} {r['fpr']:>7.1%} {r['precision']:>7.1%} {r['recall']:>7.1%} {r['f1']:>7.1%} {r['true_positives']:>5} {r['true_negatives']:>5} {r['false_positives']:>5} {r['false_negatives']:>5} {r['latency_mean_ms']:>7.2f}")
    print("-" * 100)
    print(f"{'Overall F1':<20} {'':<8} {'':<8} {'':<8} {'':<8} {results['overall_f1']:>7.1%}")
    print()

    # Summary
    print("DOF Benchmark Results:")
    for cat in ["hallucination", "code_safety", "governance", "consistency"]:
        r = results[cat]
        label = cat.replace("_", " ").title()
        print(f"  {label}: FDR={r['fdr']:.1%}, FPR={r['fpr']:.1%}")
    print(f"  Overall F1: {results['overall_f1']:.1%}")
    print()

    # Save results
    logs_dir = os.path.join(BASE_DIR, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    results_path = os.path.join(logs_dir, f"benchmark_{timestamp}.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved: {results_path}")


if __name__ == "__main__":
    main()
