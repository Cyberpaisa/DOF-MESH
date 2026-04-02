"""
AST Verifier — Static Analysis for Agent-Generated Code.

Deterministic, zero-LLM verification of Python source code using the ast
module.  Runs BEFORE code execution to detect unsafe patterns:
  - Blocked imports (subprocess, os.system, etc.)
  - Hardcoded secrets (API keys, tokens)
  - Unsafe calls (eval, exec, compile)
  - Resource risks (while True without break, unbounded recursion)

Results logged to logs/ast_verification.jsonl for audit.
"""

import ast
import json
import os
import re
import time
import logging
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("core.ast_verifier")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(BASE_DIR, "logs", "ast_verification.jsonl")

# ─────────────────────────────────────────────────────────────────────
# Rule definitions
# ─────────────────────────────────────────────────────────────────────

BLOCKED_IMPORTS = [
    "subprocess", "os.system", "shutil.rmtree", "__import__", "pty", "os.popen",
]

UNSAFE_CALLS = ["eval", "exec", "compile", "getattr", "setattr"]

SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),        # OpenAI
    re.compile(r"ghp_[a-zA-Z0-9]{36,}"),        # GitHub PAT
    re.compile(r"AKIA[A-Z0-9]{16}"),            # AWS Access Key
    re.compile(r"gho_[a-zA-Z0-9]{36,}"),        # GitHub OAuth
    re.compile(r"glpat-[a-zA-Z0-9\-]{20,}"),    # GitLab PAT
    re.compile(r"xox[baprs]-[a-zA-Z0-9\-]{10,}"),  # Slack token
]

def _sync_ast_rules():
    """Sync AST rules with the YAML constitution if available."""
    global BLOCKED_IMPORTS, UNSAFE_CALLS
    try:
        from core.governance import load_constitution
        const = load_constitution()
        if not const:
            return
        
        ast_rules = const.get("rules", {}).get("ast", [])
        for rule in ast_rules:
            if rule.get("rule_key") == "BLOCKED_IMPORTS":
                BLOCKED_IMPORTS = list(set(BLOCKED_IMPORTS + rule.get("pattern", {}).get("blocked", [])))
            elif rule.get("rule_key") == "UNSAFE_CALLS":
                UNSAFE_CALLS = list(set(UNSAFE_CALLS + rule.get("pattern", {}).get("blocked_calls", [])))
            elif rule.get("rule_key") == "SECRET_PATTERNS":
                new_patterns = rule.get("pattern", {}).get("patterns", [])
                for p in new_patterns:
                    try:
                        SECRET_PATTERNS.append(re.compile(p))
                    except:
                        pass
        logger.info("AST Verifier synced with constitution")
    except Exception as e:
        logger.warning(f"AST Verifier sync failed: {e}")

# Run sync
_sync_ast_rules()


# ─────────────────────────────────────────────────────────────────────
# Dataclasses
# ─────────────────────────────────────────────────────────────────────

@dataclass
class Violation:
    """Single verification violation."""
    rule_id: str
    severity: str       # "block" or "warn"
    line_number: int
    code_snippet: str
    message: str


@dataclass
class VerificationResult:
    """Result of AST verification on a code string."""
    passed: bool
    violations: list[dict] = field(default_factory=list)
    score: float = 1.0  # 1.0 = clean, 0.0 = all rules violated


# ─────────────────────────────────────────────────────────────────────
# AST Visitor
# ─────────────────────────────────────────────────────────────────────

class _UnsafePatternVisitor(ast.NodeVisitor):
    """Walk the AST collecting violations."""

    def __init__(self, source_lines: list[str]):
        self.source_lines = source_lines
        self.violations: list[Violation] = []

    def _snippet(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.source_lines):
            return self.source_lines[lineno - 1].strip()
        return ""

    # ── Imports ──────────────────────────────────────────────────────

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            if alias.name in BLOCKED_IMPORTS:
                self.violations.append(Violation(
                    rule_id="BLOCKED_IMPORTS",
                    severity="block",
                    line_number=node.lineno,
                    code_snippet=self._snippet(node.lineno),
                    message=f"Blocked import: '{alias.name}'",
                ))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        for alias in node.names:
            full = f"{module}.{alias.name}" if module else alias.name
            for blocked in BLOCKED_IMPORTS:
                if full == blocked or module == blocked:
                    self.violations.append(Violation(
                        rule_id="BLOCKED_IMPORTS",
                        severity="block",
                        line_number=node.lineno,
                        code_snippet=self._snippet(node.lineno),
                        message=f"Blocked import: '{full}'",
                    ))
                    break
        self.generic_visit(node)

    # ── Unsafe calls ─────────────────────────────────────────────────

    def visit_Call(self, node: ast.Call):
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name in UNSAFE_CALLS:
            self.violations.append(Violation(
                rule_id="UNSAFE_CALLS",
                severity="block",
                line_number=node.lineno,
                code_snippet=self._snippet(node.lineno),
                message=f"Unsafe call: '{func_name}()'",
            ))

        # Check __import__()
        if func_name == "__import__":
            self.violations.append(Violation(
                rule_id="BLOCKED_IMPORTS",
                severity="block",
                line_number=node.lineno,
                code_snippet=self._snippet(node.lineno),
                message="Blocked call: '__import__()'",
            ))

        self.generic_visit(node)

    # ── Resource risks: while True without break ─────────────────────

    def visit_While(self, node: ast.While):
        if isinstance(node.test, ast.Constant) and node.test.value is True:
            has_break = any(
                isinstance(child, ast.Break)
                for child in ast.walk(node)
            )
            if not has_break:
                self.violations.append(Violation(
                    rule_id="RESOURCE_RISKS",
                    severity="warn",
                    line_number=node.lineno,
                    code_snippet=self._snippet(node.lineno),
                    message="'while True' without 'break' — potential infinite loop",
                ))
        self.generic_visit(node)

    # ── Resource risks: recursion without depth guard ────────────────

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._check_recursion(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._check_recursion(node)
        self.generic_visit(node)

    def _check_recursion(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        """Detect self-calls without any visible depth guard."""
        func_name = node.name
        calls_self = False
        has_guard = False

        for child in ast.walk(node):
            # Self-call?
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id == func_name:
                    calls_self = True
            # Depth guard heuristic: comparison with a name/constant (e.g. if depth > N)
            if isinstance(child, ast.Compare):
                has_guard = True
            if isinstance(child, ast.If):
                # base-case return inside the function counts
                for sub in ast.walk(child):
                    if isinstance(sub, ast.Return):
                        has_guard = True

        if calls_self and not has_guard:
            self.violations.append(Violation(
                rule_id="RESOURCE_RISKS",
                severity="warn",
                line_number=node.lineno,
                code_snippet=self._snippet(node.lineno),
                message=f"Recursive function '{func_name}' without visible depth guard",
            ))


# ─────────────────────────────────────────────────────────────────────
# Secret detection (string literal scan)
# ─────────────────────────────────────────────────────────────────────

def _check_secrets(source: str, lines: list[str]) -> list[Violation]:
    """Scan raw source for hardcoded secrets using regex patterns."""
    violations = []
    for i, line in enumerate(lines, 1):
        for pattern in SECRET_PATTERNS:
            if pattern.search(line):
                violations.append(Violation(
                    rule_id="SECRET_PATTERNS",
                    severity="block",
                    line_number=i,
                    code_snippet=line.strip()[:80],
                    message=f"Possible hardcoded secret matching {pattern.pattern}",
                ))
                break  # one violation per line
    return violations


# ─────────────────────────────────────────────────────────────────────
# JSONL logger
# ─────────────────────────────────────────────────────────────────────

def _log_result(result: VerificationResult, source_preview: str = ""):
    """Append verification result to logs/ast_verification.jsonl."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    entry = {
        "ts": time.time(),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "event": "ast_verification",
        "passed": result.passed,
        "score": result.score,
        "violation_count": len(result.violations),
        "violations": result.violations,
        "source_preview": source_preview[:200],
    }
    try:
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception as e:
        logger.error(f"AST verification log error: {e}")


# ─────────────────────────────────────────────────────────────────────
# Main verifier class
# ─────────────────────────────────────────────────────────────────────

# Total number of rule categories for score calculation
_RULE_COUNT = 4  # BLOCKED_IMPORTS, UNSAFE_CALLS, SECRET_PATTERNS, RESOURCE_RISKS


class ASTVerifier:
    """Static analysis verifier for agent-generated Python code.

    Zero LLM dependency — all checks are deterministic via ast + regex.
    """

    def verify(self, source_code: str) -> VerificationResult:
        """Verify Python source code. Returns VerificationResult."""
        lines = source_code.splitlines()

        # Parse AST
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            result = VerificationResult(
                passed=False,
                violations=[asdict(Violation(
                    rule_id="SYNTAX_ERROR",
                    severity="block",
                    line_number=e.lineno or 0,
                    code_snippet=(e.text or "").strip()[:80],
                    message=f"SyntaxError: {e.msg}",
                ))],
                score=0.0,
            )
            _log_result(result, source_code[:200])
            return result

        # Run AST visitor
        visitor = _UnsafePatternVisitor(lines)
        visitor.visit(tree)

        # Run secret scan
        secret_violations = _check_secrets(source_code, lines)

        # Combine
        all_violations = visitor.violations + secret_violations
        violation_dicts = [asdict(v) for v in all_violations]

        # Score: 1.0 - (unique violated rule categories / total categories)
        violated_categories = {v.rule_id for v in all_violations}
        score = round(1.0 - (len(violated_categories) / _RULE_COUNT), 2)
        score = max(0.0, score)

        # Passed = no "block" severity violations
        has_block = any(v.severity == "block" for v in all_violations)
        passed = not has_block

        result = VerificationResult(
            passed=passed,
            violations=violation_dicts,
            score=score,
        )

        _log_result(result, source_code[:200])

        if not passed:
            logger.warning(
                f"AST verification FAILED: {len(violation_dicts)} violation(s), "
                f"score={score}"
            )
        else:
            logger.info(f"AST verification OK (score={score}, warnings={len(violation_dicts)})")

        return result
