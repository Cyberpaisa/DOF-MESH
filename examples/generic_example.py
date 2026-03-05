"""
DOF SDK — Generic Adapter Example

Demonstrates how to use GenericAdapter to govern ANY system's output.
Zero external dependencies. No API keys required.

Run with:
    pip install -e . --no-deps
    python examples/generic_example.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations.langgraph_adapter import GenericAdapter, create_governed_pipeline

# ── 1. GenericAdapter — govern any string output ─────────────────────────────

print("=== DOF GenericAdapter — Framework-Agnostic Governance ===\n")

adapter = GenericAdapter()

# Good output: has structure, sources, actionable content
good_output = """## Analysis of Python Growth in 2024

Python continues to dominate as the most popular programming language.

Key findings:
- Stack Overflow survey shows 45% developer adoption
- GitHub repository count increased by 22% year-over-year
- Enterprise adoption grew significantly in ML/AI sectors

Sources: https://survey.stackoverflow.co/2024 https://octoverse.github.com

Next steps:
1. Implement Python-first strategy for new microservices
2. Migrate legacy Java services where cost-effective
3. Invest in team training for async Python patterns
"""

result = adapter.wrap_output(good_output)
print(f"Good output governance:")
print(f"  Status:     {result['status']}")
print(f"  Score:      {result['score']:.2f}")
print(f"  Violations: {result['violations']}")
print(f"  Warnings:   {result['warnings']}")
print()

# Bad output: hallucination claim without source
bad_output = "According to recent studies, Python is 10x faster than C++."

result = adapter.wrap_output(bad_output)
print(f"Bad output governance:")
print(f"  Status:     {result['status']}")
print(f"  Score:      {result['score']:.2f}")
print(f"  Violations: {result['violations']}")
print()

# ── 2. AST verification on code ──────────────────────────────────────────────

safe_code = """
def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
"""

unsafe_code = """
import subprocess
result = eval(input("Enter expression: "))
subprocess.run(["rm", "-rf", "/"])
"""

print("=== AST Code Verification ===\n")

result = adapter.wrap_code(safe_code)
print(f"Safe code:   passed={result['passed']}, score={result['score']:.2f}")

result = adapter.wrap_code(unsafe_code)
print(f"Unsafe code: passed={result['passed']}, score={result['score']:.2f}")
print(f"  Violations: {result['violations']}")
print()

# ── 3. Pipeline nodes — use individually ─────────────────────────────────────

print("=== Governed Pipeline Nodes ===\n")

nodes = create_governed_pipeline()

state = {"output": good_output}
state = nodes["governance"](state)
print(f"Pipeline governance: passed={state['governance_pass']}, score={state['governance_result']['score']:.2f}")

state = {"code": safe_code}
state = nodes["ast"](state)
print(f"Pipeline AST:        passed={state['ast_result']['passed']}, score={state['ast_result']['score']:.2f}")
print()

print("Generic example complete.")
