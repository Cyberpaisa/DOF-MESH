"""
Autonomous Planner — DOF Mesh.

Scans the repo periodically, detects work items (missing tests, TODOs,
broken imports, missing docs), and dispatches tasks to free providers
via the mesh inbox protocol.

Usage:
  python3 core/autonomous_planner.py --once
  python3 core/autonomous_planner.py --daemon
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT  = Path(__file__).resolve().parent.parent
INBOX_ROOT = REPO_ROOT / "logs" / "mesh" / "inbox"
LOGS_DIR   = REPO_ROOT / "logs" / "mesh"

logger = logging.getLogger("core.autonomous_planner")

# ── Exceptions ────────────────────────────────────────────────────────────────

class PlanningError(Exception):
    """Raised when the planner receives invalid input."""


# ── Enums & dataclasses ───────────────────────────────────────────────────────

class PlanStatus(Enum):
    PENDING   = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    CRITICAL = 0
    HIGH     = 1
    MEDIUM   = 2
    LOW      = 3


@dataclass
class TaskNode:
    id: str
    description: str
    priority: TaskPriority
    dependencies: List[str] = field(default_factory=list)
    estimated_duration: float = 0.0
    status: PlanStatus = PlanStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    children: List["TaskNode"] = field(default_factory=list)
    parent_id: Optional[str] = None

    def __post_init__(self):
        if self.estimated_duration < 0:
            raise ValueError("Estimated duration cannot be negative")
        if not self.id:
            raise ValueError("Task ID cannot be empty")


@dataclass
class PlanningContext:
    goal: str
    constraints: List[str] = field(default_factory=list)
    resources: Dict[str, Any] = field(default_factory=dict)
    max_depth: int = 10
    timeout_seconds: float = 300.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanItem:
    task_type: str   # "code", "tests", "docs"
    subject: str
    detail: str
    target_node: str
    priority: int = 2


# ── Task router: type → preferred free providers ──────────────────────────────
TASK_ROUTER: Dict[str, List[str]] = {
    "code":  ["deepseek-coder", "sambanova-llama", "nvidia-nim"],
    "tests": ["sambanova-llama", "cerebras-llama", "groq-llama"],
    "docs":  ["cerebras-llama", "gemini-flash", "groq-llama"],
}


# ── Main class ────────────────────────────────────────────────────────────────

class AutonomousPlanner:
    """
    DOF Mesh autonomous planner.

    Singleton that scans the repo, generates PlanItems, and dispatches
    them to free-provider inboxes.  Also exposes a generic `plan()` method
    for programmatic use.
    """

    _instance = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._logger = logging.getLogger(__name__)
            self._plan_history: List[Dict[str, Any]] = []
            self._dispatched_hashes: set = set()
            self._initialized = True

    # ── Generic plan() method (used by tests) ─────────────────────────────────

    def plan(self, tasks: Any) -> List[Dict[str, Any]]:
        """
        Accept a non-empty list of tasks and return a plan list.

        Raises PlanningError for invalid input (None, empty list, non-list).
        """
        if tasks is None:
            raise PlanningError("tasks cannot be None")
        if not isinstance(tasks, list):
            raise PlanningError(f"tasks must be a list, got {type(tasks).__name__}")
        if len(tasks) == 0:
            raise PlanningError("tasks list cannot be empty")

        result = []
        for i, t in enumerate(tasks):
            result.append({
                "step": i + 1,
                "task": t,
                "status": PlanStatus.PENDING.value,
            })
        return result

    # ── Repo scanning ──────────────────────────────────────────────────────────

    def analyze(self) -> List[PlanItem]:
        """Scan repo and return list of PlanItems to dispatch."""
        items: List[PlanItem] = []
        items.extend(self._find_modules_without_tests())
        items.extend(self._find_todos_in_code())
        items.extend(self._find_modules_without_docs())
        return items

    def _find_modules_without_tests(self) -> List[PlanItem]:
        core_dir = REPO_ROOT / "core"
        tests_dir = REPO_ROOT / "tests"
        items = []
        for py in sorted(core_dir.glob("*.py")):
            name = py.stem
            if name.startswith("_"):
                continue
            test_file = tests_dir / f"test_{name}.py"
            if not test_file.exists():
                items.append(PlanItem(
                    task_type="tests",
                    subject=f"Generate tests for core/{name}.py",
                    detail=(
                        f"Write a complete unittest test suite for core/{name}.py. "
                        f"Cover all public methods. Save to tests/test_{name}.py."
                    ),
                    target_node=TASK_ROUTER["tests"][0],
                    priority=2,
                ))
        return items

    def _find_todos_in_code(self) -> List[PlanItem]:
        items = []
        for py in sorted((REPO_ROOT / "core").glob("*.py")):
            text = py.read_text(errors="ignore")
            if "TODO" in text or "FIXME" in text:
                items.append(PlanItem(
                    task_type="code",
                    subject=f"Resolve TODOs in core/{py.name}",
                    detail=(
                        f"Find all TODO/FIXME comments in core/{py.name} and implement them. "
                        f"Write the completed file back."
                    ),
                    target_node=TASK_ROUTER["code"][0],
                    priority=3,
                ))
        return items

    def _find_modules_without_docs(self) -> List[PlanItem]:
        docs_dir = REPO_ROOT / "docs"
        items = []
        for py in sorted((REPO_ROOT / "core").glob("mesh_*.py")):
            doc_file = docs_dir / f"{py.stem.upper()}.md"
            if not doc_file.exists():
                items.append(PlanItem(
                    task_type="docs",
                    subject=f"Document {py.name}",
                    detail=(
                        f"Write technical documentation for core/{py.name} in Markdown. "
                        f"Include: purpose, API, usage examples. Save to docs/{py.stem.upper()}.md"
                    ),
                    target_node=TASK_ROUTER["docs"][0],
                    priority=3,
                ))
        return items

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def _dispatch(self, item: PlanItem) -> bool:
        """Write a task JSON to the target node's inbox. Returns True if dispatched."""
        key = f"{item.task_type}:{item.subject}"
        if key in self._dispatched_hashes:
            return False
        self._dispatched_hashes.add(key)

        msg_id = str(uuid.uuid4())
        task = {
            "msg_id":   msg_id,
            "from":     "autonomous-planner",
            "to":       item.target_node,
            "ts":       time.time(),
            "type":     "task",
            "subject":  item.subject,
            "task":     item.detail,
            "priority": item.priority,
        }
        inbox = INBOX_ROOT / item.target_node
        inbox.mkdir(parents=True, exist_ok=True)
        out = inbox / f"PLAN-{msg_id[:8]}.json"
        out.write_text(json.dumps(task, ensure_ascii=False, indent=2))
        self._logger.info("  📤 Dispatched → [%s] %s", item.target_node, item.subject[:60])
        return True

    # ── Run loop ──────────────────────────────────────────────────────────────

    def run(self, interval: int = 3600, max_cycles: int = 0) -> None:
        """Daemon loop: analyze → dispatch → sleep."""
        self._logger.info("🚀 AutonomousPlanner started (interval=%ds)", interval)
        cycle = 0
        while True:
            cycle += 1
            self._logger.info("🔍 Cycle %d — scanning repo…", cycle)
            items = self.analyze()
            dispatched = sum(1 for item in items if self._dispatch(item))
            self._logger.info("✔ Cycle %d — %d new tasks dispatched", cycle, dispatched)

            if max_cycles and cycle >= max_cycles:
                break
            time.sleep(interval)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] planner — %(message)s",
        datefmt="%H:%M:%S",
    )
    parser = argparse.ArgumentParser(description="DOF Mesh Autonomous Planner")
    parser.add_argument("--once",   action="store_true", help="Run one cycle and exit")
    parser.add_argument("--daemon", action="store_true", help="Run forever (default interval 3600s)")
    parser.add_argument("--interval", type=int, default=3600)
    args = parser.parse_args()

    planner = AutonomousPlanner()
    if args.once:
        planner.run(interval=0, max_cycles=1)
    else:
        planner.run(interval=args.interval)


if __name__ == "__main__":
    main()
