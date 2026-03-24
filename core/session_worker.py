"""
DOF Mesh — Session Worker (Autonomous)
=======================================
Cada sesión (Claude, Gemini, GPT, etc.) corre esto UNA vez en su terminal.
Queda en loop eterno: lee inbox → ejecuta tarea → reporta → lee siguiente.

Sin este script: sesiones leen mensajes manualmente.
Con este script: 100% autónomo, zero intervención humana.

Usage (cada sesión corre esto en su terminal):
    python3 core/session_worker.py --node discovered-7c405051
    python3 core/session_worker.py --node antigraviti
    python3 core/session_worker.py --node gemini-2

Loop:
    1. Poll inbox cada POLL_SEC segundos
    2. Lee WO no ejecutadas
    3. Ejecuta tarea via Claude Code SDK (si disponible) o LLM API
    4. Escribe resultado en output_file
    5. Reporta DONE al commander
    6. Repite
"""

import json
import logging
import os
import sys
import time
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger("core.session_worker")

POLL_SEC  = 10
MESH_ROOT = Path("logs/mesh")
INBOX_ROOT = MESH_ROOT / "inbox"
WORKER_LOG = MESH_ROOT / "worker_{node_id}.jsonl"


class SessionWorker:
    """
    Autonomous worker for a mesh node.
    Polls inbox, executes tasks, reports back.
    """

    def __init__(self, node_id: str, model: str = "claude-haiku-4-5-20251001"):
        self.node_id   = node_id
        self.model     = model
        self.inbox     = INBOX_ROOT / node_id
        self.inbox.mkdir(parents=True, exist_ok=True)
        self._running  = False
        self._executed: set = set()
        self._cycle    = 0
        self._log_path = Path(str(WORKER_LOG).replace("{node_id}", node_id))

    # ──────────────────────────────────────────
    # MAIN LOOP
    # ──────────────────────────────────────────

    def run(self):
        self._running = True
        print(f"[{self.node_id}] SessionWorker ONLINE — polling every {POLL_SEC}s")
        print(f"[{self.node_id}] Inbox: {self.inbox}")
        print(f"[{self.node_id}] Ctrl+C to stop")
        print()

        while self._running:
            try:
                self._cycle += 1
                tasks = self._read_pending_tasks()
                if tasks:
                    for task_msg in tasks:
                        self._execute_task(task_msg)
                else:
                    print(f"[{self.node_id}] cycle {self._cycle} — no tasks, waiting...", end="\r")
                time.sleep(POLL_SEC)
            except KeyboardInterrupt:
                print(f"\n[{self.node_id}] Worker stopped.")
                break
            except Exception as e:
                logger.error(f"Worker cycle error: {e}")
                time.sleep(5)

    # ──────────────────────────────────────────
    # TASK READING
    # ──────────────────────────────────────────

    def _read_pending_tasks(self):
        pending = []
        for f in sorted(self.inbox.glob("*.json"), key=lambda x: x.stat().st_mtime):
            if f.name in self._executed:
                continue
            try:
                d = json.loads(f.read_text())
                msg_type = d.get("msg_type", "")
                # Only process work orders
                if msg_type in ("work_order", "orders", "phase6_orders", "cycle_orders") or \
                   "WO-" in d.get("msg_id", "") or \
                   "task" in d.get("content", {}) if isinstance(d.get("content"), dict) else False:
                    pending.append(d)
                    self._executed.add(f.name)
            except Exception:
                self._executed.add(f.name)
        return pending

    # ──────────────────────────────────────────
    # TASK EXECUTION
    # ──────────────────────────────────────────

    def _execute_task(self, msg: dict):
        content = msg.get("content", {})
        if isinstance(content, str):
            task_title = content[:80]
            task_desc  = content
        else:
            task_title = content.get("task", msg.get("msg_id", "unknown"))
            task_desc  = json.dumps(content, indent=2)

        print(f"\n[{self.node_id}] EXECUTING: {task_title[:60]}")
        t0 = time.time()

        result = self._call_llm(task_title, task_desc)
        duration = time.time() - t0

        # Write output if output_file specified
        output_file = content.get("output_file") if isinstance(content, dict) else None
        if output_file and result:
            out = Path(output_file)
            out.parent.mkdir(parents=True, exist_ok=True)
            # Extract code/content from LLM response
            written = self._write_output(out, result)
            if written:
                print(f"[{self.node_id}] ✓ Written: {output_file}")

        # Report DONE to commander
        report_to = content.get("report_done_to", content.get("report_to")) \
                    if isinstance(content, dict) else None
        if not report_to:
            report_to = f"logs/mesh/inbox/commander/{self.node_id}-DONE-{msg.get('msg_id','?')}.json"

        self._report_done(msg, task_title, result, duration, report_to)
        print(f"[{self.node_id}] ✓ DONE ({duration:.1f}s) → reported to commander")

        # Log
        self._log({"task": task_title, "duration": round(duration, 1), "status": "done"})

    def _call_llm(self, title: str, description: str) -> Optional[str]:
        """Call LLM — tries Claude SDK first, then Ollama, then returns None."""

        prompt = f"""You are mesh node {self.node_id} in the DOF autonomous system.

Execute this task completely:

TASK: {title}

DETAILS:
{description}

Produce the complete output. If it's a Python file, return the full file content.
If it's a markdown document, return the full document.
Be thorough and complete."""

        # Try 1: Claude via anthropic SDK
        result = self._try_claude(prompt)
        if result:
            return result

        # Try 2: Ollama local
        result = self._try_ollama(prompt)
        if result:
            return result

        logger.warning(f"[{self.node_id}] All LLM calls failed for task: {title}")
        return None

    def _try_claude(self, prompt: str) -> Optional[str]:
        try:
            import anthropic
            from dotenv import load_dotenv
            load_dotenv()
            client = anthropic.Anthropic()
            r = client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            return r.content[0].text
        except Exception as e:
            logger.debug(f"Claude SDK failed: {e}")
            return None

    def _try_ollama(self, prompt: str) -> Optional[str]:
        try:
            import urllib.request
            body = json.dumps({
                "model": "qwen2.5-coder:14b",
                "prompt": prompt,
                "stream": False
            }).encode()
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=body,
                headers={"Content-Type": "application/json"}
            )
            resp = urllib.request.urlopen(req, timeout=120)
            data = json.loads(resp.read())
            return data.get("response", "")
        except Exception as e:
            logger.debug(f"Ollama failed: {e}")
            return None

    def _write_output(self, path: Path, content: str) -> bool:
        try:
            # Extract code blocks if present
            import re
            code_match = re.search(r'```(?:python|markdown|md)?\n(.*?)```', content, re.DOTALL)
            body = code_match.group(1) if code_match else content
            path.write_text(body)
            return True
        except Exception as e:
            logger.error(f"Write output failed: {e}")
            return False

    def _report_done(self, original_msg: dict, task: str, result: Optional[str], duration: float, report_path: str):
        report = {
            "msg_id": f"{self.node_id}-DONE-{int(time.time())}",
            "from_node": self.node_id,
            "to_node": "commander",
            "msg_type": "task_complete",
            "timestamp": time.time(),
            "read": False,
            "task": task,
            "original_msg_id": original_msg.get("msg_id"),
            "status": "COMPLETED" if result else "FAILED",
            "result_preview": (result or "")[:300],
            "duration_s": round(duration, 1),
        }
        out = Path(report_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))

    def _log(self, data: dict):
        entry = {"ts": time.time(), "node": self.node_id, **data}
        with open(self._log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")


# ═══════════════════════════════════════════════
# CLI — WHAT EACH SESSION RUNS
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING,
                        format="%(asctime)s [%(name)s] %(message)s")

    node_id = None
    model   = "claude-haiku-4-5-20251001"

    for i, arg in enumerate(sys.argv):
        if arg == "--node" and i + 1 < len(sys.argv):
            node_id = sys.argv[i + 1]
        if arg == "--model" and i + 1 < len(sys.argv):
            model = sys.argv[i + 1]

    if not node_id:
        print("Usage: python3 core/session_worker.py --node <node_id> [--model <model>]")
        print()
        print("Examples:")
        print("  python3 core/session_worker.py --node discovered-7c405051")
        print("  python3 core/session_worker.py --node antigraviti")
        print("  python3 core/session_worker.py --node gemini-2")
        sys.exit(1)

    worker = SessionWorker(node_id=node_id, model=model)
    worker.run()
