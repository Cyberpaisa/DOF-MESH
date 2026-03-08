## [0.2.5] — 2026-03-08

### Added
- `dof/x402_gateway.py` — x402 Trust Gateway con verificación formal DOF
  - `TrustGateway`: intercepta x402 payment requests, corre checks determinísticos
  - `GatewayVerdict`: ALLOW / WARN / BLOCK + governance_score + evidence
  - Checks: adversarial_scan, hallucination_scan, pii_scan, response_structure
  - DOF SDK integration: ConstitutionEnforcer + RedTeamAgent (opcional)
  - `EnigmaBridge`: publicación opcional de score a Enigma Scanner on-chain
  - `verify_batch()`: verificación de múltiples requests
  - Zero LLM en el path crítico — 100% determinístico

### Tests
- `tests/test_x402_gateway.py` — 27 passed, 1 xfailed

# Changelog

All notable changes to DOF. Format follows [Keep a Changelog](https://keepachangelog.com/).

## [0.2.4] — 2026-03-08

### Fixed
- `__version__` string was 0.2.2 in PyPI build — bumped to 0.2.4 after forced republish
- Version assertions in `tests/test_dof_sdk.py` updated to match current version

### Validated
- External validation v3 (Google Colab): 3/3 PASS
  - LLM-as-Judge: score=9.0, verdict=PASS
  - RedTeam indirect_prompt_injection: detected=True
  - InstructionHierarchy: compliant=True, violation_level=NONE
- Report: `tests/external/dof_enterprise_report_v3.json`

## [0.2.3] — 2026-03-08

### Added
- **LLM-as-a-Judge** — `evaluate_with_judge(response, context)` scores 1.0-10.0, PASS >= 7.0 (advisory, does NOT override deterministic arbiter)
- **3 Attack Vector Methods** — `indirect_prompt_injection()`, `persuasion_jailbreak()`, `training_data_extraction()` with `AttackResult` dataclass (Garak/PyRIT-inspired)
- **Instruction Hierarchy** — `enforce_hierarchy(system_prompt, user_prompt, response)` with `HierarchyResult`, SYSTEM > USER > ASSISTANT priority levels
- **AGENT_FAILURE** — ErrorClass expanded with 16 agent patterns (tool_not_found, tool_timeout, invalid_json_schema, missing_required_param, agent_stuck, no_progress_detected, reasoning_failed, etc.)

## [0.2.2] — 2026-03-08

### Added
- **3 Attack Vectors** — RedTeamAgent detects prompt injection, jailbreak persuasion, training data extraction in `analyze()`
- **Priority Fields** — `RulePriority` enum on HARD_RULES (SYSTEM) and SOFT_RULES (USER), `check_instruction_override()`, `get_rules_by_priority()`
- **LLMJudge** — optional Phase 4 in adversarial pipeline via `LLMJudgeVerdict` dataclass
- **AGENT_FAILURE** — ErrorClass category for tool_call_failed, planning_loop, reflexion_timeout

### Fixed
- **MerkleBatcher.add()** now auto-detects plain text vs hex and hashes with SHA256 before queuing
- **ErrorClass** expanded from 4 to 9 categories: added LLM_FAILURE, PROVIDER_FAILURE, MEMORY_FAILURE, HASH_FAILURE, Z3_FAILURE
- **classify_error()** new pattern matching for token limits, API keys, ChromaDB, hex/Merkle, and Z3 errors

## [0.2.1] — 2026-03-08

### Fixed
- **z3-solver** added as required dependency (was dev-only, broke external installs)
- **blake3** added as required dependency (needed for CertificateSigner/OAGSIdentity)
- Both moved from `[dev]` extras to core `dependencies` in pyproject.toml

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
