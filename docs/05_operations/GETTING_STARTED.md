# Getting Started with DOF

## Why DOF?

Production AI agent systems face three unsolved problems: **hallucination governance** (who checks the checker?), **reproducibility** (can you reproduce a failure?), and **formal guarantees** (can you *prove* a safety property holds?). Existing frameworks delegate these to LLMs — creating circular dependencies where the evaluator shares the same failure modes as the evaluated [Huyen, *AI Engineering*, O'Reilly 2025].

DOF takes a different approach: **zero-LLM governance**. Every governance decision — constitutional enforcement, AST verification, formal proofs — is made by deterministic code and Z3 SMT solvers, not by another language model. This means:

- **GCR = 1.0 proven invariant** — Governance Compliance Rate cannot degrade, verified by Z3
- **8 state-transition invariants** — machine-checkable proofs that trust scores, provider selection, and escalation paths behave correctly
- **Adversarial benchmarking** — 58.4% detection rate against NVIDIA Garak attack probes, with regression tracking to prevent silent degradation
- **Full auditability** — every decision logged in JSONL, every proof reproducible

If your agents need to be *provably* safe rather than *probably* safe, DOF provides the formal foundation.

## Installation (30 seconds)

```bash
pip install dof-sdk
```

## Quick Verification (1 minute)

```python
from dof import GenericAdapter

adapter = GenericAdapter()
result = adapter.wrap_output("Your agent output here")
print(result)
# {'status': 'pass', 'violations': [], 'score': 8.5}
```

## Z3 Formal Verification (2 minutes)

```python
from dof import verify

# Verify all 4 static theorems
proofs = verify()
for p in proofs:
    print(f"{p.theorem_name}: {p.result} ({p.proof_time_ms:.1f}ms)")
```

## Z3 State Transition Verification (2 minutes)

```python
from dof import TransitionVerifier

verifier = TransitionVerifier()
results = verifier.verify_all()
for inv_id, result in results.items():
    print(f"{inv_id}: {result.status} ({result.verification_time_ms:.1f}ms)")
# INV-1: PROVEN (12.3ms)
# ... 8/8 PROVEN
```

## Z3 Gate — Validate Before Execute (3 minutes)

```python
from dof import Z3Gate, GateResult

# Create gate with your constitution rules
gate = Z3Gate(constitution_rules, timeout_ms=5000)

# Validate a trust score assignment
result = gate.validate_trust_score(
    agent_id="my-agent-001",
    proposed_score=0.95,
    evidence={"tests_passed": True, "governance_compliant": True}
)

if result.result == GateResult.APPROVED:
    print("Safe to execute — Z3 proved it")
elif result.result == GateResult.REJECTED:
    print(f"Blocked — counterexample: {result.counterexample}")
```

## x402 Trust Gateway (3 minutes)

```python
from dof import TrustGateway

gateway = TrustGateway()
verdict = gateway.verify(response_body=agent_response)
print(f"Action: {verdict.action}")  # ALLOW / WARN / BLOCK
print(f"Score: {verdict.governance_score}")
```

## On-Chain Proof Attestation (3 minutes)

```python
from dof import Z3ProofAttestation

# Create attestation with proof hash
proof = Z3ProofAttestation.from_gate_verification(
    gate_result=result,
    agent_id="my-agent-001",
    trust_score=0.95
)

print(f"Proof hash: {proof.z3_proof_hash.hex()}")
print(f"Verified: {proof.verify()}")  # True
print(f"Invariants: {proof.invariants_verified}")  # ['INV-1', ..., 'INV-8']
```

## CLI Commands

```bash
dof verify "your text"     # Governance check
dof prove                  # Z3 static proofs
dof verify-states          # 8 dynamic invariants
dof verify-hierarchy       # 42 hierarchy patterns
dof health                 # Component status
dof benchmark              # Adversarial benchmark
dof privacy                # Privacy benchmark
dof version                # Show version
```

## Architecture at a Glance

```text
5 Deterministic Layers (no LLM):
  Constitution → AST → Z3 → Arbiter → LoopGuard

2 LLM Layers (gated by Z3 in v0.3.x):
  Meta-Supervisor → [Z3 Gate] → Execute
  Red/Blue Output → [Z3 Gate] → Apply

Attestation Pipeline:
  PG (200ms) → Enigma (900ms) → Conflux eSpace (2s) + DOFProofRegistry
                                                    ↑
                                            z3_proof_hash included
```

## Next Steps

- [Full Paper](../paper/PAPER_OBSERVABILITY_LAB.md) — 32 sections of technical depth
- [CHANGELOG](../CHANGELOG.md) — Version history
- [Lessons Learned](../LESSONS_LEARNED.md) — 40+ operational lessons
- [PyPI](https://pypi.org/project/dof-sdk/) — Package page
