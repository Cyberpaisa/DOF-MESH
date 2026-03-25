"""
LocalOrchestrator — Zero-token local AGI orchestration layer.

Replaces claude_commander.py dependency on Claude SDK with local Ollama routing.
Uses the same mesh inbox protocol — 100% compatible with NodeMesh and SessionWorker.

Architecture:
    LocalOrchestrator (singleton)
        ├── Route task → best local model (deepseek-r1:14b / qwen2.5-coder:14b)
        ├── Decompose complex objectives → subtask list
        ├── Dispatch subtasks → mesh inbox (compatible with NodeMesh protocol)
        └── Aggregate results → OrchestratorResult

Model Strategy:
    reasoning / planning / analysis → deepseek-r1:14b  (9GB, ~80 tok/s, no thinking)
    code / implementation / tests   → qwen2.5-coder:14b (9GB, ~90 tok/s)
    fast / classification / routing → qwen2.5-coder:14b (already loaded)

Usage:
    from core.local_orchestrator import LocalOrchestrator

    orch = LocalOrchestrator()
    result = orch.run("Design a secure auth system")
    print(result.output)
"""

import os
import json
import time
import logging
import requests
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("core.local_orchestrator")

_BASE_DIR = Path(__file__).parent.parent
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# Model assignments — updated when deepseek-r1:14b is downloaded
LOCAL_MODELS = {
    "reasoning":    os.getenv("LOCAL_MODEL_REASONING",    "deepseek-r1:14b"),
    "code":         os.getenv("LOCAL_MODEL_CODE",         "qwen2.5-coder:14b"),
    "orchestration":os.getenv("LOCAL_MODEL_ORCHESTRATOR", "deepseek-r1:14b"),
    "fast":         os.getenv("LOCAL_MODEL_FAST",         "qwen2.5-coder:14b"),
    "default":      os.getenv("LOCAL_MODEL_DEFAULT",      "qwen2.5-coder:14b"),
}

# Task type → model routing rules
ROUTING_RULES = [
    (["reason", "plan", "analyze", "design", "architect", "strategize", "evaluate",
      "assess", "research", "decide", "orchestrat"], "reasoning"),
    (["code", "implement", "test", "debug", "fix", "refactor", "write function",
      "write class", "python", "javascript", "typescript", "sql"], "code"),
    (["classify", "route", "categorize", "label", "quick", "fast", "simple"], "fast"),
]


@dataclass
class OrchestratorResult:
    """Result from a local orchestrator run."""
    task_id: str
    objective: str
    model_used: str
    output: str
    subtasks: list = field(default_factory=list)
    dispatched_nodes: list = field(default_factory=list)
    duration_ms: float = 0.0
    success: bool = False
    error: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class OrchestratorStats:
    """Cumulative stats for this orchestrator instance."""
    tasks_run: int = 0
    tasks_succeeded: int = 0
    tasks_failed: int = 0
    total_duration_ms: float = 0.0
    models_used: dict = field(default_factory=dict)


class LocalOrchestrator:
    """
    Singleton local AGI orchestrator — zero Claude API tokens.

    Resolves tasks using Ollama local models and dispatches subtasks
    to the NodeMesh inbox protocol for multi-agent collaboration.
    """

    _instance: Optional["LocalOrchestrator"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> "LocalOrchestrator":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._stats = OrchestratorStats()
        self._inbox_root = _BASE_DIR / "logs" / "mesh" / "inbox"
        self._inbox_root.mkdir(parents=True, exist_ok=True)
        logger.info("LocalOrchestrator initialized (zero-token mode)")

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self, objective: str, task_type: str = "auto",
            decompose: bool = True) -> OrchestratorResult:
        """
        Execute an objective using local models.

        Args:
            objective: Natural language task description.
            task_type: Force a model type ('reasoning'/'code'/'fast') or 'auto'.
            decompose: If True, break complex objectives into subtasks first.

        Returns:
            OrchestratorResult with output and metadata.
        """
        task_id = f"LOCAL-{int(time.time() * 1000)}"
        t0 = time.time()

        if task_type == "auto":
            task_type = self._route_task(objective)

        model = self._select_model(task_type)
        available = self.get_available_models()

        # Fallback to any available model if preferred is not installed
        if model not in available and available:
            model = available[0]
            logger.info(f"Preferred model unavailable, using fallback: {model}")
        elif not available:
            return OrchestratorResult(
                task_id=task_id,
                objective=objective,
                model_used="none",
                output="",
                success=False,
                error="No local models available — install Ollama and pull a model",
                duration_ms=(time.time() - t0) * 1000,
            )

        subtasks = []
        dispatched = []

        if decompose and len(objective) > 120:
            subtasks = self._decompose(objective, model)
            if subtasks:
                dispatched = self._dispatch_subtasks(task_id, subtasks)

        output = self._call_ollama(model, objective)

        duration_ms = (time.time() - t0) * 1000
        success = bool(output)

        self._update_stats(model, duration_ms, success)

        return OrchestratorResult(
            task_id=task_id,
            objective=objective,
            model_used=model,
            output=output,
            subtasks=subtasks,
            dispatched_nodes=dispatched,
            duration_ms=duration_ms,
            success=success,
            error="" if success else "Model returned empty response",
        )

    def route(self, task: str) -> str:
        """Return the model name that would handle this task (dry-run)."""
        task_type = self._route_task(task)
        return self._select_model(task_type)

    def get_available_models(self) -> list[str]:
        """Return list of Ollama models currently installed."""
        try:
            r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            if r.status_code == 200:
                models = r.json().get("models", [])
                return [m["name"] for m in models]
        except Exception:
            pass
        return []

    def is_model_available(self, model_name: str) -> bool:
        """Check if a specific model is available in Ollama."""
        return model_name in self.get_available_models()

    def get_stats(self) -> dict:
        """Return current orchestrator statistics."""
        return {
            "tasks_run": self._stats.tasks_run,
            "tasks_succeeded": self._stats.tasks_succeeded,
            "tasks_failed": self._stats.tasks_failed,
            "success_rate": (
                self._stats.tasks_succeeded / self._stats.tasks_run
                if self._stats.tasks_run > 0 else 0.0
            ),
            "avg_duration_ms": (
                self._stats.total_duration_ms / self._stats.tasks_run
                if self._stats.tasks_run > 0 else 0.0
            ),
            "models_used": dict(self._stats.models_used),
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _route_task(self, objective: str) -> str:
        """Map objective text to model task type using keyword rules."""
        obj_lower = objective.lower()
        for keywords, task_type in ROUTING_RULES:
            if any(kw in obj_lower for kw in keywords):
                return task_type
        return "default"

    def _select_model(self, task_type: str) -> str:
        """Select Ollama model name for given task type."""
        return LOCAL_MODELS.get(task_type, LOCAL_MODELS["default"])

    def _call_ollama(self, model: str, prompt: str,
                     system: str = "", temperature: float = 0.7) -> str:
        """Call Ollama generate API. Returns text or '' on failure."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 4096,
            },
        }
        if system:
            payload["system"] = system

        try:
            r = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json=payload,
                timeout=180,
            )
            if r.status_code == 200:
                text = r.json().get("response", "").strip()
                # Strip any thinking tags (deepseek-r1 style)
                import re
                text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
                return text
            else:
                logger.warning(f"Ollama {model} returned {r.status_code}")
                return ""
        except requests.exceptions.ConnectionError:
            logger.warning("Ollama not running — start with: ollama serve")
            return ""
        except Exception as exc:
            logger.error(f"Ollama call failed: {exc}")
            return ""

    def _decompose(self, objective: str, model: str) -> list[str]:
        """Ask the model to break the objective into 3-5 subtasks."""
        prompt = (
            f"Break this objective into 3-5 concrete subtasks. "
            f"Return ONLY a JSON array of strings, nothing else.\n\n"
            f"Objective: {objective}"
        )
        raw = self._call_ollama(model, prompt, temperature=0.3)
        if not raw:
            return []
        try:
            import re
            match = re.search(r'\[.*?\]', raw, re.DOTALL)
            if match:
                return json.loads(match.group())[:5]
        except Exception:
            pass
        # Fallback: split by lines if JSON parsing fails
        lines = [l.strip().lstrip("0123456789.-) ") for l in raw.split("\n") if l.strip()]
        return [l for l in lines if len(l) > 10][:5]

    def _dispatch_subtasks(self, task_id: str, subtasks: list[str]) -> list[str]:
        """Write subtasks to mesh inboxes for specialized nodes."""
        node_map = {
            0: "architect",
            1: "researcher",
            2: "guardian",
            3: "verifier",
            4: "narrator",
        }
        dispatched = []
        for i, subtask in enumerate(subtasks[:5]):
            node_id = node_map.get(i, "architect")
            inbox = self._inbox_root / node_id
            inbox.mkdir(parents=True, exist_ok=True)
            msg_file = inbox / f"{task_id}-{i}.json"
            msg = {
                "msg_id": f"{task_id}-{i}",
                "from_node": "local-orchestrator",
                "to_node": node_id,
                "content": {"task": subtask, "parent_task_id": task_id},
                "msg_type": "subtask",
                "timestamp": time.time(),
            }
            try:
                msg_file.write_text(json.dumps(msg, indent=2), encoding="utf-8")
                dispatched.append(node_id)
                logger.debug(f"Dispatched subtask {i} → {node_id}")
            except Exception as exc:
                logger.warning(f"Failed to dispatch to {node_id}: {exc}")
        return dispatched

    def _update_stats(self, model: str, duration_ms: float, success: bool) -> None:
        self._stats.tasks_run += 1
        if success:
            self._stats.tasks_succeeded += 1
        else:
            self._stats.tasks_failed += 1
        self._stats.total_duration_ms += duration_ms
        self._stats.models_used[model] = self._stats.models_used.get(model, 0) + 1

    @classmethod
    def reset(cls) -> None:
        """Reset singleton — for testing only."""
        with cls._lock:
            cls._instance = None
