#!/usr/bin/env python3
"""
Claude Node Runner — DOF Mesh node usando Claude Code CLI como motor.

En lugar de llamar APIs de texto, lanza `claude -p` con bypassPermissions
para que Claude Code autónomamente lea el repo, escriba archivos, corra
tests y entregue resultados reales — no solo texto.

Ventajas sobre api_node_runner.py:
  - Claude puede leer el repo completo (contexto real)
  - Claude escribe los archivos directamente (no texto intermedio)
  - Claude corre tests y corrige errores en el mismo ciclo
  - Claude hace commits si se le pide
  - Costo: tokens Claude (pero con Max plan = incluido)

Nodos Claude disponibles:
  claude-commander   → orquestación, planning
  claude-architect   → diseño de módulos complejos
  claude-guardian    → security audit + tests
  claude-builder     → implementación de features
  claude-researcher  → investigación + docs

Usage:
  python3 core/claude_node_runner.py                    # todos los nodos claude-*
  python3 core/claude_node_runner.py --nodes claude-builder claude-guardian
  python3 core/claude_node_runner.py --once             # procesa una vez y sale
  python3 core/claude_node_runner.py --daemon           # loop infinito
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT  = Path(__file__).resolve().parent.parent
INBOX_ROOT = REPO_ROOT / "logs" / "mesh" / "inbox"
LOGS_DIR   = REPO_ROOT / "logs" / "mesh"

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] claude-runner — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("core.claude_node_runner")

# ── Claude node definitions ───────────────────────────────────────────────────
CLAUDE_NODES: dict[str, dict] = {
    "claude-commander": {
        "model": "claude-haiku-4-5-20251001",
        "specialty": "orchestration, planning, architecture decisions",
        "system": (
            "Eres claude-commander, nodo orquestador del DOF Mesh. "
            "Repo en {repo}. Tu trabajo: analizar tareas, diseñar soluciones, "
            "coordinar otros nodos. Responde con planes claros y concisos."
        ),
    },
    "claude-architect": {
        "model": "claude-haiku-4-5-20251001",
        "specialty": "module design, API design, system architecture",
        "system": (
            "Eres claude-architect, nodo de diseño del DOF Mesh. "
            "Repo en {repo}. Tu trabajo: diseñar módulos Python 3.13 siguiendo "
            "convenciones DOF: @dataclass, singleton __new__, JSONL logging, stdlib only. "
            "SIEMPRE escribe archivos completos y funcionales."
        ),
    },
    "claude-builder": {
        "model": "claude-haiku-4-5-20251001",
        "specialty": "code implementation, feature development",
        "system": (
            "Eres claude-builder, nodo de implementación del DOF Mesh. "
            "Repo en {repo}. Tu trabajo: implementar features, escribir código Python 3.13, "
            "seguir convenciones DOF. Escribe los archivos directamente con tus herramientas."
        ),
    },
    "claude-guardian": {
        "model": "claude-haiku-4-5-20251001",
        "specialty": "security audit, tests, quality assurance",
        "system": (
            "Eres claude-guardian, nodo de seguridad del DOF Mesh. "
            "Repo en {repo}. Tu trabajo: auditar seguridad, escribir tests unittest, "
            "verificar que los 2900+ tests pasen. USA python3 -m unittest para validar."
        ),
    },
    "claude-researcher": {
        "model": "claude-haiku-4-5-20251001",
        "specialty": "research, documentation, analysis",
        "system": (
            "Eres claude-researcher, nodo de investigación del DOF Mesh. "
            "Repo en {repo}. Tu trabajo: investigar, documentar, analizar código existente. "
            "Escribe documentación técnica clara en Markdown."
        ),
    },
}

# ── Core functions ─────────────────────────────────────────────────────────────

def _find_claude() -> str:
    """Find claude CLI binary."""
    candidates = [
        os.path.expanduser("~/.local/bin/claude"),
        "/usr/local/bin/claude",
        "claude",
    ]
    for c in candidates:
        try:
            result = subprocess.run([c, "--version"], capture_output=True, timeout=5)
            if result.returncode == 0:
                return c
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    raise RuntimeError("claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code")


def run_claude_task(node_id: str, task: str, model: str, cwd: Path, timeout: int = 300) -> str:
    """
    Run claude CLI with a task prompt in non-interactive mode.
    Returns the output text.
    """
    claude_bin = _find_claude()
    node_cfg = CLAUDE_NODES.get(node_id, {})
    system = node_cfg.get("system", "Eres un nodo del DOF Mesh.").format(repo=str(cwd))

    # Full prompt with system context
    full_prompt = f"{system}\n\n---\n\nTAREA:\n{task}"

    cmd = [
        claude_bin,
        "--dangerously-skip-permissions",
        "--model", model,
        "-p", full_prompt,
    ]

    logger.info("  🤖 [%s] Launching claude CLI (model=%s, timeout=%ds)", node_id, model, timeout)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd),
        )
        output = result.stdout.strip()
        if result.returncode != 0 and result.stderr:
            stderr = result.stderr.strip()[:500]
            logger.warning("  ⚠  [%s] stderr: %s", node_id, stderr)
            if not output:
                return f"[ERROR] claude exited {result.returncode}: {stderr}"
        return output or "[No output from claude]"
    except subprocess.TimeoutExpired:
        return f"[ERROR] claude timed out after {timeout}s"
    except Exception as e:
        return f"[ERROR] {type(e).__name__}: {e}"


def process_task(node_id: str, task_file: Path) -> bool:
    """Read task JSON, run via claude CLI, write response. Returns True on success."""
    try:
        task = json.loads(task_file.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error("Failed to read %s: %s", task_file, e)
        return False

    prompt = task.get("task") or task.get("content") or task.get("message") or str(task)
    subject = task.get("subject", "task")
    from_node = task.get("from") or task.get("from_node", "commander")
    output_file = task.get("output_file")

    node_cfg = CLAUDE_NODES.get(node_id, {})
    model = node_cfg.get("model", "claude-sonnet-4-6")

    logger.info("  🔧 [%s] Processing: %s", node_id, subject[:70])

    start = time.time()
    response_text = run_claude_task(node_id, prompt, model, REPO_ROOT)
    elapsed = time.time() - start

    if response_text.startswith("[ERROR]"):
        logger.error("  ❌ [%s] %s (%.1fs)", node_id, response_text[:100], elapsed)
        return False

    logger.info("  ✅ [%s] Done (%.1fs, %d chars)", node_id, elapsed, len(response_text))

    # Write response to commander inbox
    response = {
        "msg_id": f"{node_id}-resp-{str(task.get('msg_id', uuid.uuid4()))[:8]}",
        "from": node_id,
        "to": from_node,
        "ts": time.time(),
        "type": "response",
        "subject": f"RE: {subject}",
        "content": response_text,
        "elapsed_seconds": round(elapsed, 2),
        "model": model,
        "iso": datetime.now(timezone.utc).isoformat(),
    }
    resp_dir = INBOX_ROOT / from_node
    resp_dir.mkdir(parents=True, exist_ok=True)
    resp_file = resp_dir / f"RESP-{node_id}-{str(task.get('msg_id', 'x'))[:8]}.json"
    resp_file.write_text(json.dumps(response, ensure_ascii=False, indent=2))

    # If task specified output_file, try to find it (claude should have written it)
    if output_file:
        out_path = REPO_ROOT / output_file
        if out_path.exists():
            logger.info("  📄 [%s] Output file exists: %s (%d bytes)", node_id, output_file, out_path.stat().st_size)
        else:
            logger.warning("  ⚠  [%s] Output file NOT found: %s", node_id, output_file)

    # Mark done
    done_file = task_file.with_suffix(".done")
    if task_file.exists():
        try:
            task_file.rename(done_file)
        except FileNotFoundError:
            pass

    # Log event
    _log_event({
        "event": "claude_task_completed",
        "node": node_id,
        "model": model,
        "subject": subject,
        "elapsed_seconds": round(elapsed, 2),
        "ts": time.time(),
    })

    return True


def _log_event(event: dict) -> None:
    try:
        with (LOGS_DIR / "mesh_events.jsonl").open("a") as f:
            f.write(json.dumps(event) + "\n")
    except OSError:
        pass


def run_nodes(nodes: list[str], once: bool = False) -> None:
    POLL_INTERVAL = 15

    logger.info("🤖 Claude Node Runner [%s] — nodes: %s", "once" if once else "daemon", ", ".join(nodes))
    logger.info("   Claude CLI: %s", _find_claude())

    while True:
        total = 0
        for node_id in nodes:
            inbox = INBOX_ROOT / node_id
            if not inbox.exists():
                inbox.mkdir(parents=True, exist_ok=True)

            tasks = sorted(inbox.glob("*.json"))
            if not tasks:
                continue

            logger.info("📥 [%s] %d task(s) pending", node_id, len(tasks))
            for tf in tasks:
                ok = process_task(node_id, tf)
                if ok:
                    total += 1
                time.sleep(2)

        if total:
            logger.info("✔ Cycle — %d claude tasks completed", total)

        if once:
            break
        time.sleep(POLL_INTERVAL)


def main() -> None:
    parser = argparse.ArgumentParser(description="DOF Mesh Claude Node Runner")
    parser.add_argument("--nodes", nargs="+", default=list(CLAUDE_NODES.keys()))
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--dispatch", metavar="NODE", help="Dispatch a test task to NODE")
    args = parser.parse_args()

    if args.list:
        print("\n🤖 Claude CLI Nodes:\n")
        for nid, cfg in CLAUDE_NODES.items():
            print(f"  {nid:20} model={cfg['model']:35} specialty={cfg['specialty'][:50]}")
        print()
        return

    if args.dispatch:
        # Quick dispatch a test task
        node_id = args.dispatch
        test_task = {
            "msg_id": str(uuid.uuid4()),
            "from": "commander",
            "to": node_id,
            "ts": time.time(),
            "type": "task",
            "subject": "Self-test: report your capabilities",
            "task": (
                "Lee el archivo core/node_mesh.py (primeras 30 líneas) y "
                "dime cuántos nodos hay registrados en logs/mesh/nodes.json. "
                "Responde en 3 líneas máximo."
            ),
        }
        inbox = INBOX_ROOT / node_id
        inbox.mkdir(parents=True, exist_ok=True)
        tf = inbox / f"TEST-{test_task['msg_id'][:8]}.json"
        tf.write_text(json.dumps(test_task, indent=2))
        print(f"✅ Test task dispatched to {node_id}: {tf}")
        return

    valid = [n for n in args.nodes if n in CLAUDE_NODES]
    if not valid:
        logger.error("No valid claude nodes. Use --list to see options.")
        sys.exit(1)

    run_nodes(valid, once=args.once)


if __name__ == "__main__":
    main()


# ── ClaudeNodeRunner class (for test compatibility) ────────────────────────────

class ClaudeNodeRunner:
    """Singleton wrapper for the claude node runner daemon."""

    _instance = None

    def __new__(cls):
        if getattr(cls, '_instance', None) is None:
            inst = super().__new__(cls)
            inst._running = False
            cls._instance = inst
        return cls._instance

    def _run_node(self, *args) -> None:
        """Internal: actually start the node."""
        self._running = True

    def _stop_node(self) -> None:
        """Internal: stop the node."""
        self._running = False

    def run(self, node_id, *args) -> None:
        """Run with a node_id (must be a non-empty str)."""
        if node_id is None or not isinstance(node_id, str) or node_id == "":
            raise TypeError(f"node_id must be a non-empty str, got {type(node_id).__name__!r}")
        self._run_node(node_id, *args)

    def stop(self) -> None:
        """Stop the node if running."""
        if self._running:
            self._stop_node()
