"""
Multi-Model Architecture Benchmark — DOF Mesh Bottleneck Analysis.

Sends the same question to all available providers in parallel and
saves results to logs/benchmarks/multi_model_{timestamp}.json.

Usage: python3 scripts/multi_model_benchmark.py
"""
import os
import sys
import json
import time
import threading
from pathlib import Path
from typing import Optional
from datetime import datetime

import requests

REPO_ROOT = Path(__file__).parent.parent

# Load .env
_env_path = REPO_ROOT / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

QUESTION = """Analyze this DOF mesh architecture:
- 6 agent nodes: dof-coder, dof-reasoner, dof-guardian, dof-analyst, local-agi-m4max, local-agent
- All share ONE Ollama instance with 8 custom models (Qwen2.5-Coder 14.8B base)
- Each node polls a JSON inbox directory every 3 seconds for tasks
- Results written to logs/local-agent/results/{task_id}.json
- New: DeepSeek primary provider, Ollama as fallback, then Cerebras/Groq

Identify the top 3 bottlenecks and propose specific Python code solutions for each.
Be concise but technically precise."""

SYSTEM = "You are a senior distributed systems architect specializing in AI agent infrastructure."

# ─── Provider implementations ──────────────────────────────────────────────


def call_deepseek(question: str) -> dict:
    key = os.getenv("DEEPSEEK_API_KEY", "")
    if not key:
        return {"error": "no key"}
    t0 = time.perf_counter()
    try:
        r = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": question},
            ], "temperature": 0.2, "max_tokens": 2048},
            timeout=60,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        return {"response": content, "latency_s": round(time.perf_counter() - t0, 1), "tokens": r.json().get("usage", {}).get("total_tokens")}
    except Exception as e:
        return {"error": str(e), "latency_s": round(time.perf_counter() - t0, 1)}


def call_gemini(question: str) -> dict:
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        return {"error": "no key"}
    t0 = time.perf_counter()
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}",
            json={"contents": [{"parts": [{"text": f"{SYSTEM}\n\n{question}"}]}],
                  "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048}},
            timeout=60,
        )
        r.raise_for_status()
        content = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return {"response": content, "latency_s": round(time.perf_counter() - t0, 1)}
    except Exception as e:
        return {"error": str(e), "latency_s": round(time.perf_counter() - t0, 1)}


def call_openrouter(question: str, model: str = "openai/gpt-4o-mini") -> dict:
    key = os.getenv("OPENROUTER_API_KEY", "")
    if not key:
        return {"error": "no key"}
    t0 = time.perf_counter()
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                     "HTTP-Referer": "https://github.com/dof-sdk"},
            json={"model": model, "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": question},
            ], "temperature": 0.2, "max_tokens": 2048},
            timeout=60,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        return {"response": content, "latency_s": round(time.perf_counter() - t0, 1), "model": model}
    except Exception as e:
        return {"error": str(e), "latency_s": round(time.perf_counter() - t0, 1)}


def call_groq(question: str) -> dict:
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        return {"error": "no key"}
    t0 = time.perf_counter()
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile", "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": question},
            ], "temperature": 0.2, "max_tokens": 2048},
            timeout=30,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        return {"response": content, "latency_s": round(time.perf_counter() - t0, 1)}
    except Exception as e:
        return {"error": str(e), "latency_s": round(time.perf_counter() - t0, 1)}


def call_nvidia(question: str) -> dict:
    key = os.getenv("NVIDIA_API_KEY", "")
    if not key:
        return {"error": "no key"}
    t0 = time.perf_counter()
    try:
        r = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": "meta/llama-3.3-70b-instruct", "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": question},
            ], "temperature": 0.2, "max_tokens": 2048},
            timeout=60,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        return {"response": content, "latency_s": round(time.perf_counter() - t0, 1)}
    except Exception as e:
        return {"error": str(e), "latency_s": round(time.perf_counter() - t0, 1)}


def call_minimax(question: str) -> dict:
    key = os.getenv("MINIMAX_API_KEY", "")
    if not key:
        return {"error": "no key"}
    t0 = time.perf_counter()
    try:
        r = requests.post(
            "https://api.minimax.chat/v1/text/chatcompletion_v2",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": "MiniMax-Text-01", "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": question},
            ], "temperature": 0.2, "max_tokens": 2048},
            timeout=60,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        return {"response": content, "latency_s": round(time.perf_counter() - t0, 1)}
    except Exception as e:
        return {"error": str(e), "latency_s": round(time.perf_counter() - t0, 1)}


def call_sambanova(question: str) -> dict:
    key = os.getenv("SAMBANOVA_API_KEY", "")
    if not key:
        return {"error": "no key"}
    t0 = time.perf_counter()
    try:
        r = requests.post(
            "https://api.sambanova.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": "Meta-Llama-3.3-70B-Instruct", "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": question},
            ], "temperature": 0.2, "max_tokens": 2048},
            timeout=60,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        return {"response": content, "latency_s": round(time.perf_counter() - t0, 1)}
    except Exception as e:
        return {"error": str(e), "latency_s": round(time.perf_counter() - t0, 1)}


# ─── Parallel runner ────────────────────────────────────────────────────────

PROVIDERS = {
    "deepseek-chat":              call_deepseek,
    "gemini-2.0-flash":           call_gemini,
    "gpt-4o-mini (openrouter)":   lambda q: call_openrouter(q, "openai/gpt-4o-mini"),
    "groq-llama3.3-70b":          call_groq,
    "nvidia-llama3.3-70b":        call_nvidia,
    "minimax-text-01":            call_minimax,
    "sambanova-llama3.3-70b":     call_sambanova,
}


def run_benchmark() -> dict:
    results = {}
    threads = []
    lock = threading.Lock()

    def query_provider(name, fn):
        print(f"  → querying {name}...")
        result = fn(QUESTION)
        with lock:
            results[name] = result
        status = "✓" if "response" in result else "✗"
        latency = result.get("latency_s", "?")
        chars = len(result.get("response", ""))
        print(f"  {status} {name}: {latency}s, {chars} chars")

    t0 = time.perf_counter()
    for name, fn in PROVIDERS.items():
        t = threading.Thread(target=query_provider, args=(name, fn))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    total = round(time.perf_counter() - t0, 1)
    return {"question": QUESTION, "results": results, "total_time_s": total,
            "timestamp": datetime.utcnow().isoformat()}


def main():
    print("=" * 60)
    print("  DOF Multi-Model Architecture Benchmark")
    print(f"  {len(PROVIDERS)} providers — parallel")
    print("=" * 60)

    data = run_benchmark()

    # Save
    out_dir = REPO_ROOT / "logs" / "benchmarks"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"multi_model_{ts}.json"
    out_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    # Summary table
    print("\n" + "=" * 60)
    print("  RESULTS SUMMARY")
    print("=" * 60)
    successes = [(k, v) for k, v in data["results"].items() if "response" in v]
    failures = [(k, v) for k, v in data["results"].items() if "error" in v]

    successes.sort(key=lambda x: x[1].get("latency_s", 99))
    for name, r in successes:
        chars = len(r["response"])
        print(f"  ✓ {name:<35} {r['latency_s']:>5}s  {chars:>5} chars")
    for name, r in failures:
        print(f"  ✗ {name:<35} ERROR: {r['error'][:40]}")

    print(f"\n  Total wall time: {data['total_time_s']}s (parallel)")
    print(f"  Results saved → {out_file.name}")
    print("=" * 60)

    # Print best response
    if successes:
        best_name, best = successes[0]
        print(f"\n── FASTEST: {best_name} ({best['latency_s']}s) ──")
        print(best["response"][:800])

    return out_file


if __name__ == "__main__":
    main()
