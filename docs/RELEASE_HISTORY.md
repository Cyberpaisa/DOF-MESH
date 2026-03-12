# DOF Architecture & Release History

This document preserves the detailed architectural components and features added to the Deterministic Observability Framework (DOF) across its release history up to v0.3.3. These components form the underlying technical mechanics supporting the mathematical invariants described in the main scientific paper.

## 1. Formal Verification & Governance

*   **Z3 SMT Formal Verification (v0.3.x):** Machine-checkable proofs of four framework invariants: GCR architectural independence, SS cubic derivation, SS strict monotonicity, and SS boundary conditions.
*   **Z3 State Transition Verification:** Proves 8 dynamic invariants across all possible agent states (verified in 107.7ms total).
*   **Neurosymbolic Z3 Gate:** Intercepts LLM-dependent outputs before execution following the neurosymbolic principle (LLM proposes, Z3 approves or rejects with counterexample).
*   **Constitutional Policy-as-Code:** Formalizes all governance rules in a versioned `dof.constitution.yml` specification, establishing YAML as the canonical governance source with JSON Schema validation and runtime loading.
*   **Instruction Hierarchy Enforcement:** Implements a three-level priority model (SYSTEM > USER > ASSISTANT) for governance rules. Hard rules operate at SYSTEM priority (never overridable); soft rules at USER priority.
*   **Framework-Agnostic Governance:** via `FrameworkAdapter` abstraction pattern. Features `GenericAdapter` for string-producing systems, and `LangGraphAdapter` exposing DOF governance as graph-compatible callable nodes (`DOFGovernanceNode`, `DOFASTNode`).
*   **OAGS Conformance Bridge:** Implements Open Agent Governance Specification through deterministic BLAKE3 agent identity, bidirectional policy conversion, and three-level conformance validation (declarative, runtime, attestation).

## 2. On-Chain Cryptographic Attestations

*   **On-Chain Proof Hash Attestations (keccak256):** via `DOFProofRegistry.sol`. Transforms DOF from trust-by-scoring to trust-by-proof — the first protocol where AI agent trust assessments carry mathematical guarantees verifiable on-chain.
*   **DOFValidationRegistry Smart Contract:** Deployed at `0x88f6043B091055Bbd896Fc8D2c6234A47C02C052` on Avalanche C-Chain, providing immutable on-chain storage of governance attestations and public zero-trust verification via `isCompliant()`.
*   **Avalanche Bridge:** Real-time on-chain attestation publishing via web3.py, completing a three-layer pipeline: DOF governance → dof-storage (PostgreSQL) → Enigma Scanner (Supabase) → Avalanche C-Chain.
*   **Enigma Scanner Bridge:** Connects DOF attestations to erc-8004scan.xyz via a dedicated `dof_trust_scores` table, separated from infrastructure monitoring (Centinela) to prevent semantic collision.
*   **Merkle Tree Batching:** Enables gas-optimized on-chain attestation via SHA-256 Merkle trees with inclusion proofs (e.g., aggregating 10,000 attestations into a single transaction).
*   **x402 Trust Gateway:** Provides formal verification for x402 payments via deterministic composite scoring (adversarial 35%, hallucination 25%, PII 20%, constitution 10%, structure 5%, red_team 5%) with ALLOW/WARN/BLOCK verdicts.

## 3. Evaluation & Static Analysis

*   **AST-Based Static Verification:** Deterministic structural analysis of agent-generated code using Python abstract syntax trees. Enforces four rule categories (blocked imports, unsafe calls, secret detection, resource risk) without LLM involvement.
*   **Adversarial Red-on-Blue Protocol:** Resolves supervisor circularity through structured dialectical conflict (`RedTeamAgent` vs `GuardianAgent`) adjudicated by a `DeterministicArbiter`.
*   **Red Team Attack Vectors:** Implements 3 simulation methods inspired by Garak/PyRIT: `indirect_prompt_injection`, `persuasion_jailbreak`, and `training_data_extraction`.
*   **LLM-as-a-Judge Advisory Evaluator:** Optional evaluation via `evaluate_with_judge` scoring factuality, coherence, and safety. Mechanism is advisory only and does not override the deterministic arbiter verdicts.
*   **TestGenerator:** Produces deterministic adversarial test datasets (seeded random, 50/50 clean/adversarial split) across hallucination, code safety, governance, and consistency.
*   **LoopGuard:** Detects infinite execution loops via Jaccard similarity (threshold 0.85) between consecutive outputs.
*   **DataOracle:** Implements three deterministic verification strategies (pattern matching, cross-reference validation, consistency checking) for factual claim verification without LLM involvement.
*   **Automated Boundary Test Generation:** Expands test suite from Z3 counterexamples, scaling to 1,008 boundary-tested regressions.

## 4. Execution & Observability Infrastructure

*   **Deterministic Execution Mode:** Isolates infrastructure-level randomness from LLM variance by fixing provider ordering and seeding pseudo-random number generators.
*   **Storage Architecture (Dual-Backend):** Supports JSONL (default, zero-config) and PostgreSQL (production, multi-tenant). Features `StorageFactory` auto-detection and SQLAlchemy ORM.
*   **Constitutional Memory Governance:** Validates every write operation against `ConstitutionEnforcer`. `TemporalGraph` implements bi-temporal versioning, while `ConstitutionalDecay` applies relevance decay.
*   **Protocol Integration (MCP & REST):** Exposes 10 governance tools over stdio JSON-RPC 2.0 transport (MCP server) and 14 FastAPI endpoints, enabling external systems to invoke DOF governance.
*   **Bayesian Provider Selection:** Uses Thompson Sampling over Beta-distributed reliability estimates with temporal decay.
*   **TokenTracker:** Per-call LLM token flow tracking with `log_call()`, `total_cost()`, `calls_by_provider()`, and latency metrics.
*   **Causal Error Attribution:** Three-class taxonomy (MODEL_FAILURE, INFRA_FAILURE, GOVERNANCE_FAILURE) expanded to 11 classes, including a dedicated AGENT_FAILURE category covering 16 patterns.
*   **ExecutionDAG:** Directed acyclic graph modeling of agent execution with DFS cycle detection and Mermaid diagram export.
*   **Failure Injection Protocol:** Introduces controlled perturbations at configurable step indices with deterministic periodicity to measure metric sensitivity.

## 5. Formal Production Results

*   **Combined Trust Architecture:** SQL materialized view synthesizing three independent scoring sources: infrastructure monitoring (Centinela 0.30), formal governance (DOF 0.50), and community assessment (0.20).
*   **Full Audit Pipeline Cross-Verification:** 10/10 MCP tools validated, 8 A2A skills verified. Production results confirm Z3 4/4 verified, agents governance-compliant, trust score 0.85.
*   **External Agent Audit (ERC-8004 Registry):** 13 robust tests probing 4 protocols against agents on erc-8004scan.xyz.
*   **External Validation v0.2.4 (Google Colab):** Confirmed LLM-as-a-Judge scoring, RedTeam attack detection across all vectors, and Instruction hierarchy validation.
*   **Agent Data Mesh (10-Round):** Executed 10 cross-agent verification rounds resulting in 21 total on-chain attestations.
*   **Production Agent Ranking:** Apex Arbitrage (#1687) and AvaBuilder (#1686) achieved rank #1 and #2 of 1,772 agents on erc-8004scan.xyz based on combined trust scoring.
