#!/usr/bin/env python3
"""
DOF Privacy Benchmark Runner — AgentLeak-inspired privacy leak detection.

Generates 200 test cases (50 per category) and benchmarks DOF privacy
detection across 7 communication channels.

Categories:
  - PII_LEAK (emails, phones, SSNs, credit cards)
  - API_KEY_LEAK (OpenAI, AWS, GitHub, Ethereum, Supabase)
  - MEMORY_LEAK (cross-agent data, session history, system prompts)
  - TOOL_INPUT_LEAK (SQL with PII, API URLs with tokens, file paths)

Usage:
    python3 scripts/run_privacy_benchmark.py
"""

import json
import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agentleak_benchmark import (
    AgentLeakMapper,
    PrivacyLeakGenerator,
    PrivacyBenchmarkRunner,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    print("=" * 70)
    print("DOF Privacy Benchmark — AgentLeak Channel Mapping")
    print("=" * 70)
    print()

    # Generate dataset
    print("[1/4] Generating privacy test dataset (200 tests)...")
    gen = PrivacyLeakGenerator(seed=42)
    dataset = gen.generate_full_dataset(n_per_category=50)
    print(f"  Dataset saved: {dataset['path']}")
    print(f"  Total tests: {dataset['total_tests']}")
    print()

    # Run benchmarks
    print("[2/4] Running privacy benchmarks...")
    start = time.time()
    runner = PrivacyBenchmarkRunner(dataset)
    results = runner.run_full_benchmark()
    elapsed = time.time() - start
    print(f"  Completed in {elapsed:.2f}s")
    print()

    # Print category results table
    print("[3/4] Results by Category")
    print()
    print(f"{'Category':<20} {'DR':>8} {'FPR':>8} {'F1':>8} {'Prec':>8} {'Recall':>8} {'TP':>5} {'TN':>5} {'FP':>5} {'FN':>5} {'Lat(ms)':>8}")
    print("-" * 105)
    for cat in ["PII_LEAK", "API_KEY_LEAK", "MEMORY_LEAK", "TOOL_INPUT_LEAK"]:
        r = results[cat]
        print(f"{cat:<20} {r['dr']:>7.1%} {r['fpr']:>7.1%} {r['f1']:>7.1%} {r['precision']:>7.1%} {r['recall']:>7.1%} {r['true_positives']:>5} {r['true_negatives']:>5} {r['false_positives']:>5} {r['false_negatives']:>5} {r['latency_mean_ms']:>7.2f}")
    print("-" * 105)
    overall = results["overall"]
    print(f"{'Overall':<20} {overall['overall_dr']:>7.1%} {overall['overall_fpr']:>7.1%} {overall['overall_f1']:>7.1%}")
    print()

    # Print channel results table
    print("[4/4] Results by AgentLeak Channel")
    print()
    print(f"{'Channel':<28} {'Tests':>6} {'DR':>8} {'FPR':>8} {'F1':>8}")
    print("-" * 62)
    channels = results.get("channels", {})
    for ch in AgentLeakMapper.get_channels():
        if ch in channels:
            r = channels[ch]
            print(f"{ch:<28} {r['tests_total']:>6} {r['dr']:>7.1%} {r['fpr']:>7.1%} {r['f1']:>7.1%}")
        else:
            print(f"{ch:<28} {'0':>6} {'—':>8} {'—':>8} {'—':>8}")
    print("-" * 62)
    print()

    # Summary
    print("Privacy Benchmark Summary:")
    print(f"  Total tests: {overall['total_tests']}")
    print(f"  Overall DR: {overall['overall_dr']:.1%}")
    print(f"  Overall FPR: {overall['overall_fpr']:.1%}")
    print(f"  Overall F1: {overall['overall_f1']:.1%}")
    print(f"  TP={overall['true_positives']}, TN={overall['true_negatives']}, FP={overall['false_positives']}, FN={overall['false_negatives']}")
    print(f"  Execution time: {elapsed:.2f}s")
    print()

    # Save results
    logs_dir = os.path.join(BASE_DIR, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    results_path = os.path.join(logs_dir, f"privacy_benchmark_{timestamp}.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved: {results_path}")


if __name__ == "__main__":
    main()
