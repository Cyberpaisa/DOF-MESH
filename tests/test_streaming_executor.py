"""
tests/test_streaming_executor.py — Tests for StreamingToolExecutor.
Run with: python3 -m unittest tests.test_streaming_executor
"""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from core.streaming_executor import (
    StreamingToolExecutor,
    ToolCall,
    ExecutionStarted,
    ToolStarted,
    ToolCompleted,
    ExecutionComplete,
    ExecutionAborted,
)


def run(coro):
    return asyncio.run(coro)


class TestToolCall(unittest.TestCase):
    def test_auto_tool_id(self):
        tc = ToolCall("read_file", {"path": "x"})
        self.assertIsNotNone(tc.tool_id)
        self.assertTrue(tc.tool_id.startswith("read_file-"))

    def test_custom_tool_id(self):
        tc = ToolCall("read_file", {}, tool_id="my-id")
        self.assertEqual(tc.tool_id, "my-id")


class TestStreamingExecutorBasic(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "stream.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def _read_events(self):
        return [json.loads(l) for l in self.path.read_text().strip().splitlines()]

    def test_empty_tools_emits_started_and_complete(self):
        ex = StreamingToolExecutor(self.path)
        summary = run(ex.run([], {}))
        events = self._read_events()
        self.assertEqual(events[0]["event"], "execution_started")
        self.assertEqual(events[-1]["event"], "execution_complete")
        self.assertEqual(summary.completed, 0)
        self.assertEqual(summary.failed, 0)

    def test_single_tool_success(self):
        ex = StreamingToolExecutor(self.path)
        handlers = {"add": lambda x, y: x + y}
        tools = [ToolCall("add", {"x": 2, "y": 3})]
        summary = run(ex.run(tools, handlers))
        self.assertEqual(summary.completed, 1)
        self.assertEqual(summary.failed, 0)
        events = self._read_events()
        tool_done = next(e for e in events if e["event"] == "tool_completed")
        self.assertEqual(tool_done["status"], "ok")
        self.assertEqual(tool_done["result"], 5)

    def test_unknown_handler_is_error(self):
        ex = StreamingToolExecutor(self.path)
        tools = [ToolCall("nonexistent", {})]
        summary = run(ex.run(tools, {}))
        self.assertEqual(summary.failed, 1)
        self.assertEqual(summary.completed, 0)
        events = self._read_events()
        err = next(e for e in events if e["event"] == "tool_completed")
        self.assertEqual(err["status"], "error")
        self.assertIn("No handler", err["error"])

    def test_handler_exception_counted_as_failure(self):
        def boom(**_):
            raise ValueError("intentional failure")
        ex = StreamingToolExecutor(self.path)
        tools = [ToolCall("boom", {})]
        summary = run(ex.run(tools, {"boom": boom}))
        self.assertEqual(summary.failed, 1)

    def test_multiple_tools_all_succeed(self):
        ex = StreamingToolExecutor(self.path)
        results = []
        handlers = {"step": lambda n: results.append(n)}
        tools = [ToolCall("step", {"n": i}) for i in range(4)]
        summary = run(ex.run(tools, handlers))
        self.assertEqual(summary.completed, 4)
        self.assertEqual(summary.failed, 0)
        self.assertEqual(results, [0, 1, 2, 3])

    def test_mixed_success_and_failure(self):
        def fail_on_even(n):
            if n % 2 == 0:
                raise RuntimeError("even")
            return n
        ex = StreamingToolExecutor(self.path)
        tools = [ToolCall("f", {"n": i}) for i in range(4)]
        summary = run(ex.run(tools, {"f": fail_on_even}))
        self.assertEqual(summary.completed, 2)
        self.assertEqual(summary.failed, 2)


class TestStreamingExecutorAsync(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "stream.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def test_async_handler_is_awaited(self):
        async def async_add(x, y):
            await asyncio.sleep(0)
            return x + y

        ex = StreamingToolExecutor(self.path)
        tools = [ToolCall("async_add", {"x": 10, "y": 5})]
        summary = run(ex.run(tools, {"async_add": async_add}))
        self.assertEqual(summary.completed, 1)


class TestStreamingExecutorAbort(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "stream.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def test_abort_before_start_returns_zero(self):
        abort = asyncio.Event()
        abort.set()
        ex = StreamingToolExecutor(self.path, abort_event=abort)
        called = []
        handlers = {"t": lambda: called.append(1)}
        tools = [ToolCall("t", {}) for _ in range(5)]
        summary = run(ex.run(tools, handlers))
        self.assertEqual(called, [])
        self.assertEqual(summary.completed, 0)

    def test_abort_mid_run_stops_remaining_tools(self):
        abort = asyncio.Event()
        called = []

        def handler(n):
            called.append(n)
            if n == 1:
                abort.set()

        ex = StreamingToolExecutor(self.path, abort_event=abort)
        tools = [ToolCall("h", {"n": i}) for i in range(5)]
        summary = run(ex.run(tools, {"h": handler}))
        # Should stop after tool 1 sets the abort
        self.assertLess(summary.completed, 5)

    def test_abort_emits_aborted_event(self):
        abort = asyncio.Event()
        abort.set()
        ex = StreamingToolExecutor(self.path, abort_event=abort)
        run(ex.run([ToolCall("t", {})], {"t": lambda: None}))
        events = [json.loads(l) for l in self.path.read_text().strip().splitlines()]
        self.assertTrue(any(e["event"] == "execution_aborted" for e in events))


class TestStreamingExecutorJSONL(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "stream.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def test_all_lines_are_valid_json(self):
        ex = StreamingToolExecutor(self.path)
        tools = [ToolCall("echo", {"msg": "hello"})]
        run(ex.run(tools, {"echo": lambda msg: msg}))
        for line in self.path.read_text().strip().splitlines():
            obj = json.loads(line)
            self.assertIn("event", obj)

    def test_on_event_callback_receives_all_events(self):
        received = []
        ex = StreamingToolExecutor(self.path)
        tools = [ToolCall("noop", {})]
        run(ex.run(tools, {"noop": lambda: None}, on_event=received.append))
        types = [type(e).__name__ for e in received]
        self.assertIn("ExecutionStarted", types)
        self.assertIn("ToolStarted", types)
        self.assertIn("ToolCompleted", types)
        self.assertIn("ExecutionComplete", types)

    def test_elapsed_ms_positive(self):
        ex = StreamingToolExecutor(self.path)
        tools = [ToolCall("noop", {})]
        summary = run(ex.run(tools, {"noop": lambda: None}))
        self.assertGreaterEqual(summary.total_elapsed_ms, 0)


if __name__ == "__main__":
    unittest.main()
