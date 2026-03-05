"""
Framework-Agnostic Governance — LangGraph adapter + generic adapter.

DOF governance nodes that can be plugged into any agentic pipeline:
  - DOFGovernanceNode: constitutional enforcement on output
  - DOFASTNode: static analysis on generated code
  - DOFMemoryNode: governed memory add/query
  - DOFObservabilityNode: step tracing and metrics

FrameworkAdapter: abstraction for wrapping any framework's output
  - GenericAdapter: works with ANY system that produces a string
  - LangGraphAdapter: uses DOF nodes as LangGraph-compatible callables
  - CrewAIAdapter: wrapper over existing crew_runner

Philosophy: "DOF governs output, not the framework that produced it."

Zero external dependencies for GenericAdapter.
LangGraph dependency is OPTIONAL (try/except ImportError).

Usage:
    from integrations.langgraph_adapter import GenericAdapter

    adapter = GenericAdapter()
    result = adapter.wrap_output("The analysis shows Python grew 15%. Sources: stackoverflow.com")
    print(result)  # {"status": "pass", "score": 0.7, "violations": [], ...}
"""

import os
import sys
import time
import logging
from dataclasses import dataclass, asdict

logger = logging.getLogger("integrations.langgraph_adapter")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


# ─────────────────────────────────────────────────────────────────────
# DOF Governance Node
# ─────────────────────────────────────────────────────────────────────

class DOFGovernanceNode:
    """A node that executes DOF governance verification.

    Can be used as a callable node in LangGraph or any graph-based pipeline.
    Extracts output from state, runs ConstitutionEnforcer, and returns
    updated state with governance results.
    """

    def __init__(self):
        from core.governance import ConstitutionEnforcer
        self._enforcer = ConstitutionEnforcer()

    def __call__(self, state: dict) -> dict:
        """Execute governance check on state output.

        Reads: state["output"] or last message in state["messages"].
        Writes: state["governance_result"], state["governance_pass"].
        """
        output = self._extract_output(state)
        if not output:
            state["governance_pass"] = False
            state["governance_result"] = {
                "passed": False,
                "score": 0.0,
                "violations": ["No output found in state"],
                "warnings": [],
            }
            return state

        result = self._enforcer.check(output)
        state["governance_pass"] = result.passed
        state["governance_result"] = {
            "passed": result.passed,
            "score": result.score,
            "violations": result.violations,
            "warnings": result.warnings,
        }
        return state

    @staticmethod
    def _extract_output(state: dict) -> str:
        """Extract output text from various state formats."""
        if "output" in state and isinstance(state["output"], str):
            return state["output"]
        if "messages" in state and isinstance(state["messages"], list):
            for msg in reversed(state["messages"]):
                if isinstance(msg, str):
                    return msg
                if isinstance(msg, dict) and "content" in msg:
                    return msg["content"]
        return ""


# ─────────────────────────────────────────────────────────────────────
# DOF AST Node
# ─────────────────────────────────────────────────────────────────────

class DOFASTNode:
    """A node that verifies generated code via AST static analysis.

    Checks for unsafe imports, eval/exec calls, hardcoded secrets.
    """

    def __init__(self):
        from core.ast_verifier import ASTVerifier
        self._verifier = ASTVerifier()

    def __call__(self, state: dict) -> dict:
        """Execute AST verification on code in state.

        Reads: state["code"].
        Writes: state["ast_result"].
        """
        code = state.get("code", "")
        if not code:
            state["ast_result"] = {"score": 1.0, "violations": [], "passed": True}
            return state

        result = self._verifier.verify(code)
        state["ast_result"] = {
            "score": result.score,
            "violations": result.violations,
            "passed": result.passed,
        }
        return state


# ─────────────────────────────────────────────────────────────────────
# DOF Memory Node
# ─────────────────────────────────────────────────────────────────────

class DOFMemoryNode:
    """A node that interacts with GovernedMemoryStore.

    Supports add and query actions via state["memory_action"].
    """

    def __init__(self, store=None):
        if store is not None:
            self._store = store
        else:
            from core.memory_governance import GovernedMemoryStore
            self._store = GovernedMemoryStore()

    def __call__(self, state: dict) -> dict:
        """Execute memory action from state.

        Reads: state["memory_action"] ("add" or "query"),
               state["memory_content"] (for add),
               state["memory_query"] (for query),
               state["memory_category"] (optional).
        Writes: state["memory_result"].
        """
        action = state.get("memory_action", "")

        if action == "add":
            content = state.get("memory_content", "")
            category = state.get("memory_category", "")
            if not content:
                state["memory_result"] = {"error": "No content provided"}
                return state
            entry = self._store.add(content, category=category)
            state["memory_result"] = {
                "action": "add",
                "memory_id": entry.id,
                "category": entry.category,
                "governance_status": entry.governance_status,
            }

        elif action == "query":
            query = state.get("memory_query", "")
            category = state.get("memory_category", "")
            results = self._store.query(query=query, category=category)
            state["memory_result"] = {
                "action": "query",
                "count": len(results),
                "results": [
                    {"id": e.id, "content": e.content[:100], "category": e.category}
                    for e in results[:10]
                ],
            }

        else:
            state["memory_result"] = {"error": f"Unknown action: {action}"}

        return state


# ─────────────────────────────────────────────────────────────────────
# DOF Observability Node
# ─────────────────────────────────────────────────────────────────────

class DOFObservabilityNode:
    """A node that registers observability metrics.

    Creates StepTrace entries from state data.
    """

    def __call__(self, state: dict) -> dict:
        """Record observability step from state.

        Reads: state["agent"], state["provider"], state["status"].
        Writes: state["trace_step"].
        """
        from core.observability import StepTrace

        step = StepTrace(
            step_index=state.get("step_index", 0),
            agent=state.get("agent", "unknown"),
            provider=state.get("provider", "unknown"),
            latency_ms=state.get("latency_ms", 0.0),
            status=state.get("status", "completed"),
            governance_passed=state.get("governance_pass", True),
        )
        state["trace_step"] = asdict(step)
        return state


# ─────────────────────────────────────────────────────────────────────
# Framework Adapter — Abstract
# ─────────────────────────────────────────────────────────────────────

class FrameworkAdapter:
    """Abstract adapter for wrapping any framework's output with DOF governance."""

    def wrap_output(self, output: str) -> dict:
        """Apply ConstitutionEnforcer to output text.

        Returns: {status, violations, warnings, score}.
        """
        raise NotImplementedError

    def wrap_code(self, code: str) -> dict:
        """Apply ASTVerifier to code.

        Returns: {score, violations, passed}.
        """
        raise NotImplementedError

    def record_step(self, step_data: dict) -> None:
        """Record a step in observability."""
        raise NotImplementedError


# ─────────────────────────────────────────────────────────────────────
# Generic Adapter — works with ANY framework
# ─────────────────────────────────────────────────────────────────────

class GenericAdapter(FrameworkAdapter):
    """DOF governance for ANY system that produces string output.

    Zero external dependencies. If you can produce a string, DOF can govern it.
    """

    def __init__(self):
        from core.governance import ConstitutionEnforcer
        from core.ast_verifier import ASTVerifier
        self._enforcer = ConstitutionEnforcer()
        self._ast_verifier = ASTVerifier()

    def wrap_output(self, output: str) -> dict:
        """Apply governance to any text output.

        Returns:
            {status: "pass"|"fail", score: float, violations: list, warnings: list}
        """
        result = self._enforcer.check(output)
        return {
            "status": "pass" if result.passed else "fail",
            "score": result.score,
            "violations": result.violations,
            "warnings": result.warnings,
        }

    def wrap_code(self, code: str) -> dict:
        """Apply AST verification to code.

        Returns:
            {score: float, violations: list, passed: bool}
        """
        result = self._ast_verifier.verify(code)
        return {
            "score": result.score,
            "violations": result.violations,
            "passed": result.passed,
        }

    def record_step(self, step_data: dict) -> None:
        """Record step in observability trace."""
        node = DOFObservabilityNode()
        node(step_data)


# ─────────────────────────────────────────────────────────────────────
# CrewAI Adapter
# ─────────────────────────────────────────────────────────────────────

class CrewAIAdapter(FrameworkAdapter):
    """DOF governance adapter for CrewAI crews.

    Wraps the existing crew_runner with governance hooks.
    """

    def __init__(self):
        from core.governance import ConstitutionEnforcer
        from core.ast_verifier import ASTVerifier
        self._enforcer = ConstitutionEnforcer()
        self._ast_verifier = ASTVerifier()

    def wrap_output(self, output: str) -> dict:
        result = self._enforcer.check(output)
        return {
            "status": "pass" if result.passed else "fail",
            "score": result.score,
            "violations": result.violations,
            "warnings": result.warnings,
        }

    def wrap_code(self, code: str) -> dict:
        result = self._ast_verifier.verify(code)
        return {
            "score": result.score,
            "violations": result.violations,
            "passed": result.passed,
        }

    def record_step(self, step_data: dict) -> None:
        node = DOFObservabilityNode()
        node(step_data)


# ─────────────────────────────────────────────────────────────────────
# LangGraph Adapter
# ─────────────────────────────────────────────────────────────────────

class LangGraphAdapter(FrameworkAdapter):
    """DOF governance adapter for LangGraph pipelines.

    Uses DOF nodes as LangGraph-compatible callables.
    LangGraph is an OPTIONAL dependency.
    """

    def __init__(self):
        self._governance_node = DOFGovernanceNode()
        self._ast_node = DOFASTNode()
        self._observability_node = DOFObservabilityNode()

    def wrap_output(self, output: str) -> dict:
        state = {"output": output}
        state = self._governance_node(state)
        return state.get("governance_result", {})

    def wrap_code(self, code: str) -> dict:
        state = {"code": code}
        state = self._ast_node(state)
        return state.get("ast_result", {})

    def record_step(self, step_data: dict) -> None:
        self._observability_node(step_data)

    def get_nodes(self) -> dict:
        """Return DOF nodes for direct use in LangGraph graphs.

        Usage in LangGraph:
            adapter = LangGraphAdapter()
            nodes = adapter.get_nodes()
            graph.add_node("governance", nodes["governance"])
        """
        return {
            "governance": self._governance_node,
            "ast": self._ast_node,
            "observability": self._observability_node,
        }


# ─────────────────────────────────────────────────────────────────────
# Pipeline Helper
# ─────────────────────────────────────────────────────────────────────

def create_governed_pipeline() -> dict:
    """Create pre-configured DOF governance nodes.

    Returns a dict of callable nodes that can be used in any pipeline.

    Usage:
        nodes = create_governed_pipeline()
        state = {"output": "My LLM output..."}
        state = nodes["governance"](state)
        if state["governance_pass"]:
            print("Output approved!")
    """
    return {
        "governance": DOFGovernanceNode(),
        "ast": DOFASTNode(),
        "memory": DOFMemoryNode(),
        "observability": DOFObservabilityNode(),
    }
