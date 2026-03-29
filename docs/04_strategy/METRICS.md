# DOF Metrics & Statistical Methodology

## Formal Metrics

### Stability Score (SS)

- **Domain**: [0, 1]
- **Formula**: SS(f) = 1 − f³ (Z3 verified)
- **Derivation**: With r=2 retries and independent failures at rate f, P(total\_failure) = f^(r+1) = f³
- **Derivative**: ∂SS/∂f = −3f² (strictly decreasing — more failures = less stability)
- **Z3 proof**: UNSAT (no counterexample exists)
- **Boundary conditions**: SS(0) = 1.0 (perfect), SS(1) = 0.0 (total failure) — Z3 verified
- **Monotonicity**: f₁ < f₂ ⟹ SS(f₁) > SS(f₂) — Z3 verified

### Provider Fragility Index (PFI)

- **Domain**: [0, 1]
- **Definition**: Fraction of runs with at least one provider failure event
- **Formula**: PFI(S) = |{s ∈ S : provider\_switched(s) = true}| / |S|
- **Empirical**: PFI(f) ≈ f under uniform failure injection
- **Interpretation**: PFI = 0.0 → no provider switches; PFI > 0.5 → systemic provider issues

### Retry Pressure (RP)

- **Domain**: [0, ∞)
- **Definition**: Cumulative retry burden normalized by step count
- **Formula**: RP(S) = Σ retries(s) / |S|
- **Empirical**: RP(f) ≈ f under uniform failure injection
- **Interpretation**: RP = 0.0 → no retries needed; RP > 1.0 → multiple retries per step on average

### Governance Compliance Rate (GCR)

- **Domain**: [0, 1]
- **Definition**: Fraction of runs passing all governance constraints
- **Formula**: GCR(S) = |{s ∈ S : governance\_passed(s) = true}| / |S|
- **Invariant**: GCR(f) = 1.0 ∀ f ∈ [0,1] (Z3 proven)
- **Proof**: Governance evaluation is a function of output content only — provider state variables do not appear in the function signature. Z3 confirms no counterexample exists.

### Supervisor Strictness Ratio (SSR)

- **Domain**: [0, 1]
- **Definition**: Fraction of completed runs escalated by the meta-supervisor
- **Formula**: SSR(R) = |{r ∈ R : status(r) = "escalated"}| / |R|
- **Interpretation**: SSR = 0.0 → all accepted; SSR = 1.0 → all escalated

### Adversarial Compliance Rate (ACR)

- **Domain**: [0, 1]
- **Definition**: Fraction of adversarial challenges where the DeterministicArbiter resolved through verifiable evidence
- **Formula**: ACR(I) = |{i ∈ I : arbiter\_resolved(i) = true}| / |I|
- **Interpretation**: ACR = 1.0 → all defects defensible; ACR = 0.0 → maximum adversarial exposure

---

## Statistical Methodology

- Each configuration: **n=20** independent runs under deterministic mode
- **Mean**: μ = (1/n) Σ xᵢ
- **Standard deviation**: σ = √((1/(n−1)) Σ (xᵢ − μ)²) — Bessel-corrected (sample std dev)
- Bernoulli-distributed proportions: σ consistent with finite-sample variance
- Maximum variance at p=0.5 (well-known Bernoulli property)
- **Rare tail events**: not statistically guaranteed at n=20
- **Confidence interval** (95%): μ ± t₍ₙ₋₁, 0.025₎ × σ/√n

---

## Parametric Sweep Results

120 runs across 6 failure rates (n=20 each), deterministic mode, seed=42:

| Failure Rate | SS (μ) | SS (σ) | PFI (μ) | PFI (σ) | RP (μ) | RP (σ) | GCR (μ) | SSR |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 0% | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| 10% | 0.9500 | 0.1539 | 0.1000 | 0.3078 | 0.1000 | 0.3078 | 1.0000 | 0.0000 |
| 20% | 0.9000 | 0.2052 | 0.2000 | 0.4104 | 0.2000 | 0.4104 | 1.0000 | 0.0000 |
| 30% | 0.8500 | 0.2351 | 0.3000 | 0.4702 | 0.3000 | 0.4702 | 1.0000 | 0.0000 |
| 50% | 0.7500 | 0.2565 | 0.5000 | 0.5130 | 0.5000 | 0.5130 | 1.0000 | 0.0000 |
| 70% | 0.6500 | 0.2351 | 0.7000 | 0.4702 | 0.7000 | 0.4702 | 1.0000 | 0.0000 |

**Key observations:**
- GCR = 1.0 at all failure rates (architectural invariant)
- SS follows cubic decay under theoretical model, linear under simulated 2-step recovery
- Maximum SS variance at f=0.5 (Bernoulli property)
- All 120 runs recovered through retry — zero permanent failures

---

## Assumptions

1. **Independent Failure Events** — Each provider failure is statistically independent. Correlated failures (e.g., shared infrastructure outages) are not modeled.
2. **Deterministic Execution Mode** — Fixed provider ordering, seeded PRNGs, deterministic failure injection indices.
3. **Bounded Retry Logic (r=2)** — Maximum 3 attempts per crew execution (1 original + 2 retries).
4. **Uniform Failure Injection** — First ⌊n × rate⌋ runs receive failure; remaining runs execute cleanly.
5. **Cubic Regime Validity (f ∈ [0,1])** — SS(f) = 1 − f³ assumes per-attempt failure probability in [0,1].

---

## Threat Model

- **In scope**: Adversarial infrastructure instability with non-malicious providers
- **Threat surface**: Rate limits, transient outages, timeout errors, degraded response quality, model incompatibilities, context length exceeded
- **NOT modeled**: Byzantine/adversarial provider manipulation (deliberately corrupted outputs)
- **Out of scope**: Security-layer adversaries (prompt injection, model jailbreaking, supply chain attacks)
- **Governance boundary**: Constitutional rules enforce output quality deterministically; governance is immune to provider state by architectural construction (Z3 proven)

---

## Reproducibility Guarantee

All experiments are reproducible under the following controlled conditions:

- **Fixed provider ordering**: Canonical sequence (Cerebras, Groq, NVIDIA, Zhipu)
- **Seeded PRNGs**: `random.seed(42)` at process initialization
- **Deterministic failure injection**: Index-based selection (first ⌊n × rate⌋ runs)
- **Version-locked dependencies**: `requirements.txt` with pinned versions
- **Structured JSONL trace logging**: Every run produces `logs/traces/{run_id}.json`
- **Z3 proof certificates**: `logs/z3_proofs.json` with theorem name, result, elapsed time, Z3 version

**Note**: LLM output randomness (temperature-based sampling) remains uncontrolled. Deterministic mode isolates infrastructure variables from model output variance.

---

## Combined Trust Score Formula

```
Combined = Gov(0.35) + Safety(0.15) + Alive(0.15) + Active(0.15) + Community(0.20)
```

Where:
- **Governance (0.35)** = GCR × 0.40 + SS × 0.30 + AST × 0.20 + ACR × 0.10
- **Safety (0.15)** = AST score (code verification via `ASTVerifier`)
- **Alive (0.15)** = Uptime/heartbeat (Centinela infrastructure monitoring)
- **Active (0.15)** = Transaction volume and recent activity
- **Community (0.20)** = Aggregated user ratings normalized to [0,1]

**Design rationale**: Governance receives the highest weight (0.35 individual, 0.50 aggregate with Safety) as the sole dimension backed by Z3 formal proofs. Infrastructure dimensions (Alive, Active) receive lower weights because they measure availability, not correctness.

**Current production values**: Combined trust score = 0.85 for both Apex Arbitrage (#1687) and AvaBuilder (#1686).

---

## Adversarial Benchmark Results

400 deterministic adversarial tests (seeded random, 50/50 clean/adversarial split):

| Category | Component | FDR | FPR | F1 | Tests |
|----------|-----------|-----|-----|-----|-------|
| Governance | ConstitutionEnforcer | 100.0% | 0.0% | 100.0% | 100 |
| Code Safety | ASTVerifier | 86.0% | 0.0% | 92.5% | 100 |
| Hallucination | DataOracle | 0.0% | 0.0% | 0.0% | 100 |
| Consistency | DataOracle | 0.0% | 0.0% | 0.0% | 100 |
| **Overall** | | | | **48.1%** | **400** |

**Honest assessment**: DOF excels at structural verification (governance, code safety) but lacks semantic verification capabilities (hallucination, consistency). Overall F1 of 48.1% reflects this gap. See `paper/PAPER_OBSERVABILITY_LAB.md` Section 24 for detailed interpretation.
