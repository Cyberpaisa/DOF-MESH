# Changelog

All notable changes to DOF. Format follows [Keep a Changelog](https://keepachangelog.com/).

## [0.2.0] — 2026-03-07

### Added
- **dof-sdk v0.2.0** — 20+ exports, quick functions, CLI commands
- **Semantic Hallucination Detection** — 3 new DataOracle strategies
- **AgentLeak Privacy Benchmark** — 200 tests, 7 channels, 4 categories
- **OpenTelemetry Integration** — optional OTLP tracing for 7 governance layers
- **EventBus** — in-memory event streaming with pub/sub (Phase 8 prep)
- **CLI** — `python -m dof verify|prove|benchmark|privacy|health|version`
- **PII Detection** — email, phone, SSN, credit card patterns

### Changed
- Hallucination FDR: 0% → 90%
- Consistency FDR: 0% → 100%
- Overall F1: 48.1% → 96.8%
- DataOracle: 3 → 6 strategies
- Tests: 646 → 719

## [0.1.2] — 2026-03-06

### Added
- **TestGenerator + BenchmarkRunner** — 400 adversarial tests
- **ExecutionDAG** — cycle detection, topological sort, critical path
- **LoopGuard** — Jaccard 0.85, max 10 iterations, 300s timeout
- **DataOracle** — 3 verification strategies
- **TokenTracker** — per-call token count, cost, latency
- **Merkle Tree** — N attestations = 1 tx = $0.01
- **10-Round Agent Data Mesh** — 21 on-chain attestations
- **E2E Tests** — 54 tests, 15 modules, zero external deps
- **GitHub Actions CI** — external validation Python 3.11 + 3.12
- **DOF Owl Banner** — project mascot
- **README Rewrite** — 971 → 222 lines

### Security
- oracle_key.json leaked via git add -A — rotated in 3 min

## [0.1.1] — 2026-03-05

### Added
- **Enigma Bridge** — attestations to erc-8004scan.xyz
- **Avalanche Bridge** — DOFValidationRegistry on mainnet
- **Agent Cross-Transactions** — Apex ↔ AvaBuilder
- **Combined Trust View** — SQL materialized view

## [0.1.0] — 2026-03-03

### Added
- Initial release: 8 core modules, 149 tests
- ConstitutionEnforcer, ASTVerifier, Z3Verifier
- 5 formal metrics: SS, PFI, RP, GCR, SSR
- PyPI: dof-sdk v0.1.0
