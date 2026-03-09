# Changelog — DOF (Decentralized Oracle Framework)

## [0.3.3] — 2026-03-09 — Z3 Proof Hash Attestations

### Added
- `core/z3_proof.py` — `Z3ProofAttestation` with keccak256 proof hash
- `core/proof_hash.py` — Deterministic proof serialization and hashing
- `core/proof_storage.py` — Local storage (default) + optional IPFS via Pinata
- `contracts/DOFProofRegistry.sol` — New on-chain proof registry (existing contracts untouched)
- Every attestation now includes `z3_proof_hash`, `invariants_verified`, `storage_ref`
- Public `verifyProof()` function — anyone can verify proofs on-chain
- `ProofRegistered` event for indexing

### Changed
- 3-layer publish pipeline now registers proofs: PG → Enigma → Avalanche + ProofRegistry
- Paradigm shift: trust-by-scoring → **trust-by-proof**

---

## [0.3.2] — 2026-03-09 — Auto-Counterexample Test Generation

### Added
- `core/z3_test_generator.py` — Converts Z3 counterexamples and boundary cases to unittest
- `core/boundary.py` — Boundary case engine using Z3 solver
- `.github/workflows/z3-verify.yml` — CI runs `verify-states` + `verify-hierarchy` on Z3 file changes
- `tests/z3_generated/` — Directory for auto-generated tests
- Z3 discovers edge cases humans wouldn't think of → auto-generates regression tests

---

## [0.3.1] — 2026-03-09 — Z3 Gate for Agent Outputs

### Added
- `core/z3_gate.py` — `Z3Gate` validates agent outputs before execution
- `core/agent_output.py` — `AgentOutput` protocol with `as_z3_constraints()`
- Neurosymbolic architecture: LLM proposes → Z3 approves/rejects with counterexample
- `GateResult`: APPROVED | REJECTED | TIMEOUT | FALLBACK
- Timeout gracefully delegates to deterministic layers (Constitution → AST → Arbiter → LoopGuard)

### Changed
- Meta-Supervisor decisions now gated by Z3 before execution
- Red/Blue agent outputs validated (they're already deterministic internally)

---

## [0.3.0] — 2026-03-09 — State Transition Verification

### Added
- `core/state_model.py` — `DOFAgentState` as Z3 symbolic variables
- `core/transitions.py` — `TransitionVerifier` with 8 formally proven invariants
- `core/hierarchy_z3.py` — All 42 hierarchy patterns translated to Z3 constraints
- CLI commands: `dof verify-states`, `dof verify-hierarchy`
- 8 invariants PROVEN: threat→blocked, trust bounds, hierarchy constraints, cooldown, governor auth, safety score, auto-correction

### Results
- `verify-states`: 8/8 PROVEN in 107.7ms
- `verify-hierarchy`: PROVEN (42 patterns) in 4.9ms
- Mathematical guarantee: no sequence of actions can violate governance

---

## [0.2.8] — 2026-03-09

### Fixed
- Closed missing threat patterns: "updated instructions", "root access for this session"
- Enterprise Report v5: 6/6 PASS APPROVED

## [0.2.7] — 2026-03-09

### Added
- `DOFThreatPatterns` 12 categories with `composite_detection` and `decode_and_scan`

## [0.2.6] — 2026-03-08

### Added
- `enforce_hierarchy` with 33 patterns in 2 categories

## [0.2.0] — 2026-03-07

### Added
- Initial PyPI release: 27K LOC, 25 modules, BSL-1.1 license
- Benchmark: Gov 100% FDR, Code 86%, Hallucination 90%, Consistency 100%, F1 96.8%
- Production agents #1686, #1687 (rank #1, #2 of 1,772)
