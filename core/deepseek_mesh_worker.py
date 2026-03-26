#!/usr/bin/env python3
"""
DeepSeek Mesh Worker — Processes pending mesh queue tasks via DeepSeek API.

Polls inbox directories for .json tasks, sends them to DeepSeek chat API,
writes responses back to the mesh, and marks originals as .done.

Usage:
    python3 core/deepseek_mesh_worker.py --once          # Process all pending, then exit
    python3 core/deepseek_mesh_worker.py --daemon         # Poll every 15s forever
    python3 core/deepseek_mesh_worker.py --once --all     # Process ALL inboxes, not just default two
    python3 core/deepseek_mesh_worker.py --once --limit 5 # Process max 5 tasks

No dependencies beyond stdlib (uses urllib).
"""

import argparse
import json
import logging
import os
import ssl
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ── Config ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
INBOX_DIR = BASE_DIR / "logs" / "mesh" / "inbox"
ENV_FILE = BASE_DIR / ".env"

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# Default inboxes to drain (user-specified targets + heavy queues)
DEFAULT_INBOXES = [
    "deepseek-coder",
    "cerebras-llama",
    "local-qwen",
    "gpt-legion",
    "commander",
    "autonomous-planner",
]

RESPONSE_INBOX = "claude-session-1"
POLL_INTERVAL = 15  # seconds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("deepseek-worker")


# ── Env loader ──────────────────────────────────────────
def load_env(path: Path) -> dict:
    """Parse .env file manually (no dotenv dependency)."""
    env = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        env[key] = value
    return env


def get_api_key() -> str:
    """Get DEEPSEEK_API_KEY from environment or .env file."""
    key = os.environ.get("DEEPSEEK_API_KEY")
    if key:
        return key
    env = load_env(ENV_FILE)
    key = env.get("DEEPSEEK_API_KEY")
    if key:
        return key
    log.error("DEEPSEEK_API_KEY not found in environment or %s", ENV_FILE)
    sys.exit(1)


# ── DeepSeek API ────────────────────────────────────────
def call_deepseek(api_key: str, prompt: str, max_tokens: int = 1024) -> dict:
    """Call DeepSeek chat completions API. Returns dict with response or error."""
    payload = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful coding assistant in a multi-agent mesh network. Respond concisely and directly."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    req = urllib.request.Request(DEEPSEEK_URL, data=payload, headers=headers, method="POST")

    # Handle SSL (macOS sometimes needs this)
    ctx = ssl.create_default_context()
    try:
        ctx.load_default_certs()
    except Exception:
        pass

    try:
        with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return {
                "ok": True,
                "content": content,
                "model": data.get("model", DEEPSEEK_MODEL),
                "tokens_in": usage.get("prompt_tokens", 0),
                "tokens_out": usage.get("completion_tokens", 0),
            }
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        return {"ok": False, "error": f"HTTP {e.code}: {body}"}
    except urllib.error.URLError as e:
        return {"ok": False, "error": f"URL error: {e.reason}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Task extraction ─────────────────────────────────────
def extract_prompt(task: dict) -> str:
    """Extract a usable prompt string from various task formats."""
    content = task.get("content", "")

    # If content is a dict, look for common fields
    if isinstance(content, dict):
        # Try payload first (stress-test format)
        if "payload" in content:
            return str(content["payload"])
        # Try content inside content (nested)
        if "content" in content:
            return str(content["content"])
        # Try task field
        if "task" in content:
            return str(content["task"])
        # Fallback: serialize the dict
        return json.dumps(content, indent=2)

    if isinstance(content, str) and content.strip():
        return content

    # Try top-level fields
    for key in ("task", "prompt", "message", "subject", "description"):
        if key in task and task[key]:
            return str(task[key])

    # Last resort
    return json.dumps(task, indent=2)


def extract_task_id(task: dict, filename: str) -> str:
    """Get a task_id from the task or derive from filename."""
    content = task.get("content", {})
    if isinstance(content, dict) and "task_id" in content:
        return str(content["task_id"])
    if "task_id" in task:
        return str(task["task_id"])
    if "msg_id" in task:
        return str(task["msg_id"])
    return Path(filename).stem


# ── Task processing ─────────────────────────────────────
def find_pending_tasks(inboxes: list[str]) -> list[Path]:
    """Find all .json files (not .done) in the specified inboxes."""
    tasks = []
    for inbox_name in inboxes:
        inbox_path = INBOX_DIR / inbox_name
        if not inbox_path.is_dir():
            continue
        for f in sorted(inbox_path.iterdir()):
            if f.suffix == ".json" and not f.name.endswith(".done.json"):
                tasks.append(f)
    return tasks


def process_task(task_path: Path, api_key: str, stats: dict) -> bool:
    """Process a single task file. Returns True on success."""
    try:
        raw = task_path.read_text(encoding="utf-8")
        # Handle concatenated JSON (some files have multiple objects)
        # Take the first valid object
        task = None
        try:
            task = json.loads(raw)
        except json.JSONDecodeError:
            # Try to find first complete JSON object
            depth = 0
            start = None
            for i, c in enumerate(raw):
                if c == '{':
                    if depth == 0:
                        start = i
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0 and start is not None:
                        try:
                            task = json.loads(raw[start:i+1])
                            break
                        except json.JSONDecodeError:
                            start = None

        if task is None:
            log.warning("  Skip (invalid JSON): %s", task_path.name)
            stats["skipped"] += 1
            return False

        prompt = extract_prompt(task)
        task_id = extract_task_id(task, task_path.name)
        from_node = task.get("from_node", task.get("from", "unknown"))
        to_node = task.get("to_node", task.get("to", task_path.parent.name))

        # Skip empty or trivially short prompts
        if len(prompt.strip()) < 3:
            log.warning("  Skip (empty prompt): %s", task_path.name)
            stats["skipped"] += 1
            return False

        log.info("  → Calling DeepSeek for %s (%.50s...)", task_id, prompt.replace('\n', ' '))

        t0 = time.time()
        result = call_deepseek(api_key, prompt)
        elapsed = time.time() - t0

        if not result["ok"]:
            log.error("  ✗ API error for %s: %s", task_id, result["error"])
            stats["errors"] += 1
            return False

        # Write response to claude-session-1 inbox
        response_dir = INBOX_DIR / RESPONSE_INBOX
        response_dir.mkdir(parents=True, exist_ok=True)

        response_msg = {
            "msg_id": f"ds-{task_id}",
            "from_node": "deepseek-worker",
            "to_node": RESPONSE_INBOX,
            "content": result["content"],
            "msg_type": "response",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "original_task": task_id,
                "original_inbox": to_node,
                "original_from": from_node,
                "model": result["model"],
                "tokens_in": result["tokens_in"],
                "tokens_out": result["tokens_out"],
                "elapsed_s": round(elapsed, 2),
            },
            "read": False,
        }

        resp_path = response_dir / f"RESP-deepseek-{task_id}.json"
        resp_path.write_text(json.dumps(response_msg, indent=2, ensure_ascii=False), encoding="utf-8")

        # Mark original as done
        done_path = task_path.with_suffix(".done")
        task_path.rename(done_path)

        stats["processed"] += 1
        stats["tokens_in"] += result["tokens_in"]
        stats["tokens_out"] += result["tokens_out"]

        log.info("  ✓ Done %s (%.1fs, %d→%d tok)", task_id, elapsed, result["tokens_in"], result["tokens_out"])
        return True

    except Exception as e:
        log.error("  ✗ Exception processing %s: %s", task_path.name, e)
        stats["errors"] += 1
        return False


def run_once(inboxes: list[str], api_key: str, limit: int = 0) -> dict:
    """Process all pending tasks once. Returns stats dict."""
    stats = {"processed": 0, "errors": 0, "skipped": 0, "tokens_in": 0, "tokens_out": 0}

    tasks = find_pending_tasks(inboxes)
    total = len(tasks)

    if total == 0:
        log.info("No pending tasks in: %s", ", ".join(inboxes))
        return stats

    if limit > 0:
        tasks = tasks[:limit]

    log.info("Found %d pending tasks (processing %d) in: %s", total, len(tasks), ", ".join(inboxes))

    for i, task_path in enumerate(tasks, 1):
        log.info("[%d/%d] %s/%s", i, len(tasks), task_path.parent.name, task_path.name)
        process_task(task_path, api_key, stats)

        # Polite rate limiting — DeepSeek free tier
        if i < len(tasks):
            time.sleep(0.5)

    log.info(
        "Done: %d processed, %d errors, %d skipped, %d/%d tokens in/out",
        stats["processed"], stats["errors"], stats["skipped"],
        stats["tokens_in"], stats["tokens_out"],
    )
    return stats


def run_daemon(inboxes: list[str], api_key: str, interval: int = POLL_INTERVAL):
    """Poll for tasks forever."""
    log.info("Starting daemon mode (poll every %ds)...", interval)
    log.info("Watching inboxes: %s", ", ".join(inboxes))
    log.info("Responses go to: %s", RESPONSE_INBOX)
    log.info("Press Ctrl+C to stop.\n")

    cycle = 0
    while True:
        cycle += 1
        tasks = find_pending_tasks(inboxes)
        if tasks:
            log.info("── Cycle %d: %d pending tasks ──", cycle, len(tasks))
            run_once(inboxes, api_key)
        else:
            if cycle % 20 == 1:  # Log silence every ~5 min
                log.info("── Cycle %d: no pending tasks ──", cycle)
        time.sleep(interval)


# ── CLI ─────────────────────────────────────────────────
def get_all_inboxes() -> list[str]:
    """Get all inbox directory names."""
    if not INBOX_DIR.is_dir():
        return []
    return sorted(
        d.name for d in INBOX_DIR.iterdir()
        if d.is_dir() and any(f.suffix == ".json" for f in d.iterdir())
    )


def main():
    """CLI entry point — parse arguments and run once, daemon, or status check."""
    parser = argparse.ArgumentParser(description="DeepSeek Mesh Worker — process mesh queue tasks via DeepSeek API")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true", help="Process all pending tasks once, then exit")
    mode.add_argument("--daemon", action="store_true", help="Poll every 15s forever")
    mode.add_argument("--status", action="store_true", help="Show pending task counts and exit")

    parser.add_argument("--all", action="store_true", help="Process ALL inboxes, not just default targets")
    parser.add_argument("--limit", type=int, default=0, help="Max tasks to process (0 = unlimited)")
    parser.add_argument("--inbox", action="append", help="Add specific inbox(es) to process")
    parser.add_argument("--interval", type=int, default=POLL_INTERVAL, help="Daemon poll interval in seconds")
    parser.add_argument("--max-tokens", type=int, default=1024, help="Max response tokens per task")
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine inboxes
    if args.all:
        inboxes = get_all_inboxes()
    elif args.inbox:
        inboxes = args.inbox
    else:
        inboxes = DEFAULT_INBOXES

    if args.status:
        total = 0
        for name in sorted(get_all_inboxes()):
            path = INBOX_DIR / name
            count = sum(1 for f in path.iterdir() if f.suffix == ".json")
            done = sum(1 for f in path.iterdir() if f.name.endswith(".done"))
            if count > 0 or done > 0:
                print(f"  {name:30s}  {count:4d} pending  {done:4d} done")
            total += count
        print(f"\n  TOTAL: {total} pending tasks")
        return

    api_key = get_api_key()

    # Quick validation
    log.info("Validating DeepSeek API key...")
    test = call_deepseek(api_key, "ping", max_tokens=5)
    if not test["ok"]:
        log.error("API validation failed: %s", test["error"])
        sys.exit(1)
    log.info("API key valid. Model: %s\n", test.get("model", "?"))

    if args.once:
        stats = run_once(inboxes, api_key, limit=args.limit)
        sys.exit(0 if stats["errors"] == 0 else 1)
    elif args.daemon:
        try:
            run_daemon(inboxes, api_key, interval=args.interval)
        except KeyboardInterrupt:
            log.info("\nDaemon stopped by user.")


if __name__ == "__main__":
    main()
