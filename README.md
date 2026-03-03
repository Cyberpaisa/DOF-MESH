# Deterministic Observability Framework for Multi-Agent LLM Systems

**Python 3.11+** | **Apache-2.0** | **2,252 LOC** | **9 core modules** | **120 parametric experiments executed**

---

## Problem

Multi-agent LLM systems operating across heterogeneous free-tier providers exhibit failure modes that cannot be characterized with existing orchestration tools. Provider rate limits, cascading retries, and non-deterministic output quality interact across execution steps. Without formal metrics and deterministic evaluation, observed differences cannot be attributed to specific variables.

## Key Contributions

1. **Five formal metrics** — Stability Score (SS), Provider Fragility Index (PFI), Retry Pressure (RP), Governance Compliance Rate (GCR), Supervisor Strictness Ratio (SSR) — with explicit mathematical formulations and domain specifications.
2. **Deterministic execution mode** — isolates infrastructure randomness from LLM output variance via fixed provider ordering and seeded PRNGs.
3. **Failure injection protocol** — controlled perturbations at configurable rates with index-based deterministic selection.
4. **Integrated observability stack** — run-level tracing (UUID v4), step-level checkpointing (JSONL), constitutional governance, meta-supervisor quality gating.
5. **Batch experiment runner** — automatic statistical aggregation (sample mean + Bessel-corrected std dev), 50+ runs per configuration.
6. **Parametric sensitivity analysis** — empirical validation that SS(f) follows linear degradation SS ≈ 1 − f/2, with GCR invariance across all failure rates.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Experiment Layer                    │
│   ExperimentDataset  │  BatchRunner  │  Schema       │
├─────────────────────────────────────────────────────┤
│                Observability Layer                   │
│  RunTrace  │  StepTrace  │  DerivedMetrics  │  Store │
├─────────────────────────────────────────────────────┤
│                 Crew Runner (Integration)            │
│  Orchestrates: Providers + Checkpoint + Governance   │
│                + Supervisor + Metrics + Traces        │
├──────────┬──────────┬───────────┬───────────────────┤
│ Provider │Checkpoint│Governance │  Meta-Supervisor   │
│ Manager  │ Manager  │ Enforcer  │  (Quality Gate)    │
│ TTL/Back │ JSONL    │ Hard/Soft │  Q+A+C+F Scoring   │
│ off/Rec. │ Steps    │ Rules     │  ACCEPT/RETRY/ESC  │
├──────────┴──────────┴───────────┴───────────────────┤
│               Metrics Logger (JSONL + Rotation)      │
└─────────────────────────────────────────────────────┘
```

## Metrics

| Metric | Symbol | Domain | Interpretation |
|--------|--------|--------|----------------|
| Stability Score | SS | [0, 1] | Fraction of runs completing without failure |
| Provider Fragility Index | PFI | [0, 1] | Fraction of runs with at least one provider failure |
| Retry Pressure | RP | [0, 1] | Fraction of runs requiring retry attempts |
| Governance Compliance Rate | GCR | [0, 1] | Fraction of runs passing all governance checks |
| Supervisor Strictness Ratio | SSR | [0, 1] | Fraction of completed runs rejected by supervisor |

## Parametric Sweep Results

120 runs across 6 failure rates (n=20 each), deterministic mode:

| Failure Rate | SS (μ±σ) | PFI (μ±σ) | RP (μ±σ) | GCR | SSR |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 0% | 1.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 1.0 | 0.0 |
| 10% | 0.95 ± 0.15 | 0.10 ± 0.31 | 0.10 ± 0.31 | 1.0 | 0.0 |
| 20% | 0.90 ± 0.21 | 0.20 ± 0.41 | 0.20 ± 0.41 | 1.0 | 0.0 |
| 30% | 0.85 ± 0.24 | 0.30 ± 0.47 | 0.30 ± 0.47 | 1.0 | 0.0 |
| 50% | 0.75 ± 0.26 | 0.50 ± 0.51 | 0.50 ± 0.51 | 1.0 | 0.0 |
| 70% | 0.65 ± 0.24 | 0.70 ± 0.47 | 0.70 ± 0.47 | 1.0 | 0.0 |

GCR = 1.0 across all rates confirms governance is structurally decoupled from provider failures.

## Quickstart

```bash
# 1. Clone
git clone <repo-url> && cd equipo-de-agentes

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure providers
cp .env.example .env
# Edit .env with your API keys

# 4. Run baseline experiment (10 runs, no failures)
python -c "
from core.experiment import run_experiment
result = run_experiment(n_runs=10, deterministic=True)
print(f'SS={result[\"aggregate\"][\"ss_mean\"]}, GCR={result[\"aggregate\"][\"gcr_mean\"]}')
"

# 5. Run parametric sweep (120 runs)
python -c "
from core.experiment import run_parametric_sweep
run_parametric_sweep(rates=[0.0, 0.1, 0.2, 0.3, 0.5, 0.7], n_runs=20)
"
```

## Project Structure

```
core/
  __init__.py          # Public API exports
  providers.py         # Provider resilience (TTL, backoff, rotation, singleton)
  checkpointing.py     # Step-level JSONL checkpointing
  governance.py        # Constitutional enforcement (hard/soft rules)
  supervisor.py        # Meta-supervisor quality gate (Q+A+C+F)
  metrics.py           # Structured JSONL metrics logging
  memory_manager.py    # Agent memory management
  crew_runner.py       # Integration layer (FASE 0 + FASE 1)
  observability.py     # RunTrace, StepTrace, derived metrics, deterministic mode
  experiment.py        # Batch runner, parametric sweep, failure injection
paper/
  PAPER_OBSERVABILITY_LAB.md   # Technical paper (8,700+ words)
experiments/
  schema.json          # Experiment output schema
  parametric_sweep.csv # 120-run sweep results
release_artifacts/
  v1.0/                # Pre-fix metric snapshots for audit
tests/
  test_report.py       # Test incident logging and reporting
examples/              # Mock API demos (see mock_api_server.py)
docs/                  # Internal design documents
```

## Citation

```bibtex
@article{cyberpaisa2026deterministic,
  title={Deterministic Observability and Resilience Engineering for Multi-Agent LLM Systems: An Experimental Framework},
  author={Cyber Paisa and Enigma Group},
  year={2026},
  note={2,252 LOC, 120 parametric experiments, 5 formal metrics}
}
```

## License

[Apache License 2.0](LICENSE) — Copyright 2026 Cyber Paisa / Enigma Group.

## Resilience & Deterministic Observability

Formal resilience specification available at:
[docs/research/deterministic-observability-framework.md](docs/research/deterministic-observability-framework.md)
