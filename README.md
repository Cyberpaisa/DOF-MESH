# Deterministic Observability Framework for Multi-Agent LLM Systems

> A research-grade deterministic orchestration and observability framework for multi-agent LLM systems operating under adversarial infrastructure constraints.
>
> This repository formalizes reproducible experimentation, resilience metrics, controlled degradation modeling, governance invariance, and deterministic evaluation in heterogeneous provider environments.

Python 3.11+ | Apache-2.0 | 2,400+ LOC | 11 core modules | 120 parametric experiments executed

---

## Abstract

Multi-agent LLM systems operating across heterogeneous providers exhibit infrastructure-induced instability that cannot be rigorously characterized using conventional orchestration tooling. Rate limits, cascading retries, infrastructure-induced degradation, and non-deterministic provider behavior introduce execution variance that obscures causal attribution.

This framework establishes a deterministic execution regime, formal resilience metrics, controlled failure injection protocols, empirical parametric validation, and reproducibility guarantees to model stability degradation under bounded retry logic. Experimental evidence supports a linear degradation regime:

SS(f) ≈ 1 − (f / 2)

while constitutional governance enforcement remains invariant:

GCR(f) = 1.0

The system provides a reproducible experimental substrate for evaluating resilience in multi-agent LLM systems under adversarial infrastructure perturbations.

---

## Problem

Multi-agent LLM systems operating across heterogeneous free-tier providers exhibit failure modes that cannot be characterized using conventional orchestration tools. Provider rate limits, cascading retries, and non-deterministic output quality interact across execution steps, producing unstable system-level behavior.

Without formal metrics and deterministic evaluation, observed performance differences cannot be attributed to specific infrastructure variables. Infrastructure variance and model stochasticity become conflated, preventing scientific reproducibility and causal isolation.

---

## Key Contributions

1. Five formal metrics — Stability Score (SS), Provider Fragility Index (PFI), Retry Pressure (RP), Governance Compliance Rate (GCR), and Supervisor Strictness Ratio (SSR) — with explicit mathematical domains and operational definitions.

2. Deterministic execution mode — isolates infrastructure randomness from model stochasticity via fixed provider ordering and seeded pseudo-random number generators.

3. Failure injection protocol — controlled perturbations at configurable rates using deterministic index-based selection.

4. Integrated observability stack — run-level tracing (UUID v4), step-level JSONL checkpointing, constitutional governance enforcement, and meta-supervisor quality gating.

5. Batch experiment runner — automatic statistical aggregation (sample mean with Bessel-corrected standard deviation) across repeated trials.

6. Parametric sensitivity analysis — experimental validation that SS(f) ≈ 1 − (f / 2) while GCR remains invariant across all tested failure rates.

7. Governance–Infrastructure Decoupling Validation — empirical confirmation that constitutional enforcement remains invariant under infrastructure degradation.

---

## Architecture

┌─────────────────────────────────────────────────────┐
│                  Experiment Layer                  │
│   ExperimentDataset  │  BatchRunner  │  Schema     │
├─────────────────────────────────────────────────────┤
│                Observability Layer                 │
│  RunTrace  │  StepTrace  │  DerivedMetrics  │ Store│
├─────────────────────────────────────────────────────┤
│              Crew Runner (Integration)             │
│  Providers + Checkpoint + Governance + Supervisor  │
│             + Metrics + Determinism                │
├──────────┬──────────┬───────────┬──────────────────┤
│ Provider │Checkpoint│Governance │  Meta-Supervisor │
│ Manager  │ Manager  │ Enforcer  │  (Quality Gate)  │
│ TTL/Back │ JSONL    │ Hard/Soft │  Q+A+C+F Scoring │
│ off/Rec. │ Steps    │ Rules     │  ACCEPT/RETRY/ESC│
├──────────┴──────────┴───────────┴──────────────────┤
│          Metrics Logger (JSONL + Rotation)         │
└─────────────────────────────────────────────────────┘

---

## Metrics

Metric: Stability Score (SS)  
Domain: [0,1]  
Definition: Fraction of runs completing without terminal failure.

Metric: Provider Fragility Index (PFI)  
Domain: [0,1]  
Definition: Mean provider failure count per execution, normalized over batch size.

Metric: Retry Pressure (RP)  
Domain: [0,1]  
Definition: Mean retry count per execution, normalized over batch size.

Metric: Governance Compliance Rate (GCR)  
Domain: [0,1]  
Definition: Fraction of runs passing all governance constraints.

Metric: Supervisor Strictness Ratio (SSR)  
Domain: [0,1]  
Definition: Fraction of completed runs rejected by the meta-supervisor.

All metrics are defined over finite experimental batches of size n ≥ 1.

---

## Theoretical Model

Let:

f ∈ [0,1] be the provider-level failure injection probability  
SS ∈ [0,1] be the Stability Score  
PFI ∈ [0,1] be the Provider Fragility Index  
RP ∈ [0,1] be the Retry Pressure  
GCR ∈ [0,1] be the Governance Compliance Rate  

Assuming deterministic execution mode and statistically independent provider failures:

PFI(f) ≈ f  
RP(f) ≈ f  

Under bounded retry and recovery logic, experimental evidence indicates a linear degradation regime:

SS(f) ≈ 1 − (f / 2)

Hence:

∂SS/∂f ≈ −0.5

Governance remains structurally decoupled from infrastructure instability:

GCR(f) = 1.0  ∀ f ∈ [0,1]

This establishes a linear stability degradation regime under controlled failure injection while constitutional enforcement remains invariant.

---

## Assumptions

1. Independent Failure Events — Provider failures are statistically independent across execution steps.
2. Deterministic Execution Mode — Fixed provider ordering and seeded PRNGs isolate infrastructure variance from model stochasticity.
3. Bounded Retry Logic — Retry attempts are capped and recovery policies are deterministic.
4. Uniform Failure Injection — Failure probability f is applied uniformly without structural bias.
5. Linear Regime Validity — The approximation SS(f) ≈ 1 − (f / 2) holds within the explored range f ∈ [0,0.7].

---

## Limitations

1. No correlated or cascading failure modeling.
2. Retry policies are static and non-adaptive.
3. Economic cost and latency modeling are excluded.
4. Deterministic results may not generalize to fully stochastic deployments.
5. Finite sample evaluation (n=20 per configuration) may not capture rare tail events.

---

## Threat Model

The framework assumes adversarial infrastructure instability but non-malicious providers. Threat surface includes rate limits, transient outages, timeout errors, and degraded response quality. Byzantine or adversarial provider manipulation is not modeled. Security-layer adversaries are out of scope.

---

## Reproducibility Guarantee

All experiments are reproducible under deterministic mode with:
- Fixed provider ordering
- Seeded pseudo-random number generators
- Deterministic failure injection indices
- Version-locked dependencies
- Structured JSONL trace logging

Re-running experiments with identical configuration yields identical aggregate metrics within floating-point tolerance.

---

## Statistical Methodology

Each configuration is evaluated with n = 20 independent runs under deterministic execution mode.

Aggregate metrics are reported as:

μ = (1/n) Σ xᵢ  
σ = sqrt( (1/(n−1)) Σ (xᵢ − μ)² )

where σ corresponds to the Bessel-corrected sample standard deviation.

Given that several metrics are Bernoulli-distributed proportions, the reported σ values are consistent with finite-sample variance under bounded support in [0,1].

The chosen sample size balances computational cost and variance stabilization under deterministic constraints. Rare tail-event estimation is not statistically guaranteed.

---

## Parametric Sweep Results

120 runs across 6 failure rates (n=20 each), deterministic mode:

Failure Rate | SS (μ±σ) | PFI (μ±σ) | RP (μ±σ) | GCR | SSR
0%  | 1.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 1.0 | 0.0
10% | 0.95 ± 0.15 | 0.10 ± 0.31 | 0.10 ± 0.31 | 1.0 | 0.0
20% | 0.90 ± 0.21 | 0.20 ± 0.41 | 0.20 ± 0.41 | 1.0 | 0.0
30% | 0.85 ± 0.24 | 0.30 ± 0.47 | 0.30 ± 0.47 | 1.0 | 0.0
50% | 0.75 ± 0.26 | 0.50 ± 0.51 | 0.50 ± 0.51 | 1.0 | 0.0
70% | 0.65 ± 0.24 | 0.70 ± 0.47 | 0.70 ± 0.47 | 1.0 | 0.0

GCR = 1.0 across all rates confirms governance invariance under infrastructure perturbation.

---

## Production Runtime Integration

The framework transitions from offline simulation to production-grade runtime integration. All execution entrypoints (`main.py`, `a2a_server.py`) delegate to `core.crew_runner.run_crew()`, which orchestrates the full observability pipeline on every request.

### Runtime Execution Pipeline

```
Entrypoint (main.py | a2a_server.py)
│
▼
crew_runner.run_crew(crew_name, crew, input_text, crew_factory)
│
├── ProviderManager ── TTL-based backoff, exhaustion marking, rotation
├── crew.kickoff()  ── CrewAI agent execution
├── ConstitutionEnforcer ── Hard rules (block) + Soft rules (score)
├── MetaSupervisor ── Q+A+C+F quality scoring
├── RunTrace + StepTrace ── JSONL observability
├── CheckpointManager ── Step-level JSONL persistence
└── MetricsLogger ── JSONL with rotation
│
▼
Decision: ACCEPT | RETRY (rebuild via crew_factory) | ESCALATE
```

Prior to integration, entrypoints called `crew.kickoff()` directly — bypassing supervisor, governance, provider management, and tracing. This constituted blind execution with no quality guarantees.

### Meta-Supervisor Scoring Model

The supervisor evaluates final output quality using a weighted linear combination:

S = Q(0.40) + A(0.25) + C(0.20) + F(0.15)

where:
- Q ∈ [0,10]: Structural quality (headers, organization, coherence)
- A ∈ [0,10]: Actionability (concrete recommendations, next steps)
- C ∈ [0,10]: Completeness (coverage of requested scope)
- F ∈ [0,10]: Factuality (source citations, verifiable claims)

Decision thresholds (calibration phase):
- ACCEPT: S ≥ 7.0
- RETRY:  S ≥ 5.0 (max 2 retries, crew rebuilt via factory)
- ESCALATE: S < 5.0

Thresholds are intentionally relaxed during calibration. Production targets: ACCEPT ≥ 8.0, RETRY ≥ 6.0.

### Provider Resilience — crew_factory Pattern

CrewAI binds LLM instances at crew construction time. If a provider fails mid-execution, retrying with the same crew object reuses the exhausted provider. LiteLLM fallback parameters are not propagated by CrewAI's internal completion calls.

Solution: `crew_factory` — a callable that reconstructs the crew with fresh LLM assignments on each retry. When `ProviderManager` marks a provider as exhausted, the factory calls `get_llm_for_role()` which skips exhausted providers and selects the next available in the chain.

Provider chains per role:

| Role | Chain (first available wins) |
|---|---|
| Research Analyst | Groq (Llama 3.3) → NVIDIA (DeepSeek V3.2) → Cerebras (GPT-OSS) → Zhipu (GLM-4.7) |
| Code Architect | NVIDIA (Kimi K2.5) → Groq (Kimi K2) → Cerebras (GPT-OSS) → Zhipu (GLM-4.7) |
| MVP Strategist | NVIDIA (Qwen3.5-397B) → Cerebras (GPT-OSS) → Zhipu (GLM-4.7) → Groq (Llama 3.3) |
| Verifier | Cerebras (GPT-OSS) → Groq (Llama 3.3) → NVIDIA (DeepSeek V3.2) → Zhipu (GLM-4.7) |

### Optimized Agent Pipeline

Research crew reduced from 5 sequential tasks to 3:

| Phase | Agent | Function |
|---|---|---|
| 1 | Research Analyst | Deep web research + source gathering |
| 2 | Verifier | Fact-checking, claim validation, scoring |
| 3 | MVP Strategist | Final plan incorporating verified data only |

Removed: redundant QA Reviewer and duplicate Strategist pass. Measured reduction: 11m → 4m48s (56% faster).

### Empirical Production Validation

| Metric | Before Integration | After Integration |
|---|---|---|
| Supervisor in runtime | No (blind execution) | Yes (every request) |
| Governance enforcement | No | Yes (hard + soft rules) |
| Provider rotation on failure | Crash | Automatic via crew_factory |
| Execution time (research) | 10m56s (5 tasks) | 4m48s (3 tasks) |
| Tracing | None | RunTrace + StepTrace JSONL |
| Groq TPD exhaustion | Terminal failure | Automatic rotation to NVIDIA/Cerebras |

---

## Quickstart

1. Clone repository  
git clone https://github.com/Cyberpaisa/deterministic-observability-framework.git
cd deterministic-observability-framework  

2. Install dependencies  
pip install -r requirements.txt  

3. Configure providers  
cp .env.example .env  
Edit .env with your API keys  

4. Run baseline experiment  
python -c "from core.experiment import run_experiment; result = run_experiment(n_runs=10, deterministic=True); print(result['aggregate'])"

5. Run parametric sweep  
python -c "from core.experiment import run_parametric_sweep; run_parametric_sweep(rates=[0.0,0.1,0.2,0.3,0.5,0.7], n_runs=20)"

---

## Project Structure

```
main.py                    # Interactive entrypoint with supervisor
a2a_server.py              # A2A HTTP entrypoint with supervisor
crew.py                    # Agent and crew factories
llm_config.py              # Provider chain configuration

core/
  crew_runner.py            # Orchestrator with crew_factory rotation
  providers.py              # TTL-based provider management
  checkpointing.py          # Step-level JSONL persistence
  governance.py             # Constitutional enforcement (hard + soft)
  supervisor.py             # Meta-supervisor quality gating
  metrics.py                # Structured JSONL metrics with rotation
  memory_manager.py         # Agent memory management
  observability.py          # RunTrace, StepTrace, derived metrics
  experiment.py             # Batch runner, parametric sweep

config/
  agents.yaml               # 17 agent definitions
  tasks.yaml                # 10 task definitions

paper/
  PAPER_OBSERVABILITY_LAB.md

experiments/
  schema.json
  parametric_sweep.csv

release_artifacts/
  v1.0/

tests/
examples/
docs/
```

---

## Citation

@article{cyberpaisa2026deterministic,
  title={Deterministic Observability and Resilience Engineering for Multi-Agent LLM Systems: An Experimental Framework},
  author={Cyber Paisa and Enigma Group},
  year={2026},
  note={2,400+ LOC, 120 parametric experiments, 5 formal metrics}
}

---

## License

Apache License 2.0 — Copyright 2026 Cyber Paisa / Enigma Group.                                                                                 
