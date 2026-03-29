# Show HN: Formal governance for AI agents – Z3 proofs + on-chain attestations
## Hacker News Post — Draft for Publication
### Prepared: March 29, 2026

---

## TITLE (exact, copy-paste)

```
Show HN: Formal governance for AI agents – Z3 proofs + on-chain attestations
```

---

## BODY (exact, copy-paste — ~400 words)

```
I've been building a governance framework for autonomous AI agents called DOF-MESH
(Deterministic Observability Framework). The core idea: every agent action is verified
before execution using math, not another LLM.

What it actually does:

- Z3 SMT formal verification (4 theorems proven, <10ms): privilege escalation
  boundaries, instruction override detection, output integrity, scope containment
- 6-dimensional TRACER scoring (trust/reliability/autonomy/capability/economics/
  reputation) gates every agent output with ACCEPT/REJECT
- On-chain attestation: keccak256 hash of every governance decision written to
  Avalanche C-Chain. 21 immutable proofs on mainnet right now
- EvolveEngine: AlphaEvolve-inspired optimizer that re-weights TRACER dimensions
  against historical outcomes. Validated against 18,394 real evaluation records
  across 4 data sources. Result: current weights already score 0.9963/1.0 –
  confirming the governance theory matches empirical data
- MetaSupervisor: Q(40%) + Accuracy(25%) + Coherence(20%) + Format(15%) scoring,
  independent of any LLM

The data behind this (all real, independently verifiable):

- 4,902 adversarial evaluations (2,743 PASS / 2,159 FAIL) on real agent traffic
- 7,046 security hierarchy evaluations across 5 privilege layers (L0–L4)
- 6,441 Enigma bridge score records (proxy, uptime, oz_match, community)
- 21 on-chain attestations: 0x8004B663056A597Dffe9eCcC1965A193B7388713 on
  Snowtrace – independently queryable without asking me

Why deterministic instead of LLM-based governance?

If you use an LLM to verify another LLM's output, you've substituted one
non-deterministic system for another. You can't prove anything. Z3 gives you
proofs you can independently verify. The on-chain attestation means the audit
trail is public and immutable – I literally cannot alter a past governance decision.

Where this fits in the emerging agent stack:

ERC-8004 establishes who the agent is. x402 authorizes what it spends. DOF governs
whether its actions are safe to execute. Three complementary layers.

SDK:
  pip install dof-sdk  # 0.5.0, PyPI

  from dof import DOFVerifier
  verifier = DOFVerifier()
  result = verifier.verify_action(agent_id, action, params)
  # Returns: APPROVED | REJECTED + z3_proof

Built solo from Medellín in one month. Won The Synthesis hackathon (Privacy & x402
categories). Happy to answer questions about the Z3 implementation, the EvolveEngine
design, or why I think deterministic governance is the only technically honest approach
to this problem.

Repo: github.com/Cyberpaisa/DOF-MESH
```

---

## PRE-ANSWER: Top 3 Hardest Technical Questions

These will come. Have answers ready in the comments.

---

### Q1: "Z3 can only prove tautologies about your formal model, not about real agent behavior."

**Answer:**
Correct — and that's exactly the claim. Z3 doesn't verify the agent's intentions; it
verifies that the governance contract is internally consistent and that a given output
satisfies the formally specified invariants.

The 4 theorems are:
1. Privilege escalation is bounded: no agent can claim permissions beyond its registered scope
2. Override instructions are detectable: specific linguistic patterns trigger a hard block
3. Output integrity: the hash of the pre-governance output matches the post-check record
4. Scope containment: actions are bounded to the agent's declared capability set

If an agent produces an output that satisfies all 4 invariants, we can prove (not claim)
it passed the governance check. That's a narrower guarantee than "the agent behaved well
in some philosophical sense" — but it's a real, machine-verifiable guarantee, which is
more than LLM-based governance provides.

---

### Q2: "On-chain attestation doesn't bind the agent. You can just not call the contract."

**Answer:**
True for any system that makes the contract call optional. In DOF, the MetaSupervisor
is in the critical path — ACCEPT/REJECT happens before the action is executed. The
on-chain write happens at the same time. You can verify this in the SDK source:
`dof/verifier.py` → `verify_action()` is synchronous; it does not return an APPROVED
result without completing the attestation.

This is an architectural enforcement, not a policy. You'd have to modify the SDK to
bypass it — at which point you've explicitly removed governance, which is a different
kind of accountability.

---

### Q3: "TRACER scores are self-reported. How is this not just agents claiming to be trustworthy?"

**Answer:**
TRACER scores are computed externally, not reported by the agent. The 6 dimensions are
evaluated against observable behavioral data: on-chain transaction history, endpoint
uptime, adversarial test results, community reputation from independent sources. The
EvolveEngine validates the weights against 18,394 historical outcome records where we
know the ground truth (PASS/FAIL). An agent cannot manipulate its own TRACER score
any more than it can manipulate its own on-chain transaction history.

---

## KARMA STRATEGY (before posting)

Your account is new. HN de-ranks new accounts algorithmically. Steps to build karma
before the post goes live:

1. Comment 5-10 times on technical threads this week — genuine technical insight
2. Good targets: "Ask HN" threads, Show HN posts with technical questions, posts
   about AI agents, formal verification, blockchain governance
3. Aim for ~10-20 karma before posting Show HN
4. Post on a weekday between 8am-11am US Eastern time (peak HN traffic)
5. Be in the comments for the first 2 hours after posting — HN algorithm rewards
   engagement velocity

---

*DOF-MESH — Deterministic Observability Framework*
*Enigma Group — Medellín, Colombia — 2026*
