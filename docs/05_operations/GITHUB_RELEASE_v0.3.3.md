# DOF v0.3.3 — Z3 Formal Verification: Trust-by-Proof

> "We don't trust the AI. We trust the Math."

## What Changed

DOF evolved from **trust-by-scoring** to **trust-by-proof**. Every trust score is now backed by a mathematical guarantee, not just a probabilistic assessment.

### 4 Phases in 1 Release

| Phase | Version | What it does |
|-------|---------|-------------|
| State Verification | v0.3.0 | Proves governance is mathematically inviolable |
| Z3 Gate | v0.3.1 | LLM proposes → Z3 approves or rejects with proof |
| Auto-Test Gen | v0.3.2 | Z3 discovers edge cases → generates regression tests |
| Proof Attestations | v0.3.3 | On-chain proof hash, verifiable by anyone |

### Numbers

```
Tests:           986 PASS (0 failures)
Z3 new tests:    207/207 PASS
verify-states:   8/8 PROVEN (107.7ms)
verify-hierarchy: PROVEN — 42 patterns (4.9ms)
New modules:     10 in core/
New files:       15 total
New contract:    DOFProofRegistry.sol
```

### New Modules

- `core/state_model.py` — Agent state as Z3 symbolic variables
- `core/transitions.py` — Transition verifier with 8 proven invariants
- `core/hierarchy_z3.py` — 42 hierarchy patterns as Z3 constraints
- `core/z3_gate.py` — Neurosymbolic gate: validates before execution
- `core/agent_output.py` — Output protocol with Z3 constraint translation
- `core/boundary.py` — Boundary case discovery engine
- `core/z3_test_generator.py` — Auto-generates tests from counterexamples
- `core/z3_proof.py` — Attestation with keccak256 proof hash
- `core/proof_hash.py` — Deterministic proof serialization
- `core/proof_storage.py` — Local (default) + optional IPFS storage

### 8 Proven Invariants

| ID | Invariant | Status |
|----|-----------|--------|
| INV-1 | Threat detected → publish blocked | ✅ PROVEN |
| INV-2 | Low trust → no attestation | ✅ PROVEN |
| INV-3 | No hierarchy jumps without auth | ✅ PROVEN |
| INV-4 | Trust score always in [0,1] | ✅ PROVEN |
| INV-5 | Cooldown prevents re-publish | ✅ PROVEN |
| INV-6 | Governor requires trust > 0.8 | ✅ PROVEN |
| INV-7 | SS(f) = 1-f³ consistency | ✅ PROVEN |
| INV-8 | Governance violation → auto-demote | ✅ PROVEN |

### Breaking Changes

None. Fully backward-compatible. Existing 21 on-chain attestations remain valid. Existing contracts untouched — `DOFProofRegistry.sol` is a new companion contract.

### Install

```bash
pip install dof-sdk==0.3.3
```

```python
from dof import TransitionVerifier, Z3Gate, Z3ProofAttestation

# Verify all governance invariants
verifier = TransitionVerifier()
results = verifier.verify_all()  # 8/8 PROVEN

# Gate an LLM decision
gate = Z3Gate(constitution_rules)
result = gate.validate_trust_score("agent-1686", 0.95, evidence)
# result.result == GateResult.APPROVED → safe to execute

# Create proof attestation
proof = Z3ProofAttestation.from_gate_verification(result, "agent-1686", 0.95)
print(proof.z3_proof_hash.hex())  # keccak256, verifiable on-chain
```

---

**Full Changelog**: v0.2.8...v0.3.3
