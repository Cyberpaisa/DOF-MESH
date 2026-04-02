import re
import os

filepath = "core/autonomous_executor.py"
with open(filepath, "r") as f:
    code = f.read()

# 1. Imports
if "import hmac" not in code:
    code = code.replace("import traceback", "import traceback\nimport hashlib\nimport hmac\nfrom datetime import datetime, timezone")

# 2. Key extraction
if "QAION_PRIVATE_KEY" not in code:
    code = code.replace("DEEPSEEK_API_KEY = os.getenv(\"DEEPSEEK_API_KEY\", \"\")", "DEEPSEEK_API_KEY = os.getenv(\"DEEPSEEK_API_KEY\", \"\")\nQAION_PRIVATE_KEY = os.getenv(\"QAION_PRIVATE_KEY\", \"dof-local-dev-key\")")

# 3. Prompt
if "<sub_task>" not in code:
    code = code.replace("<list_dir>{REPO_ROOT}/core</list_dir>", "<list_dir>{REPO_ROOT}/core</list_dir>\n\nDelegate an isolated sub-task if you need parallel workspace math without losing context:\n<sub_task>Scan these files and return the IDs.</sub_task>")

# 4. depth init
if "self.depth =" not in code:
    code = code.replace("def __init__(self, model: str = \"dof-coder\") -> None:", "def __init__(self, model: str = \"dof-coder\", depth: int = 0) -> None:")
    code = code.replace("self._model = model", "self._model = model\n        self.depth = depth")

# 5. Auditing function
if "_log_security_event" not in code:
    audit_func = """
    def _log_security_event(self, event_type: str, details: str) -> None:
        log_dir = os.path.join(REPO_ROOT, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "mesh_security.jsonl")
        entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event_type, "details": details, "model": getattr(self, "_model", "unknown")}
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\\n")
"""
    code = code.replace("    def execute(self, task_id: str, task: str, model: Optional[str] = None) -> ExecutionResult:", audit_func + "\n    def execute(self, task_id: str, task: str, model: Optional[str] = None) -> ExecutionResult:")

# 6. Auditing injections
code = re.sub(r'return f"\[BLOCKED\] Command matches security rule: (\{pattern\})", False', r'self._log_security_event("BASH_BLOCKED", f"Command match: {pattern} | {cmd}"); return f"[BLOCKED] Command matches security rule: {pattern}", False', code)
code = re.sub(r'return f"\[BLOCKED\] Cannot write to sensitive file: (\{path\})", False', r'self._log_security_event("WRITE_SENSITIVE", f"Attempted write: {path}"); return f"[BLOCKED] Cannot write to sensitive file: {path}", False', code)
code = re.sub(r'return f"\[BLOCKED\] READ-BEFORE-WRITE[\s\S]*?", False', r'self._log_security_event("WRITE_WITHOUT_READ", f"Blind write block: {path}"); return f"[BLOCKED] READ-BEFORE-WRITE ENFORCEMENT: You must <read_file> the entire file before you can write to it or overwrite it.", False', code)

# 7. Sub-task routing
if "elif tool == \"sub_task\":" not in code:
    code = code.replace("output, success = self._list_dir(inp)", "output, success = self._list_dir(inp)\n            elif tool == \"sub_task\":\n                output, success = self._run_sub_task(inp)")
    
    subtask_parser = """
        # <sub_task>instructions</sub_task>
        for m in re.finditer(r"<sub_task>([\\s\\S]*?)</sub_task>", text, re.IGNORECASE):
            tools.append(("sub_task", m.group(1).strip()))
"""
    code = code.replace("return tools", subtask_parser + "\n        return tools")

    subtask_impl = """
    def _run_sub_task(self, instructions: str) -> tuple[str, bool]:
        if self.depth >= 1:
            self._log_security_event("FORK_BOMB_PREVENTION", "Sub-task tried to delegate another sub-task.")
            return "[BLOCKED] Maximum recursion depth reached. A sub-task cannot spawn another sub-task.", False
        
        sub_executor = AutonomousExecutor(model=self._model, depth=self.depth + 1)
        # Using a distinct task ID for the sub-task
        res = sub_executor.execute(f"sub-{int(time.time())}", instructions)
        return res.result, res.success
"""
    code = code.replace("def _run_bash(self,", subtask_impl + "\n    def _run_bash(self,")

# 8. Signature injection
if "def _sign_payload(" not in code:
    sign_func = """
    def _sign_headers(self, payload: str = "") -> dict:
        signature = hmac.new(QAION_PRIVATE_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return {"X-DOF-Signature": signature}
"""
    code = code.replace("def _call_ollama(self,", sign_func + "\n    def _call_ollama(self,")

    # Hook into headers
    code = code.replace('{"Content-Type": "application/json"}', '{"Content-Type": "application/json", **self._sign_headers()}')
    code = code.replace('"Content-Type": "application/json",', '"Content-Type": "application/json", **self._sign_headers(),')

with open(filepath, "w") as f:
    f.write(code)

print("Patch applied to core/autonomous_executor.py")
