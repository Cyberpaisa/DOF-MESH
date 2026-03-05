"""
DOF SDK — LangGraph Adapter Example

Demonstrates how to use DOF governance nodes in a LangGraph-style pipeline.
No API keys required. LangGraph is NOT required — this example uses
DOF nodes as plain callables.

Run with:
    pip install -e . --no-deps
    python examples/langgraph_example.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations.langgraph_adapter import (
    LangGraphAdapter,
    DOFGovernanceNode,
    DOFASTNode,
    DOFObservabilityNode,
)

print("=== DOF LangGraph Adapter — Governance Nodes ===\n")

# ── 1. Use LangGraphAdapter for simple governance ────────────────────────────

adapter = LangGraphAdapter()

mock_output = """## Market Analysis Report

The technology sector shows strong growth indicators for Q1 2024.

Key metrics:
- Cloud computing revenue increased 28% YoY
- AI/ML adoption reached 67% in enterprise
- DevOps tooling market grew to $15B

Sources: https://www.gartner.com/reports/2024 https://aws.amazon.com/economics

Recommended actions:
1. Increase cloud infrastructure budget by 15%
2. Prioritize AI integration in existing products
3. Evaluate serverless migration for cost optimization
"""

result = adapter.wrap_output(mock_output)
print(f"LangGraph adapter governance:")
print(f"  Passed:     {result.get('passed', result.get('status'))}")
print(f"  Score:      {result.get('score', 0):.2f}")
print(f"  Violations: {result.get('violations', [])}")
print()

# ── 2. Use DOF nodes directly (LangGraph-compatible callables) ───────────────

print("=== Using DOF Nodes as Graph Callables ===\n")

nodes = adapter.get_nodes()

# Simulate a LangGraph state dict flowing through nodes
state = {
    "output": mock_output,
    "code": "def greet(name): return f'Hello, {name}!'",
    "agent": "researcher",
    "provider": "groq",
    "step_index": 0,
    "latency_ms": 245.0,
    "status": "completed",
}

# Node 1: Governance check
state = nodes["governance"](state)
print(f"After governance node:")
print(f"  governance_pass:  {state['governance_pass']}")
print(f"  governance_score: {state['governance_result']['score']:.2f}")

# Node 2: AST verification
state = nodes["ast"](state)
print(f"After AST node:")
print(f"  ast_passed: {state['ast_result']['passed']}")
print(f"  ast_score:  {state['ast_result']['score']:.2f}")

# Node 3: Observability trace
state = nodes["observability"](state)
print(f"After observability node:")
print(f"  trace_step: agent={state['trace_step']['agent']}, "
      f"provider={state['trace_step']['provider']}, "
      f"latency={state['trace_step']['latency_ms']}ms")
print()

# ── 3. Extracting output from messages (LangGraph message format) ────────────

print("=== Message-Based State Extraction ===\n")

governance_node = DOFGovernanceNode()

# LangGraph-style messages list
message_state = {
    "messages": [
        {"role": "user", "content": "Analyze market trends"},
        {"role": "assistant", "content": mock_output},
    ]
}

message_state = governance_node(message_state)
print(f"Governance from messages list:")
print(f"  Passed: {message_state['governance_pass']}")
print(f"  Score:  {message_state['governance_result']['score']:.2f}")
print()

print("LangGraph example complete.")
