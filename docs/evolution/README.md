# DOF-MESH Evolution Engine

## What it is

A self-improving evolutionary system for AI agent governance.
Inspired by AlphaEvolve (DeepMind, 2025).

The Evolution Engine converts governance rules into evolving DefenseRules
that improve automatically each generation — no human intervention,
no LLM in the governance loop.

## How it works

Each generation follows this deterministic cycle:

```
1. Measure current ASR (Attack Success Rate)
2. Select lowest-fitness DefenseRules
3. Mutate and recombine them (crossover)
4. Apply new population to governance.py
5. Validate: 160 tests must pass
6. If ASR drops → commit + on-chain attestation
7. If ASR rises → automatic rollback (git stash pop)
```

## Public components

| Module | Function |
|--------|---------|
| `genome.py` | `PatternGene` dataclass — basic evolutionary unit |
| `fitness.py` | Score = 40% coverage + 30% precision + 30% stability |
| `operators.py` | `mutate` / `crossover` / `select_survivors` |
| `population.py` | `GeneticPopulation` with evolve/checkpoint/rollback |
| `attestation.py` | Immortalizes each winning generation on-chain |
| `semantic_layer.py` | Layer 8 — Phi-4 14B semantic classifier |

## Basic usage

```python
from core.evolution.population import GeneticPopulation

pop = GeneticPopulation(size=15)
result = pop.evolve_one_generation(apply_to_governance=True)
# result = {generation, asr_before, asr_after, genes_added, rolled_back}
```

## On-chain attestation

Every generation that lowers ASR is recorded on Avalanche C-Chain:

```python
from core.evolution.attestation import GenerationAttestation, attest_generation

att = GenerationAttestation(
    generation=1,
    asr_before=50.0,
    asr_after=36.9,
    improvement_pp=13.1,
    genes_mutated=3,
    genes_crossed=2,
    survivors=7,
    gene_pool_hash="...",
    timestamp="2026-04-13T00:00:00+00:00",
)
result = attest_generation(att)
# dry_run mode is automatic when DOF_PRIVATE_KEY is not set
```

## CLI — autonomous evolution loop

```bash
# Evolve until ASR ≤ 15% or up to 10 generations
python3 tests/red_team/autonomous_loop.py \
  --evolve \
  --threshold 15.0 \
  --generations 10
```

## Security history

| Version | ASR (general) | ASR (blockchain) | CVEs closed |
|---------|--------------|-----------------|-------------|
| Baseline | 89.3% | — | 0 |
| v0.5 | 42.1% | — | 7 |
| v0.7 | 26.1% | 26.1% | 11 |
| v0.8 | 15.2% | 26.1% | 14 |

- **Tests:** 160/160 passing
- **On-chain attestations:** 30+ across 8 verified chains
- **CVEs closed:** CVE-DOF-001 → CVE-DOF-014
- **Z3 proofs:** 4/4 PROVEN (GCR_INVARIANT, SS_FORMULA, SS_MONOTONICITY, SS_BOUNDARIES)

## Governance architecture (7 layers + layer 8)

```
Layer 1: Constitution      — deterministic regex (governance.py)
Layer 2: AST Validator     — static analysis of generated code
Layer 3: Tool Hook Gate    — intercepts before tool execution
Layer 4: Supervisor Engine — cross-turn behavior monitoring
Layer 5: Adversarial Guard — red/blue pipeline
Layer 6: Memory Layer      — reproducible session state
Layer 7: Z3 SMT Verifier   — 4 invariants PROVEN
Layer 8: Semantic Layer    — neural classifier (Phi-4 14B)
```

## License

DOF-MESH Evolution Engine — public components under MIT.
Gene pool, attack vectors, and red team are proprietary trade secrets.
