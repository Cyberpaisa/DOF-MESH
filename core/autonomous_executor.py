"""
AutonomousExecutor — Agentic execution loop for DOF Mesh nodes.

Turns a local Ollama model into a fully autonomous agent that can:
  - Run bash commands
  - Execute Python code
  - Read / write files
  - List directories

Loop: call model → parse tool tags → execute → feed result back → repeat until <done>.
Max 10 iterations per task to prevent infinite loops.

Tool format (XML tags the model uses):
  <bash>command</bash>
  <python>code</python>
  <read_file>/path/to/file</read_file>
  <write_file path="/path/to/file">content</write_file>
  <list_dir>/path/to/dir</list_dir>
  <done>summary of what was accomplished</done>
"""
import io
import os
import re
import sys
import json
import time
import logging
import subprocess
import traceback
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass, field
from typing import Optional

import requests

logger = logging.getLogger("core.autonomous_executor")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")
CEREBRAS_FALLBACK_MODEL = "llama-3.3-70b"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_FALLBACK_MODEL = "llama-3.3-70b-versatile"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_FALLBACK_MODEL = "deepseek-chat"
MAX_ITERATIONS = 10
BASH_TIMEOUT = 30   # seconds per command
FILE_READ_LIMIT = 200  # max lines to return from read_file

# Blocked commands — absolute safety rules
BLOCKED_PATTERNS = [
    r"rm\s+-rf",
    r"git\s+push",
    r"git\s+add\s+-A",
    r"DROP\s+TABLE",
    r"mkfs",
    r"dd\s+if=",
    r":\(\)\{",    # fork bomb
    r"curl.*\|.*sh",
    r"wget.*\|.*sh",
]

AGENT_SYSTEM = f"""You are an autonomous AI agent running inside the DOF (Deterministic Observability Framework) repository.
Repository: {REPO_ROOT}
Stack: Python 3.12+, 103 core modules, 3360+ tests, local Ollama models.

You have access to tools. Use them to complete the task autonomously.
After each tool execution, you will receive the output. Analyze it and continue.

== TOOL FORMAT ==

Run a shell command:
<bash>ls core/ | head -20</bash>

Execute Python code:
<python>
import json
with open('dof/__init__.py') as f:
    print(f.read()[:500])
</python>

Read a file (returns up to {FILE_READ_LIMIT} lines):
<read_file>{REPO_ROOT}/core/governance.py</read_file>

Write a file:
<write_file path="{REPO_ROOT}/core/new_module.py">
# content here
</write_file>

List a directory:
<list_dir>{REPO_ROOT}/core</list_dir>

When the task is complete, output ONLY this tag with a summary:
<done>
What was built/fixed/analyzed. Files created or modified. Tests run.
</done>

== RULES ==
- NEVER use: rm -rf, git push, git add -A, DROP TABLE
- Always read a file before modifying it
- Run tests after implementing: python3 -m unittest tests.test_MODULE -v
- Working directory for all commands: {REPO_ROOT}
- If a command fails, analyze the error and try a different approach
- Maximum {MAX_ITERATIONS} tool calls — be efficient
- After writing code, always verify it runs without errors
"""


@dataclass
class ToolCall:
    tool: str
    input: str
    output: str
    success: bool
    duration_ms: float = 0.0


@dataclass
class ExecutionResult:
    task_id: str
    task: str
    result: str          # final summary from <done> tag
    tool_calls: list = field(default_factory=list)
    iterations: int = 0
    success: bool = False
    duration_ms: float = 0.0
    model_used: str = ""


class AutonomousExecutor:
    """
    Runs a task through a full agentic loop using a local Ollama model.
    Singleton per process.
    """

    _instance: Optional["AutonomousExecutor"] = None

    def __new__(cls, *args, **kwargs) -> "AutonomousExecutor":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model: str = "dof-coder") -> None:
        if self._initialized:
            return
        self._model = model
        self._initialized = True
        logger.info("AutonomousExecutor ready | model=%s repo=%s", model, REPO_ROOT)

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def execute(self, task_id: str, task: str, model: Optional[str] = None) -> ExecutionResult:
        """
        Run a task to completion through the agentic loop.
        Returns an ExecutionResult with the final summary and all tool calls.
        """
        model = model or self._model
        result = ExecutionResult(task_id=task_id, task=task, model_used=model, result="")
        t0 = time.time()

        messages = [
            {"role": "system", "content": AGENT_SYSTEM},
            {"role": "user", "content": task},
        ]

        logger.info("Starting autonomous execution | task_id=%s model=%s", task_id, model)

        for iteration in range(1, MAX_ITERATIONS + 1):
            result.iterations = iteration
            logger.debug("Iteration %d/%d", iteration, MAX_ITERATIONS)

            # Call the model (Ollama first, Cerebras fallback if Ollama is busy/down)
            response = self._call_llm(messages, model)
            if response is None:
                result.result = "[ERROR] Ollama did not respond. Check that Ollama is running."
                break

            # Strip deepseek internal thinking
            response = re.sub(r"<think>[\s\S]*?</think>", "", response).strip()

            # Check for <done> — task complete
            done_match = re.search(r"<done>([\s\S]*?)</done>", response, re.IGNORECASE)
            if done_match:
                result.result = done_match.group(1).strip()
                result.success = True
                logger.info("Task %s completed in %d iterations", task_id, iteration)
                break

            # Find all tool calls in the response
            tool_calls = self._parse_tool_calls(response)

            if not tool_calls:
                # Model gave a plain text response — treat as final answer
                result.result = response
                result.success = True
                logger.info("Task %s: plain text response (no tools used)", task_id)
                break

            # Execute each tool call
            tool_outputs = []
            for tool, inp in tool_calls:
                tc = self._execute_tool(tool, inp)
                result.tool_calls.append(tc)
                tool_outputs.append(
                    f"<tool_result tool='{tc.tool}' success='{tc.success}' duration='{tc.duration_ms:.0f}ms'>\n{tc.output}\n</tool_result>"
                )
                logger.debug("Tool %s | success=%s | output_len=%d", tc.tool, tc.success, len(tc.output))

            # Feed results back to the model
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": "\n".join(tool_outputs) + "\n\nContinue with the task. When done, use <done> tag."})

        else:
            # Reached max iterations without <done>
            result.result = f"[MAX ITERATIONS REACHED] Last response:\n{response}"
            result.success = False

        result.duration_ms = round((time.time() - t0) * 1000, 2)
        logger.info(
            "Execution finished | task_id=%s success=%s iterations=%d duration=%.0fms",
            task_id, result.success, result.iterations, result.duration_ms,
        )
        return result

    # ------------------------------------------------------------------ #
    # Tool execution
    # ------------------------------------------------------------------ #

    def _parse_tool_calls(self, text: str) -> list[tuple[str, str]]:
        """Extract (tool_name, input) pairs from model response."""
        tools = []

        # <bash>...</bash>
        for m in re.finditer(r"<bash>([\s\S]*?)</bash>", text, re.IGNORECASE):
            tools.append(("bash", m.group(1).strip()))

        # <python>...</python>
        for m in re.finditer(r"<python>([\s\S]*?)</python>", text, re.IGNORECASE):
            tools.append(("python", m.group(1).strip()))

        # <read_file>path</read_file>
        for m in re.finditer(r"<read_file>([\s\S]*?)</read_file>", text, re.IGNORECASE):
            tools.append(("read_file", m.group(1).strip()))

        # <write_file path="...">content</write_file>
        for m in re.finditer(r'<write_file\s+path=["\']?([^"\'>\s]+)["\']?>([\s\S]*?)</write_file>', text, re.IGNORECASE):
            tools.append(("write_file", json.dumps({"path": m.group(1).strip(), "content": m.group(2)})))

        # <list_dir>path</list_dir>
        for m in re.finditer(r"<list_dir>([\s\S]*?)</list_dir>", text, re.IGNORECASE):
            tools.append(("list_dir", m.group(1).strip()))

        return tools

    def _execute_tool(self, tool: str, inp: str) -> ToolCall:
        t0 = time.time()
        try:
            if tool == "bash":
                output, success = self._run_bash(inp)
            elif tool == "python":
                output, success = self._run_python(inp)
            elif tool == "read_file":
                output, success = self._read_file(inp)
            elif tool == "write_file":
                data = json.loads(inp)
                output, success = self._write_file(data["path"], data["content"])
            elif tool == "list_dir":
                output, success = self._list_dir(inp)
            else:
                output, success = f"Unknown tool: {tool}", False
        except Exception as exc:
            output = f"[EXECUTOR ERROR] {exc}\n{traceback.format_exc()}"
            success = False

        return ToolCall(
            tool=tool,
            input=inp[:500],
            output=output[:4000],   # cap output to avoid context overflow
            success=success,
            duration_ms=round((time.time() - t0) * 1000, 2),
        )

    def _run_bash(self, cmd: str) -> tuple[str, bool]:
        # Security check
        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, cmd, re.IGNORECASE):
                return f"[BLOCKED] Command matches security rule: {pattern}", False

        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=BASH_TIMEOUT,
                cwd=REPO_ROOT,
            )
            output = (proc.stdout + proc.stderr).strip()
            if not output:
                output = f"[exit code {proc.returncode}]"
            return output[:4000], proc.returncode == 0
        except subprocess.TimeoutExpired:
            return f"[TIMEOUT] Command exceeded {BASH_TIMEOUT}s", False
        except Exception as exc:
            return f"[ERROR] {exc}", False

    def _run_python(self, code: str) -> tuple[str, bool]:
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        namespace = {
            "__name__": "__agent__",
            "REPO_ROOT": REPO_ROOT,
        }
        try:
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                exec(compile(code, "<agent>", "exec"), namespace)  # noqa: S102
            out = stdout_buf.getvalue()
            err = stderr_buf.getvalue()
            combined = (out + err).strip()
            return combined[:4000] if combined else "[OK — no output]", True
        except Exception:
            err = traceback.format_exc()
            out = stdout_buf.getvalue()
            return (f"{out}\n[EXCEPTION]\n{err}").strip()[:4000], False

    def _read_file(self, path: str) -> tuple[str, bool]:
        # Resolve relative paths against repo root
        if not os.path.isabs(path):
            path = os.path.join(REPO_ROOT, path)
        path = os.path.realpath(path)

        # Safety: only read within repo or home dir
        if not (path.startswith(REPO_ROOT) or path.startswith(os.path.expanduser("~"))):
            return f"[BLOCKED] Path outside allowed directories: {path}", False

        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            total = len(lines)
            content = "".join(lines[:FILE_READ_LIMIT])
            suffix = f"\n[... {total - FILE_READ_LIMIT} more lines]" if total > FILE_READ_LIMIT else ""
            return content + suffix, True
        except FileNotFoundError:
            return f"[NOT FOUND] {path}", False
        except Exception as exc:
            return f"[ERROR] {exc}", False

    def _write_file(self, path: str, content: str) -> tuple[str, bool]:
        if not os.path.isabs(path):
            path = os.path.join(REPO_ROOT, path)
        path = os.path.realpath(path)

        # Safety: only write within repo
        if not path.startswith(REPO_ROOT):
            return f"[BLOCKED] Write outside repo: {path}", False

        # Block sensitive files
        blocked_names = ["oracle_key.json", ".env", "id_rsa", "id_ed25519"]
        if os.path.basename(path) in blocked_names:
            return f"[BLOCKED] Cannot write to sensitive file: {path}", False

        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"[WRITTEN] {path} ({len(content)} bytes)", True
        except Exception as exc:
            return f"[ERROR] {exc}", False

    def _list_dir(self, path: str) -> tuple[str, bool]:
        if not os.path.isabs(path):
            path = os.path.join(REPO_ROOT, path)
        try:
            entries = sorted(os.listdir(path))
            lines = []
            for e in entries[:100]:
                full = os.path.join(path, e)
                prefix = "d " if os.path.isdir(full) else "f "
                lines.append(prefix + e)
            return "\n".join(lines), True
        except Exception as exc:
            return f"[ERROR] {exc}", False

    # ------------------------------------------------------------------ #
    # Ollama
    # ------------------------------------------------------------------ #

    def _call_ollama(self, messages: list[dict], model: str) -> Optional[str]:
        """Call Ollama via streaming so timeout only fires if model STOPS generating.
        This prevents false timeouts caused by queue wait time.
        """
        try:
            resp = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,  # stream=True: get chunks as model generates
                    "options": {
                        "temperature": 0.2,
                        "num_predict": -1,
                        "top_p": 0.9,
                    },
                },
                timeout=(120, 300),  # (connect/queue timeout, inter-chunk timeout)
                stream=True,
            )
            resp.raise_for_status()

            # Collect streamed chunks — timeout resets on each chunk received
            import json as _json
            parts = []
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    chunk = _json.loads(line)
                except Exception:
                    continue
                content = chunk.get("message", {}).get("content", "")
                if content:
                    parts.append(content)
                if chunk.get("done"):
                    break

            raw = "".join(parts).strip()
            # Strip deepseek think tags
            import re as _re
            return _re.sub(r"<think>[\s\S]*?</think>", "", raw).strip()

        except requests.Timeout:
            logger.error("Ollama timeout (model=%s) — queue wait or generation stalled", model)
        except Exception as exc:
            logger.error("Ollama error: %s", exc)
        return None

    # ------------------------------------------------------------------ #
    # External fallback (Cerebras API)
    # ------------------------------------------------------------------ #

    def _call_external(self, messages: list[dict], model: str = CEREBRAS_FALLBACK_MODEL) -> Optional[str]:
        """Call Cerebras API as fallback when Ollama is busy or unavailable.

        Free tier supports llama-3.3-70b up to rate limits.
        Returns None if the call fails (key missing, rate limit, network error).
        """
        if not CEREBRAS_API_KEY:
            logger.warning("CEREBRAS_API_KEY not set — external fallback unavailable")
            return None
        try:
            import json as _json
            resp = requests.post(
                CEREBRAS_URL,
                headers={
                    "Authorization": f"Bearer {CEREBRAS_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "max_tokens": 4096,
                },
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            import re as _re
            return _re.sub(r"<think>[\s\S]*?</think>", "", content).strip()
        except requests.Timeout:
            logger.error("Cerebras API timeout (model=%s)", model)
        except Exception as exc:
            logger.error("Cerebras API error: %s", exc)
        return None

    # ------------------------------------------------------------------ #
    # External fallback (Groq API)
    # ------------------------------------------------------------------ #

    def _call_groq(self, messages: list[dict], model: str = GROQ_FALLBACK_MODEL) -> Optional[str]:
        """Call Groq API as second fallback when both Ollama and Cerebras are unavailable.

        Free tier supports llama-3.3-70b-versatile up to rate limits.
        Returns None if the call fails (key missing, rate limit, network error).
        """
        if not GROQ_API_KEY:
            logger.warning("GROQ_API_KEY not set — Groq fallback unavailable")
            return None
        try:
            resp = requests.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "max_tokens": 4096,
                },
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            import re as _re
            return _re.sub(r"<think>[\s\S]*?</think>", "", content).strip()
        except requests.Timeout:
            logger.error("Groq API timeout (model=%s)", model)
        except Exception as exc:
            logger.error("Groq API error: %s", exc)
        return None

    # ------------------------------------------------------------------ #
    # Unified LLM caller — Ollama first, Cerebras second, Groq third
    # ------------------------------------------------------------------ #

    def _call_deepseek(self, messages: list[dict], model: str = DEEPSEEK_FALLBACK_MODEL) -> Optional[str]:
        """Call DeepSeek API — very low cost, good quality, OpenAI-compatible.

        Priority 2 in the fallback chain (after Ollama).
        """
        if not DEEPSEEK_API_KEY:
            return None
        try:
            resp = requests.post(
                DEEPSEEK_URL,
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "temperature": 0.2, "max_tokens": 4096},
                timeout=60,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"] or ""
            return re.sub(r"<think>[\s\S]*?</think>", "", content).strip() or None
        except Exception as exc:
            logger.warning("DeepSeek call failed: %s", exc)
            return None

    def _call_llm(self, messages: list[dict], model: str) -> Optional[str]:
        """Provider chain: Ollama (free local) → DeepSeek (cheap) → Cerebras → Groq.

        Prioritizes zero/low-cost providers first.
        """
        response = self._call_ollama(messages, model)
        if response is not None:
            return response

        logger.warning("Ollama unavailable for model=%s — trying DeepSeek", model)
        response = self._call_deepseek(messages, DEEPSEEK_FALLBACK_MODEL)
        if response is not None:
            return response

        logger.warning("DeepSeek unavailable — trying Cerebras (model=%s)", CEREBRAS_FALLBACK_MODEL)
        response = self._call_external(messages, CEREBRAS_FALLBACK_MODEL)
        if response is not None:
            return response

        logger.warning("Cerebras unavailable — trying Groq (model=%s)", GROQ_FALLBACK_MODEL)
        return self._call_groq(messages, GROQ_FALLBACK_MODEL)
