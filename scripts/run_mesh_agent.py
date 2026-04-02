"""
Mesh Agent Daemon — Autonomous execution engine for DOF local chat.

Polls logs/mesh/inbox/local-agent/ every 3 seconds.
For each task: runs autonomous agentic loop (bash + python + file ops).
Writes result to logs/local-agent/results/{task_id}.json.

Usage:
  python3 scripts/run_mesh_agent.py
  python3 scripts/run_mesh_agent.py --model dof-coder
  python3 scripts/run_mesh_agent.py --poll 5
"""
import os
import sys
import json
import time
import signal
import logging
import argparse
import threading
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.autonomous_executor import AutonomousExecutor
from core.mesh_scheduler import MeshScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("mesh_agent")

INBOX_DIRS = [
    REPO_ROOT / "logs" / "mesh" / "inbox" / "local-agent",
    REPO_ROOT / "logs" / "mesh" / "inbox" / "dof-coder",
    REPO_ROOT / "logs" / "mesh" / "inbox" / "dof-reasoner",
    REPO_ROOT / "logs" / "mesh" / "inbox" / "dof-guardian",
    REPO_ROOT / "logs" / "mesh" / "inbox" / "dof-analyst",
    REPO_ROOT / "logs" / "mesh" / "inbox" / "local-agi-m4max",
]
RESULTS_DIR = REPO_ROOT / "logs" / "local-agent" / "results"
WAL_DIR = REPO_ROOT / "logs" / "mesh" / "wal"


def wal_write(task_id: str, status: str) -> None:
    """Append WAL entry: timestamp,task_id,status"""
    WAL_DIR.mkdir(parents=True, exist_ok=True)
    entry = f"{time.time()},{task_id},{status}\n"
    (WAL_DIR / "tasks.wal").open("a").write(entry)


def wal_recover_orphans() -> list[Path]:
    """Find .processing files older than 300s and re-queue them."""
    recovered = []
    for inbox_dir in INBOX_DIRS:
        for stale in inbox_dir.glob("*.processing"):
            age = time.time() - stale.stat().st_mtime
            if age > 300:
                # Re-queue: rename back to .json
                original = stale.with_suffix(".json")
                stale.rename(original)
                logger.warning("WAL RECOVERY: %s (age=%.0fs)", stale.name, age)
                wal_write(stale.stem, "RECOVERED")
                recovered.append(original)
    return recovered

# Map inbox folder → model to use
NODE_MODEL_MAP = {
    "dof-coder":       "dof-coder",
    "dof-reasoner":    "dof-reasoner",
    "dof-guardian":    "dof-guardian",
    "dof-analyst":     "dof-analyst",
    "local-agi-m4max": "local-agi-m4max",
    "local-agent":     "dof-coder",   # default
}

_stop = threading.Event()
scheduler = MeshScheduler(max_concurrent=3)


def handle_signal(signum, frame):
    logger.info("Signal %d received — shutting down gracefully...", signum)
    _stop.set()


def scan_inbox(inbox_dir: Path) -> list[Path]:
    """Return all pending .json task files in the inbox."""
    if not inbox_dir.exists():
        return []
    return sorted(inbox_dir.glob("*.json"))


def read_task(task_file: Path) -> tuple[str, str, str] | None:
    """
    Parse a task file. Returns (task_id, prompt, task_type) or None on error.
    Marks file as .processing to prevent double-pick.
    """
    try:
        data = json.loads(task_file.read_text(encoding="utf-8"))
        # Support both flat and nested formats
        content_val = data.get("content", {})
        if isinstance(content_val, str):
            task_data = {"prompt": content_val}
        else:
            task_data = content_val.get("task") or data

        task_id   = task_data.get("task_id") or data.get("msg_id") or task_file.stem
        prompt    = task_data.get("prompt") or task_data.get("task") or ""
        task_type = task_data.get("task_type", "default")

        if not prompt:
            logger.warning("Empty prompt in %s — skipping", task_file.name)
            task_file.rename(task_file.with_suffix(".done"))
            return None

        # Atomic: rename to .processing so other workers skip it
        task_file.rename(task_file.with_suffix(".processing"))
        return task_id, prompt, task_type
    except json.JSONDecodeError as exc:
        logger.error("JSON error in %s: %s", task_file.name, exc)
        task_file.rename(task_file.with_suffix(".error"))
        return None
    except Exception as exc:
        logger.error("Error reading %s: %s", task_file.name, exc)
        return None


def write_result(task_id: str, result, node: str) -> None:
    """Persist execution result for polling by local-chat."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "task_id": task_id,
        "task_type": "autonomous",
        "prompt": result.task,
        "result": result.result,
        "model_used": result.model_used,
        "duration_ms": result.duration_ms,
        "success": result.success,
        "iterations": result.iterations,
        "tool_calls": [
            {
                "tool": tc.tool,
                "input": tc.input,
                "output": tc.output[:500],
                "success": tc.success,
                "duration_ms": tc.duration_ms,
            }
            for tc in result.tool_calls
        ],
        "node": node,
        "completed_at": time.time(),
    }
    out_file = RESULTS_DIR / f"{task_id}.json"
    out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    logger.info("Result written → %s", out_file.name)


def process_task(task_file: Path, inbox_dir: Path, default_model: str) -> None:
    """Pick up and execute one task."""
    parsed = read_task(task_file)
    if not parsed:
        return

    task_id, prompt, _ = parsed
    node = inbox_dir.name
    model = NODE_MODEL_MAP.get(node, default_model)

    logger.info("▶ Task %s | node=%s model=%s", task_id, node, model)
    logger.info("  Prompt: %s", prompt[:120])

    wal_write(task_id, "STARTED")

    executor = AutonomousExecutor(model=model)
    scheduler.acquire()
    try:
        result = executor.execute(task_id=task_id, task=prompt, model=model)
    except Exception as exc:
        scheduler.release()
        wal_write(task_id, "FAILED")
        logger.error("Executor error for task %s: %s", task_id, exc)
        raise
    write_result(task_id, result, node)
    wal_write(task_id, "COMPLETED")
    scheduler.release()

    # Mark original as done (remove .processing)
    proc_file = task_file.parent / (task_file.stem + ".processing")
    if proc_file.exists():
        proc_file.rename(proc_file.with_suffix(".done"))

    status = "✓ DONE" if result.success else "✗ FAILED"
    logger.info(
        "%s | task=%s | tools=%d | iterations=%d | %.0fms",
        status, task_id, len(result.tool_calls), result.iterations, result.duration_ms,
    )


LOCK_FILE = REPO_ROOT / "logs" / "mesh-agent.lock"


def acquire_lock() -> bool:
    """Ensure only ONE daemon instance runs at a time.
    Returns True if lock acquired, False if another instance is already running.
    """
    if LOCK_FILE.exists():
        try:
            old_pid = int(LOCK_FILE.read_text().strip())
            # Check if that process is still alive
            import os as _os
            _os.kill(old_pid, 0)  # signal 0 = existence check
            logger.warning("Another daemon instance running (PID %d) — exiting.", old_pid)
            return False
        except (ProcessLookupError, ValueError):
            # Stale lock — previous daemon died without cleanup
            logger.info("Stale lock from PID in %s — taking over.", LOCK_FILE)
    LOCK_FILE.write_text(str(os.getpid()))
    return True


def release_lock() -> None:
    try:
        if LOCK_FILE.exists() and int(LOCK_FILE.read_text().strip()) == os.getpid():
            LOCK_FILE.unlink()
    except Exception:
        pass


def run(default_model: str = "dof-coder", poll_interval: int = 3) -> None:
    """Main daemon loop — single instance enforced via lockfile."""
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    if not acquire_lock():
        return  # Another instance is running — exit cleanly

    # Create all inbox dirs
    for d in INBOX_DIRS:
        d.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("  DOF Mesh Agent Daemon  (PID %d)", os.getpid())
    logger.info("  Model: %s  |  Poll: %ds", default_model, poll_interval)
    logger.info("  Watching %d inbox dirs", len(INBOX_DIRS))
    logger.info("  Results: %s", RESULTS_DIR)
    logger.info("=" * 60)

    iteration = 0
    recovery_counter = 0
    while not _stop.is_set():
        iteration += 1
        recovery_counter += 1

        # Run orphan recovery once every ~60 seconds
        if recovery_counter >= max(1, 60 // poll_interval):
            recovered = wal_recover_orphans()
            if recovered:
                logger.info("WAL: re-queued %d orphaned task(s)", len(recovered))
            recovery_counter = 0

        for inbox_dir in INBOX_DIRS:
            for task_file in scan_inbox(inbox_dir):
                if _stop.is_set():
                    break
                if not scheduler.can_accept():
                    logger.info("Scheduler at capacity — skipping %s", task_file.name)
                    continue
                process_task(task_file, inbox_dir, default_model)

        if iteration % 5 == 0:
            logger.info("Scheduler status: %s", scheduler.status())

        _stop.wait(poll_interval)

    release_lock()
    logger.info("Mesh Agent Daemon stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DOF Mesh Agent Daemon")
    parser.add_argument("--model", default="dof-coder", help="Default Ollama model")
    parser.add_argument("--poll", type=int, default=3, help="Poll interval in seconds")
    args = parser.parse_args()
    run(default_model=args.model, poll_interval=args.poll)
