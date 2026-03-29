"""
DOF Provider Benchmark — direct latency test for each LLM provider.

Tests each provider independently (not via mesh):
  1. Ollama (local) — via AutonomousExecutor._call_ollama
  2. Cerebras (cloud) — via AutonomousExecutor._call_external
  3. Groq (cloud) — via AutonomousExecutor._call_groq

Benchmark prompt: "What is 2+2? Answer in one word."
Prints a results table with latency, success, and response preview.
"""

import os
import sys
import time
from pathlib import Path

# Ensure repo root is on the path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.autonomous_executor import (
    AutonomousExecutor,
    CEREBRAS_API_KEY,
    GROQ_API_KEY,
    CEREBRAS_FALLBACK_MODEL,
    GROQ_FALLBACK_MODEL,
    OLLAMA_URL,
)

BENCHMARK_PROMPT = "What is 2+2? Answer in one word."

# Use the simplest available local model for Ollama benchmark
OLLAMA_BENCH_MODEL = os.getenv("OLLAMA_BENCH_MODEL", "dof-coder:latest")


def _header(title: str) -> None:
    print()
    print(f"  ── {title} " + "─" * max(0, 60 - len(title)))


def _run_ollama(executor: AutonomousExecutor) -> dict:
    messages = [{"role": "user", "content": BENCHMARK_PROMPT}]
    _header(f"Ollama  [{OLLAMA_URL}]  model={OLLAMA_BENCH_MODEL}")
    t0 = time.perf_counter()
    resp = executor._call_ollama(messages, OLLAMA_BENCH_MODEL)
    latency_ms = (time.perf_counter() - t0) * 1000
    success = resp is not None and not resp.startswith("[")
    snippet = (resp or "")[:60]
    print(f"  Latency   : {latency_ms:.0f} ms")
    print(f"  Success   : {success}")
    print(f"  Response  : {snippet!r}")
    return {
        "provider": "ollama",
        "model": OLLAMA_BENCH_MODEL,
        "latency_ms": round(latency_ms),
        "success": success,
        "response": resp or "",
    }


def _run_cerebras(executor: AutonomousExecutor) -> dict:
    messages = [{"role": "user", "content": BENCHMARK_PROMPT}]
    _header(f"Cerebras  model={CEREBRAS_FALLBACK_MODEL}")
    if not CEREBRAS_API_KEY:
        print("  SKIPPED — CEREBRAS_API_KEY not set")
        return {"provider": "cerebras", "model": CEREBRAS_FALLBACK_MODEL, "latency_ms": 0, "success": False, "response": "SKIPPED"}
    t0 = time.perf_counter()
    resp = executor._call_external(messages, CEREBRAS_FALLBACK_MODEL)
    latency_ms = (time.perf_counter() - t0) * 1000
    success = resp is not None and not resp.startswith("[")
    snippet = (resp or "")[:60]
    print(f"  Latency   : {latency_ms:.0f} ms")
    print(f"  Success   : {success}")
    print(f"  Response  : {snippet!r}")
    return {
        "provider": "cerebras",
        "model": CEREBRAS_FALLBACK_MODEL,
        "latency_ms": round(latency_ms),
        "success": success,
        "response": resp or "",
    }


def _run_groq(executor: AutonomousExecutor) -> dict:
    messages = [{"role": "user", "content": BENCHMARK_PROMPT}]
    _header(f"Groq  model={GROQ_FALLBACK_MODEL}")
    if not GROQ_API_KEY:
        print("  SKIPPED — GROQ_API_KEY not set")
        return {"provider": "groq", "model": GROQ_FALLBACK_MODEL, "latency_ms": 0, "success": False, "response": "SKIPPED"}
    t0 = time.perf_counter()
    resp = executor._call_groq(messages, GROQ_FALLBACK_MODEL)
    latency_ms = (time.perf_counter() - t0) * 1000
    success = resp is not None and not resp.startswith("[")
    snippet = (resp or "")[:60]
    print(f"  Latency   : {latency_ms:.0f} ms")
    print(f"  Success   : {success}")
    print(f"  Response  : {snippet!r}")
    return {
        "provider": "groq",
        "model": GROQ_FALLBACK_MODEL,
        "latency_ms": round(latency_ms),
        "success": success,
        "response": resp or "",
    }


def _print_table(results: list[dict]) -> None:
    print()
    print("=" * 72)
    print("  PROVIDER BENCHMARK RESULTS")
    print("=" * 72)
    print(f"  Prompt: {BENCHMARK_PROMPT!r}")
    print()
    print(f"  {'Provider':<12} {'Model':<30} {'Latency':>10}  {'OK':>4}  Response")
    print("  " + "-" * 70)
    for r in results:
        ok_str  = "YES" if r["success"] else "NO "
        resp_preview = r["response"][:28]
        latency_str = f"{r['latency_ms']} ms" if r["latency_ms"] > 0 else "—"
        print(f"  {r['provider']:<12} {r['model']:<30} {latency_str:>10}  {ok_str:>4}  {resp_preview!r}")
    print()

    # Rank by latency (only successful ones)
    ranked = sorted([r for r in results if r["success"]], key=lambda x: x["latency_ms"])
    if ranked:
        print("  Fastest providers (successful only):")
        for i, r in enumerate(ranked, 1):
            print(f"    {i}. {r['provider']:<12} {r['latency_ms']} ms")
    else:
        print("  No providers returned a successful response.")
    print()


def main():
    print("=" * 72)
    print("  DOF PROVIDER BENCHMARK — direct latency test per provider")
    print("=" * 72)
    print(f"  Ollama URL : {OLLAMA_URL}")
    print(f"  Cerebras   : {'CONFIGURED' if CEREBRAS_API_KEY else 'NOT SET'}")
    print(f"  Groq       : {'CONFIGURED' if GROQ_API_KEY else 'NOT SET'}")

    # Use a fresh executor instance
    AutonomousExecutor.reset()
    executor = AutonomousExecutor(model=OLLAMA_BENCH_MODEL)

    results = []
    results.append(_run_ollama(executor))
    results.append(_run_cerebras(executor))
    results.append(_run_groq(executor))

    _print_table(results)


if __name__ == "__main__":
    main()
