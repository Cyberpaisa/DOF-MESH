# DOF Determinism Checklist — v0.3.3

Run before every release. All items must pass.

## Constitutional Layer (L1)
- [ ] dof verify-states → 8/8 PROVEN
- [ ] dof verify-hierarchy → 42 patterns PROVEN
- [ ] Same input → same classify_error result (run 10x, compare hashes)
- [ ] 4 HARD rules are immutable (check SHA of constitution config)
- [ ] 5 SOFT rules have fixed thresholds (not LLM-derived)

## Z3 Layer (L4)
- [ ] z3_proof_hash is identical for same proof transcript across builds
- [ ] verify-hierarchy passes in <10ms consistently
- [ ] Z3 Gate TIMEOUT activates documented fallback (not silent)
- [ ] All 8 invariants hold under get_execution_trace output

## On-Chain Layer (L7)
- [ ] DOFProofRegistry.verifyProof() returns true for all existing hashes
- [ ] Merkle batch produces identical root across 3 independent runs
- [ ] get_execution_trace(run_id) trace_hash is deterministic

## Regression
- [ ] dof regression-check exits 0 (no regressions vs baseline)
- [ ] All 5 RegressionTracker subsystems green
  - Z3 subsystem
  - hierarchy subsystem
  - tests subsystem
  - Garak subsystem
  - llm_routing subsystem (new v0.3.3)

## Anti-False Positives
- [ ] FPR = 0% on internal adversarial benchmark (400 tests)
- [ ] Garak detection >= 58.4% (12,229 payloads)
- [ ] Privacy detection >= 71% (7 AgentLeak channels)
