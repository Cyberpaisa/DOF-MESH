# Contributing to DOF

Thank you for your interest in contributing to the Deterministic Observability Framework!

## Quick Start

```bash
git clone https://github.com/Cyberpaisa/deterministic-observability-framework.git
cd deterministic-observability-framework
pip install -e ".[dev]"
python3 -m unittest discover tests/ -v
```

## Development Setup

- **Python**: 3.11+
- **Z3 Solver**: `pip install z3-solver`
- **Tests**: `python3 -m unittest` (NOT pytest -- web3 conflict)
- **Verify**: `python3 -m dof verify-states` (8/8 PROVEN required)

## How to Contribute

### Bug Reports
Open an issue with: steps to reproduce, expected vs actual behavior, DOF version (`pip show dof-sdk`).

### Feature Proposals
Open an issue tagged `enhancement` with: use case, proposed API, how it fits DOF's 7-layer architecture.

### Pull Requests
1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Write tests (`unittest`, not pytest)
4. Run full suite: `python3 -m unittest discover tests/ -v`
5. Run Z3 verification: `python3 -m dof verify-states` (must be 8/8 PROVEN)
6. Run regression check: `python3 -m dof regression-check` (must be 0 regressions)
7. Submit PR with clear description

### Code Style
- Type hints on all functions
- Google-style docstrings
- Imports ordered: stdlib > third-party > local
- New modules go in `core/`, re-export from `dof/__init__.py`

## Architecture
See [docs/ARCHITECTURAL_REDESIGN_v1.md](docs/ARCHITECTURAL_REDESIGN_v1.md) for the module map and 7-layer governance stack.

## Testing
All tests use `unittest`. Run with:
```bash
python3 -m unittest discover tests/ -v          # Full suite (1,008+ tests)
python3 -m dof verify-states                     # Z3 invariants (8/8 PROVEN)
python3 -m dof verify-hierarchy                  # Hierarchy (42 patterns)
python3 -m dof regression-check                  # Post-merge regression check
```

## Adding a New Metric

1. Define the metric mathematically in `core/observability.py` -> `compute_derived_metrics()`
2. Add the field to `RunTrace` dataclass
3. Update `run_experiment()` aggregation in `core/experiment.py`
4. Document the metric in the paper (`paper/PAPER_OBSERVABILITY_LAB.md`, Section 5)

## Adding a Governance Rule

1. Open `core/governance.py`
2. Add rule to `HARD_RULES` (blocks output) or `SOFT_RULES` (warning only)
3. Each rule is a function `(text: str) -> bool` returning `True` if violation detected
4. Run baseline experiment to verify GCR impact

## Singleton Reset Requirement

All singletons (`ProviderManager`) accumulate state across runs. When adding new singletons:

1. Implement a `reset_all()` or `reset()` method
2. Call it at the start of `run_experiment()`
3. Verify that parametric sweeps produce identical results with and without the reset

## License
BSL-1.1 -- Free for non-commercial use, research, and personal projects. Converts to Apache 2.0 on 2028-03-08. Commercial use requires a separate agreement. Contact: @Cyber_paisa on Telegram.
