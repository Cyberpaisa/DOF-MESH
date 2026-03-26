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
REPO_ROOT    = Path(__file__).resolve().parent.parent
INBOX_ROOT   = REPO_ROOT / "logs" / "mesh" / "inbox"
LOGS_DIR     = REPO_ROOT / "logs" / "mesh"
STATE_FILE   = LOGS_DIR / "planner_state.json"

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

    # ── Feedback loop ────────────────────────────────────────────────────────

    def check_completed_tasks(self) -> Dict[str, Any]:
        """Scan logs/mesh/inbox/*/ for .done files and update planner_state.json."""
        done_files: List[Path] = []
        results: List[Dict[str, Any]] = []

        if INBOX_ROOT.exists():
            for node_dir in sorted(INBOX_ROOT.iterdir()):
                if not node_dir.is_dir():
                    continue
                for done in node_dir.glob("*.done"):
                    done_files.append(done)
                    try:
                        data = json.loads(done.read_text(errors="ignore"))
                        results.append({
                            "file": str(done),
                            "node": node_dir.name,
                            "subject": data.get("subject", ""),
                            "has_result": "result" in data,
                            "result_text": str(data.get("result", "")),
                            "from_planner": done.name.startswith("PLAN-"),
                        })
                    except (json.JSONDecodeError, OSError):
                        results.append({
                            "file": str(done),
                            "node": node_dir.name,
                            "subject": "",
                            "has_result": False,
                            "result_text": "",
                            "from_planner": done.name.startswith("PLAN-"),
                        })

        planner_tasks = [r for r in results if r["from_planner"]]
        total_done = len(done_files)
        planner_done = len(planner_tasks)

        # Use dispatched count from memory or state file, whichever is larger
        dispatched_count = len(self._dispatched_hashes)
        if STATE_FILE.exists():
            try:
                prev = json.loads(STATE_FILE.read_text())
                file_count = len(prev.get("dispatched_hashes", []))
                dispatched_count = max(dispatched_count, file_count,
                                       prev.get("tasks_dispatched", 0))
            except (json.JSONDecodeError, OSError):
                pass
        completion_rate = (planner_done / max(dispatched_count, 1)) * 100

        # Update state file
        state: Dict[str, Any] = {}
        if STATE_FILE.exists():
            try:
                state = json.loads(STATE_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                state = {}

        state["completed_total"] = total_done
        state["completed_planner"] = planner_done
        state["completion_rate_pct"] = round(completion_rate, 1)

        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))

        self._logger.info(
            "Feedback: %d total .done files, %d from planner (%.1f%% completion rate)",
            total_done, planner_done, completion_rate,
        )
        return {
            "total_done": total_done,
            "planner_done": planner_done,
            "completion_rate_pct": completion_rate,
            "details": planner_tasks,
        }

    def verify_task_quality(self, completed: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Basic quality check on completed tasks that have results."""
        if completed is None:
            completed = self.check_completed_tasks()

        details = completed.get("details", [])
        quality_scores: List[Dict[str, Any]] = []

        for task in details:
            result_text = task.get("result_text", "")
            subject = task.get("subject", "")

            non_empty = bool(result_text.strip())
            sufficient_length = len(result_text.strip()) > 50

            # Extract keywords from subject (words > 3 chars, lowered)
            keywords = [w.lower() for w in subject.split() if len(w) > 3]
            result_lower = result_text.lower()
            keyword_hits = sum(1 for kw in keywords if kw in result_lower) if keywords else 0
            keyword_match = (keyword_hits / max(len(keywords), 1)) > 0.2

            score = sum([non_empty, sufficient_length, keyword_match])
            label = {0: "empty", 1: "poor", 2: "acceptable", 3: "good"}[score]

            quality_scores.append({
                "file": task["file"],
                "node": task["node"],
                "subject": subject[:80],
                "score": score,
                "label": label,
                "checks": {
                    "non_empty": non_empty,
                    "sufficient_length": sufficient_length,
                    "keyword_match": keyword_match,
                },
            })

            self._logger.info(
                "  Quality [%s] %s — %s",
                task["node"], subject[:50], label,
            )

        good = sum(1 for q in quality_scores if q["score"] >= 2)
        total = len(quality_scores)
        quality_rate = (good / max(total, 1)) * 100

        self._logger.info(
            "Quality: %d/%d tasks acceptable or better (%.1f%%)",
            good, total, quality_rate,
        )
        return {
            "quality_rate_pct": quality_rate,
            "total_checked": total,
            "good_count": good,
            "scores": quality_scores,
        }

    def report(self) -> Dict[str, Any]:
        """Print current state without dispatching new tasks."""
        completed = self.check_completed_tasks()
        quality = self.verify_task_quality(completed)

        state: Dict[str, Any] = {}
        if STATE_FILE.exists():
            try:
                state = json.loads(STATE_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                pass

        report_data = {
            "dispatched_total": len(self._dispatched_hashes),
            "completed": completed,
            "quality": quality,
            "state_file": state,
        }

        self._logger.info("=== Planner Report ===")
        self._logger.info("Dispatched: %d", len(self._dispatched_hashes))
        self._logger.info("Completed (planner): %d", completed["planner_done"])
        self._logger.info("Completion rate: %.1f%%", completed["completion_rate_pct"])
        self._logger.info("Quality rate: %.1f%%", quality["quality_rate_pct"])
        return report_data

    # ── Run loop ──────────────────────────────────────────────────────────────

    def run(self, interval: int = 3600, max_cycles: int = 0) -> None:
        """Daemon loop: analyze → dispatch → sleep."""
        self._logger.info("🚀 AutonomousPlanner started (interval=%ds)", interval)
        cycle = 0
        while True:
            cycle += 1
            self._logger.info("🔍 Cycle %d — checking completed tasks…", cycle)
            completed = self.check_completed_tasks()
            self.verify_task_quality(completed)

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
    parser.add_argument("--report", action="store_true", help="Print current state without dispatching")
    args = parser.parse_args()

    planner = AutonomousPlanner()
    if args.report:
        data = planner.report()
        print(json.dumps(data, indent=2, default=str))
    elif args.once:
        planner.run(interval=0, max_cycles=1)
    else:
        planner.run(interval=args.interval)


if __name__ == "__main__":
    main()
