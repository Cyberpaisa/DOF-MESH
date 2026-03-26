"""
DOF Mesh Stress Test — 18 simultaneous work orders across 6 nodes.

Fires 3 tasks to each of: dof-coder, dof-reasoner, dof-guardian,
dof-analyst, local-agi-m4max, local-agent

Writes JSON work orders to logs/mesh/inbox/{node}/ then calls Ollama
directly (same path as LocalAgentLoop) and writes results to
logs/local-agent/results/.  Polls every 2s up to 5 minutes.
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

# Ensure required directories exist
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ── task definitions ────────────────────────────────────────────────────────────
NODE_TASKS = {
    "dof-coder": [
        "List all Python files in core/ directory and count the lines in each file. Use shell commands to do this.",
        "Show the first 10 lines of core/kms.py and summarize what the module does.",
        "List all Python files in tests/ directory and count how many test classes exist across them.",
    ],
    "dof-reasoner": [
        "Analyze the DOF (Deterministic Observability Framework) architecture and list the top 3 improvements that could be made to the system design.",
        "Explain the difference between deterministic and probabilistic governance in AI systems, and why DOF chose deterministic.",
        "Describe the tradeoffs between using local Ollama models vs cloud LLMs for an autonomous agent mesh like DOF.",
    ],
    "dof-guardian": [
        "Scan core/cerberus.py for any security patterns — identify authentication, authorization, rate-limiting, or anomaly detection logic.",
        "List all security-related Python modules in core/ (by filename) and briefly describe each one's role.",
        "Describe what a 7-layer security stack means for an AI mesh system and identify any potential weaknesses.",
    ],
    "dof-analyst": [
        "Describe what bases_consolidadas_009.xlsb is likely used for based on its name and the context of a data migration project.",
        "What are the 5 formal metrics of the DOF system? List them with a one-sentence description each.",
        "Explain the Z3 theorem prover and why it is useful for governance in an AI system.",
    ],
    "local-agi-m4max": [
        "What are the 5 formal metrics of DOF? List them with their Z3 invariant names and brief descriptions.",
        "Explain how the M4 Max Neural Engine (ANE) can be leveraged for local AI inference and what advantages it provides over GPU.",
        "What is the AES-256-GCM encryption scheme and why is it used in the DOF Key Management System?",
    ],
    "local-agent": [
        "Count the total number of test files in the tests/ directory. List each filename.",
        "List all Python files in agents/ directory. Count how many there are.",
        "What files exist in the scripts/ directory? Count them and list the ones with .py extension.",
    ],
}

# ── model routing (mirrors local_agent_loop.py) ─────────────────────────────────
MODEL_ROUTING = {
    "dof-coder":        "dof-coder:latest",
    "dof-reasoner":     "dof-reasoner:latest",
    "dof-guardian":     "dof-guardian:latest",
    "dof-analyst":      "dof-analyst:latest",
    "local-agi-m4max":  "local-agi-m4max:latest",
    "local-agent":      "dof-coder:latest",   # local-agent uses code model
}

# ── state tracking ──────────────────────────────────────────────────────────────
_lock          = threading.Lock()
_task_registry = {}   # task_id -> dict with node, prompt, status, start, end, result, success

# ── helpers ─────────────────────────────────────────────────────────────────────

def _make_msg_id() -> str:
    return f"stress-{uuid.uuid4().hex[:8]}"


def _write_work_order(node: str, task_id: str, prompt: str) -> Path:
    """Write a JSON work order to the node's inbox. Returns the file path."""
    inbox_dir = INBOX_ROOT / node
    inbox_dir.mkdir(parents=True, exist_ok=True)

    msg = {
        "msg_id": task_id,
        "from_node": "stress-test",
        "to_node": node,
        "msg_type": "work_order",
        "timestamp": time.time(),
        "content": {
            "task": {
                "task_id": task_id,
                "task_type": "default",
                "prompt": prompt,
                "context": {},
            }
        },
    }
    path = inbox_dir / f"{task_id}.json"
    path.write_text(json.dumps(msg, indent=2), encoding="utf-8")
    return path


def _call_ollama(model: str, prompt: str, timeout: int = 280) -> tuple[str, bool]:
    """Call Ollama directly. Returns (response_text, success)."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 256, "temperature": 0.2},
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
        return f"[ERROR] {exc}", False


def _run_task(task_id: str, node: str, prompt: str) -> None:
    """Execute one task via Ollama and persist the result."""
    model = MODEL_ROUTING.get(node, "dof-coder:latest")
    start = time.time()

    with _lock:
        _task_registry[task_id]["status"] = "running"
        _task_registry[task_id]["model"]  = model

    text, success = _call_ollama(model, prompt)
    elapsed_ms = (time.time() - start) * 1000

    result_payload = {
        "task_id":    task_id,
        "task_type":  "default",
        "prompt":     prompt,
        "result":     text,
        "model_used": model,
        "duration_ms": round(elapsed_ms, 2),
        "success":    success,
        "node":       node,
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
        _task_registry[task_id]["status"]     = "done"
        _task_registry[task_id]["success"]    = success
        _task_registry[task_id]["duration_ms"] = round(elapsed_ms, 2)
        _task_registry[task_id]["end"]        = time.time()
        _task_registry[task_id]["result_snippet"] = text[:120]


def _status_line() -> str:
    with _lock:
        total   = len(_task_registry)
        done    = sum(1 for t in _task_registry.values() if t["status"] == "done")
        running = sum(1 for t in _task_registry.values() if t["status"] == "running")
        pending = total - done - running
    return f"[{datetime.now().strftime('%H:%M:%S')}] Total={total} | Done={done} | Running={running} | Pending={pending}"


# ── main ────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  DOF MESH STRESS TEST — 18 simultaneous work orders / 6 nodes")
    print("=" * 70)
    print(f"  Base dir  : {BASE_DIR}")
    print(f"  Ollama URL: {OLLAMA_URL}")
    print(f"  Results   : {RESULTS_DIR}")
    print()

    # ── 1. Write all work orders ────────────────────────────────────────────────
    print("── PHASE 1: Writing work orders to inboxes ─────────────────────────")
    all_tasks: list[tuple[str, str, str]] = []  # (task_id, node, prompt)

    for node, prompts in NODE_TASKS.items():
        for prompt in prompts:
            task_id = _make_msg_id()
            _write_work_order(node, task_id, prompt)
            _task_registry[task_id] = {
                "node":     node,
                "prompt":   prompt[:60] + "…" if len(prompt) > 60 else prompt,
                "status":   "pending",
                "model":    MODEL_ROUTING.get(node),
                "start":    time.time(),
                "end":      None,
                "success":  None,
                "duration_ms": None,
                "result_snippet": None,
            }
            all_tasks.append((task_id, node, prompt))
            print(f"  [QUEUED] {node:<18} {task_id}  {prompt[:55]}…")

    print(f"\n  Total work orders written: {len(all_tasks)}")
    print()

    # ── 2. Fire all tasks simultaneously ───────────────────────────────────────
    print("── PHASE 2: Firing all tasks simultaneously ────────────────────────")
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

    # ── 3. Poll for completion ──────────────────────────────────────────────────
    print("── PHASE 3: Polling for completion (every 2s, max 5 min) ───────────")
    POLL_INTERVAL = 2
    MAX_WAIT_S    = 360
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
        print("  WARNING: Timeout reached — some tasks may still be running.")

    # Wait for all threads to finish (max 10s extra grace)
    for t in threads:
        t.join(timeout=10)

    total_elapsed = time.time() - fire_time

    # ── 4. Final report ─────────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("  FINAL REPORT")
    print("=" * 70)

    with _lock:
        snapshot = dict(_task_registry)

    per_node: dict[str, dict] = {}
    for node in NODE_TASKS:
        per_node[node] = {"total": 0, "success": 0, "durations": []}

    for task_id, info in snapshot.items():
        node = info["node"]
        per_node[node]["total"] += 1
        if info.get("success"):
            per_node[node]["success"] += 1
        if info.get("duration_ms") is not None:
            per_node[node]["durations"].append(info["duration_ms"])

    total_tasks     = len(snapshot)
    total_success   = sum(1 for i in snapshot.values() if i.get("success"))
    total_fail      = total_tasks - total_success
    all_durations   = [i["duration_ms"] for i in snapshot.values() if i.get("duration_ms")]
    avg_duration    = sum(all_durations) / len(all_durations) if all_durations else 0
    success_rate    = 100 * total_success / total_tasks if total_tasks else 0

    print(f"\n  Tasks fired       : {total_tasks}")
    print(f"  Tasks succeeded   : {total_success}")
    print(f"  Tasks failed      : {total_fail}")
    print(f"  Success rate      : {success_rate:.1f}%")
    print(f"  Avg duration      : {avg_duration / 1000:.1f}s")
    print(f"  Wall-clock elapsed: {total_elapsed:.1f}s")
    print()

    print("  Per-node breakdown:")
    print(f"  {'Node':<20} {'Done':>4}  {'OK':>4}  {'Avg (s)':>8}")
    print("  " + "-" * 44)
    for node, stats in per_node.items():
        avg_s = (sum(stats["durations"]) / len(stats["durations"]) / 1000) if stats["durations"] else 0
        print(f"  {node:<20} {stats['total']:>4}  {stats['success']:>4}  {avg_s:>8.1f}")

    print()
    print("  Per-task summary:")
    print(f"  {'Task ID':<22} {'Node':<18} {'Status':<8} {'ms':>8}  Snippet")
    print("  " + "-" * 90)
    for task_id, info in snapshot.items():
        status_icon = "OK" if info.get("success") else "FAIL"
        dur = f"{info['duration_ms']:.0f}" if info.get("duration_ms") else "—"
        snippet = (info.get("result_snippet") or "")[:40]
        print(f"  {task_id:<22} {info['node']:<18} {status_icon:<8} {dur:>8}  {snippet}")

    print()
    print(f"  Results persisted in: {RESULTS_DIR}")
    print("=" * 70)

    # Return exit code based on success rate
    sys.exit(0 if success_rate >= 80 else 1)


if __name__ == "__main__":
    main()
