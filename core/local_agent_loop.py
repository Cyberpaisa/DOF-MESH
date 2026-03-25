"""
LocalAgentLoop — Autonomous daemon using Ollama local models.
Replaces Claude SDK with local inference. Zero API tokens. Zero external dependency.

Models (configurable via env or constructor):
  ORCHESTRATOR: phi4:14b  (fast, no thinking mode, 120 tok/s)
  CODER:        qwen2.5-coder:14b  (already available)
  FAST:         llama3.3:8b  (230 tok/s, tool-calling)

Falls back gracefully if a model is not available.
"""
import os
import json
import time
import logging
import threading
import requests
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("core.local_agent_loop")

_BASE_DIR = Path(__file__).parent.parent
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# Model routing by task type
# deepseek-r1:14b: reasoning/orchestration (9GB, ~80 tok/s, distilled, no thinking overhead)
# qwen2.5-coder:14b: code/implementation (9GB, ~90 tok/s, already installed)
MODEL_ROUTING = {
    "code":         os.getenv("LOCAL_MODEL_CODE",         "qwen2.5-coder:14b"),
    "orchestration":os.getenv("LOCAL_MODEL_ORCHESTRATOR", "deepseek-r1:14b"),
    "fast":         os.getenv("LOCAL_MODEL_FAST",         "qwen2.5-coder:14b"),
    "reasoning":    os.getenv("LOCAL_MODEL_REASONING",    "deepseek-r1:14b"),
    "default":      os.getenv("LOCAL_MODEL_DEFAULT",      "qwen2.5-coder:14b"),
}


@dataclass
class LocalTask:
    task_id: str
    task_type: str = "default"  # code / orchestration / fast / reasoning / default
    prompt: str = ""
    context: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    result: Optional[str] = None
    model_used: Optional[str] = None
    duration_ms: float = 0.0
    success: bool = False


@dataclass
class LoopStats:
    cycles: int = 0
    tasks_processed: int = 0
    tasks_failed: int = 0
    total_tokens_used: int = 0
    uptime_seconds: float = 0.0
    available_models: list = field(default_factory=list)


class LocalAgentLoop:
    """
    Autonomous daemon that polls a file-based inbox and runs each task
    through a local Ollama model. Zero external API calls.

    Singleton — one loop per process.
    """

    _instance: Optional["LocalAgentLoop"] = None

    def __new__(cls, *args, **kwargs) -> "LocalAgentLoop":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        inbox_dir: str = "logs/mesh/inbox/local-agent",
        poll_interval: int = 10,
    ) -> None:
        if self._initialized:
            return

        self._inbox_dir = _BASE_DIR / inbox_dir
        self._inbox_dir.mkdir(parents=True, exist_ok=True)

        self._poll_interval = poll_interval
        self._running = False
        self._stats = LoopStats()
        self._start_time = time.time()
        self._lock = threading.Lock()

        # Import the local permission classifier (same singleton pattern)
        from core.local_permission_classifier import LocalPermissionClassifier
        self._permission_classifier = LocalPermissionClassifier()

        self._initialized = True
        logger.info(
            "LocalAgentLoop initialised | inbox=%s poll_interval=%ds",
            self._inbox_dir,
            self._poll_interval,
        )

    # ------------------------------------------------------------------
    # Model discovery
    # ------------------------------------------------------------------

    def get_available_models(self) -> list[str]:
        """Query Ollama for locally available models. Returns list of model names."""
        try:
            resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            logger.debug("Available Ollama models: %s", models)
            return models
        except Exception as exc:
            logger.warning("Could not reach Ollama at %s: %s", OLLAMA_URL, exc)
            return []

    def get_best_model(self, task_type: str) -> str:
        """
        Return the preferred model for the given task type.

        Falls back through:
          1. Preferred model from MODEL_ROUTING[task_type]
          2. Any model currently available in Ollama
          3. MODEL_ROUTING["default"] (hard-coded name, may fail if not pulled)
        """
        preferred = MODEL_ROUTING.get(task_type, MODEL_ROUTING["default"])
        available = self.get_available_models()

        if not available:
            logger.warning("No Ollama models available — using configured default %r", preferred)
            return preferred

        # Update stats cache
        with self._lock:
            self._stats.available_models = available

        if preferred in available:
            return preferred

        # Fallback: pick first available model
        fallback = available[0]
        logger.warning(
            "Preferred model %r not available; falling back to %r",
            preferred,
            fallback,
        )
        return fallback

    # ------------------------------------------------------------------
    # Task execution
    # ------------------------------------------------------------------

    def run_task(self, task: LocalTask) -> LocalTask:
        """
        Execute a single LocalTask through Ollama.

        Steps:
          1. Select the best model for task.task_type.
          2. Classify the prompt through the permission classifier.
          3. Call Ollama /api/generate.
          4. Populate task fields and return.
        """
        model = self.get_best_model(task.task_type)

        # Permission gate — block destructive prompts before sending to model
        classification = self._permission_classifier.classify(task.prompt)
        from core.local_permission_classifier import ActionClass
        if classification.action_class == ActionClass.BLOCK:
            task.result = (
                f"[BLOCKED] {classification.reason}. "
                f"Alternatives: {'; '.join(classification.alternatives)}"
            )
            task.model_used = None
            task.success = False
            logger.warning(
                "Task %s BLOCKED by permission classifier: %s",
                task.task_id,
                classification.reason,
            )
            with self._lock:
                self._stats.tasks_failed += 1
            return task

        # Build system prompt from context if provided
        system_prompt = task.context.get("system", "")

        t0 = time.time()
        raw = self._call_ollama(model=model, prompt=task.prompt, system=system_prompt)
        elapsed_ms = (time.time() - t0) * 1000

        task.model_used = model
        task.duration_ms = round(elapsed_ms, 2)

        if raw is not None:
            task.result = raw
            task.success = True
            with self._lock:
                self._stats.tasks_processed += 1
            logger.info(
                "Task %s completed | model=%s duration=%.0fms",
                task.task_id,
                model,
                elapsed_ms,
            )
        else:
            task.result = "[ERROR] Ollama returned no response."
            task.success = False
            with self._lock:
                self._stats.tasks_failed += 1
            logger.error("Task %s failed — Ollama returned None", task.task_id)

        return task

    def _call_ollama(
        self,
        model: str,
        prompt: str,
        system: str = "",
    ) -> Optional[str]:
        """
        POST a generation request to Ollama.

        Returns the response text, or None on any error.
        """
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 2048,
                "temperature": 0.2,
            },
        }
        if system:
            payload["system"] = system

        try:
            resp = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response")
        except requests.Timeout:
            logger.error("Ollama request timed out after 120s (model=%s)", model)
        except requests.HTTPError as exc:
            logger.error("Ollama HTTP error: %s", exc)
        except Exception as exc:
            logger.error("Unexpected error calling Ollama: %s", exc)
        return None

    # ------------------------------------------------------------------
    # Inbox polling
    # ------------------------------------------------------------------

    def _read_inbox_tasks(self) -> list[LocalTask]:
        """
        Scan the inbox directory for pending .json task files.

        Expected JSON schema:
          {
            "content": {
              "task": {
                "task_id": "...",
                "task_type": "code",
                "prompt": "...",
                "context": {}
              }
            }
          }

        Processed files are renamed to .done.
        """
        tasks: list[LocalTask] = []
        for task_file in sorted(self._inbox_dir.glob("*.json")):
            try:
                raw = task_file.read_text(encoding="utf-8")
                data = json.loads(raw)

                task_data = data.get("content", {}).get("task", {})
                if not task_data:
                    # Try flat format: top-level task fields
                    task_data = data

                task = LocalTask(
                    task_id=task_data.get("task_id", task_file.stem),
                    task_type=task_data.get("task_type", "default"),
                    prompt=task_data.get("prompt", ""),
                    context=task_data.get("context", {}),
                )
                tasks.append(task)

                # Mark as processed
                done_path = task_file.with_suffix(".done")
                task_file.rename(done_path)
                logger.debug("Queued task %s from %s", task.task_id, task_file.name)

            except json.JSONDecodeError as exc:
                logger.error("Malformed JSON in %s: %s", task_file.name, exc)
            except Exception as exc:
                logger.error("Error reading inbox file %s: %s", task_file.name, exc)

        return tasks

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self, max_cycles: int = 0) -> None:
        """
        Start the agent loop. Polls the inbox and processes tasks.

        Args:
            max_cycles: Stop after this many cycles. 0 = run forever.
        """
        self._running = True
        self._start_time = time.time()
        logger.info(
            "LocalAgentLoop started | max_cycles=%s poll_interval=%ds inbox=%s",
            max_cycles if max_cycles else "∞",
            self._poll_interval,
            self._inbox_dir,
        )

        try:
            while self._running:
                with self._lock:
                    self._stats.cycles += 1
                    current_cycle = self._stats.cycles

                logger.debug("Cycle %d — scanning inbox", current_cycle)
                tasks = self._read_inbox_tasks()

                for task in tasks:
                    if not self._running:
                        break
                    completed = self.run_task(task)
                    self._persist_result(completed)

                if max_cycles and current_cycle >= max_cycles:
                    logger.info("Reached max_cycles=%d — stopping", max_cycles)
                    break

                time.sleep(self._poll_interval)

        except KeyboardInterrupt:
            logger.info("LocalAgentLoop interrupted by user — shutting down gracefully")
        finally:
            self._running = False
            logger.info("LocalAgentLoop stopped after %d cycles", self._stats.cycles)

    def stop(self) -> None:
        """Signal the loop to stop after the current cycle."""
        self._running = False
        logger.info("LocalAgentLoop stop requested")

    # ------------------------------------------------------------------
    # Stats & persistence
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Return runtime statistics as a plain dict."""
        with self._lock:
            uptime = time.time() - self._start_time
            return {
                "cycles": self._stats.cycles,
                "tasks_processed": self._stats.tasks_processed,
                "tasks_failed": self._stats.tasks_failed,
                "total_tokens_used": self._stats.total_tokens_used,
                "uptime_seconds": round(uptime, 2),
                "available_models": list(self._stats.available_models),
            }

    def _persist_result(self, task: LocalTask) -> None:
        """Write the completed task result to the results directory."""
        results_dir = _BASE_DIR / "logs" / "local-agent" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)

        result_file = results_dir / f"{task.task_id}.json"
        payload = {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "prompt": task.prompt,
            "result": task.result,
            "model_used": task.model_used,
            "duration_ms": task.duration_ms,
            "success": task.success,
            "created_at": task.created_at,
            "completed_at": time.time(),
        }
        try:
            result_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            logger.debug("Result persisted to %s", result_file)
        except Exception as exc:
            logger.error("Could not persist result for task %s: %s", task.task_id, exc)
