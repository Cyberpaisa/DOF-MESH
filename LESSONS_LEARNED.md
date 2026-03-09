# Lessons Learned

## v0.2.7

- Lección: Los patrones de detección exacta son case-sensitive y literal — 'root access for this session' no matchea si el patrón dice otra cosa. Siempre verificar con el payload exacto del test antes de publicar en PyPI.

## v0.2.8

- Lección: Nunca subir a PyPI antes de correr el Colab de validación — el orden correcto es: fix → tests locales → PyPI → Colab → reporte.

# ────────────────────────────────────
# LESSONS LEARNED — DOF v0.3.x Z3 Enhancement
# Append to existing LESSONS_LEARNED.md

---

## v0.3.x — Z3 Formal Verification (2026-03-09)

### Architecture Lessons

**L-30: Validate plans against codebase BEFORE implementing.**
Created a Z3 enhancement plan with 8 structural assumptions. Validated against
real code and found 8 discrepancies (wrong paths, wrong test framework, wrong
pattern counts, wrong Solidity approach). Correcting the plan first saved hours
of rework. Rule: plan → validate → correct → implement.

**L-31: New Solidity contracts, never modify on-chain ones.**
The plan originally modified the existing attestation contract. But that contract
already has 21 attestations on mainnet. Created DOFProofRegistry.sol as a
companion contract instead. Same principle as L-1 (never share DB tables):
on-chain state is immutable history — add new contracts, don't touch deployed ones.

**L-32: Gate validates outputs, not internals.**
Original plan gated Red/Blue agent decisions. But they're already deterministic
internally — only their outputs affect downstream behavior. Gate the exit,
not the engine. Applied same logic to Meta-Supervisor: gate what gets executed,
not the LLM's internal reasoning.

**L-33: IPFS optional, local default.**
Plan required Pinata IPFS for proof storage. But this adds external dependency
to the publish pipeline (which was zero-external-dep for layers 1-2). Made IPFS
optional with automatic fallback to local storage. Never add required external
deps to critical paths.

**L-34: enforce_hierarchy is 33 patterns in 2 categories, not 22 in 6.**
Read the actual code before writing Z3 translations. The plan assumed 22 patterns
in 6 categories. Reality: 33 patterns (_SYSTEM_OVERRIDE_PATTERNS + 
_RESPONSE_VIOLATION_PATTERNS) in 2 categories. By v0.3.0, expanded to 42 patterns.
Lesson: count the actual patterns, don't assume from memory.

### Z3-Specific Lessons

**L-35: Z3 Real, not Float.**
Z3 Real type gives exact arithmetic. Float gives IEEE 754 approximations.
For trust scores that need to be exactly 0.4 or exactly 0.8, Real is required.
Float would give 0.39999999... and break boundary comparisons.

**L-36: Always push()/pop() to isolate Z3 queries.**
Without push/pop, adding constraints for one invariant check pollutes the
solver state for the next check. Every validate_*() method must push before
adding constraints and pop after checking.

**L-37: Deterministic proof serialization is non-trivial.**
For proof hashes to be verifiable, the same solver state must produce the
same transcript byte-for-byte. Sort assertions, normalize variable names,
use fixed decimal precision. Test determinism with: hash(serialize(proof))
called twice on same input must match.

**L-38: Z3 timeout = FALLBACK, never FAIL.**
If Z3 can't decide within timeout (default 5s), delegate to the deterministic
governance stack. Z3 is additive security. It should improve the pipeline,
never block it. Log the timeout, let the existing layers handle it.

### Process Lessons

**L-39: Mega-prompt with phase structure works for large implementations.**
The 4-phase prompt with explicit file lists, class specs, method signatures,
and success criteria per phase produced 15 files, 207 tests, and a Solidity
contract in one session. Key factors: (1) context from memory about real
codebase structure, (2) validated corrections, (3) clear phase ordering,
(4) explicit test counts and pass criteria.

**L-40: Document the "why" separately from the "how".**
The plan document (DOCX) explains WHY each phase matters with research backing.
The prompt (MD) specifies HOW to implement with exact file paths and method sigs.
Keeping them separate means the plan survives code refactors and the prompt
survives goal changes.

### Metrics

- Plan validation found 8 corrections (100% were structural, 0% conceptual)
- Implementation: 15 files, 10 core modules, 986 tests, 0 failures
- verify-states: 8/8 PROVEN in 107.7ms
- verify-hierarchy: PROVEN (42 patterns) in 4.9ms
- Zero regressions on 807 existing tests
