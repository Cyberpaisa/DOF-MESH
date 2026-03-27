# No API keys required. Run: PYTHONPATH=. python3 examples/governance_check.py
"""
DOF SDK -- Governance Check Example

Demonstrates the ConstitutionEnforcer: hard rules block non-compliant
output deterministically, without any LLM involvement.
"""

from core.governance import ConstitutionEnforcer

enforcer = ConstitutionEnforcer()

# -- 1. Good text: should PASS --------------------------------------------------
good = (
    "The research findings indicate clear evidence of deterministic "
    "behavior across all test conditions."
)
r1 = enforcer.enforce(good)
print(f"[1] Good text:       {r1['status']}")
print(f"    Violations:      {len(r1['hard_violations'])}")
print()

# -- 2. Bad text: "statistics show" without a source URL -------------------------
bad = (
    "Statistics show that 73% of autonomous agents fail under load. "
    "This is a well-known fact in the industry."
)
r2 = enforcer.enforce(bad)
print(f"[2] Unsourced claim: {r2['status']}")
for v in r2["hard_violations"]:
    rule = v if isinstance(v, str) else v.get("rule_id", v)
    print(f"    -> {rule}")
print()

# -- 3. Code block with eval() -- triggers AST verification ---------------------
code_block = (
    "Here is a helper:\n"
    "```python\n"
    "result = eval(user_input)\n"
    "```\n"
    "Use it to process data."
)
r3 = enforcer.enforce(code_block)
print(f"[3] eval() in code:  {r3['status']}")
for v in r3["hard_violations"]:
    rule = v if isinstance(v, str) else v.get("rule_id", v)
    print(f"    -> {rule}")
print()

print("Governance check complete.")
