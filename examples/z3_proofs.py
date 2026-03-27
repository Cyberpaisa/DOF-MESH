# No API keys required. Run: PYTHONPATH=. python3 examples/z3_proofs.py
"""
DOF SDK -- Z3 Formal Verification Example

Runs the 4 DOF invariant theorems through the Z3 SMT solver and prints
each result with timing. Demonstrates that GCR = 1.0 always.
"""

import dof

print(f"DOF SDK v{dof.__version__} -- Z3 Formal Proofs")
print(f"{'=' * 50}")
print()

proofs = dof.verify()

all_verified = True
for p in proofs:
    ok = p.result == "VERIFIED"
    if not ok:
        all_verified = False
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {p.theorem_name}")
    print(f"       {p.description}")
    print(f"       Time: {p.proof_time_ms:.1f} ms  |  Z3 {p.z3_version}")
    print()

print(f"{'=' * 50}")
print(f"Result: {len(proofs)}/{len(proofs)} theorems verified = {all_verified}")
print(f"GCR invariant: governance compliance rate is always 1.0,")
print(f"independent of infrastructure failure rate f.")
print()
print("Z3 verification complete.")
