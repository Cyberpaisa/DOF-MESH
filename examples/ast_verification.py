# No API keys required. Run: PYTHONPATH=. python3 examples/ast_verification.py
"""
DOF SDK -- AST Security Verification Example

Demonstrates the ASTVerifier: static analysis of Python code using the
ast module to detect unsafe patterns before execution.
"""

from core.ast_verifier import ASTVerifier

verifier = ASTVerifier()

# -- 1. Safe code: json.dumps ---------------------------------------------------
safe_code = """
import json
data = {"agent": "apex", "score": 85}
output = json.dumps(data, indent=2)
print(output)
"""
r1 = verifier.verify(safe_code)
print(f"[1] Safe code (json.dumps):  passed={r1.passed}  score={r1.score:.1f}")
print(f"    Violations: {len(r1.violations)}")
print()

# -- 2. Unsafe code: eval + subprocess ------------------------------------------
unsafe_code = """
import subprocess
result = eval(user_input)
subprocess.run(["rm", "-rf", "/"])
exec(compile("print(1)", "<x>", "exec"))
"""
r2 = verifier.verify(unsafe_code)
print(f"[2] Unsafe code (eval+subprocess):  passed={r2.passed}  score={r2.score:.1f}")
print(f"    Violations: {len(r2.violations)}")
for v in r2.violations:
    rid = v.get("rule_id", v) if isinstance(v, dict) else v.rule_id
    msg = v.get("message", "") if isinstance(v, dict) else v.message
    print(f"    -> [{rid}] {msg}")
print()

print("AST verification complete.")
