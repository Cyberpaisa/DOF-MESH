"""
DOF Mesh Stress Test v2 — 18 tasks across 5 nodes with multi-provider tracking.

Improvements over v1:
  - Simpler uniform task: "Respond with one sentence: what is your role in the DOF system?"
  - 5 nodes instead of 6: dof-coder (6), dof-reasoner (3), dof-analyst (3),
    dof-guardian (3), local-agi-m4max (3)
  - Provider breakdown in final report (ollama vs cerebras vs groq)
  - Shorter polling window: 120s max (v1 used 360s)
  - ASCII bar chart of per-node success results
  - Tracks which provider actually served each task
"""

import json
import os
import sys
import time
import uuid
import threading
import requests
from pathlib import Path
from datetime import datetime

# ── paths ──────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent.parent
INBOX_ROOT  = BASE_DIR / "logs" / "mesh" / "inbox"
RESULTS_DIR = BASE_DIR / "logs" / "local-agent" / "results"
OLLAMA_URL  = os.getenv("OLLAMA_URL", "http://localhost:11434")
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ── task definitions — uniform simple prompt across all nodes ──────────────────
SIMPLE_PROMPT = "Respond with one sentence: what is your role in the DOF system?"

NODE_TASK_COUNTS = {
    "dof-coder":       6,
    "dof-reasoner":    3,
    "dof-analyst":     3,
    "dof-guardian":    3,
    "local-agi-m4max": 3,
}

# ── model routing ──────────────────────────────────────────────────────────────
MODEL_ROUTING = {
    "dof-coder":       "dof-coder:latest",
    "dof-reasoner":    "dof-reasoner:latest",
    "dof-analyst":     "dof-analyst:latest",
    "dof-guardian":    "dof-guardian:latest",
    "local-agi-m4max": "local-agi-m4max:latest",
}

CEREBRAS_FALLBACK_MODEL = "llama-3.3-70b"
GROQ_FALLBACK_MODEL     = "llama-3.3-70b-versatile"

# ── state tracking ─────────────────────────────────────────────────────────────
_lock          = threading.Lock()
_task_registry = {}  # task_id -> dict


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_task_id() -> str:
    return f"sv2-{uuid.uuid4().hex[:8]}"


def _write_work_order(node: str, task_id: str, prompt: str) -> Path:
    inbox_dir = INBOX_ROOT / node
    inbox_dir.mkdir(parents=True, exist_ok=True)
    msg = {
        "msg_id":    task_id,
        "from_node": "stress-test-v2",
        "to_node":   node,
        "msg_type":  "work_order",
        "timestamp": time.time(),
        "content": {
            "task": {
                "task_id":   task_id,
                "task_type": "default",
                "prompt":    prompt,
                "context":   {},
            }
        },
    }
    path = inbox_dir / f"{task_id}.json"
    path.write_text(json.dumps(msg, indent=2), encoding="utf-8")
    return path


def _call_ollama(model: str, prompt: str, timeout: int = 110) -> tuple[str, bool]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 128, "temperature": 0.2},
    }
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        text = resp.json().get("response", "").strip()
        return text or "[EMPTY RESPONSE]", bool(text)
    except requests.Timeout:
        return f"[TIMEOUT after {timeout}s]", False
    except Exception as exc:
        return f"[OLLAMA ERROR] {exc}", False


def _call_external_cerebras(prompt: str, timeout: int = 60) -> tuple[str, bool]:
    if not CEREBRAS_API_KEY:
        return "[CEREBRAS_API_KEY not set]", False
    messages = [{"role": "user", "content": prompt}]
    try:
        resp = requests.post(
            CEREBRAS_URL,
            headers={
                "Authorization": f"Bearer {CEREBRAS_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": CEREBRAS_FALLBACK_MODEL,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 128,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        return content or "[EMPTY RESPONSE]", bool(content)
    except requests.Timeout:
        return f"[CEREBRAS TIMEOUT]", False
    except Exception as exc:
        return f"[CEREBRAS ERROR] {exc}", False


def _call_groq(prompt: str, timeout: int = 60) -> tuple[str, bool]:
    if not GROQ_API_KEY:
        return "[GROQ_API_KEY not set]", False
    messages = [{"role": "user", "content": prompt}]
    try:
        resp = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_FALLBACK_MODEL,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 128,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        return content or "[EMPTY RESPONSE]", bool(content)
    except requests.Timeout:
        return "[GROQ TIMEOUT]", False
    except Exception as exc:
        return f"[GROQ ERROR] {exc}", False


def _run_task(task_id: str, node: str, prompt: str) -> None:
    """Execute one task, trying Ollama first then Cerebras then Groq."""
    model = MODEL_ROUTING.get(node, "dof-coder:latest")
    start = time.time()

    with _lock:
        _task_registry[task_id]["status"] = "running"
        _task_registry[task_id]["model"]  = model

    # Try Ollama first
    text, success = _call_ollama(model, prompt)
    provider = "ollama"

    # Fallback to Cerebras
    if not success and CEREBRAS_API_KEY:
        text, success = _call_external_cerebras(prompt)
        provider = "cerebras"

    # Fallback to Groq
    if not success and GROQ_API_KEY:
        text, success = _call_groq(prompt)
        provider = "groq"

    if not success:
        provider = "none"

    elapsed_ms = (time.time() - start) * 1000

    result_payload = {
        "task_id":      task_id,
        "task_type":    "default",
        "prompt":       prompt,
        "result":       text,
        "model_used":   model,
        "provider":     provider,
        "duration_ms":  round(elapsed_ms, 2),
        "success":      success,
        "node":         node,
        "completed_at": time.time(),
    }

    result_file = RESULTS_DIR / f"{task_id}.json"
    result_file.write_text(json.dumps(result_payload, indent=2), encoding="utf-8")

    # Mark inbox file as done
    inbox_file = INBOX_ROOT / node / f"{task_id}.json"
    done_file  = INBOX_ROOT / node / f"{task_id}.done"
    if inbox_file.exists():
        inbox_file.rename(done_file)

    with _lock:
        _task_registry[task_id]["status"]       = "done"
        _task_registry[task_id]["success"]      = success
        _task_registry[task_id]["provider"]     = provider
        _task_registry[task_id]["duration_ms"]  = round(elapsed_ms, 2)
        _task_registry[task_id]["end"]          = time.time()
        _task_registry[task_id]["result_snippet"] = text[:120]


def _status_line() -> str:
    with _lock:
        total   = len(_task_registry)
        done    = sum(1 for t in _task_registry.values() if t["status"] == "done")
        running = sum(1 for t in _task_registry.values() if t["status"] == "running")
        pending = total - done - running
    return f"[{datetime.now().strftime('%H:%M:%S')}] Total={total} | Done={done} | Running={running} | Pending={pending}"


def _ascii_bar(value: int, max_value: int, width: int = 30) -> str:
    if max_value == 0:
        return " " * width
    filled = int(width * value / max_value)
    return "█" * filled + "░" * (width - filled)


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 72)
    print("  DOF MESH STRESS TEST v2 — 18 tasks / 5 nodes / multi-provider")
    print("=" * 72)
    print(f"  Base dir   : {BASE_DIR}")
    print(f"  Ollama URL : {OLLAMA_URL}")
    print(f"  Cerebras   : {'CONFIGURED' if CEREBRAS_API_KEY else 'NOT SET'}")
    print(f"  Groq       : {'CONFIGURED' if GROQ_API_KEY else 'NOT SET'}")
    print(f"  Results    : {RESULTS_DIR}")
    print(f"  Prompt     : {SIMPLE_PROMPT}")
    print()

    # ── 1. Write all work orders ─────────────────────────────────────────────
    print("── PHASE 1: Writing work orders to inboxes ──────────────────────────")
    all_tasks: list[tuple[str, str, str]] = []

    for node, count in NODE_TASK_COUNTS.items():
        for i in range(count):
            task_id = _make_task_id()
            _write_work_order(node, task_id, SIMPLE_PROMPT)
            _task_registry[task_id] = {
                "node":           node,
                "prompt":         SIMPLE_PROMPT,
                "status":         "pending",
                "model":          MODEL_ROUTING.get(node),
                "provider":       None,
                "start":          time.time(),
                "end":            None,
                "success":        None,
                "duration_ms":    None,
                "result_snippet": None,
            }
            all_tasks.append((task_id, node, SIMPLE_PROMPT))
            print(f"  [QUEUED] {node:<20} {task_id}  (task {i + 1}/{count})")

    print(f"\n  Total work orders written: {len(all_tasks)}")
    print()

    # ── 2. Fire all tasks simultaneously ─────────────────────────────────────
    print("── PHASE 2: Firing all tasks simultaneously ──────────────────────────")
    threads: list[threading.Thread] = []
    fire_time = time.time()

    for task_id, node, prompt in all_tasks:
        t = threading.Thread(
            target=_run_task,
            args=(task_id, node, prompt),
            daemon=True,
            name=f"worker-{task_id}",
        )
        threads.append(t)

    for t in threads:
        t.start()

    print(f"  {len(threads)} threads launched at {datetime.now().strftime('%H:%M:%S')}")
    print()

    # ── 3. Poll for completion (120s max) ─────────────────────────────────────
    print("── PHASE 3: Polling for completion (every 2s, max 120s) ─────────────")
    POLL_INTERVAL = 2
    MAX_WAIT_S    = 120
    deadline      = time.time() + MAX_WAIT_S

    while time.time() < deadline:
        print(_status_line())
        with _lock:
            done = sum(1 for t in _task_registry.values() if t["status"] == "done")
        if done == len(all_tasks):
            print("  All tasks completed!")
            break
        time.sleep(POLL_INTERVAL)
    else:
        print("  WARNING: 120s timeout reached — some tasks may still be running.")

    for t in threads:
        t.join(timeout=10)

    total_elapsed = time.time() - fire_time

    # ── 4. Final report ───────────────────────────────────────────────────────
    print()
    print("=" * 72)
    print("  FINAL REPORT")
    print("=" * 72)

    with _lock:
        snapshot = dict(_task_registry)

    # Aggregate per-node stats
    per_node: dict[str, dict] = {n: {"total": 0, "success": 0, "durations": []} for n in NODE_TASK_COUNTS}
    provider_counts: dict[str, int] = {"ollama": 0, "cerebras": 0, "groq": 0, "none": 0}

    for info in snapshot.values():
        node = info["node"]
        per_node[node]["total"] += 1
        if info.get("success"):
            per_node[node]["success"] += 1
        if info.get("duration_ms") is not None:
            per_node[node]["durations"].append(info["duration_ms"])
        prov = info.get("provider") or "none"
        provider_counts[prov] = provider_counts.get(prov, 0) + 1

    total_tasks   = len(snapshot)
    total_success = sum(1 for i in snapshot.values() if i.get("success"))
    total_fail    = total_tasks - total_success
    all_durations = [i["duration_ms"] for i in snapshot.values() if i.get("duration_ms")]
    avg_duration  = sum(all_durations) / len(all_durations) if all_durations else 0
    success_rate  = 100 * total_success / total_tasks if total_tasks else 0

    print(f"\n  Tasks fired       : {total_tasks}")
    print(f"  Tasks succeeded   : {total_success}")
    print(f"  Tasks failed      : {total_fail}")
    print(f"  Success rate      : {success_rate:.1f}%")
    print(f"  Avg duration      : {avg_duration / 1000:.2f}s  ({avg_duration:.0f}ms)")
    print(f"  Wall-clock elapsed: {total_elapsed:.1f}s")

    # Provider breakdown
    print()
    print("  Provider breakdown:")
    for prov, count in sorted(provider_counts.items(), key=lambda x: -x[1]):
        if count > 0:
            pct = 100 * count / total_tasks if total_tasks else 0
            print(f"    {prov:<12} {count:>3} tasks  ({pct:.0f}%)")

    # Per-node summary
    print()
    print("  Per-node breakdown:")
    print(f"  {'Node':<22} {'Done':>4}  {'OK':>4}  {'Avg(s)':>7}")
    print("  " + "-" * 46)
    for node, stats in per_node.items():
        avg_s = (sum(stats["durations"]) / len(stats["durations"]) / 1000) if stats["durations"] else 0
        print(f"  {node:<22} {stats['total']:>4}  {stats['success']:>4}  {avg_s:>7.2f}")

    # ASCII bar chart
    print()
    print("  ASCII bar chart — success count per node:")
    print("  " + "-" * 60)
    max_tasks = max(s["total"] for s in per_node.values()) if per_node else 1
    for node, stats in per_node.items():
        bar = _ascii_bar(stats["success"], max_tasks, width=30)
        label = f"{stats['success']}/{stats['total']}"
        print(f"  {node:<22} [{bar}] {label}")

    print()
    print(f"  Results persisted in: {RESULTS_DIR}")
    print("=" * 72)

    sys.exit(0 if success_rate >= 80 else 1)


if __name__ == "__main__":
    main()
