# Z3 Formal Verification in DOF

*Summary of Sections 8 and 32 of the [full paper](../paper/PAPER_OBSERVABILITY_LAB.md)*

## Overview

DOF uses the Z3 SMT solver to provide **mathematical guarantees** — not just test coverage — that governance cannot be violated.

```bash
dof verify-states      # 8/8 PROVEN (107ms)
dof verify-hierarchy   # 42 patterns PROVEN (5ms)
dof prove              # 4 static theorems VERIFIED
```

## Static Theorems (v0.2.x — Section 8)

| Theorem          | Formal Statement                     | Result     | Time   |
|:-----------------|:-------------------------------------|:----------:|-------:|
| GCR Invariant    | `∀f∈[0,1]: GCR(f) = 1.0`            | **VERIFIED** | 0.30ms |
| SS Formula       | `∀f∈[0,1]: SS(f) = 1 − f³`          | **VERIFIED** | 0.19ms |
| SS Monotonicity  | `f₁ < f₂ ⟹ SS(f₁) > SS(f₂)`       | **VERIFIED** | 0.82ms |
| SS Boundaries    | `SS(0) = 1.0 ∧ SS(1) = 0.0`         | **VERIFIED** | 0.35ms |

Total: **1.66ms** for all 4 theorems.

## Dynamic Invariants (v0.3.x — Section 32)

| ID    | Property                                        | Result     | Time  |
|:------|:------------------------------------------------|:----------:|------:|
| INV-1 | `threat_detected → ¬publish_allowed`            | **PROVEN** | <15ms |
| INV-2 | `trust_score < 0.4 → attestation_count = 0`     | **PROVEN** | <15ms |
| INV-3 | `hierarchy_next ≤ hierarchy_current + 1`         | **PROVEN** | <15ms |
| INV-4 | `0 ≤ trust_score ≤ 1`                            | **PROVEN** | <10ms |
| INV-5 | `cooldown_active → ¬publish_allowed`             | **PROVEN** | <10ms |
| INV-6 | `hierarchy = GOVERNOR → trust_score > 0.8`       | **PROVEN** | <15ms |
| INV-7 | `safety_score = 1 − f³` (consistency)            | **PROVEN** | <10ms |
| INV-8 | `governance_violation → DEMOTE`                  | **PROVEN** | <15ms |

Total: **107.7ms** for all 8 invariants. 42 hierarchy patterns verified in **4.9ms**.

## Neurosymbolic Z3 Gate

```text
Agent Output → Z3Gate.validate_output() → APPROVED | REJECTED | TIMEOUT
                                              ↓          ↓          ↓
                                           Execute    Log+Escalate  Fallback to
                                                      counterexample deterministic
                                                                     layers
```

```python
from dof import Z3Gate, GateResult

gate = Z3Gate(constitution_rules, timeout_ms=5000)
result = gate.validate_trust_score("agent-1686", 0.95, evidence)

if result.result == GateResult.APPROVED:
    execute(action)                    # Z3 proved it's safe
elif result.result == GateResult.REJECTED:
    log(result.counterexample)         # Z3 shows exactly why
elif result.result == GateResult.TIMEOUT:
    fallback_to_deterministic_layers() # Never blocks pipeline
```

## On-Chain Proof Hash

Every attestation includes `z3_proof_hash` (keccak256 of serialized Z3 proof transcript), verifiable on-chain via `DOFProofRegistry.verifyProof()`.

```python
from dof import Z3ProofAttestation

proof = Z3ProofAttestation.from_gate_verification(result, "agent-1686", 0.95)
print(f"Hash: {proof.z3_proof_hash.hex()}")
print(f"Verified: {proof.verify()}")  # True
```

## Auto-Generated Tests

Z3 discovers edge cases humans wouldn't think of:
- **Counterexample tests**: Weakened invariant → Z3 finds violating inputs → unittest
- **Boundary tests**: threshold−ε, threshold, threshold+ε for each governance threshold
- **Threat pattern tests**: Minimal trigger/non-trigger inputs for 12 threat categories

Test progression: 807 (v0.2.8) → **986** (v0.3.3), with 207 Z3-specific tests.

## Details

- [Section 8: Static Verification](../paper/PAPER_OBSERVABILITY_LAB.md#8-formal-verification-via-z3-smt-solver)
- [Section 32: Neurosymbolic Verification](../paper/PAPER_OBSERVABILITY_LAB.md#32-neurosymbolic-formal-verification-layer-v03x)
