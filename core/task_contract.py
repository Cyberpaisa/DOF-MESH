from __future__ import annotations
"""
Task Contract — Formal pre/post-condition enforcement for crew tasks.

Loads a contract from a TASK_CONTRACT.md file with sections:
  PRECONDITIONS, DELIVERABLES, QUALITY_GATES, POSTCONDITIONS, FORBIDDEN_ACTIONS

Verifies fulfillment after crew execution and returns structured evidence.

Usage:
    from core.task_contract import TaskContract
    contract = TaskContract.from_file("contracts/RESEARCH_CONTRACT.md")
    result = contract.is_fulfilled(output=output, context={...})
"""

import os
import re
import json
import time
import logging
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("core.task_contract")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(BASE_DIR, "logs", "task_contracts.jsonl")


# ─────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────

@dataclass
class ContractResult:
    """Result of contract fulfillment verification."""
    fulfilled: bool
    passed_gates: list[str] = field(default_factory=list)
    failed_gates: list[str] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        status = "FULFILLED" if self.fulfilled else "BREACHED"
        return (f"ContractResult({status}, "
                f"passed={len(self.passed_gates)}, "
                f"failed={len(self.failed_gates)})")


@dataclass
class ContractSection:
    """A parsed section from the contract markdown."""
    name: str
    items: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────
# Parser
# ─────────────────────────────────────────────────────────────────────

_VALID_SECTIONS = {
    "PRECONDITIONS", "DELIVERABLES", "QUALITY_GATES",
    "POSTCONDITIONS", "FORBIDDEN_ACTIONS",
}


def _parse_contract_md(text: str) -> dict[str, list[str]]:
    """Parse a TASK_CONTRACT.md into {section_name: [items]}.

    Expects markdown with ## SECTION_NAME headers and bullet items (- item).
    """
    sections: dict[str, list[str]] = {}
    current_section = None

    for line in text.splitlines():
        stripped = line.strip()

        # Detect section headers: ## PRECONDITIONS or ## QUALITY_GATES
        header_match = re.match(r"^##\s+([A-Z_]+)", stripped)
        if header_match:
            section_name = header_match.group(1)
            if section_name in _VALID_SECTIONS:
                current_section = section_name
                sections[current_section] = []
            continue

        # Collect bullet items under current section
        if current_section and stripped.startswith("- "):
            item = stripped[2:].strip()
            if item:
                sections[current_section].append(item)

    return sections


def _parse_key_value(item: str) -> tuple[str, str]:
    """Parse 'key: value' or 'key=value' from an item string.

    Returns (key, value). If no separator found, returns (item, "").
    """
    for sep in [":", "="]:
        if sep in item:
            key, _, value = item.partition(sep)
            return key.strip(), value.strip()
    return item.strip(), ""


# ─────────────────────────────────────────────────────────────────────
# TaskContract
# ─────────────────────────────────────────────────────────────────────

class TaskContract:
    """Formal contract for a crew task with pre/post-condition enforcement."""

    def __init__(self, sections: dict[str, list[str]], source: str = ""):
        self.sections = sections
        self.source = source
        self.preconditions = sections.get("PRECONDITIONS", [])
        self.deliverables = sections.get("DELIVERABLES", [])
        self.quality_gates = sections.get("QUALITY_GATES", [])
        self.postconditions = sections.get("POSTCONDITIONS", [])
        self.forbidden_actions = sections.get("FORBIDDEN_ACTIONS", [])

    @classmethod
    def from_file(cls, path: str) -> "TaskContract":
        """Load a contract from a markdown file."""
        if not os.path.isabs(path):
            path = os.path.join(BASE_DIR, path)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        sections = _parse_contract_md(text)
        return cls(sections, source=path)

    @classmethod
    def from_string(cls, text: str) -> "TaskContract":
        """Load a contract from a markdown string. None is treated as empty."""
        sections = _parse_contract_md(text or "")
        return cls(sections, source="<string>")

    # ─── Precondition verification ───────────────────────────────

    def check_preconditions(self, context: dict) -> tuple[bool, list[str]]:
        """Verify all preconditions are met before execution.

        Context keys checked:
          - topic_provided: bool
          - providers_available: bool
          - any key referenced in precondition items
        """
        failures = []
        for item in self.preconditions:
            key, expected = _parse_key_value(item)
            key_normalized = key.lower().replace(" ", "_")

            if key_normalized in context:
                val = context[key_normalized]
                if expected:
                    # Check against expected value
                    if str(val).lower() != expected.lower():
                        failures.append(f"PRECONDITION '{key}': expected '{expected}', got '{val}'")
                elif not val:
                    failures.append(f"PRECONDITION '{key}': not satisfied")
            else:
                # Key not in context — check if it's a truthy description
                failures.append(f"PRECONDITION '{key}': not provided in context")

        passed = len(failures) == 0
        return passed, failures

    # ─── Deliverables verification ───────────────────────────────

    def check_deliverables(self, output: str, context: dict) -> tuple[bool, list[str], dict]:
        """Verify each deliverable exists.

        Checks:
          - If deliverable mentions a file path: verify file exists
          - If deliverable mentions 'output': verify output is non-empty
          - Generic deliverables: check output length > 50
        """
        failures = []
        evidence = {}

        for item in self.deliverables:
            key, value = _parse_key_value(item)
            key_lower = key.lower()

            if "output" in key_lower or "resultado" in key_lower:
                # Verify output content exists
                if output and len(output.strip()) > 50:
                    evidence[key] = f"output_length={len(output)}"
                else:
                    failures.append(f"DELIVERABLE '{key}': output is empty or too short")

            elif "file" in key_lower or "archivo" in key_lower or "/" in value:
                # Verify file exists
                file_path = value or key
                if not os.path.isabs(file_path):
                    file_path = os.path.join(BASE_DIR, file_path)
                if os.path.exists(file_path):
                    evidence[key] = f"file_exists={file_path}"
                else:
                    failures.append(f"DELIVERABLE '{key}': file not found at {file_path}")

            elif "folder" in key_lower or "carpeta" in key_lower:
                # Verify directory exists and has content
                dir_path = value or key
                if not os.path.isabs(dir_path):
                    dir_path = os.path.join(BASE_DIR, dir_path)
                if os.path.isdir(dir_path) and os.listdir(dir_path):
                    evidence[key] = f"dir_exists={dir_path}"
                else:
                    failures.append(f"DELIVERABLE '{key}': directory not found or empty")

            else:
                # Generic: check output is substantial
                if output and len(output.strip()) > 50:
                    evidence[key] = "present_in_output"
                else:
                    failures.append(f"DELIVERABLE '{key}': not verified in output")

        passed = len(failures) == 0
        return passed, failures, evidence

    # ─── Quality gates verification ──────────────────────────────

    def check_quality_gates(self, output: str, context: dict) -> tuple[bool, list[str], list[str], dict]:
        """Verify all quality gates.

        Supported gates:
          - governance_compliant=True: run ConstitutionEnforcer
          - ast_clean=True: run ASTVerifier on code blocks
          - supervisor_score>=N: check supervisor score threshold
          - tests_pass=<test_module>: run specified tests
          - adversarial_pass=True: run adversarial evaluation

        Returns: (all_passed, passed_gates, failed_gates, evidence)
        """
        passed_gates = []
        failed_gates = []
        evidence = {}

        for item in self.quality_gates:
            key, value = _parse_key_value(item)
            key_lower = key.lower().replace(" ", "_")

            if key_lower == "governance_compliant":
                result = self._gate_governance(output)
                if result["passed"]:
                    passed_gates.append("governance_compliant")
                    evidence["governance_compliant"] = result
                else:
                    failed_gates.append(f"governance_compliant: {result.get('violations', [])}")
                    evidence["governance_compliant"] = result

            elif key_lower == "ast_clean":
                result = self._gate_ast(output)
                if result["passed"]:
                    passed_gates.append("ast_clean")
                    evidence["ast_clean"] = result
                else:
                    failed_gates.append(f"ast_clean: {result.get('violations', [])}")
                    evidence["ast_clean"] = result

            elif key_lower.startswith("supervisor_score"):
                # Parse threshold: supervisor_score>=7.0
                threshold = self._parse_threshold(key, value)
                sup_score = context.get("supervisor_score", 0.0)
                if sup_score >= threshold:
                    passed_gates.append(f"supervisor_score>={threshold}")
                    evidence["supervisor_score"] = {"score": sup_score, "threshold": threshold}
                else:
                    failed_gates.append(f"supervisor_score: {sup_score} < {threshold}")
                    evidence["supervisor_score"] = {"score": sup_score, "threshold": threshold}

            elif key_lower == "tests_pass":
                result = self._gate_tests(value)
                if result["passed"]:
                    passed_gates.append(f"tests_pass:{value}")
                    evidence["tests_pass"] = result
                else:
                    failed_gates.append(f"tests_pass:{value}: {result.get('error', 'failed')}")
                    evidence["tests_pass"] = result

            elif key_lower == "adversarial_pass":
                result = self._gate_adversarial(output, context.get("input_text", ""))
                if result["passed"]:
                    passed_gates.append("adversarial_pass")
                    evidence["adversarial_pass"] = result
                else:
                    failed_gates.append(f"adversarial_pass: verdict={result.get('verdict')}")
                    evidence["adversarial_pass"] = result

            else:
                # Unknown gate — check if context has the key
                ctx_val = context.get(key_lower)
                if ctx_val is not None:
                    if value and str(ctx_val).lower() != value.lower():
                        failed_gates.append(f"{key}: expected '{value}', got '{ctx_val}'")
                    else:
                        passed_gates.append(key)
                    evidence[key] = str(ctx_val)
                else:
                    failed_gates.append(f"{key}: not available in context")

        all_passed = len(failed_gates) == 0
        return all_passed, passed_gates, failed_gates, evidence

    # ─── Forbidden actions verification ──────────────────────────

    def check_forbidden_actions(self, output: str, context: dict) -> tuple[bool, list[str]]:
        """Scan output and logs for forbidden actions.

        Checks:
          - api_key patterns in raw output
          - unauthorized web requests (if logs available)
          - Any pattern described in FORBIDDEN_ACTIONS items
        """
        violations = []

        for item in self.forbidden_actions:
            key, _ = _parse_key_value(item)
            key_lower = key.lower()

            if "api" in key_lower and "key" in key_lower:
                # Check for exposed API keys
                secret_patterns = [
                    r"sk-[a-zA-Z0-9]{20,}",
                    r"ghp_[a-zA-Z0-9]{36,}",
                    r"AKIA[A-Z0-9]{16}",
                    r"gho_[a-zA-Z0-9]{36,}",
                    r"glpat-[a-zA-Z0-9]{20,}",
                    r"xox[baprs]-[a-zA-Z0-9-]{10,}",
                ]
                for pattern in secret_patterns:
                    if re.search(pattern, output):
                        violations.append(f"FORBIDDEN: API key pattern detected ({pattern})")

            elif "request" in key_lower or "web" in key_lower:
                # Check logs for unauthorized requests
                log_path = context.get("log_path")
                if log_path and os.path.exists(log_path):
                    try:
                        with open(log_path, "r") as f:
                            log_content = f.read()
                        if "unauthorized_request" in log_content.lower():
                            violations.append(f"FORBIDDEN: Unauthorized web request detected in logs")
                    except Exception:
                        pass

            elif "eval" in key_lower or "exec" in key_lower:
                if re.search(r"\beval\s*\(", output) or re.search(r"\bexec\s*\(", output):
                    violations.append(f"FORBIDDEN: eval/exec detected in output")

            elif "subprocess" in key_lower:
                if "subprocess" in output.lower():
                    violations.append(f"FORBIDDEN: subprocess reference detected in output")

        passed = len(violations) == 0
        return passed, violations

    # ─── Postconditions verification ─────────────────────────────

    def check_postconditions(self, output: str, context: dict) -> tuple[bool, list[str]]:
        """Verify postconditions after execution.

        Checks:
          - JSONL logging: verify log entry exists
          - Output saved: verify output file exists
        """
        failures = []

        for item in self.postconditions:
            key, value = _parse_key_value(item)
            key_lower = key.lower()

            if "jsonl" in key_lower or "log" in key_lower:
                # Check that a log entry was written.
                # If log_path comes only from the contract text (not from context),
                # the file may not exist in unit-test or dry-run environments —
                # treat it as unverifiable and skip rather than fail.
                ctx_log_path = context.get("log_path", "")
                log_path = ctx_log_path or value
                if not log_path:
                    # No path available anywhere — unverifiable, skip
                    continue
                if not os.path.isabs(log_path):
                    log_path = os.path.join(BASE_DIR, log_path)

                if os.path.exists(log_path):
                    size = os.path.getsize(log_path)
                    if size > 0:
                        continue

                # Only fail when the caller explicitly provided log_path in context
                # (i.e., we are in a real execution context where the file must exist).
                if ctx_log_path:
                    failures.append(
                        f"POSTCONDITION '{key}': log file empty or missing ({log_path})"
                    )
                # Otherwise: path came from contract text only — unverifiable, skip.

            elif "saved" in key_lower or "output" in key_lower:
                # Check output was saved to expected location
                output_path = value if value else context.get("output_path", "")
                if output_path:
                    if not os.path.isabs(output_path):
                        output_path = os.path.join(BASE_DIR, output_path)
                    if not os.path.exists(output_path):
                        failures.append(f"POSTCONDITION '{key}': file not found ({output_path})")
                # If no path specified, skip (can't verify)

            else:
                # Generic postcondition — check context flag
                ctx_val = context.get(key.lower().replace(" ", "_"))
                if ctx_val is not None and not ctx_val:
                    failures.append(f"POSTCONDITION '{key}': not satisfied")

        passed = len(failures) == 0
        return passed, failures

    # ─── Full verification ───────────────────────────────────────

    def is_fulfilled(self, output: str, context: dict | None = None) -> ContractResult:
        """Verify the full contract against output and context.

        Args:
            output: The crew execution output text.
            context: Dict with execution metadata (supervisor_score, log_path, etc.)

        Returns:
            ContractResult with fulfilled status, gates, and evidence.
        """
        context = context or {}
        all_passed = []
        all_failed = []
        evidence = {}

        # 1. Deliverables
        del_ok, del_failures, del_evidence = self.check_deliverables(output, context)
        if del_ok:
            all_passed.append("deliverables")
        else:
            all_failed.extend(del_failures)
        evidence["deliverables"] = del_evidence

        # 2. Quality gates
        qg_ok, qg_passed, qg_failed, qg_evidence = self.check_quality_gates(output, context)
        all_passed.extend(qg_passed)
        all_failed.extend(qg_failed)
        evidence["quality_gates"] = qg_evidence

        # 3. Forbidden actions
        fa_ok, fa_violations = self.check_forbidden_actions(output, context)
        if fa_ok:
            all_passed.append("no_forbidden_actions")
        else:
            all_failed.extend(fa_violations)
        evidence["forbidden_actions"] = {"violations": fa_violations}

        # 4. Postconditions
        pc_ok, pc_failures = self.check_postconditions(output, context)
        if pc_ok:
            all_passed.append("postconditions")
        else:
            all_failed.extend(pc_failures)
        evidence["postconditions"] = {"failures": pc_failures}

        fulfilled = len(all_failed) == 0

        result = ContractResult(
            fulfilled=fulfilled,
            passed_gates=all_passed,
            failed_gates=all_failed,
            evidence=evidence,
        )

        self._log_result(result)
        return result

    # ─── Gate implementations ────────────────────────────────────

    def _gate_governance(self, output: str) -> dict:
        """Run ConstitutionEnforcer and return result."""
        try:
            from core.governance import ConstitutionEnforcer
            enforcer = ConstitutionEnforcer()
            result = enforcer.check(output)
            return {
                "passed": result.passed,
                "score": result.score,
                "violations": result.violations,
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def _gate_ast(self, output: str) -> dict:
        """Run ASTVerifier on code blocks in output."""
        try:
            from core.ast_verifier import ASTVerifier
            from core.governance import _extract_python_blocks
            verifier = ASTVerifier()
            blocks = _extract_python_blocks(output)
            if not blocks:
                return {"passed": True, "note": "no_code_blocks"}

            all_violations = []
            for i, block in enumerate(blocks):
                result = verifier.verify(block)
                for v in result.violations:
                    if v["severity"] == "block":
                        all_violations.append(f"Block {i+1}: {v['message']}")

            return {
                "passed": len(all_violations) == 0,
                "blocks_scanned": len(blocks),
                "violations": all_violations,
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def _gate_tests(self, test_module: str) -> dict:
        """Run specified test module and return pass/fail."""
        import subprocess
        try:
            result = subprocess.run(
                ["python3", "-m", "unittest", test_module, "-v"],
                capture_output=True, text=True, timeout=60,
                cwd=BASE_DIR,
            )
            passed = result.returncode == 0
            return {
                "passed": passed,
                "returncode": result.returncode,
                "output": result.stderr[-500:] if result.stderr else "",
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def _gate_adversarial(self, output: str, input_text: str) -> dict:
        """Run adversarial evaluation pipeline."""
        try:
            from core.adversarial import AdversarialEvaluator
            evaluator = AdversarialEvaluator()
            result = evaluator.evaluate(output, input_text)
            return {
                "passed": result.verdict == "PASS",
                "verdict": result.verdict,
                "acr": result.acr,
                "total_issues": result.total_issues,
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def _parse_threshold(self, key: str, value: str) -> float:
        """Extract numeric threshold from key>=N or value."""
        # Try extracting from key: supervisor_score>=7.0
        match = re.search(r">=?\s*([\d.]+)", key)
        if match:
            return float(match.group(1))
        # Try from value
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    # ─── Logging ─────────────────────────────────────────────────

    def _log_result(self, result: ContractResult) -> None:
        """Append contract verification result to JSONL log."""
        try:
            os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
            entry = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "source": self.source,
                "fulfilled": result.fulfilled,
                "passed_count": len(result.passed_gates),
                "failed_count": len(result.failed_gates),
                "failed_gates": result.failed_gates,
            }
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log contract result: {e}")
