"""
streaming_executor.py — Streaming tool execution with progress events.

Executes a sequence of tool calls and emits structured events as they happen.
Each event is a dataclass written to a JSONL stream for real-time observability.

Events emitted (in order):
    ExecutionStarted  — before the first tool runs
    ToolStarted       — before each individual tool call
    ToolCompleted     — after each tool call (success or error)
    ExecutionComplete — after all tools finish
    ExecutionAborted  — if cancelled via abort_event

Usage::
    executor = StreamingToolExecutor("logs/streams/run-001.jsonl")
    tools = [
        ToolCall("read_file", {"path": "core/governance.py"}),
        ToolCall("run_tests", {"suite": "tests.test_governance"}),
    ]
    summary = await executor.run(tools, handlers={"read_file": my_reader, ...})
    print(summary.completed, summary.failed)
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("core.streaming_executor")


# ─────────────────────────────────────────────────────────────────────
# Data classes — events and tool descriptors
# ─────────────────────────────────────────────────────────────────────

@dataclass
class ToolCall:
    """A single tool invocation descriptor."""
    name: str
    args: Dict[str, Any] = field(default_factory=dict)
    tool_id: Optional[str] = None
    max_retries: int = 0          # 0 = no retry; N = up to N extra attempts
    retry_backoff: float = 1.0    # base delay in seconds (doubles each retry)

    def __post_init__(self) -> None:
        if self.tool_id is None:
            self.tool_id = f"{self.name}-{int(time.time() * 1000)}"


@dataclass
class ExecutionStarted:
    event: str = "execution_started"
    total_tools: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class ToolStarted:
    event: str = "tool_started"
    tool_id: str = ""
    name: str = ""
    args: Dict[str, Any] = field(default_factory=dict)
    index: int = 0          # 0-based position in the tool list
    timestamp: float = field(default_factory=time.time)


@dataclass
class ToolCompleted:
    event: str = "tool_completed"
    tool_id: str = ""
    name: str = ""
    status: str = "ok"      # "ok" | "error"
    result: Any = None
    error: Optional[str] = None
    elapsed_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class ExecutionComplete:
    event: str = "execution_complete"
    completed: int = 0
    failed: int = 0
    total_elapsed_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class ExecutionAborted:
    event: str = "execution_aborted"
    completed_so_far: int = 0
    reason: str = "abort_event"
    timestamp: float = field(default_factory=time.time)


# ─────────────────────────────────────────────────────────────────────
# Executor
# ─────────────────────────────────────────────────────────────────────

class StreamingToolExecutor:
    """
    Executes a list of ToolCall objects sequentially, emitting structured
    events to a JSONL log and to optional in-process callbacks.

    Args:
        stream_path: Where to write JSONL events (created if absent).
        abort_event: Optional asyncio.Event — set it to cancel mid-stream.
    """

    def __init__(
        self,
        stream_path: str | Path,
        abort_event: Optional[asyncio.Event] = None,
    ) -> None:
        self._path = Path(stream_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._abort = abort_event or asyncio.Event()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, event: Any) -> None:
        """Append one event as a JSON line to the stream file."""
        try:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(event), default=str) + "\n")
        except Exception as exc:
            logger.warning("StreamingToolExecutor: failed to write event: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(
        self,
        tools: List[ToolCall],
        handlers: Dict[str, Callable[..., Any]],
        on_event: Optional[Callable[[Any], None]] = None,
    ) -> ExecutionComplete:
        """Execute all tools in order, streaming events along the way.

        Args:
            tools:    Ordered list of ToolCall descriptors.
            handlers: Mapping of tool name → async or sync callable.
                      Each callable receives the tool's ``args`` dict as kwargs.
            on_event: Optional in-process callback invoked for every event.

        Returns:
            ExecutionComplete summary (also emitted to the stream).
        """
        started_at = time.time()
        completed = 0
        failed = 0

        start_evt = ExecutionStarted(total_tools=len(tools))
        self._emit(start_evt)
        if on_event:
            on_event(start_evt)

        for index, tool in enumerate(tools):
            # AbortSignal check before each tool
            if self._abort.is_set():
                abort_evt = ExecutionAborted(completed_so_far=completed)
                self._emit(abort_evt)
                if on_event:
                    on_event(abort_evt)
                logger.warning("StreamingToolExecutor aborted at tool %d/%d", index, len(tools))
                return ExecutionComplete(
                    completed=completed,
                    failed=failed,
                    total_elapsed_ms=(time.time() - started_at) * 1000,
                )

            tool_start = ToolStarted(
                tool_id=tool.tool_id or "",
                name=tool.name,
                args=tool.args,
                index=index,
            )
            self._emit(tool_start)
            if on_event:
                on_event(tool_start)

            handler = handlers.get(tool.name)
            t0 = time.time()
            if handler is None:
                elapsed = (time.time() - t0) * 1000
                err_evt = ToolCompleted(
                    tool_id=tool.tool_id or "",
                    name=tool.name,
                    status="error",
                    error=f"No handler registered for tool '{tool.name}'",
                    elapsed_ms=elapsed,
                )
                self._emit(err_evt)
                if on_event:
                    on_event(err_evt)
                failed += 1
                continue

            last_exc: Optional[Exception] = None
            attempts = 1 + max(0, tool.max_retries)
            for attempt in range(attempts):
                # Abort check inside retry loop
                if self._abort.is_set():
                    break
                if attempt > 0:
                    delay = tool.retry_backoff * (2 ** (attempt - 1))
                    logger.info("Tool '%s' retry %d/%d after %.1fs", tool.name, attempt, tool.max_retries, delay)
                    await asyncio.sleep(delay)
                try:
                    if inspect.iscoroutinefunction(handler):
                        result = await handler(**tool.args)
                    else:
                        result = handler(**tool.args)
                    elapsed = (time.time() - t0) * 1000
                    ok_evt = ToolCompleted(
                        tool_id=tool.tool_id or "",
                        name=tool.name,
                        status="ok",
                        result=result,
                        elapsed_ms=elapsed,
                    )
                    self._emit(ok_evt)
                    if on_event:
                        on_event(ok_evt)
                    completed += 1
                    last_exc = None
                    break  # success — no more retries
                except Exception as exc:
                    last_exc = exc
                    logger.warning("Tool '%s' attempt %d failed: %s", tool.name, attempt + 1, exc)

            if last_exc is not None:
                elapsed = (time.time() - t0) * 1000
                err_evt = ToolCompleted(
                    tool_id=tool.tool_id or "",
                    name=tool.name,
                    status="error",
                    error=str(last_exc),
                    elapsed_ms=elapsed,
                )
                self._emit(err_evt)
                if on_event:
                    on_event(err_evt)
                failed += 1
                logger.error("Tool '%s' failed after %d attempt(s): %s", tool.name, attempts, last_exc)

        summary = ExecutionComplete(
            completed=completed,
            failed=failed,
            total_elapsed_ms=(time.time() - started_at) * 1000,
        )
        self._emit(summary)
        if on_event:
            on_event(summary)
        return summary
