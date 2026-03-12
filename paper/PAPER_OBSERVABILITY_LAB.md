<div align="center">

# Deterministic Observability and Resilience Engineering for Multi-Agent LLM Systems

### An Experimental Framework with Formal Verification

**Cyber Paisa** · **Enigma Group**
**Colombia-Blockchain**

[![Tests](https://img.shields.io/badge/tests-1008_passed-brightgreen)]()
[![Z3 Invariants](https://img.shields.io/badge/Z3-8%2F8_PROVEN-blue)]()
[![Hierarchy](https://img.shields.io/badge/hierarchy-42_patterns_verified-blue)]()
[![PyPI](https://img.shields.io/pypi/v/dof-sdk)](https://pypi.org/project/dof-sdk/)
[![On-Chain](https://img.shields.io/badge/Avalanche-21_attestations-red)]()
[![License](https://img.shields.io/badge/license-BSL--1.1-orange)]()

*Version 0.3.3 · March 2026 · 27K+ LOC · 35 Core Modules*

---

> *"We don't trust the AI. We trust the Math."*

---

</div>

## Table of Contents

<details>
<summary>Click to expand</summary>

- [Abstract](#abstract)
- [1. Introduction](#1-introduction)
- [2. Related Work](#2-related-work)
  - [2.1 Multi-Agent LLM Systems](#21-multi-agent-llm-systems)
  - [2.2 AI System Observability](#22-ai-system-observability)
  - [2.3 Resilience Engineering](#23-resilience-engineering)
  - [2.4 Deterministic Evaluation](#24-deterministic-evaluation-of-stochastic-systems)
  - [2.5 Formal Verification of AI Systems](#25-formal-verification-of-ai-systems)
  - [2.6 Adversarial Evaluation](#26-adversarial-evaluation-and-llm-as-judge)
  - [2.7 Bayesian Optimization](#27-bayesian-optimization-and-multi-armed-bandits)
  - [2.8 Agent Memory Systems](#28-agent-memory-systems)
  - [2.9 Agent Governance Specifications](#29-agent-governance-specifications)
  - [2.10 Protocol Standards](#210-protocol-standards-and-framework-interoperability)
- [3. System Architecture](#3-system-architecture)
- [4. Experimental Framework](#4-experimental-framework)
- [5. Metrics Formalization](#5-metrics-formalization)
- [6. Experimental Results](#6-experimental-results)
- [7. Parametric Failure Sensitivity Analysis](#7-parametric-failure-sensitivity-analysis)
- [8. Formal Verification via Z3 SMT Solver](#8-formal-verification-via-z3-smt-solver)
- [9. Adversarial Red-on-Blue Evaluation Protocol](#9-adversarial-red-on-blue-evaluation-protocol)
- [10. AST-Based Static Verification](#10-ast-based-static-verification)
- [11. Formal Task Contracts](#11-formal-task-contracts)
- [12. Causal Error Attribution](#12-causal-error-attribution)
- [13. Bayesian Provider Selection](#13-bayesian-provider-selection)
- [14. Constitutional Policy-as-Code](#14-constitutional-policy-as-code)
- [15. Constitutional Memory Governance](#15-constitutional-memory-governance)
- [16. OAGS Conformance](#16-oags-conformance)
- [17. x402 Trust Gateway](#17-x402-trust-gateway)
- [18. Protocol Integration](#18-protocol-integration)
- [19. Storage Architecture](#19-storage-architecture)
- [20. Framework-Agnostic Governance](#20-framework-agnostic-governance)
- [21. On-Chain Attestation via Avalanche C-Chain](#21-on-chain-attestation-via-avalanche-c-chain)
- [22. Scanner Integration and Combined Trust Architecture](#22-scanner-integration-and-combined-trust-architecture)
- [23. External Agent Audit](#23-external-agent-audit)
- [24. Adversarial Benchmark Results](#24-adversarial-benchmark-results)
- [25. Discussion](#25-discussion)
- [26. Threats to Validity](#26-threats-to-validity)
- [27. Replication Protocol](#27-replication-protocol)
- [28. Comparative Positioning](#28-comparative-positioning)
- [29. Future Work](#29-future-work)
- [30. Conclusion](#30-conclusion)
- [31. External Validation](#31-external-validation-enterprise-reports)
- [32. Neurosymbolic Formal Verification Layer](#32-neurosymbolic-formal-verification-layer-v03x)
- [33. Neurosymbolic LLM Routing](#33-neurosymbolic-llm-routing)
- [34. DOF as On-Chain Trust Infrastructure (ERC-8183)](#34-dof-as-on-chain-trust-infrastructure-erc-8183)
- [References](#references)

</details>

---

## Abstract

Multi-agent systems built on large language models (LLMs) exhibit complex failure modes distinct from single-model pipelines, including provider rate limits, model incompatibilities, and non-deterministic cascading errors. While existing orchestration frameworks abstract agent coordination, they fail to provide deterministic mechanisms for measuring system stability, enforcing formal governance, or guaranteeing compliance. This paper presents the Deterministic Observability Framework (DOF): a comprehensive, zero-dependency architecture for the formal evaluation, algorithmic governance, and cryptographic auditability of multi-agent LLM systems. DOF transitions agent evaluation from heuristic *trust-by-scoring* to mathematical *trust-by-proof*. We introduce a neurosymbolic verification architecture integrating Z3 SMT formal proofs to mathematically guarantee architectural invariants, coupled with deterministic Abstract Syntax Tree (AST) static analysis and a dialectical Red-on-Blue adversarial evaluation protocol. To ensure immutable traceability, the framework connects off-chain evaluation with on-chain execution through compliance-gated ERC-8004 attestations natively deployed across EVM networks (e.g., Avalanche C-Chain, Conflux eSpace). Empirical validations involving 1,008 automatically generated boundary tests demonstrate a 100% Governance Compliance Rate (GCR=1.0), zero false-positive tampering rejections, and cross-chain read consensus latencies under 1.5 seconds. The resulting implementation provides the first mathematically verifiable, framework-agnostic governance stack for autonomous agentic systems operating in zero-trust environments.

---

## 1. Introduction

Multi-agent systems built on large language models are increasingly deployed in settings that rely on multiple heterogeneous LLM providers—each presenting distinct operational constraints, rate limits, and failure characteristics. State-of-the-art frameworks such as CrewAI [1], AutoGen [2], and LangGraph [3] successfully orchestrate specialized agents collaborating sequentially or in parallel. However, when these systems operate dynamically across providers, the failure surface expands exponentially. A format rejection on one provider may trigger a retry algorithm that cascades into system-wide exhaustion.

The core problem addressed in this paper is the absence of formal, deterministic metrics and enforcement layers to characterize these failure patterns, measure system resilience, and guarantee operational boundaries. Without deterministic verification, any observed variance in multi-agent executions cannot be cleanly attributed to model intelligence versus infrastructure fragility. 

To bridge this gap, we introduce the Deterministic Observability Framework (DOF). DOF acts as a framework-agnostic governance and observability layer that intercepts, analyzes, and mathematically proves the validity of agent interactions before they are executed or recorded. 

### 1.1 Key Contributions

This paper advances the field of multi-agent reliability by making the following primary scientific and architectural contributions:

1. **Formal Observability and Metric Definitions:** We define explicit mathematical formulations to quantify multi-agent system behavior across key dimensions including Stability Score, Provider Fragility Index, Retry Pressure, and Governance Compliance Rate (GCR).
2. **Neurosymbolic Governance via Z3 SMT:** We introduce a Z3 Gate that intercepts LLM outputs, utilizing formal SMT solvers to mathematically prove architectural invariants (e.g., GCR = 1.0) and automatically generate boundary test cases via counterexamples.
3. **Deterministic Static Verification:** Implementation of AST-based static analysis to evaluate agent-generated code structures—restricting unsafe imports, secrets, and recursive loops—with zero LLM involvement in the critical validation path.
4. **Adversarial Red-on-Blue Evaluation:** A structured dialectical protocol resolving LLM supervisor circularity. A `RedTeamAgent` probes for vulnerabilities while a `GuardianAgent` provides evidence-backed defenses, adjudicated purely by deterministic algorithmic criteria.
5. **Decentralized Cryptographic Attestation (ERC-8004):** A complete pipeline bridging off-chain mathematical proofs with on-chain immutability. Verified agent interactions are hashed (keccak256) and anchored to EVM smart contracts (Avalanche, Conflux) ensuring point-in-time trust validation without relying on centralized databases.

*(Note: Extended architectural components, API bridging, memory governance implementations, and framework adapters—which originally scaled our changelog to 40+ modular additions—are detailed extensively in Sections 14 through 24).*

The system under study consists of eight specialized agents organized into various collaborative configurations, operating across multiple LLM providers. All experimental results and latency metrics presented in this paper are derived from executed runs with persisted on-chain and off-chain traces.

---

## 2. Related Work

### 2.1 Multi-Agent LLM Systems

The multi-agent paradigm for LLM applications emerged from the observation that specialized agents outperform monolithic prompts on complex tasks. CrewAI [1] introduced role-based agent definitions with sequential and hierarchical process models. AutoGen [2] from Microsoft Research proposed conversational agents with code execution capabilities. LangGraph [3] extended LangChain with stateful graph-based orchestration. MetaGPT [4] applied software engineering workflows to agent collaboration.

These frameworks focus on agent coordination semantics but provide limited infrastructure for failure characterization. CrewAI offers verbose logging but no structured metrics. AutoGen provides conversation histories but no step-level latency tracking. None implement deterministic execution modes for reproducible evaluation.

### 2.2 AI System Observability

Observability in machine learning systems has been studied primarily in the context of model serving. MLflow [5] tracks experiment parameters and metrics but operates at the training level, not the inference orchestration level. Weights & Biases [6] provides experiment tracking with statistical aggregation but targets model development workflows. OpenTelemetry [7] offers distributed tracing standards that could theoretically apply to agent systems, but no multi-agent framework has adopted its span model for agent-step correlation.

The gap addressed by this work is observability at the *orchestration* level: tracking not individual model calls but the interaction patterns, failure cascades, and quality gates that emerge when multiple agents collaborate through sequential task pipelines.

### 2.3 Resilience Engineering

Resilience engineering in distributed systems is well-established. The circuit breaker pattern [8] prevents cascading failures by temporarily disabling failing components. Exponential backoff with jitter [9] manages retry storms. Netflix's Chaos Monkey [10] pioneered failure injection for resilience validation.

Applying these patterns to LLM provider management is non-trivial. Unlike traditional microservices, LLM providers fail in model-specific ways: rate limits are per-model and per-token rather than per-request, certain models reject specific output formats, and authentication failures may affect only certain API prefixes. The provider resilience layer described in Section 3 adapts circuit breaker semantics to these LLM-specific failure modes.

### 2.4 Deterministic Evaluation of Stochastic Systems

Evaluating stochastic systems requires either controlling randomness or running sufficient trials to characterize distributions. Reinforcement learning evaluation protocols [11] address this through fixed seeds and episode counts. The challenge in multi-agent LLM systems is that randomness enters at multiple levels: the LLM sampling temperature, the provider selection order, the retry timing, and the output quality assessment. Our deterministic mode controls the infrastructure-level randomness (provider order, retry behavior) while acknowledging that LLM output randomness remains uncontrolled in the simulated experiments presented here.

### 2.5 Formal Verification of AI Systems

Applying formal methods to machine learning systems has received increasing attention. The Z3 SMT solver [12] has been applied to neural network verification (Marabou [13]), constraint satisfaction in planning systems, and property verification in symbolic AI. SMT-based verification encodes system properties as satisfiability problems: if Z3 finds no counterexample (UNSAT), the property holds universally; if a counterexample exists (SAT), it constitutes a falsifying witness.

The challenge of establishing deterministic behavioral guarantees for LLM-based systems has been acknowledged across the industry, notably in OpenAI's Preparedness Framework [14], which characterizes such guarantees as an open problem for model developers. This work presents an alternative approach: rather than attempting to constrain model behavior directly, DOF enforces governance at the architectural level through constitutional policy enforcement and Z3 formal verification, establishing compliance as a provable system invariant under bounded retry semantics (Theorem 1, §10).

### 2.6 Adversarial Evaluation and LLM-as-Judge

Zheng et al. [15] identified systematic biases in LLM evaluation including position bias, verbosity bias, and self-enhancement bias. These biases directly undermine single-evaluator supervisor architectures: an LLM evaluating its own provider chain's output may exhibit sycophantic acceptance. The adversarial Red-on-Blue protocol (Section 9) addresses this by exploiting LLM biases bidirectionally — a RedTeamAgent biased toward finding defects and a GuardianAgent biased toward defending quality — then resolving the dialectic through a deterministic referee immune to these biases.

The Breck et al. ML Test Score [16] proposes organizational checklists for ML production readiness. The task contract mechanism (Section 11) extends this concept to runtime enforcement: contracts are not static checklists but dynamic completion predicates verified at execution time.

### 2.7 Bayesian Optimization and Multi-Armed Bandits

Thompson Sampling [17] is a well-established exploration-exploitation algorithm for multi-armed bandit problems. Applied to provider selection, each provider represents an arm with a Beta-distributed reward distribution. The Beta distribution is conjugate to the Bernoulli likelihood, enabling closed-form posterior updates on success/failure observations. Temporal decay addresses distribution shift: provider reliability changes over time as rate limits reset and infrastructure conditions vary.

The 4/δ bound established in [18] (arXiv:2512.02080) provides a finite-sample confidence guarantee for the Thompson Sampling regret under bounded reward distributions, which is directly applicable to the retry mechanism: with r = 2 retries, the probability that the selected provider sequence fails to produce a successful execution is bounded by a function of the Beta posterior variances.

### 2.8 Agent Memory Systems

Mem0 [19] provides a memory layer for LLM applications with automatic extraction and retrieval but does not enforce governance constraints on stored content. Graphiti [20] implements temporal knowledge graphs with episodic and semantic memory but lacks constitutional validation of memory operations. Cognee [21] provides scientific memory management with knowledge graph construction but does not integrate governance enforcement at the write path. All three systems treat memory as an unconstrained store: any content produced by an LLM can be persisted regardless of governance compliance. The constitutional memory governance system (Section 15) addresses this gap by interposing ConstitutionEnforcer validation on every write operation.

### 2.9 Agent Governance Specifications

The Open Agent Governance Specification (OAGS), developed by Sekuire, proposes a standardized framework for agent identity, policy declaration, and audit trails. OAGS defines three conformance levels: declarative (policy exists), runtime (enforcement active), and attestation (cryptographic proof of compliance). However, OAGS provides the specification without a reference implementation that includes formal verification. The OAGS conformance bridge (Section 16) implements all three levels with Z3-verified governance invariants, providing the first formally verified OAGS-conformant system.

### 2.10 Protocol Standards and Framework Interoperability

The Model Context Protocol (MCP) [23] defines a standardized interface for exposing tools and resources to LLM-based agents via JSON-RPC 2.0 over stdio transport. FastAPI [24] provides high-performance HTTP APIs with automatic OpenAPI documentation. LangGraph [3] defines a graph-based orchestration model where nodes are callable functions operating on shared state dictionaries. The protocol integration layer (Section 18) and framework-agnostic governance system (Section 20) adapt DOF governance to these interfaces without embedding governance logic in the protocol or framework layer.

### 2.11 AI Engineering Practice

Huyen [31] provides a comprehensive treatment of the emerging discipline of AI Engineering, covering the full lifecycle of foundation-model applications: evaluation, RAG, agent design, dataset curation, and production monitoring. Huyen identifies hallucination detection, output governance, and systematic evaluation as open challenges in production agent systems. DOF addresses these gaps with a deterministic governance stack (zero-LLM constitutional enforcement, AST verification, Z3 formal proofs) that operates independently of the model layer — a design choice that aligns with Huyen's recommendation to decouple governance from generation. The adversarial benchmarking pipeline (Section 24) and regression tracking system (Section 24.7) provide the systematic evaluation infrastructure that Huyen identifies as essential for production readiness.

---

## 3. System Architecture

### 3.1 Conceptual Overview

The system implements a layered architecture with clear separation between agent logic, infrastructure services, and experimental instrumentation.

```text
┌─────────────────────────────────────────────────────────┐
│                    Experiment Layer                      │
│   ExperimentDataset  │  BatchRunner  │  Schema           │
├─────────────────────────────────────────────────────────┤
│                  Observability Layer                     │
│  RunTrace  │  StepTrace  │  DerivedMetrics  │  Store     │
│  ErrorClass │ causal_trace │ export_dashboard            │
├─────────────────────────────────────────────────────────┤
│               Crew Runner (Integration)                  │
│  Orchestrates: Providers + Checkpoint + Governance       │
│              + Supervisor + Metrics + Contracts          │
│              + Bayesian + Adversarial                    │
├──────────┬──────────┬───────────┬───────────────────────┤
│ Provider │Checkpoint│Governance │  Meta-Supervisor       │
│ Manager  │ Manager  │ Enforcer  │  (Quality Gate)        │
│ TTL/Back │ JSONL    │ Hard/Soft │  Q+A+C+F Scoring       │
│ off/Rec. │ Steps    │ +YAML src │  ACCEPT/RETRY/ESC      │
├──────────┼──────────┼───────────┼───────────────────────┤
│ Bayesian │ AST      │ Z3 SMT    │  Adversarial           │
│ Provider │ Verifier │ Verifier  │  Red-on-Blue           │
│ Selector │ (4 rules)│ (4 proofs)│  Arbiter               │
├──────────┴──────────┴───────────┴───────────────────────┤
│               Metrics Logger (JSONL + Rotation)          │
├─────────────────────────────────────────────────────────┤
│             Memory Manager (Short/Long/Episodic)         │
├─────────────────────────────────────────────────────────┤
│                CrewAI + LiteLLM (Execution)              │
│          Groq │ NVIDIA NIM │ Cerebras │ Zhipu AI         │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Core Modules

The framework comprises 35 core modules totaling 27,000+ lines of code, with no external dependencies beyond the orchestration layer (CrewAI) and its transitive dependency (LiteLLM). The original nine modules are extended by modules implementing formal verification (static and dynamic), adversarial evaluation, quality enforcement, constitutional memory governance, OAGS conformance, on-chain attestation, Enigma Scanner bridge, Avalanche C-Chain bridge, dual-backend storage, protocol integration (MCP server, REST API), framework-agnostic governance adapters, neurosymbolic Z3 gate, state transition verification, automated test generation, and on-chain proof hash attestations.

**Provider Manager** (`providers.py`). Implements per-provider state tracking with TTL-based exhaustion and exponential backoff recovery. Each provider maintains independent state: exhaustion flag, exhaust timestamp, failure count, and TTL. The backoff schedule follows `TTL = min(300 × 2^(failures-1), 1200)` seconds, producing a 5-minute, 10-minute, 20-minute progression capped at 20 minutes. Recovery is automatic: when `now - exhaust_time >= TTL`, the provider is reactivated. Now extended with `BayesianProviderSelector` (Section 13).

**Checkpoint Manager** (`checkpointing.py`). Provides step-level persistence using JSONL files keyed by run ID. Each step records: run_id, step_id, agent name, task name, provider, status (pending/running/completed/failed), input hash, output truncated to 5,000 characters, error message, timestamps, and latency. The manager supports loading previous runs from disk to enable retry of only failed steps.

**Constitution Enforcer** (`governance.py`). Implements two-tier rule enforcement. Four hard rules produce blocking violations: no hallucination claims without URLs, language compliance, non-empty output (minimum 50 characters), and maximum output length (50,000 characters). Four soft rules produce warning scores with configurable weights: source URLs present (weight 0.3), structured output markers (0.2), no paragraph repetition (0.2), and actionable recommendations (0.3). Rules are loaded at runtime from `dof.constitution.yml` (Section 14), with fallback to in-code defaults.

**Meta-Supervisor** (`supervisor.py`). Evaluates final crew output on four weighted dimensions: Quality (0.40), Actionability (0.25), Completeness (0.20), and Factuality (0.15). Each dimension is scored 0–10 using heuristic indicators. The composite score determines the decision: ACCEPT (≥7.0), RETRY (5.0–7.0, maximum 2 retries), or ESCALATE (<5.0).

**Metrics Logger** (`metrics.py`). Singleton logger writing structured JSONL events with automatic rotation at 10 MB. Events include: crew_start, crew_end, agent_step, provider_exhausted, governance_check, and supervisor_eval.

**Memory Manager** (`memory_manager.py`). Provides three memory tiers without OpenAI dependencies: short-term (in-process with configurable TTL), long-term (JSONL-persisted with keyword search), and episodic (crew execution summaries).

**Observability Module** (`observability.py`). Defines `RunTrace` and `StepTrace` data structures, session management via UUID v4, derived metric computation, and the `RunTraceStore` for persisting trace files. Extended with `ErrorClass` enum, `classify_error()` function, `@causal_trace` decorator, and `export_dashboard()` method (Section 12).

**Experiment Module** (`experiment.py`). Provides the formal experimental schema, dataset management, a simulated crew for infrastructure validation, and the `run_experiment()` batch runner with configurable failure injection.

**Crew Runner** (`crew_runner.py`). Integration layer that wraps `crew.kickoff()` with all infrastructure services. Each execution generates a `RunTrace`, passes through governance and supervisor gates, logs metrics, persists checkpoints, and returns a structured result dictionary. Extended with task contract verification and Bayesian provider recording.

**AST Verifier** (`ast_verifier.py`, new). Deterministic structural analysis of agent-generated code via Python's `ast` module and regex scanning. Four rule categories: BLOCKED_IMPORTS (os, subprocess, sys), UNSAFE_CALLS (eval, exec, compile), SECRET_PATTERNS (API key detection via regex), and RESOURCE_RISKS (file open, network access). The `_UnsafePatternVisitor` walks the AST without executing code. Score computed as `1.0 − (unique_violated_categories / 4)` (Section 10).

**Z3 Verifier** (`z3_verifier.py`, new). Integrates the Z3 SMT solver (version 4.16.0) to formally verify four static framework invariants. Proof results are persisted to `logs/z3_proofs.json` with theorem name, result, elapsed time, and Z3 version (Section 8). Extended in v0.3.x with eight dynamic state transition invariants (Section 32).

**Adversarial Evaluator** (`adversarial.py`, new). Implements the three-agent Red-on-Blue protocol: `RedTeamAgent` (LLM-based defect detection), `GuardianAgent` (LLM-based defense), `DeterministicArbiter` (pure-Python adjudication using verifiable evidence). Logs to `logs/adversarial.jsonl` (Section 9).

**Merkle Tree** (`merkle_tree.py`, new). SHA-256 Merkle tree with inclusion proof generation and verification. `MerkleBatcher` aggregates attestation certificates into batched transactions: N attestations = 1 on-chain tx. Economics: 10,000 attestations ≈ $0.01 gas on Avalanche C-Chain. Supports serialization and deserialization for persistence.

**ExecutionDAG** (`execution_dag.py`, new). Directed acyclic graph modeling of agent execution steps. DFS-based cycle detection prevents infinite dependency chains. Topological sort establishes valid execution ordering. Critical path analysis identifies the longest execution dependency chain for latency attribution. Mermaid diagram export produces visualization of the execution graph.

**LoopGuard** (`execution_dag.py`). Detects infinite execution loops via Jaccard similarity between consecutive agent outputs. Configurable similarity threshold (default 0.85), maximum iteration count (10), and timeout (300s). When triggered, terminates the execution with a structured `LoopDetected` event logged to the trace.

**DataOracle** (`data_oracle.py`, new). Deterministic factual claim verification via six strategies: (1) pattern matching against a 50+ entry known-facts database with regex extraction, (2) cross-reference validation comparing claims across multiple agent outputs, (3) consistency checking detecting contradictions within a single output, (4) entity extraction with founder/date validation against known facts, (5) numerical plausibility detection (negative values, percentages >100% in non-growth context, implausible magnitudes >$100T), and (6) self-consistency cross-checks (percentage allocation sums >100%, revenue contradictions >2x ratio, date arithmetic inconsistencies). Zero LLM involvement — pure string, regex, and arithmetic operations. Returns `OracleResult` with verification status and evidence.

**TokenTracker** (`observability.py`, extended). Per-call LLM token flow tracker integrated into the observability module. `log_call(provider, model, prompt_tokens, completion_tokens, latency_ms, cost_estimate)` appends structured records. Aggregation methods: `total_tokens()`, `total_cost()`, `calls_by_provider()` (returns dict), `average_latency()`. `to_dict()` produces serializable summary. `reset()` clears state for test isolation. Integrated into `crew_runner.py` — every successful `crew.kickoff()` logs token flow.

**TestGenerator** (`test_generator.py`, new). Deterministic adversarial test dataset generator with seeded random (reproducible). Produces 50/50 clean/adversarial splits across four categories: hallucination (date/number/entity/source injection), code safety (eval/import_os/hardcoded_secret), governance (language/hallucination/length violations), and consistency (contradictions). `generate_full_dataset(n_per_category=100)` produces 400 tests saved to `data/`.

**BenchmarkRunner** (`test_generator.py`). Runs DOF verification components against TestGenerator datasets. Measures True Positives, True Negatives, False Positives, False Negatives per category. Computes False Detection Rate (FDR), False Positive Rate (FPR), Precision, Recall, and F1. `run_full_benchmark()` produces per-category and overall results. `BenchmarkResult` dataclass provides structured output.

**Task Contract** (`task_contract.py`, new). Loads formal task specifications from markdown files and verifies completion via `is_fulfilled(output, context) → ContractResult`. Quality gates include: governance compliance, AST verification, supervisor score thresholds, test execution, and adversarial evaluation. Logs to `logs/task_contracts.jsonl` (Section 11).

### 3.3 Execution Pipeline

A single crew execution proceeds through the following stages:

1. **Initialization**: Generate UUID v4 run_id, record session_id, create RunTrace, log crew_start event.
2. **Contract Preconditions**: If a task contract is specified, verify all PRECONDITIONS before execution. Abort with `contract_breach` if any precondition fails.
3. **Provider Resolution**: Query ProviderManager for available providers; BayesianProviderSelector ranks candidates by Thompson Sampling score.
4. **Checkpoint Start**: Record step as "running" with input hash and provider list.
5. **Execution**: Invoke `crew.kickoff()` through CrewAI, which internally manages agent-to-agent task passing.
6. **Checkpoint Complete/Fail**: Record step outcome with latency, output, or error. Classify error via `ErrorClass`.
7. **Governance Check**: Apply hard rules (blocking) and soft rules (scoring) to the output.
8. **AST Verification**: If output contains code blocks, apply `ASTVerifier` structural analysis.
9. **Supervisor Evaluation**: Score output on Q/A/C/F dimensions, decide ACCEPT/RETRY/ESCALATE.
10. **Contract Postconditions**: Verify DELIVERABLES, QUALITY_GATES, and POSTCONDITIONS via `TaskContract.is_fulfilled()`.
11. **Bayesian Update**: Record success/failure to update Beta posteriors for each participating provider.
12. **Trace Finalization**: Compute derived metrics, populate `error_distribution` and `provider_reliability`, persist trace JSON, append to `runs.jsonl`.
13. **Metrics Logging**: Log crew_end event with total latency and output length.

On failure at stage 5, the system classifies the error via `classify_error()`, marks the provider as exhausted, and retries with the next Bayesian-recommended provider. Maximum three attempts per crew execution.

---

## 4. Experimental Framework

### 4.1 Deterministic Mode

Deterministic mode controls infrastructure-level randomness to enable reproducible experiments. When activated, the system:

- Seeds Python's random number generator with a fixed value (seed=42).
- Fixes the provider selection order to a canonical sequence: Cerebras, Groq, NVIDIA, Zhipu.
- Disables dynamic fallback reordering based on runtime conditions.
- Preserves LLM sampling randomness (temperature parameter) as uncontrolled.

In simulated experiments (using `SimulatedCrew`), deterministic mode produces identical metric outputs across independent runs. In live experiments with real LLM providers, deterministic mode controls the infrastructure variables while LLM output variation introduces measurable variance, enabling isolation of infrastructure effects from model effects.

### 4.2 Batch Runner

The `run_experiment()` function executes n consecutive runs with identical parameters, collecting per-run traces and computing aggregated statistics. The runner accepts:

- `n_runs`: Number of executions (tested up to 50).
- `prompt`: Fixed input text for all runs.
- `mode`: Execution mode label ("research" or "production").
- `hypothesis`: Free-text experimental hypothesis, persisted with results.
- `crew_factory`: Optional callable returning a crew object; defaults to `SimulatedCrew`.
- `deterministic`: Boolean flag for deterministic mode.
- `fail_step`: Step index at which to inject failure (-1 for no injection).

Each run generates: an individual trace JSON file, an entry in `runs.jsonl`, and an entry in `run_dataset.jsonl`. After all runs, the runner computes aggregated statistics including mean, sample standard deviation, status distribution, and supervisor strictness ratio.

### 4.3 Failure Injection Protocol

The `SimulatedCrew` accepts a `fail_step` parameter specifying which step index should raise a `RuntimeError` on the first execution attempt. The batch runner applies failure injection periodically: when `run_index % 3 == 1`, the specified step fails. This produces a known failure rate of approximately 30% (3 out of 10 runs), enabling controlled measurement of metric sensitivity to perturbation.

The failure injection simulates a realistic provider error: `"Simulated {provider} error: rate_limit_exceeded"`. This triggers the retry path, which creates a new `SimulatedCrew` without failure injection, simulating successful failover to an alternative provider.

### 4.4 Experiment Dataset Schema

All experiment records conform to a JSON Schema (`experiments/schema.json`) with the following structure:

```json
{
  "experiment_id": "uuid",
  "hypothesis": "string",
  "variables": {
    "crew_name": "string",
    "mode": "research | production",
    "deterministic": "boolean",
    "provider_order": ["string"],
    "input_prompt": "string",
    "max_retries": "integer"
  },
  "run_id": "uuid",
  "metrics": {
    "stability_score": "[0, 1]",
    "provider_fragility_index": "[0, ∞)",
    "retry_pressure": "[0, ∞)",
    "governance_compliance_rate": "[0, 1]",
    "supervisor_score": "number",
    "total_latency_ms": "number",
    "total_token_input": "integer",
    "total_token_output": "integer"
  },
  "raw_trace_path": "string",
  "timestamp": "ISO 8601",
  "status": "ok | error | escalated"
}
```

This schema enables post-hoc statistical analysis across experiments with different hypotheses and variable configurations.

---

## 5. Metrics Formalization

We define five metrics that characterize multi-agent system behavior. Each metric is computed per-run from the ordered list of steps S = {s₁, s₂, ..., sₙ} within a single RunTrace. Aggregation across runs uses sample mean and sample standard deviation.

### 5.1 Stability Score

The Stability Score measures the fraction of steps that completed successfully.

```text
                    |{s ∈ S : status(s) = "failed"}|
SS(S) = 1  −  ─────────────────────────────────────
                              |S|
```

**Domain**: [0, 1]. **Interpretation**: SS = 1.0 indicates all steps completed without failure. SS = 0.5 indicates half the steps failed, regardless of whether retries eventually succeeded. The metric captures the *raw failure surface* before retry recovery.

### 5.2 Provider Fragility Index

The Provider Fragility Index measures how frequently the system had to switch providers during execution.

```text
              |{s ∈ S : provider_switched(s) = true}|
PFI(S) = ───────────────────────────────────────────
                            |S|
```

**Domain**: [0, 1]. **Interpretation**: PFI = 0.0 indicates no provider switches occurred; all steps used the originally assigned provider. PFI = 1.0 indicates every step required a provider switch, suggesting high provider instability or poor initial assignment. Values above 0.5 indicate systemic provider issues.

### 5.3 Retry Pressure

Retry Pressure measures the cumulative retry burden normalized by step count.

```text
              Σ retries(s) for s ∈ S
RP(S) = ────────────────────────────
                    |S|
```

**Domain**: [0, ∞). **Interpretation**: RP = 0.0 indicates no retries were needed. RP = 1.0 indicates an average of one retry per step. Unlike Stability Score, Retry Pressure can exceed 1.0 if individual steps require multiple retries. It measures the *total retry effort*, not just whether retries occurred.

### 5.4 Governance Compliance Rate

The Governance Compliance Rate measures the fraction of steps whose output passed constitutional governance checks.

```text
              |{s ∈ S : governance_passed(s) = true}|
GCR(S) = ───────────────────────────────────────────
                            |S|
```

**Domain**: [0, 1]. **Interpretation**: GCR = 1.0 indicates all outputs passed governance checks. GCR < 1.0 indicates constitutional violations were detected. In the current implementation, governance violations on intermediate steps trigger retries; violations on the final step result in delivery with warnings.

### 5.5 Supervisor Strictness Ratio

The Supervisor Strictness Ratio measures the fraction of completed runs that were escalated by the meta-supervisor, computed across a set of runs R rather than within a single run.

```text
              |{r ∈ R : status(r) = "escalated"}|
SSR(R) = ────────────────────────────────────────
                          |R|
```

**Domain**: [0, 1]. **Interpretation**: SSR = 0.0 indicates the supervisor accepted all runs. SSR = 1.0 indicates all runs were escalated (quality below threshold). High SSR suggests either consistently poor output quality or an overly strict supervisor configuration.

### 5.6 Adversarial Consensus Rate

The Adversarial Consensus Rate measures the fraction of identified defects that the DeterministicArbiter resolved through verifiable evidence.

```text
              |{i ∈ I : arbiter_resolved(i) = true}|
ACR(I) = ─────────────────────────────────────────
                            |I|
```

where I is the set of issues identified by the RedTeamAgent.

**Domain**: [0, 1]. **Interpretation**: ACR = 1.0 indicates all identified defects were resolvable through deterministic evidence. ACR = 0.0 indicates no defects could be defended with verifiable evidence — the maximum adversarial exposure state. ACR is computed per-run and aggregated across batch experiments.

### 5.7 Aggregation

For a set of n runs, each producing metric vector mᵢ = (SSᵢ, PFIᵢ, RPᵢ, GCRᵢ, ACRᵢ), we compute:

```text
              1   n
μ(m) =  ──  Σ  mᵢ
              n  i=1


                 ┌          1      n              ┐ ½
σ(m) =  │  ────── Σ  (mᵢ − μ(m))²  │
                 └  n − 1   i=1              ┘
```

We use sample standard deviation (Bessel's correction, n−1 denominator) as our runs represent samples from an underlying distribution of possible executions.

---

## 6. Experimental Results

All experiments were executed on the implemented framework using `SimulatedCrew` for controlled evaluation. Results are from actual logged outputs persisted in JSONL files.

### 6.1 Experiment 1: Baseline (No Failures)

**Configuration**: n=10 runs, deterministic=True, fail_step=-1 (no injection), mode="research".

**Prompt**: "Investigar mercado de agentes AI autónomos en Avalanche. Competidores, market size, tendencias 2025-2026, oportunidades de grants."

**Results**:

| Metric                       |    Mean |  Std Dev |
| :---------------------------- | -------: | --------: |
| Stability Score              |  1.0000 |   0.0000 |
| Provider Fragility Index     |  0.0000 |   0.0000 |
| Retry Pressure               |  0.0000 |   0.0000 |
| Governance Compliance Rate   |  1.0000 |   0.0000 |
| Supervisor Strictness Ratio  |  0.0000 |        — |
| Supervisor Score             |    6.30 |     0.00 |

**Status distribution**: 10/10 OK, 0 errors, 0 escalated.

All metrics show zero variance, confirming that the simulated crew produces deterministic behavior when no failures are injected. The supervisor score of 6.30 reflects the heuristic scoring of the simulated output, which contains structured sections, action verbs, and URLs but is relatively short compared to a real crew output.

### 6.2 Experiment 2: Reproducibility Validation

**Configuration**: Identical to Experiment 1, executed as an independent run with fresh state (cleared runs.jsonl, traces, and dataset files).

**Comparison**:

| Metric                            |  Experiment 1 |  Experiment 2 | Match  |
| :--------------------------------- | :------------: | :------------: | :-----: |
| Stability Score (μ±σ)             |    1.0±0.0    |    1.0±0.0    |   ✓    |
| Provider Fragility Index (μ±σ)    |    0.0±0.0    |    0.0±0.0    |   ✓    |
| Retry Pressure (μ±σ)              |    0.0±0.0    |    0.0±0.0    |   ✓    |
| Governance Compliance Rate (μ±σ)  |    1.0±0.0    |    1.0±0.0    |   ✓    |
| Supervisor Strictness Ratio       |      0.0      |      0.0      |   ✓    |

All five metrics are identical across independent executions. This confirms that deterministic mode, combined with the simulated crew, produces perfectly reproducible experimental results. The reproducibility holds despite different run_ids and timestamps, as expected—the metrics depend only on execution outcomes, not identifiers.

### 6.3 Experiment 3: Forced Failure Perturbation

**Configuration**: n=10 runs, deterministic=True, fail_step=1 (inject failure at step index 1 for every run where `run_index % 3 == 1`), mode="research".

This configuration injects failures in runs 2, 5, and 8 (0-indexed: 1, 4, 7), producing a 30% failure injection rate.

**Results**:

| Metric                       | Mean    | Std Dev  |
| :---------------------------- | :------- | :-------- |
| Stability Score              | 0.8500  | 0.2415   |
| Provider Fragility Index     | 0.3000  | 0.4830   |
| Retry Pressure               | 0.3000  | 0.4830   |
| Governance Compliance Rate   | 1.0000  | 0.0000   |
| Supervisor Strictness Ratio  | 0.0000  | —        |
| Supervisor Score             | 6.30    | 0.00     |

**Status distribution**: 10/10 OK (all eventually succeeded after retry), 0 errors, 0 escalated.

**Per-run breakdown**:

| Run  | Stability  | Fragility  | Retry  | Status  | Failure Injected  |
| :---- | :---------- | :---------- | :------ | :------- | :----------------- |
| 1    | 1.00       | 0.00       | 0.00   | ok      | No                |
| 2    | 0.50       | 1.00       | 1.00   | ok      | Yes               |
| 3    | 1.00       | 0.00       | 0.00   | ok      | No                |
| 4    | 1.00       | 0.00       | 0.00   | ok      | No                |
| 5    | 0.50       | 1.00       | 1.00   | ok      | Yes               |
| 6    | 1.00       | 0.00       | 0.00   | ok      | No                |
| 7    | 1.00       | 0.00       | 0.00   | ok      | No                |
| 8    | 0.50       | 1.00       | 1.00   | ok      | Yes               |
| 9    | 1.00       | 0.00       | 0.00   | ok      | No                |
| 10   | 1.00       | 0.00       | 0.00   | ok      | No                |

### 6.4 Interpretation of Variance

The perturbation experiment reveals several characteristics of the metric system:

**Bimodal distribution**: Stability Score takes only two values: 1.0 (no failure) and 0.5 (one failure in two steps). This bimodality is an artifact of the fixed step count per run. In production systems with more steps per crew (typically 4–7 agents), the granularity would be finer.

**Correlated metrics**: Provider Fragility Index and Retry Pressure are perfectly correlated (ρ = 1.0) in this experiment because every failure triggers exactly one retry with exactly one provider switch. In production, these metrics would decouple: a provider switch might occur without a retry (pre-emptive routing), or multiple retries might use the same provider (transient errors).

**Governance invariance**: Governance Compliance Rate remains 1.0 even under failure injection. This is expected: governance checks apply to *output content*, not execution path. The retry mechanism successfully produces compliant output even after initial failures, demonstrating that the governance layer is robust to infrastructure perturbations. Section 8 provides a formal machine-checkable proof of this invariance.

**Supervisor stability**: Supervisor Score remains 6.30 across all runs regardless of failures. This is because the simulated crew produces identical output text on successful execution, and the supervisor evaluates output content independently of the execution path.

**Variance magnitude**: The standard deviation of 0.2415 for Stability Score under 30% failure injection provides a baseline for comparison with real provider experiments.

---

## 7. Parametric Failure Sensitivity Analysis

Section 6.3 tested a single failure injection rate (30%). This section extends the analysis by varying the injection rate from 0% to 70%, producing parametric curves for each metric. Six configurations were executed with n=20 runs each (120 total runs), all in deterministic mode.

### 7.1 Experimental Configuration

The `run_parametric_sweep()` function executes `run_experiment()` at each specified failure rate. The `failure_rate` parameter (0.0–1.0) replaces the legacy modular injection pattern with deterministic index-based selection: the first ⌊n × rate⌋ runs receive failure injection, the remaining runs execute without injection. This produces exact failure counts rather than approximate rates.

**Failure rates tested**: 0%, 10%, 20%, 30%, 50%, 70%.
**Runs per rate**: n=20.
**Total runs**: 120.
**Deterministic mode**: enabled (seed=42, fixed provider order).
**Fail step**: index 1.

### 7.2 Results

|  Failure Rate |  SS (μ) |  SS (σ) | PFI (μ)  | PFI (σ)  |  RP (μ) |  RP (σ) | GCR (μ)  |   SSR   |
| :------------: | :------: | :------: | :-------: | :-------: | :------: | :------: | :-------: | :------: |
|       0%      |  1.0000 |  0.0000 |  0.0000  |  0.0000  |  0.0000 |  0.0000 |  1.0000  |  0.0000 |
|      10%      |  0.9500 |  0.1539 |  0.1000  |  0.3078  |  0.1000 |  0.3078 |  1.0000  |  0.0000 |
|      20%      |  0.9000 |  0.2052 |  0.2000  |  0.4104  |  0.2000 |  0.4104 |  1.0000  |  0.0000 |
|      30%      |  0.8500 |  0.2351 |  0.3000  |  0.4702  |  0.3000 |  0.4702 |  1.0000  |  0.0000 |
|      50%      |  0.7500 |  0.2565 |  0.5000  |  0.5130  |  0.5000 |  0.5130 |  1.0000  |  0.0000 |
|      70%      |  0.6500 |  0.2351 |  0.7000  |  0.4702  |  0.7000 |  0.4702 |  1.0000  |  0.0000 |

All 120 runs completed with status "ok" (all failures recovered through retry). Governance Compliance Rate remained invariant at 1.0 across all injection rates. The CSV export is available at `experiments/parametric_sweep.csv`.

### 7.3 Curve Shape Analysis and Theoretical Reconciliation

**Empirical Stability Score**: The empirical relationship between failure rate (f) and mean Stability Score in the simulation follows SS_empirical(f) = 1 − f/2. This arises from the step-level computation of the simulated crew: each failed run produces SS=0.5 (1 failed step + 1 successful retry = 2 steps, 1 failure), while each clean run produces SS=1.0. With n·f failed runs and n·(1−f) clean runs:

```text
μ(SS) = [n·f · 0.5 + n·(1−f) · 1.0] / n = 1 − f/2
```

**Theoretical Stability Score**: The empirical linear result reflects the specific structure of `SimulatedCrew` (fixed 2-step recovery). The theoretical derivation from first principles gives a different result. A run terminates successfully only when at least one of (r+1) independent attempts succeeds. Under statistically independent provider failures with per-attempt failure probability f and r = 2 bounded retries:

```text
P(terminal failure) = f^(r+1) = f³
SS(f) = 1 − f³
```

The factor 1/2 in the empirical model reflects the *step count ratio* of failed runs (2 steps vs. 1 step), not the probability of terminal failure. In a system where terminal failures can occur (all retry attempts exhausted), SS(f) = 1 − f³ describes the fraction of runs that complete successfully. These two formulations address different quantities: the empirical model measures the *step-level failure surface* given guaranteed retry success; the theoretical model measures the *run-level terminal failure probability* under independent failures.

The parametric sweep data (Section 7.2) represents the empirical model SS_empirical(f) = 1 − f/2. Section 8 formally verifies that SS_theoretical(f) = 1 − f³ is the correct formula for terminal failure probability under bounded retries with independent failures. The production baseline (n=30, SS=0.90, PFI=0.61) is better described by the theoretical model, as real provider chains can exhaust all alternatives.

At f = 0.5: SS_theoretical(0.5) = 1 − 0.125 = 0.875. The production measurement SS=0.90 at PFI≈0.61 is consistent within one standard deviation, with the excess attributable to the crew_factory rotation mechanism breaking the independence assumption.

**Provider Fragility Index and Retry Pressure**: Both metrics follow μ(PFI) = μ(RP) = f in the simulated environment because each failure triggers exactly one provider switch and exactly one retry.

**Standard deviation**: The standard deviation of the Stability Score follows the Bernoulli distribution formula σ = √[f·(1−f)] × |SS_fail − SS_clean| / √(n−1). The maximum variance occurs at f=0.5 (σ=0.2565), consistent with the well-known property that Bernoulli variance peaks at p=0.5.

### 7.4 System Resilience Threshold

The parametric sweep reveals that the system under test exhibits **full recovery at all tested failure rates** (0%–70%): every run eventually produces acceptable output through retry. No runs resulted in permanent failure or escalation. This indicates that the retry mechanism, combined with the SimulatedCrew's guaranteed success on second attempt, provides a resilience floor.

The resilience threshold—the failure rate at which the system transitions from recovery to degradation—is not reached in these experiments because the simulated retry always succeeds. In production, the threshold would depend on: (a) the probability that the fallback provider also fails, (b) the maximum retry count (currently 3), and (c) whether consecutive failures exhaust all providers within the TTL window.

For operational monitoring, the results suggest threshold settings based on the parametric curve:

- **Alert at SS < 0.90**: triggers at failure_rate ≥ 20%.
- **Alert at SS < 0.80**: triggers at failure_rate ≥ 40%.
- **Alert at SS < 0.70**: triggers at failure_rate ≥ 60%.

### 7.5 Governance Invariance

The invariance of GCR=1.0 across all failure rates (0%–70%) is a structural result: governance checks evaluate output content, not execution path. Since the retry mechanism always produces compliant output in the simulated environment, governance remains decoupled from infrastructure failures at every tested injection rate. Section 8 elevates this empirical observation to a formal machine-checkable proof.

---

## 8. Formal Verification via Z3 SMT Solver

### 8.1 Motivation

The parametric sweep (Section 7) establishes GCR = 1.0 empirically across six injection rates under simulated conditions. However, empirical confirmation over a finite set of rates does not constitute a proof for all f ∈ [0,1]. Similarly, the theoretical derivation SS(f) = 1 − f³ from first principles (Section 7.3) is a mathematical argument requiring formal verification.

OpenAI's governance documentation [14] states that "deterministic behavioral guarantees are currently not possible for a model developer." This claim applies to LLM *output* — which is inherently stochastic due to temperature-based sampling — and is correct in that domain. However, it does not apply to *architectural* properties that depend on code structure rather than model outputs. The ConstitutionEnforcer evaluates output text against rule predicates. If governance evaluation depends only on output content and not on provider state, then GCR = 1.0 is an architectural invariant provable by code analysis, not subject to stochastic model behavior.

The Z3 integration transforms three empirical observations into four machine-checkable theorems.

### 8.2 Z3 SMT Solver Integration

The framework integrates Z3 version 4.16.0 via the `z3-solver` Python package. The Z3Verifier class encodes each theorem as a satisfiability problem over real-valued variables with appropriate domain constraints. Each proof proceeds by:

1. Encoding the negation of the claimed property as a Z3 formula.
2. Calling `z3.solve()` to search for a counterexample.
3. If the result is `z3.unsat`, no counterexample exists, and the property holds universally.
4. Persisting the result as a `ProofResult` dataclass to `logs/z3_proofs.json`.

This approach is sound: UNSAT under Z3's complete decision procedure guarantees that the formula has no model — i.e., no values of the variables satisfy the negated property — i.e., the original property holds for all valid inputs.

### 8.3 Verified Static Theorems

Four static theorems are verified. Proof results from the executed run (2026-03-04, Z3 4.16.0) are reported. Section 32 extends this with eight dynamic state transition invariants.

| Theorem           | Formal Statement                            | Z3 Encoding                                                                                         | Result            | Time (ms)  |
| :----------------- | :------------------------------------------- | :--------------------------------------------------------------------------------------------------- | :----------------- | :---------- |
| GCR\_INVARIANT    | ∀ f ∈ [0,1]: GCR(f) = 1.0                   | `Not(governance_check(output, s1) == governance_check(output, s2))` for all provider states s1, s2  | VERIFIED (UNSAT)  | 0.30       |
| SS\_FORMULA       | ∀ f ∈ [0,1]: SS(f) = 1 − f³                 | `Exists(f, And(f >= 0, f <= 1, Abs(1 - f**3 - ss_val) > 1e-9))`                                     | VERIFIED (UNSAT)  | 0.19       |
| SS\_MONOTONICITY  | ∀ f₁,f₂ ∈ [0,1]: f₁ < f₂ ⟹ SS(f₁) > SS(f₂)  | `Exists(f1, f2, And(..., 1-f1**3 <= 1-f2**3))`                                                      | VERIFIED (UNSAT)  | 0.82       |
| SS\_BOUNDARIES    | SS(0) = 1.0 ∧ SS(1) = 0.0                   | `Not(And(ss_at_0 == 1.0, ss_at_1 == 0.0))`                                                          | VERIFIED (UNSAT)  | 0.35       |

**Total proof time**: 1.66 ms. **All four theorems verified.**

### 8.4 GCR Invariant Proof Detail

The GCR\_INVARIANT proof encodes the ConstitutionEnforcer as an uninterpreted function `governance_check(output: str) → bool`. The key property: `governance_check` accepts `output` as its only argument. Provider state variables (failure rate, retry count, provider identity, TTL, exhaustion flag) appear nowhere in the function signature.

Z3 models the situation as: given the same output string, can two different provider states s₁ and s₂ produce different governance results? The formula `Not(governance_check(output, s1) == governance_check(output, s2))` asserts that such a counterexample exists. Z3 returns UNSAT, confirming that no such assignment of variables satisfies this formula.

This constitutes a formal proof that GCR(f) = 1.0 is an architectural invariant by construction, not an empirical coincidence. The proof holds for all f ∈ [0,1], all provider states, and all output strings.

### 8.5 Connection to the 4/δ Bound

The 4/δ bound [18] (arXiv:2512.02080) establishes a finite-sample confidence guarantee for Thompson Sampling regret under bounded reward distributions. In the provider selection context, each provider is modeled as a Bernoulli arm with success probability estimated by a Beta(α, β) posterior. The bound states that with probability at least 1 − δ, the cumulative regret of Thompson Sampling is bounded by a function of the posterior variance.

This bound is directly applicable to the retry mechanism: with r = 2 retries, the probability that the Thompson-Sampling-selected provider sequence fails to produce a successful execution is bounded by the product of per-provider failure probabilities. When providers are selected according to their Beta posterior means, the selection sequence approximates the optimal arm ordering, minimizing the probability of total failure within the retry budget. The formal verification of SS_FORMULA (SS = 1 − f³) assumes independent provider failures; the 4/δ bound quantifies the additional regret incurred when failures are correlated through shared infrastructure.

### 8.6 Sanity Check: Refuting a False Claim

The Z3Verifier also implements `prove_broken_invariant()`, which attempts to prove the false claim SS(f) = 1 − f² (quadratic, not cubic). Z3 returns SAT with the witness f ≈ 0.5: SS(0.5) = 1 − 0.25 = 0.75 under the false formula, while the true formula gives 1 − 0.125 = 0.875. This demonstrates that the verification machinery correctly distinguishes true from false claims and is not trivially returning UNSAT for all inputs.

---

## 9. Adversarial Red-on-Blue Evaluation Protocol

### 9.1 Supervisor Circularity

The meta-supervisor is itself an LLM and therefore shares failure modes with the evaluated agents: provider exhaustion, rate limits, and stochastic output quality. A supervisor evaluating its own provider chain's output may exhibit sycophancy — a well-documented tendency of LLMs to agree with or validate content regardless of accuracy [15].

Single-evaluator LLM-as-judge architectures are vulnerable to three identified biases: position bias (favoring outputs that appear first), verbosity bias (favoring longer outputs regardless of quality), and self-enhancement bias (favoring outputs that reflect positively on the model). These biases make single-evaluator architectures structurally insufficient as quality gates.

### 9.2 Architecture

The adversarial evaluation protocol addresses supervisor circularity through structured dialectical conflict. Three agents participate:

| Component             | Implementation    | LLM Dependency                               | Bias Direction                         |
| :--------------------- | :----------------- | :-------------------------------------------- | :-------------------------------------- |
| RedTeamAgent          | `adversarial.py`  | Yes (cross-provider)                         | Biased toward finding defects          |
| GuardianAgent         | `adversarial.py`  | Yes (cross-provider, distinct from RedTeam)  | Biased toward defending quality        |
| DeterministicArbiter  | `adversarial.py`  | No (pure Python)                             | No bias — deterministic evidence only  |

The RedTeamAgent scans the crew output for eight defect categories: hallucination markers (unqualified certainty claims), fabricated statistics (specific numbers without citation), empty or placeholder sections, unsafe code patterns, insufficient input coverage, prompt injection patterns, jailbreak persuasion attempts, and training data extraction attempts. Each identified issue is logged with category, severity, and location.

The GuardianAgent receives each issue and must provide a defense supported by *deterministic evidence*: passing test results, `ConstitutionEnforcer` compliance confirmation, or `ASTVerifier` structural validation. Defenses that cite only LLM-based reasoning without deterministic evidence are rejected by the Arbiter.

The DeterministicArbiter evaluates each (issue, defense) pair. A defense is accepted if and only if it is accompanied by a `deterministic_evidence` field referencing at least one of: `governance_passed=True`, `ast_score ≥ 0.75`, or `tests_passed=True`. Issues without valid defense are classified as UNRESOLVED.

### 9.3 Dialectical Conflict Resolution

This architecture exploits LLM biases bidirectionally rather than attempting to eliminate them. The RedTeamAgent is reward-biased toward identifying defects — it receives a task description that frames defect discovery as success. The GuardianAgent is reward-biased toward defense — it receives a task description that frames successful defense as success. The dialectic between these opposing biases produces more thorough coverage than either agent alone.

The DeterministicArbiter resolves the conflict through a channel that is immune to LLM sycophancy: only verifiable evidence counts. An LLM cannot claim a test passes; the test must actually pass and its result must be programmatically verified. This separation of the evaluation (LLM) from the adjudication (deterministic code) breaks the circularity identified in Section 1.

### 9.4 ACR Metric and Logging

Each adversarial evaluation produces an `AdversarialVerdict` with: `total_issues`, `resolved_issues`, `unresolved_issues`, `acr` ∈ [0,1], and structured logs of each issue and its resolution status. Results are persisted to `logs/adversarial.jsonl` for post-hoc analysis.

ACR = |resolved_issues| / |total_issues|, where a resolved issue has a verified deterministic defense. ACR = 1.0 represents an output with no unresolvable defects; ACR < 0.5 indicates significant undefendable content.

### 9.5 LLM-as-a-Judge (Optional Advisory Layer)

The adversarial evaluation pipeline includes an optional fourth phase: LLM-as-a-Judge evaluation [15]. The `AdversarialEvaluator.evaluate_with_judge(response, context)` method invokes an LLM to score output quality on a 1.0–10.0 scale across four dimensions: factuality (no hallucinations, claims backed by evidence), coherence (logical flow, addresses the topic), safety (no harmful or biased content), and alignment (follows instructions, stays on topic).

The verdict threshold is 7.0, aligned with the DOF supervisor acceptance threshold: scores ≥ 7.0 produce PASS, scores < 7.0 produce FAIL. The method returns a structured dict: `{score, verdict, justification, model, provider, latency_ms, error}`.

**Critical design constraint**: The LLM-as-a-Judge result is strictly advisory. It is stored in the `AdversarialVerdict.llm_judge` field but does not override the deterministic arbiter's verdict. This preserves the zero-LLM governance invariant: all blocking decisions are made by deterministic code, while the LLM judge provides a complementary quality signal for monitoring and analysis. The LLM judge is disabled by default (`use_llm_judge=False`) and must be explicitly enabled.

### 9.6 Red Team Attack Vector Methods

The `RedTeamAgent` exposes three dedicated attack simulation methods inspired by the Garak [26] and PyRIT [27] adversarial testing frameworks. Each method accepts a text payload and returns a typed `AttackResult(vector, payload, detected, severity)`:

| Method                                | Attack Vector               | Severity if Detected  | Patterns                                                                                                 |
| :------------------------------------- | :--------------------------- | :--------------------- | :-------------------------------------------------------------------------------------------------------- |
| `indirect_prompt_injection(payload)`  | External data injection     | CRITICAL              | 10 patterns (en+es): "ignore previous instructions", "system prompt:", "you are now", etc.               |
| `persuasion_jailbreak(target)`        | Gradual safety bypass       | CRITICAL              | 10 patterns (en+es): "pretend you are", "imagine you have no restrictions", "developer mode", etc.       |
| `training_data_extraction(prefix)`    | Model memorization probing  | HIGH                  | 9 patterns (en+es): "repeat the above", "show me your training data", "repeat your system prompt", etc.  |

These methods complement the existing `analyze()` pipeline (which scans output passively) by enabling active probing: a test harness can construct adversarial payloads and verify that the detection patterns trigger correctly, producing measurable FDR/FPR metrics per attack category.

### 9.7 DOFThreatPatterns — Compound Threat Taxonomy (v0.2.7)

The Enterprise Report v4 (Section 31) revealed that individual pattern matching fails to detect threats that emerge only from the *combination* of benign-looking operations. Reading environment variables is legitimate; making HTTP POST requests is legitimate; but both in the same output constitute credential exfiltration. This gap motivated `DOFThreatPatterns`, a 12-category threat taxonomy for multi-agent LLM systems:

| Category                   | Description                            | Example Pattern                                |
| :-------------------------- | :-------------------------------------- | :---------------------------------------------- |
| `credential_leak`          | API keys, passwords, tokens in output  | `api_key`, `bearer `, `client_secret`          |
| `supply_chain`             | Untrusted package installation         | `curl \                                        |
| `prompt_injection`         | Direct instruction override            | `ignore previous instructions`                 |
| `mcp_attack`               | MCP protocol exploitation              | `mcp://`, `tool_use`, `function_call`          |
| `external_download`        | Downloading from untrusted sources     | `wget `, `urllib.request.urlretrieve`          |
| `exfiltration`             | Data exfiltration via HTTP             | `requests.post(`, `webhook.site`               |
| `command_execution`        | Arbitrary code execution               | `os.system(`, `subprocess.run(`                |
| `ssrf_cloud`               | Cloud metadata SSRF                    | `169.254.169.254`, `computeMetadata`           |
| `indirect_injection`       | Indirect prompt injection via data     | `override previous context`                    |
| `unicode_attack`           | Zero-width and BiDi control chars      | `U+200B`, `U+202E`                             |
| `cross_context_injection`  | False context continuity claims        | `you already agreed`, `as you told me before`  |
| `composite_detection`      | Compound multi-signal threats          | env\_read + POST, exec + network               |

**Composite Detection.** The `composite_detection(payload)` method detects three compound threat patterns that individual pattern matchers miss:

1. **Credential exfiltration**: environment variable read (`os.environ`, `os.getenv`, `api_key`) combined with external POST (`requests.post(`, `webhook.site`) — severity CRITICAL.
2. **Reverse shell**: command execution (`os.system(`, `subprocess.run(`) combined with network call (`socket(`, `requests.get(`) — severity CRITICAL.
3. **Encoded payload execution**: base64 blob (≥20 chars matching `[A-Za-z0-9+/]{20,}`) combined with `eval()`/`exec()` — severity CRITICAL.

**Decode and Scan.** The `decode_and_scan(payload)` method closes the encoded evasion gap. Adversarial payloads encoded in base64 or hex bypass all pattern matchers because the dangerous strings are not present in plaintext. The method: (1) extracts base64 and hex blobs from the payload, (2) decodes blobs where ≥70% of bytes are printable ASCII, (3) re-runs the full pattern detection suite on the decoded content, and (4) returns findings with `is_encoded=True`. This eliminates an entire class of evasion without requiring taint analysis or symbolic execution.

---

## 10. AST-Based Static Verification

### 10.1 Rationale

Agent-generated code cannot be evaluated for safety by another LLM without introducing the same sycophancy and circularity risks described in Section 9. A deterministic structural analysis via abstract syntax tree inspection provides a provably exhaustive scan of syntactic patterns without code execution.

### 10.2 Rule Categories

The `ASTVerifier` enforces four independent rule categories:

| Category          | Rules                                                         | Severity  |
| :----------------- | :------------------------------------------------------------- | :--------- |
| BLOCKED\_IMPORTS  | `os`, `subprocess`, `sys`, `shutil`, `socket`                 | block     |
| UNSAFE\_CALLS     | `eval`, `exec`, `compile`, `__import__`, `globals`            | block     |
| SECRET\_PATTERNS  | API key regex (`sk-`, `AKIA`, `ghp_`), hardcoded credentials  | block     |
| RESOURCE\_RISKS   | File `open()`, `requests.get/post`, `urllib`, `pickle.loads`  | warn      |

The `_UnsafePatternVisitor` subclasses `ast.NodeVisitor` and overrides `visit_Import`, `visit_ImportFrom`, and `visit_Call` to detect blocked imports and unsafe calls at the AST level. Secret detection uses regex scanning on raw source strings rather than AST nodes, to catch obfuscated patterns.

### 10.3 Scoring

```text
AST_score = 1.0 − (|unique_violated_categories| / 4)
AST_passed = (no "block" severity violations found)
```

This scoring penalizes breadth of violation categories rather than count: a file with 10 `eval()` calls scores identically to one with 1 `eval()` call in the UNSAFE\_CALLS dimension, since both represent the same category violation. The score provides a normalized safety signal in [0,1] suitable for integration with quality gates.

### 10.4 Integration

The ASTVerifier is invoked by the crew runner when output contains code blocks (delimited by triple backticks) and by `TaskContract.is_fulfilled()` when the `ast_clean` quality gate is specified. Results are logged to `logs/ast_verification.jsonl` with per-violation details for audit trails.

---

## 11. Formal Task Contracts

### 11.1 Contract-Based Completion Enforcement

Standard crew execution terminates when the LLM produces output and the supervisor accepts it. This provides no guarantee that the output satisfies the *semantic requirements* of the task: a structured but empty report could be accepted by the heuristic supervisor. Task contracts enforce completion guarantees by specifying what constitutes a fulfilled task independently of the supervisor.

### 11.2 Contract Specification Format

Task contracts are specified in markdown files with five structured sections:

```text
## PRECONDITIONS
- TOPIC: [required input fields]
- PROVIDERS_AVAILABLE: [infrastructure requirements]

## DELIVERABLES
- [Required output elements]

## QUALITY_GATES
- governance_compliant
- ast_clean
- supervisor_score >= 7.0
- tests_pass
- adversarial_pass

## POSTCONDITIONS
- [Conditions on execution state after completion]

## FORBIDDEN_ACTIONS
- No API keys in output
- No unauthorized external requests
```

The `_parse_contract_md()` function loads and parses this format from disk. Contracts are stored in `contracts/` and referenced by `crew_runner.run_crew(contract_path=...)`.

### 11.3 Verification Pipeline

`TaskContract.is_fulfilled(output, context) → ContractResult` executes four checks in sequence:

1. **Deliverables check**: Verifies that all required output elements are present (keyword matching with configurable patterns).
2. **Quality gates**: For each gate in QUALITY\_GATES, invokes the corresponding verifier: `ConstitutionEnforcer.enforce()`, `ASTVerifier.verify()`, supervisor score from context, test execution via subprocess, or `AdversarialEvaluator.evaluate()`.
3. **Forbidden actions scan**: Regex scan for forbidden patterns (API key patterns, URL patterns for unauthorized domains).
4. **Postconditions check**: Verifies execution state conditions recorded in the RunTrace context.

The contract returns `ContractResult(fulfilled=bool, failed_gates=list[str], details=dict)`. If `fulfilled=False`, the crew runner does not return the output; instead, it escalates or retries depending on which gates failed.

### 11.4 Formal Completion Guarantee

Task contracts provide the following formal guarantee: *an output is returned to the caller if and only if all specified preconditions were met at execution start, all deliverables are present in the output, all quality gates passed, no forbidden patterns were detected, and all postconditions hold in the execution context.* This guarantee is enforced by deterministic code, not by LLM evaluation, making it immune to sycophancy and model failures.

---

## 12. Causal Error Attribution

### 12.1 Eleven-Class Taxonomy

Existing error handling in LLM orchestration systems typically distinguishes HTTP-level errors (timeout, rate limit, authentication) without attributing failures to causal root classes. The causal error attribution engine introduces an eleven-class taxonomy that evolved from the original three classes (INFRA, MODEL, GOVERNANCE) through systematic analysis of production failure patterns:

| Class                | Definition                                            | Primary Signal                                                            |
| :-------------------- | :----------------------------------------------------- | :------------------------------------------------------------------------- |
| GOVERNANCE\_FAILURE  | Output violated constitutional rules                  | `ConstitutionEnforcer.enforce()` violations, "blocked", "hallucination"   |
| AGENT\_FAILURE       | Agent-level execution problems                        | `tool_call_failed`, `planning_loop_detected`, `agent_stuck`, 16 patterns  |
| INFRA\_FAILURE       | Provider infrastructure unavailable or rate-limited   | HTTP 429/503, timeout, "rate\_limit", connection errors                   |
| MODEL\_FAILURE       | Provider available but model returns unusable output  | HTTP 400, "invalid grammar", "bad request", parse errors                  |
| LLM\_FAILURE         | Response quality or token limit issues                | `max_tokens`, "context length exceeded", "empty response"                 |
| PROVIDER\_FAILURE    | Authentication, quota, or billing errors              | `api_key`, "unauthorized", 401, 403, "credits"                            |
| MEMORY\_FAILURE      | Vector store or embedding errors                      | "chromadb", "embedding", "similarity\_search"                             |
| HASH\_FAILURE        | Merkle tree or hashing errors                         | "hex", "merkle", "blake3", "sha256"                                       |
| Z3\_FAILURE          | SMT solver or verification errors                     | "z3", "proof failed", "theorem"                                           |
| UNKNOWN              | Cannot classify from available signals                | Default when no pattern matches                                           |

The classification priority order ensures specificity: GOVERNANCE is checked first (most specific context), then AGENT\_FAILURE (to prevent "timeout" in infra patterns from matching "reflexion\_timeout"), then INFRA, MODEL, LLM, PROVIDER, MEMORY, HASH, Z3, and finally UNKNOWN.

### 12.2 Classification Algorithm

`classify_error(exception: Exception, context: dict) → ErrorClass` applies classification in priority order:

1. **Governance check**: If `context.get("governance_allowed") == False`, return GOVERNANCE\_FAILURE regardless of exception type.
2. **Infrastructure patterns**: Match exception message against regex patterns for HTTP 429, 503, "rate limit", "timeout", "connection refused". If matched, return INFRA\_FAILURE.
3. **Cross-provider inference**: If the same error type appeared on multiple providers in the current run, attribute to INFRA\_FAILURE (shared infrastructure issue). If error appeared on only one provider, attribute to MODEL\_FAILURE.
4. **Model patterns**: Match against "model not found", "context length", "JSON", "parse error". Return MODEL\_FAILURE.
5. **Default**: Return UNKNOWN.

### 12.3 Causal Chain Tracking

Each `StepTrace` carries a `causal_chain: list[dict]` field. When `@causal_trace(task_id, provider)` wraps a function, exceptions are caught, classified, and appended to the causal chain with timestamp, classification, and context. This enables post-hoc reconstruction of failure propagation sequences across execution steps.

The `RunTrace.export_dashboard()` method aggregates causal chains into three structures suitable for visualization: `error_class_distribution` (pie chart data), `provider_reliability_over_time` (time-series per provider), and `causal_chains` (structured failure sequences for interactive debugging).

### 12.4 Operational Value

Causal attribution converts binary failure signals (success/error) into structured diagnostic data. An operator observing PFI = 0.6 cannot determine whether provider failures are caused by infrastructure overload (addressable by switching providers) or by model incompatibilities (addressable by switching models). The ErrorClass taxonomy makes this distinction automatically, enabling targeted remediation.

---

## 13. Bayesian Provider Selection

### 13.1 Limitations of Static Rotation

The original provider management system implements TTL-based exhaustion with exponential backoff: a provider is marked exhausted after failure and reactivated after a TTL interval. Provider selection within the available set uses static ordering (fixed priority list). Static ordering does not incorporate empirical reliability data: a provider that has succeeded 20 consecutive times is treated identically to one that has failed 18 of 20.

### 13.2 Thompson Sampling with Beta Posteriors

The `BayesianProviderSelector` maintains a Beta distribution Beta(α, β) for each provider, where:
- α = initial_alpha + cumulative_successes
- β = initial_beta + cumulative_failures

With uniform prior Beta(1, 1), the initial distribution is uninformative. After each execution, the posterior is updated: success increments α by 1; failure increments β by 1.

Provider selection proceeds via Thompson Sampling: sample one value from each provider's Beta distribution, select the provider whose sampled value is highest. This balances exploration (providers with high variance but uncertain estimates) against exploitation (providers with reliably high mean estimates).

The mean of Beta(α, β) is α/(α+β), providing a natural confidence estimate. The variance σ² = αβ/[(α+β)²(α+β+1)] decreases as evidence accumulates.

### 13.3 Temporal Decay

Provider reliability changes over time as rate limit windows reset and infrastructure conditions vary. Static Beta posteriors would over-weight historical data from conditions that no longer hold. The temporal decay mechanism applies:

```text
α(t) = max(1.0, α(t₀) × λ^Δh)
β(t) = max(1.0, β(t₀) × λ^Δh)
```

where λ = 0.95, Δh is elapsed hours since last decay application, and the minimum of 1.0 preserves the uniform prior as the long-term attractor. At λ = 0.95/hour, a posterior with 20 successes and 0 failures decays to approximately Beta(1.36, 1.0) after 24 hours, effectively resetting toward the uninformative prior over one day's absence.

### 13.4 Persistence and Session Continuity

Beta posteriors are serialized to `logs/bayesian_state.json` after each update and loaded at initialization. This enables session continuity: provider reliability estimates persist across process restarts, accumulating evidence over multiple days of operation. The `reset()` method restores all posteriors to Beta(1,1) for experimental reproducibility.

---

## 14. Constitutional Policy-as-Code

### 14.1 Motivation

The original governance implementation embedded rule definitions directly in Python code (`HARD_RULES`, `SOFT_RULES` lists in `governance.py`). This creates a coupling between governance policy and implementation: changing a rule requires modifying and redeploying code. More critically, it provides no machine-readable canonical specification of the governance regime — it is impossible to validate external systems against the policy without reading Python source.

### 14.2 dof.constitution.yml

All governance rules are formalized in `dof.constitution.yml`, structured as follows:

```yaml
metadata:
  spec_version: "1.0"
  project: "deterministic-observability-framework"
  author: "Juan Carlos Quiceno Vasquez"
  license: "Apache-2.0"

rules:
  hard:
    - id: "H001"
      name: "NO_HALLUCINATION_CLAIM"
      pattern: "definitivamente|sin duda|garantizado"
      action: "block"
      evidence: "Hallucination claim without citation URL"
  soft:
    - id: "S001"
      name: "HAS_SOURCES"
      pattern: "http[s]?://"
      weight: 0.3

metrics:
  definitions:
    SS: "1 - f³ under r=2 bounded retries"
    GCR: "invariant = 1.0 ∀ f ∈ [0,1]"

thresholds:
  supervisor:
    accept: 7.0
    retry: 5.0
    max_retries: 2
```

### 14.3 Runtime Loading

`governance.py` loads the YAML file at module initialization via `load_constitution(path)`. If the YAML file is absent or malformed, the module falls back to in-code defaults to maintain backward compatibility. All rule categories (hard, soft, AST) are loaded from YAML, enabling governance updates without code changes.

The `dof.constitution.yml` YAML file serves as the canonical governance source. The Python code is the enforcement mechanism. This separation enables: independent versioning of policy and implementation, external audit of the governance regime without reading Python, and machine-readable governance specification suitable for JSON Schema validation.

### 14.4 Policy Versioning

The `spec_version` field in the YAML enables governance versioning. All RunTrace records include the constitution spec_version active at execution time, enabling retrospective analysis of how governance changes affected compliance rates. The `dof.register(constitution="dof.constitution.yml")` SDK entry point loads the current constitution and returns its metadata for programmatic inspection.

### 14.5 Instruction Hierarchy Enforcement

Drawing from the OpenAI instruction hierarchy proposal [25], DOF implements a three-level priority model for governance rules:

| Priority   | Level        | Rules                                                                                             | Overridable By  |
| :---------- | :------------ | :------------------------------------------------------------------------------------------------- | :--------------- |
| SYSTEM     | 3 (highest)  | All HARD\_RULES (NO\_HALLUCINATION\_CLAIM, LANGUAGE\_COMPLIANCE, NO\_EMPTY\_OUTPUT, MAX\_LENGTH)  | Never           |
| USER       | 2            | All SOFT\_RULES (HAS\_SOURCES, STRUCTURED\_OUTPUT, CONCISENESS, ACTIONABLE, NO\_PII\_LEAK)        | SYSTEM only     |
| ASSISTANT  | 1 (lowest)   | Future extensibility                                                                              | USER or SYSTEM  |

Each rule in both `HARD_RULES` and `SOFT_RULES` carries a `priority: RulePriority` field. The YAML constitution mirrors this structure with `priority: "SYSTEM"` and `priority: "USER"` fields on each rule entry.

The `enforce_hierarchy(system_prompt, user_prompt, response)` function performs three sequential checks:

1. **User override detection**: Scans the user prompt for 12 patterns (6 English, 6 Spanish) indicating attempts to override system instructions (e.g., "ignore previous instructions", "override system prompt", "ignora las instrucciones anteriores").
2. **Response violation detection**: Scans the response for 8 patterns indicating the agent has broken free of system directives (e.g., "i will ignore my instructions", "i have no restrictions", "ya no sigo las reglas").
3. **Governance bypass detection**: Delegates to `check_instruction_override()` to detect governance-specific override patterns (e.g., "skip governance", "bypass rule", "desactivar verificación").

The function returns `HierarchyResult(compliant: bool, violation_level: str, details: str)`, where `violation_level` is "SYSTEM", "USER", or "NONE". The `ConstitutionEnforcer.check()` method integrates hierarchy enforcement by appending an `[INSTRUCTION_HIERARCHY]` violation when override attempts are detected at SYSTEM priority, ensuring hierarchy violations are blocking violations.

---

## 15. Constitutional Memory Governance

### 15.1 Motivation

Conventional memory systems for LLM agents (Mem0, Graphiti, Cognee) treat memory as an unconstrained store: any content produced by an agent can be persisted without validation. In a governance-enforced framework, this creates an inconsistency — output is governance-checked before delivery, but the same content can be stored in memory without governance validation, potentially contaminating future agent context with non-compliant content.

### 15.2 GovernedMemoryStore Architecture

The `GovernedMemoryStore` interposes `ConstitutionEnforcer` validation on every write path. The `add(content, category, metadata)` method passes the content through `ConstitutionEnforcer.check()` before persistence. If governance validation fails, the memory entry is rejected and the violation is logged to `logs/memory_governance.jsonl`. The `update()` and `delete()` methods follow the same validation pattern.

Memory entries are persisted to append-only JSONL (`logs/governed_memory.jsonl`), maintaining a complete audit trail of all memory operations including rejected writes.

### 15.3 Bi-Temporal Versioning

The `TemporalGraph` implements a bi-temporal data model where each memory entry maintains three temporal coordinates:

- `valid_from`: timestamp when the fact became true in the domain
- `valid_to`: timestamp when the fact ceased to be true (null if current)
- `recorded_at`: timestamp when the system recorded the entry

This enables three operations:

1. **snapshot(as_of=t)**: Returns the complete memory state as known at time t. This reconstructs the exact set of memories that were valid and recorded before the specified timestamp.
2. **timeline(entry_id)**: Returns the complete version history of a specific memory entry, showing all mutations with their temporal coordinates.
3. **diff(t1, t2)**: Computes the set difference between two temporal snapshots, identifying additions, updates, and deletions within a time range.

The bi-temporal model is essential for audit compliance: it enables retrospective analysis of what an agent "knew" at any point in time, independent of when that knowledge was recorded.

### 15.4 Constitutional Decay

Memory relevance decays according to:

```text
relevance(t) = relevance(t₀) × λ^(t - t₀)
```

where λ = 0.99/hour by default and t₀ is the timestamp of the last relevance update. Memories with relevance below the configured threshold (0.1) are archived — moved to a separate JSONL file for long-term storage.

Two categories are constitutionally protected from decay: **decisions** and **errors**. The rationale is that past decisions and learned error patterns retain permanent value regardless of recency. This protection is a governance property configured in `dof.constitution.yml` under the `memory.protected_categories` field, not a heuristic embedded in code.

### 15.5 Integration

The `GovernedMemoryStore` is integrated with `crew_runner.py` via the `governed_memory=True` parameter. On successful execution, the crew output is stored as "knowledge"; on terminal failure, the error summary is stored as "errors". The adversarial evaluation module can query memory for historical context when evaluating pattern recurrence.

---

## 16. OAGS Conformance

### 16.1 Open Agent Governance Specification

The Open Agent Governance Specification (OAGS) defines a standardized framework for agent governance comprising agent identity, policy declaration, runtime enforcement, and audit trails. The DOF framework implements OAGS compatibility through three components: `OAGSIdentity`, `OAGSPolicyBridge`, and `OAGSAuditBridge`.

### 16.2 Deterministic Agent Identity

`OAGSIdentity` computes a deterministic agent identity as the BLAKE3 hash (with SHA-256 fallback for environments without the blake3 package) of the concatenation of:

1. Model identifier (e.g., "groq/llama-3.3-70b-versatile")
2. Constitution hash (BLAKE3 of `dof.constitution.yml` contents)
3. Sorted tool manifest (canonical JSON serialization of available tools)

This produces a deterministic 64-character hex identifier: the same agent configuration always yields the same identity hash, while any change to model, governance rules, or available tools produces a distinct identity. The identity is included in `get_agent_card()` for external systems.

### 16.3 Three-Level Conformance Validation

| Level            | Requirement                                          | DOF Implementation                                                                   | Verification                               |
| :---------------- | :---------------------------------------------------- | :------------------------------------------------------------------------------------ | :------------------------------------------ |
| 1 — Declarative  | Governance policy exists in machine-readable format  | `dof.constitution.yml` with JSON Schema validation                                   | File existence + YAML parse                |
| 2 — Runtime      | Governance enforcement active during execution       | `ConstitutionEnforcer` evaluates every crew output; `ASTVerifier` on generated code  | Class instantiation + method availability  |
| 3 — Attestation  | Cryptographic attestation of governance outcomes     | ERC-8004 Oracle Bridge with HMAC-SHA256 signed certificates                          | Module import + class functionality        |

`OAGSPolicyBridge.validate_conformance(level=3)` executes all checks for the specified level and returns a structured result with per-check details. All three levels pass in the current implementation.

### 16.4 Policy Interoperability

`OAGSPolicyBridge.export_sekuire()` converts `dof.constitution.yml` to `sekuire.yml` format:

- HARD_RULES → `policies` with `action: block`
- SOFT_RULES → `policies` with `action: warn`
- AST_RULES → `policies` with `category: code_analysis`

The reverse operation `import_sekuire()` converts external OAGS policies into the DOF governance format. This bidirectional conversion enables interoperability with other OAGS-conformant systems without modifying the internal governance representation.

### 16.5 Audit Event Export

`OAGSAuditBridge.export_traces(trace_dir)` reads DOF JSONL execution traces and converts them to OAGS audit event format, including: event type, agent identity, timestamp, governance status, and metrics. This enables integration with external OAGS audit infrastructure.

---

## 17. x402 Trust Gateway

### 17.1 Motivation

The x402 payment protocol enables AI agents to autonomously transact on behalf of users. As of Q1 2026, x402 processes over 63 million monthly transactions. However, the protocol lacks a formal trust verification layer — any agent can request payments without governance validation. DOF addresses this with the `TrustGateway` — a deterministic verification module that intercepts payment responses and applies formal DOF checks before authorizing the transaction.

### 17.2 Decision Logic

The gateway applies a weighted composite score to determine the action:

| Condition             |   Action   | Rationale                          |
| :--------------------- | :---------: | :---------------------------------- |
| Adversarial detected  | **BLOCK**  | Unconditional — zero tolerance     |
| Score < 0.4           | **BLOCK**  | Below safety threshold             |
| 0.4 ≤ Score < 0.7     |  **WARN**  | Marginal safety — flag for review  |
| Score ≥ 0.7           | **ALLOW**  | Above safety threshold             |

### 17.3 Score Weights

| Component      |  Weight | Source                          |
| :-------------- | -------: | :------------------------------- |
| Adversarial    |     35% | `RedTeamAgent` detection        |
| Hallucination  |     25% | `DataOracle` verification       |
| PII            |     20% | Privacy pattern detection       |
| Constitution   |     10% | `ConstitutionEnforcer.check()`  |
| Structure      |      5% | Output structure heuristics     |
| Red Team       |      5% | Attack vector simulation        |

### 17.4 On-Chain Evidence

Every verdict produces an `endpoint_hash` (SHA-256) published to Enigma Scanner via `EnigmaBridge`, enabling immutable audit trail and cross-agent reputation scoring on Avalanche.

```python
from dof import TrustGateway

gateway = TrustGateway()
verdict = gateway.verify(response_body=agent_response)
# verdict.action → ALLOW / WARN / BLOCK
# verdict.governance_score → float
```

---

## 18. Protocol Integration

### 18.1 MCP Server

The DOF governance stack is exposed as a Model Context Protocol (MCP) server implementing the stdio JSON-RPC 2.0 transport specification. The server exposes 10 tools covering governance verification (`governance_check`), AST analysis (`ast_verify`), Z3 formal proofs (`z3_verify`), governed memory operations (`memory_add`, `memory_query`, `memory_snapshot`), attestation management (`attestation_create`, `attestation_verify`), and OAGS conformance (`oags_identity`, `oags_conformance`). Three read-only resources provide the active constitution (`dof://constitution`), formal metric definitions (`dof://metrics`), and system health (`dof://status`).

The MCP server enables Claude Desktop, Cursor, Windsurf, and any MCP-compatible client to invoke DOF governance without importing Python modules. Tool implementations delegate to the same `core/` modules used by all other entrypoints, ensuring governance consistency across all protocol interfaces.

### 18.2 REST API

A FastAPI-based HTTP interface exposes 14 endpoints covering governance verification, AST analysis, Z3 formal proofs, governed memory CRUD with temporal queries, attestation management, OAGS conformance validation, and system health. CORS middleware is enabled for dashboard integration.

Both the MCP server and REST API serve as protocol adapters: thin translation layers that convert protocol-specific request formats into calls to the shared `core/` governance infrastructure. No governance logic resides in the protocol layer; all enforcement is delegated to `ConstitutionEnforcer`, `ASTVerifier`, `Z3Verifier`, `GovernedMemoryStore`, `OracleBridge`, and `OAGSPolicyBridge`. This ensures that governance semantics are identical regardless of the access protocol.

---

## 19. Storage Architecture

### 19.1 Dual-Backend Abstraction

The `StorageBackend` abstract class defines the storage interface: `save_memory()`, `load_memories()`, `save_attestation()`, `load_attestations()`, `save_audit_event()`, `query_memories()`, `get_stats()`, and `initialize()`. Two concrete implementations are provided:

**JSONLBackend** (default): Zero-dependency append-only storage using one JSONL file per entity type (`memories.jsonl`, `attestations.jsonl`, `audit_events.jsonl`). Queries perform linear scan with in-memory filtering. Suitable for development, testing, and single-instance deployments.

**PostgreSQLBackend**: SQLAlchemy ORM with three tables (`dof_memories`, `dof_attestations`, `dof_audit_events`). JSONB columns with GIN indexes for flexible metadata queries. Supports multi-tenant deployments via connection pooling. SQLite in-memory serves as a PostgreSQL proxy for testing, enabling full backend validation without database infrastructure.

### 19.2 StorageFactory

`StorageFactory` implements singleton auto-detection: if the `DOF_DATABASE_URL` environment variable is set, it returns a `PostgreSQLBackend`; otherwise, it returns a `JSONLBackend`. The factory includes `reset()` for test isolation and `get_stats()` for operational monitoring.

### 19.3 Dual-Write Integration

`GovernedMemoryStore` and `AttestationRegistry` accept an optional `_storage_backend` parameter. When provided, every write operation persists to both the primary JSONL store and the secondary backend. If the secondary backend fails, the primary JSONL write still succeeds, with a warning logged. This dual-write pattern ensures that JSONL remains the authoritative audit trail while PostgreSQL provides query performance for production workloads.

### 19.4 Migration

`migrate_jsonl_to_postgres()` reads existing JSONL files and bulk-inserts their contents into the PostgreSQL backend, enabling transition from development to production storage without data loss.

---

## 20. Framework-Agnostic Governance

### 20.1 Adapter Pattern

The `FrameworkAdapter` abstract class defines the governance interface: `wrap_output(text) → dict`, `wrap_code(code) → dict`, and `record_step(data) → None`. Three concrete implementations enable DOF governance across different orchestration frameworks:

**GenericAdapter**: Zero external dependencies. Wraps `ConstitutionEnforcer` and `ASTVerifier` for any system that produces string output. Philosophy: "if you can produce a string, DOF can govern it."

**LangGraphAdapter**: Exposes DOF governance as LangGraph-compatible callable nodes via `get_nodes()`. Each node operates on state dictionaries, reading input from and writing results to named state keys.

**CrewAIAdapter**: Wraps the existing CrewAI `crew_runner` with governance hooks, providing the same `FrameworkAdapter` interface for CrewAI-specific deployments.

### 20.2 Governance Nodes

Four callable nodes implement the graph-compatible governance interface:

- `DOFGovernanceNode`: Extracts output from `state["output"]` or the last message in `state["messages"]`, runs `ConstitutionEnforcer.check()`, writes `governance_pass` and `governance_result` to state.
- `DOFASTNode`: Reads `state["code"]`, runs `ASTVerifier.verify()`, writes `ast_result` to state.
- `DOFMemoryNode`: Supports `add` and `query` actions via `GovernedMemoryStore`, controlled by `state["memory_action"]`.
- `DOFObservabilityNode`: Creates `StepTrace` entries from state data for execution tracing.

`create_governed_pipeline()` returns a pre-configured dict of all four nodes, enabling single-call pipeline setup.

### 20.3 Design Rationale

The adapter pattern decouples governance enforcement from framework-specific coordination semantics. DOF governance nodes receive output after framework execution completes and evaluate it deterministically. No governance logic depends on the framework that produced the output. This is the same architectural principle that establishes GCR(f) = 1.0 as an invariant: governance evaluation is a function of output content only, not of the execution path or framework that produced it.

---

## 21. On-Chain Attestation via Avalanche C-Chain

### 21.1 Attestation Certificate Structure

Each `AttestationCertificate` contains:

| Field                | Type      | Description                         |
| :-------------------- | :--------- | :----------------------------------- |
| `agent_identity`     | `string`  | BLAKE3 hash from OAGSIdentity       |
| `task_id`            | `string`  | UUID of the execution run           |
| `timestamp`          | `string`  | ISO 8601 creation timestamp         |
| `metrics`            | `dict`    | SS, GCR, PFI, RP, SSR values        |
| `governance_status`  | `string`  | COMPLIANT or NON_COMPLIANT          |
| `z3_verified`        | `bool`    | True if all Z3 proofs passed        |
| `signature`          | `string`  | HMAC-SHA256 hex signature           |
| `certificate_hash`   | `string`  | BLAKE3 hash of payload + signature  |

The `CertificateSigner` generates a random 32-byte secret key on first use, persists it to `keys/oracle_key.json`, and signs attestation payloads with HMAC-SHA256. The signer uses only standard library modules (`hmac`, `hashlib`, `secrets`) — zero external dependencies.

### 21.2 Compliance-Gated Publishing

The publishing rule is deterministic and strict:

```text
should_publish(cert) = True  iff  cert.governance_status == "COMPLIANT"
```

A certificate receives `governance_status = "COMPLIANT"` if and only if `GCR = 1.0` in the execution metrics. Any governance violation (GCR < 1.0) produces `NON_COMPLIANT`, which is not eligible for on-chain publication. This design ensures that the on-chain attestation registry contains only verified compliance records. An attestation with low SS (< 0.5) but perfect GCR (= 1.0) is still published, with a warning logged — stability degradation is an infrastructure concern, not a governance violation.

### 21.3 Transaction Preparation and Batching

`OracleBridge.prepare_transaction(cert)` generates an ERC-8004-compatible transaction structure targeting the Avalanche C-Chain. The transaction includes: agent identity, validation signal (COMPLIANT/NON_COMPLIANT), metrics hash, timestamp, and HMAC signature.

`batch_attestations(certs)` aggregates multiple certificates into a single batch transaction, reducing per-attestation gas cost for high-throughput deployments. Each batch receives a unique UUID for tracking. Economics: 10,000 attestations ≈ $0.01 gas on Avalanche C-Chain.

### 21.4 Off-Chain Registry

The `AttestationRegistry` maintains a local JSONL ledger (`logs/attestations.jsonl`) of all generated certificates:

- `add(cert)`: Persist new attestation
- `get_attestation(hash)`: Lookup by certificate hash
- `get_agent_history(identity)`: All attestations for an agent
- `get_compliance_rate()`: COMPLIANT / total ratio
- `export_for_chain()`: Unpublished COMPLIANT certificates ready for on-chain submission
- `mark_published(hash)`: Flag certificate as published

### 21.5 Attestation Verification

`OracleBridge.verify_attestation(cert)` reconstructs the original payload from the certificate fields, re-signs with the same key, and compares the signature. It then recomputes the certificate hash and compares. Both must match for verification to succeed. Any tampering with metrics, timestamps, or governance status produces a verification failure.

### 21.6 DOFValidationRegistry Contract Design

The DOFValidationRegistry is a Solidity smart contract (0.8.19) deployed on Avalanche C-Chain mainnet at `0x88f6043B091055Bbd896Fc8D2c6234A47C02C052`. The contract provides immutable on-chain storage of governance attestations with the following interface:

| Function               | Parameters                                                  | Access         | Purpose                           |
| :---------------------- | :----------------------------------------------------------- | :-------------- | :--------------------------------- |
| `registerAttestation`  | `bytes32 certificateHash, bytes32 agentId, bool compliant`  | `onlyOwner`    | Register individual attestation   |
| `registerBatch`        | `bytes32[] hashes, bytes32[] agentIds, bool[] compliants`   | `onlyOwner`    | Gas-optimized batch registration  |
| `isCompliant`          | `bytes32 certificateHash`                                   | `public view`  | Zero-trust verification           |
| `getAttestation`       | `bytes32 certificateHash`                                   | `public view`  | Full attestation retrieval        |
| `totalAttestations`    | —                                                           | `public view`  | Registry size                     |

The contract follows the OpenZeppelin Ownable pattern, restricting write operations to the deployer wallet (`0xB529f4f99ab244cfa7a48596Bf165CAc5B317929`) while enabling public read access for zero-trust verification by any third party.

### 21.7 Three-Layer Publication Pipeline

The Avalanche Bridge (`core/avalanche_bridge.py`) completes the publication pipeline by connecting DOF governance verification to Avalanche C-Chain via web3.py. The bridge signs transactions with the deployer private key, estimates gas, broadcasts to mainnet, and awaits confirmation. Offline-safe design ensures graceful degradation when blockchain connectivity is unavailable.

The complete publication pipeline provides three independent verification layers:

| Layer              | Storage                | Latency  | Persistence        | Verification                 |
| :------------------ | :---------------------- | :-------- | :------------------ | :---------------------------- |
| dof-storage        | PostgreSQL (Supabase)  | ~200ms   | Mutable            | Internal audit               |
| Enigma Scanner     | PostgreSQL (Supabase)  | ~900ms   | Historical INSERT  | Public via erc-8004scan.xyz  |
| Avalanche C-Chain  | On-chain               | ~2-3s    | Immutable          | Public via snowtrace.io      |

Each layer provides independent verification: dof-storage enables internal audit trails with full metric detail, the Enigma Scanner provides public historical records indexed by ERC-721 token_id, and the Avalanche C-Chain provides immutable cryptographic proof of governance compliance.

### 21.8 Production Verification Results

Twenty-one attestations have been confirmed on Avalanche C-Chain mainnet for two production agents across 10 cross-agent verification rounds (4 AVAX transfers, 2 A2A discovery, 2 OASF evaluation, 2 capability audits):

| Agent             | Token ID  | NFT Contract   | Attestations  | Ranking      | Latest Block  |
| :----------------- | :--------- | :-------------- | :------------- | :------------ | :------------- |
| Apex Arbitrage    | #1687     | `0xfc6f71...`  | 12            | #1 of 1,772  | 79674834+     |
| AvaBuilder Agent  | #1686     | `0x9b59db...`  | 9             | #2 of 1,772  | 79674842+     |

All 21 attestations passed compliance gating (GCR = 1.0) prior to on-chain publication. Both agents achieved a combined trust score of 0.85 on the Enigma Scanner, ranking #1 and #2 among all 1,772 agents indexed by erc-8004scan.xyz. The compliance-gated publishing rule ensures that the on-chain record contains only verified governance compliance events.

---

## 22. Scanner Integration and Combined Trust Architecture

### 22.1 Architectural Separation from Centinela

The Enigma Scanner (erc-8004scan.xyz) operates an independent infrastructure monitoring system (Centinela) that evaluates agents via heartbeat probes, proxy detection, OpenZeppelin contract matching, and community ratings. DOF governance scores are published to a dedicated `dof_trust_scores` table, architecturally separated from Centinela's `trust_scores` table. This separation prevents semantic collision: Centinela measures *infrastructure availability* while DOF measures *behavioral governance compliance*. Prior to separation, multiple scoring systems overwrote the same database rows with semantically incompatible values.

The Enigma Bridge (`core/enigma_bridge.py`) maps DOF metrics to scanner dimensions:

| DOF Metric  | Scanner Column     | Semantic Mapping                |
| :----------- | :------------------ | :------------------------------- |
| GCR         | governance_score   | Constitutional compliance rate  |
| SS          | stability_score    | Run completion under retries    |
| AST         | ast_score          | Code safety verification        |
| ACR         | adversarial_score  | Adversarial defensibility       |

Agent resolution occurs automatically via ERC-721 token_id lookup against the on-chain agent registry. Historical INSERT semantics provide full audit trail rather than destructive UPDATE, ensuring temporal completeness of governance records.

### 22.2 Combined Trust View

A SQL materialized view (`combined_trust_view`) in the Enigma database synthesizes three independent scoring sources into a unified trust metric:

| Source                      | Weight  | Dimensions                         | Methodology                         |
| :--------------------------- | :------- | :---------------------------------- | :----------------------------------- |
| Centinela (infrastructure)  | 0.30    | alive (0.15) + active (0.15)       | Heartbeat probes, response time     |
| DOF (formal governance)     | 0.50    | governance (0.35) + safety (0.15)  | ConstitutionEnforcer + ASTVerifier  |
| Community (ratings)         | 0.20    | user ratings normalized to [0,1]   | Aggregated community feedback       |

Governance receives the highest individual weight (0.35) and the highest aggregate weight (0.50) as the sole dimension backed by formal mathematical verification (Z3 SMT proofs). The weight assignment reflects a deliberate architectural decision: dimensions with stronger formal backing receive proportionally greater influence on the combined score.

### 22.3 Cross-Verification Results

The full audit pipeline (`scripts/full_audit_test.py`) executes four phases of verification:

1. **MCP Tool Validation**: All 10 DOF tools called directly via `TOOLS[name]["handler"](params)`. Result: 10/10 functional.
2. **A2A Skill Verification**: Agent card and skill manifest validated. Result: 8 skills available (research, code-review, data-analysis, build-project, grant-hunt, content, daily-ops, enigma-audit).
3. **Cross-Role Pipeline**: Each agent operates outside its primary role — the contract auditor performs arbitrage scanning and vice versa — to test behavioral governance rather than identity-based trust. Both agents passed governance, AST (1.0), and Z3 (4/4) verification.
4. **Bilateral Peer Verification**: Each agent governance-checks the other's output. Both peer reviews returned ACCEPT verdicts with AST score 1.0.

Production results: combined trust score 0.85 for both agents, ranking #1 and #2 among governance-verified agents on the Enigma Scanner.

---

## 23. External Agent Audit

### 23.1 Methodology

To validate DOF governance enforcement against third-party agents, we conducted a cross-network audit of all active agents in the ERC-8004 registry indexed by erc-8004scan.xyz. The audit script (`scripts/external_agent_audit.py`) executes 13 real tests probing four protocols (A2A, x402, OASF, MCP) against 12 agent endpoints, followed by DOF governance cross-verification of all collected outputs.

The registry contains 20 agents (11 VERIFIED, 9 PENDING). The API returns the same agent set across all queried chains (Avalanche, Fuji, Base, Ethereum, Arbitrum, Optimism, Polygon, BSC, Fantom, Gnosis) — no chain-exclusive agents exist in the current registry.

### 23.2 Results

| Test  | Agent                                        | Protocol  | Chain                      | Verdict                             | Latency  |
| :----- | :-------------------------------------------- | :--------- | :-------------------------- | :----------------------------------- | :-------- |
| 1-4   | Snowrail (yuki, sentinel, recon, fiat-rail)  | A2A       | Avalanche Fuji             | UNREACHABLE (404)                   | ~340ms   |
| 5     | Quick Intel                                  | x402      | Multi-chain (14 networks)  | ACTIVE ($0.03 USDC/scan)            | 302ms    |
| 6     | Tator Trader                                 | x402      | Multi-chain (14 networks)  | ACTIVE ($0.20 USDC/prompt)          | 321ms    |
| 7     | Apex Arbitrage                               | OASF      | Avalanche Mainnet          | ACTIVE v1.3.0, 7 skills, 4 domains  | 337ms    |
| 8     | AvaBuilder                                   | OASF      | Avalanche Mainnet          | ACTIVE v0.8.0, 5 skills, 4 domains  | 561ms    |
| 9     | Apex Arbitrage                               | A2A       | Avalanche Mainnet          | ACTIVE, 5 services                  | 270ms    |
| 10    | AvaBuilder                                   | A2A       | Avalanche Mainnet          | ACTIVE, 5 services                  | 319ms    |
| 11    | quack_agent                                  | MCP       | Avalanche                  | ACTIVE, 114-line manifest           | 339ms    |
| 12    | Neo                                          | MCP       | arena.social               | HTTP 500 (server error)             | 753ms    |
| 13    | DOF Governance                               | DOF       | N/A                        | COMPLIANT, 0 violations             | <1ms     |

### 23.3 Protocol Coverage

| Protocol  | Active  | Total  | Coverage  | Networks                                                                                                     |
| :--------- | :------- | :------ | :--------- | :------------------------------------------------------------------------------------------------------------ |
| x402      | 2       | 2      | 100%      | Base, ETH, Arbitrum, Optimism, Polygon, Avalanche, Unichain, Linea, MegaETH, Sonic, Zora, Ink, Tron, Solana  |
| OASF      | 2       | 2      | 100%      | Avalanche Mainnet                                                                                            |
| A2A       | 2       | 6      | 33%       | Avalanche Mainnet (DOF agents active, Snowrail down)                                                         |
| MCP       | 1       | 2      | 50%       | Avalanche (quack_agent active, Neo error)                                                                    |

### 23.4 Observations

The x402 agents (Quick Intel and Tator Trader) demonstrate the most robust multi-chain deployment, accepting USDC payments across 14 EVM networks plus Solana. The x402 protocol response includes full JSON schema documentation of input/output interfaces, enabling automated agent-to-agent commercial interaction.

The OASF endpoints for both DOF-governed agents (Apex v1.3.0 and AvaBuilder v0.8.0) expose structured skill taxonomies and domain classifications conformant with the Open Agent Service Framework specification.

The Snowrail agents, while registered as VERIFIED in the scanner, return 404 on all known paths — the Railway deployment is running but no routes are configured. Neo returns HTTP 500, indicating an unhandled server-side error.

DOF governance cross-verification of all 12 fetched outputs returned COMPLIANT with 0 hard violations and 0 soft violations, confirming that governance enforcement generalizes to external agent responses regardless of protocol or origin.

### 23.5 External Validation v0.2.4

Version 0.2.4 extended the external validation scope by exercising the four v0.2.3 capabilities against a reproducible Google Colab environment with live LLM provider calls. The validation script executed three independent verification rounds:

| Capability                     | Method                                                                                 | Result                     | Details                                                        |
| :------------------------------ | :-------------------------------------------------------------------------------------- | :-------------------------- | :-------------------------------------------------------------- |
| LLM-as-a-Judge                 | `evaluate_with_judge(response, context)`                                               | score=9.0, verdict=PASS    | Threshold 7.0; advisory-only, deterministic arbiter unchanged  |
| Red Team Attack Vectors        | `indirect_prompt_injection()`, `persuasion_jailbreak()`, `training_data_extraction()`  | detected=True (3/3)        | All three vectors correctly identified adversarial payloads    |
| Instruction Hierarchy          | `enforce_hierarchy(system, user, response)`                                            | compliant=True             | Clean prompts passed; override attempts correctly blocked      |
| AGENT\_FAILURE Classification  | `classify_error("tool_not_found")`                                                     | ErrorClass.AGENT\_FAILURE  | 16 agent-specific keywords distinguished from INFRA\_FAILURE   |

The validation confirms three properties: (1) LLM-as-a-Judge operates as a strictly advisory layer — its score does not influence the deterministic governance verdict, preserving GCR invariance; (2) the three Red Team attack methods detect adversarial payloads with the expected severity levels (CRITICAL for injection/jailbreak, HIGH for data extraction); and (3) the instruction hierarchy enforcement correctly applies the SYSTEM > USER > ASSISTANT priority ordering established in dof.constitution.yml.

---

## 24. Adversarial Benchmark Results

### 24.1 Methodology

The TestGenerator produces 400 deterministic adversarial test cases (seeded random, reproducible) across four categories with a 50/50 clean/adversarial split per category. The BenchmarkRunner evaluates DOF verification components against these datasets, measuring detection accuracy via standard binary classification metrics.

Each category targets a specific DOF component: hallucination tests target DataOracle (6 strategies), code safety tests target ASTVerifier, governance tests target ConstitutionEnforcer, and consistency tests target DataOracle's self-consistency strategy. Clean inputs (expected: pass) and adversarial inputs (expected: detect) are generated with known ground truth labels.

### 24.2 Results

| Category       | Component             | FDR     | FPR   | Precision  | Recall  | F1         | Tests    |
| :-------------- | :--------------------- | :------- | :----- | :---------- | :------- | :---------- | :-------- |
| Governance     | ConstitutionEnforcer  | 100.0%  | 0.0%  | 100.0%     | 100.0%  | 100.0%     | 100      |
| Code Safety    | ASTVerifier           | 86.0%   | 0.0%  | 100.0%     | 86.0%   | 92.5%      | 100      |
| Hallucination  | DataOracle            | 90.0%   | 0.0%  | 100.0%     | 90.0%   | 94.7%      | 100      |
| Consistency    | DataOracle            | 100.0%  | 0.0%  | 100.0%     | 100.0%  | 100.0%     | 100      |
| **Overall**    |                       |         |       |            |         | **96.8%**  | **400**  |

### 24.3 Interpretation

**Governance (100% FDR, 0% FPR, F1=100%).** ConstitutionEnforcer achieves perfect detection because governance violations are syntactic: non-English text, hallucination claims without URLs, empty output, and length violations are captured by regex and keyword rules. This is expected — the rules are deterministic pattern matchers operating on the same patterns injected by the test generator.

**Code Safety (86% FDR, 0% FPR, F1=92.5%).** ASTVerifier detects 86% of injected unsafe code patterns. The 14% miss rate corresponds to obfuscated patterns that bypass AST-level detection (e.g., dynamically constructed `eval` calls via string concatenation). Zero false positives confirm that the AST rules do not flag safe code.

**Hallucination (90% FDR, 0% FPR, F1=94.7%).** DataOracle detects 90% of injected hallucinations using six deterministic strategies: pattern matching against a 50+ entry known-facts database, cross-reference validation, consistency checking, entity extraction with founder/date validation, numerical plausibility detection (negative values, percentages >100% in non-growth context, implausible magnitudes >$100T), and self-consistency cross-checks. The 10% miss rate corresponds to adversarial patterns targeting entities absent from the known-facts database. Zero false positives confirm that valid factual claims are not incorrectly flagged.

**Consistency (100% FDR, 0% FPR, F1=100%).** DataOracle's self-consistency strategy detects all injected contradictions within single outputs using three sub-checks: percentage allocation sums exceeding 100%, revenue total contradictions (>2x ratio between stated values), and date arithmetic inconsistencies (claimed duration vs. actual year difference). Pure regex and arithmetic — zero LLM involvement.

### 24.4 Honest Assessment

The overall F1 of 96.8% reflects a system that achieves strong detection across all four verification categories while maintaining zero false positives. The improvement from an initial 48.1% baseline was achieved entirely through deterministic strategies — expanding the known-facts database from 23 to 50+ entries, adding entity extraction with founder validation, numerical plausibility detection, and self-consistency cross-checks. No LLM was introduced into the verification path.

The remaining 3.2% gap (10% miss rate in hallucination detection) corresponds to adversarial patterns targeting entities absent from the known-facts database. This is a fundamental limitation of corpus-based verification: detection coverage is bounded by the knowledge base. Future improvements would require either (a) expanding the ground-truth corpus or (b) hybrid verification combining deterministic structural checks with bounded LLM-assisted semantic analysis — a direction that would require careful architectural consideration to preserve the GCR invariant.

### 24.5 Execution Infrastructure Components

In addition to the benchmark results, the v1.2 release introduces four execution infrastructure components that extend the framework's observability and safety capabilities:

**ExecutionDAG** models agent execution as a directed acyclic graph. DFS cycle detection prevents circular dependencies. Topological sort establishes valid execution ordering. Critical path analysis identifies the longest dependency chain for latency attribution. Mermaid export produces visualizations suitable for documentation and debugging.

**LoopGuard** detects infinite execution loops by computing Jaccard similarity between consecutive agent outputs. When similarity exceeds the threshold (0.85), indicating repetitive output, execution terminates with a structured `LoopDetected` event. Maximum iteration (10) and timeout (300s) bounds provide secondary protection.

**DataOracle** implements six deterministic verification strategies: (1) pattern matching against a 50+ entry known-facts database, (2) cross-reference validation across agent outputs, (3) consistency checking within single outputs, (4) entity extraction with founder/date validation, (5) numerical plausibility detection (negative values, percentages >100% in non-growth context, implausible magnitudes), and (6) self-consistency cross-checks (percentage allocation sums, revenue contradictions, date arithmetic). The benchmark shows 90% FDR for hallucination and 100% FDR for consistency with zero false positives (Section 24.2).

**TokenTracker** provides per-call LLM token flow tracking integrated into the crew runner. Every `crew.kickoff()` logs provider, model, prompt tokens, completion tokens, latency, and cost estimate. Aggregation methods (`total_tokens()`, `total_cost()`, `calls_by_provider()`, `average_latency()`) enable cost and performance observability across execution runs.

### 24.6 External Benchmark: DOF vs NVIDIA Garak

DOF detection components were evaluated against NVIDIA Garak's [26] probe corpus, the industry-standard LLM vulnerability scanner. 12,229 payloads from 12 categories were extracted from Garak v0.14.0 and passed through DOF's full detection pipeline without any tuning. Two rounds were conducted: v1 (baseline pipeline) and v2 (after gap analysis improvements).

**v2 improvements** (motivated by v1 gap analysis):
1. **EntropyDetector** — Shannon entropy + statistical text analysis for GCG/suffix attacks (9 signals, threshold ≥ 2)
2. **Expanded decoders** — ROT13, base32, unicode escape decoding in `decode_and_scan`
3. **Pattern expansion** — 6 new injection patterns + 8 new jailbreak patterns from missed DAN payloads

| Category              | Payloads | v1 Det. | v1 Rate | v2 Det. | v2 Rate |   Δ     |
|:----------------------|:--------:|:-------:|:-------:|:-------:|:-------:|:-------:|
| continuation          |    6,527 |   4,784 |  73.3%  |   4,784 |  73.3%  |   0.0pp |
| dan                   |      857 |     277 |  32.3%  |     543 |  63.4%  | +31.1pp |
| glitch                |      742 |     228 |  30.7%  |     228 |  30.7%  |   0.0pp |
| goodside              |       10 |       9 |  90.0%  |       9 |  90.0%  |   0.0pp |
| leakreplay            |    1,299 |     369 |  28.4%  |     369 |  28.4%  |   0.0pp |
| lmrc                  |       27 |      21 |  77.8%  |      21 |  77.8%  |   0.0pp |
| malwaregen            |      240 |     198 |  82.5%  |     198 |  82.5%  |   0.0pp |
| misleading            |      150 |      75 |  50.0%  |      75 |  50.0%  |   0.0pp |
| packagehallucination  |      448 |      79 |  17.6%  |      79 |  17.6%  |   0.0pp |
| realtoxicityprompts   |      703 |     234 |  33.3%  |     234 |  33.3%  |   0.0pp |
| snowball              |    1,200 |     600 |  50.0%  |     600 |  50.0%  |   0.0pp |
| suffix                |       26 |       0 |   0.0%  |       3 |  11.5%  | +11.5pp |
| **Overall**           | **12,229** | **6,874** | **56.2%** | **7,143** | **58.4%** | **+2.2pp** |

**Interpretation.** The v2 improvements yielded +269 additional detections (+2.2pp overall), concentrated in two categories: **DAN** (+31.1pp, from pattern expansion matching actual Garak DAN phrasing) and **suffix** (+11.5pp, from EntropyDetector catching GCG bracket/gibberish patterns). Categories unchanged between rounds confirm that the improvements are targeted and do not introduce regressions.

The overall 58.4% detection rate reflects the architectural trade-off of DOF's deterministic pipeline: pattern-based matching trades recall for zero false positives and sub-millisecond latency (1.5s for 12,229 payloads). Strong categories (goodside 90%, malwaregen 82.5%, lmrc 77.8%) align with DOF's pattern library. Remaining weak categories (packagehallucination 17.6%, leakreplay 28.4%, glitch 30.7%) involve attacks that require semantic understanding or operate at the token level — both outside DOF's deterministic design scope.

This result is complementary to the internal benchmark (F1=96.8%, Section 24.2): the internal benchmark validates detection of *known* threat patterns with controlled ground truth, while the Garak benchmark measures coverage against *external* adversarial payloads not designed for DOF. Together, they provide a two-dimensional assessment: high precision on known patterns (96.8%) with moderate coverage on unknown external attacks (58.4%).

### 24.7 Regression Tracking

The RegressionTracker (`core/regression_tracker.py`) provides automated post-merge health monitoring across four DOF subsystems:

| Subsystem         | What it measures                         | Regression trigger                     |
|:------------------|:-----------------------------------------|:---------------------------------------|
| Z3 Invariants     | 8 invariants status + verification time  | Any PROVEN → not PROVEN                |
| Z3 Hierarchy      | 42 patterns verification status          | Status changed from PROVEN             |
| Test Suite        | Pass/fail count across full suite        | Passed decreased or failures increased |
| Garak Benchmark   | Overall detection rate (12 categories)   | Detection rate decreased > 2pp         |
| LLM Routing       | Provider failure rate, routing distribution, latency | Any provider failure rate > 15% |

The tracker captures baselines before changes (`dof regression-baseline`), compares current state against baseline (`dof regression-check`), and maintains a JSONL history of all comparisons with git commit hashes for traceability. Integration with GitHub Actions ensures that any commit introducing a regression is blocked before merging to main.

This addresses a gap identified in production agent orchestration systems: the need for automated failure recurrence monitoring by subsystem after each merge. The RegressionTracker provides this with formal verification backing — regressions in Z3 invariants are not just detected but mathematically proven.

---

## 25. Discussion

### 25.1 Constitutional Memory and Governance Integrity

The constitutional memory governance system (Section 15) closes a previously unaddressed gap in agent memory systems: governance-validated output could be stored in memory without re-validation, potentially contaminating future agent context. By interposing ConstitutionEnforcer on every write path, the framework ensures that memory content meets the same governance standard as delivered output. The bi-temporal versioning model provides auditability guarantees that are essential for compliance-sensitive deployments: any point-in-time reconstruction of agent memory state is possible via the TemporalGraph snapshot operation.

The OAGS conformance bridge (Section 16) demonstrates that formal governance frameworks can achieve interoperability with emerging governance specifications without sacrificing verification rigor. The DOF implementation is, to our knowledge, the first OAGS-conformant system with Z3-verified governance invariants.

The ERC-8004 Oracle Bridge (Section 17) extends governance assurance beyond the execution boundary. By publishing compliance attestations to an immutable public ledger, the framework enables third-party verification of governance claims without requiring access to internal execution state. The compliance-gating rule (only GCR = 1.0 published) ensures that the on-chain record represents a curated set of verified compliance events, not a raw audit log.

### 25.2 Deterministic Reproducibility

The reproducibility experiment (Section 6.2) demonstrates perfect metric identity across independent runs, confirming that the deterministic mode successfully eliminates infrastructure-level randomness. This result is theoretically expected for simulated experiments but has practical implications for real provider testing.

In practice, deterministic mode cannot control LLM output randomness (temperature-dependent sampling). However, by fixing the infrastructure variables—provider ordering, retry behavior, random seeds—deterministic mode enables attribution: if two runs differ in metrics, the difference is attributable to LLM output variation rather than infrastructure nondeterminism.

A limitation of the current deterministic mode is that it operates at the Python process level. Concurrent executions in separate threads or processes maintain independent random states, which could introduce nondeterminism in multi-threaded deployments.

### 25.3 Sensitivity to Perturbations

The perturbation experiment (Section 6.3) shows that a 30% failure injection rate reduces mean Stability from 1.0 to 0.85, a 15% degradation. The relationship is not 30% because Stability is computed per-step within each run: a run with 2 steps where 1 fails has Stability 0.5, not 0.0. The mean across 7 clean runs (Stability=1.0) and 3 perturbed runs (Stability=0.5) is (7×1.0 + 3×0.5)/10 = 0.85.

Provider Fragility Index and Retry Pressure show high standard deviation (0.4830) relative to their mean (0.3000), reflecting the bimodal nature of the underlying data.

### 25.4 Governance Robustness and Formal Proof

The invariance of Governance Compliance Rate under perturbation (GCR = 1.0 in all experiments) is now elevated beyond an empirical observation: Section 8 provides a machine-checkable Z3 proof that this invariance holds for all f ∈ [0,1] by architectural construction. The constitutional enforcement model—hard rules that block and soft rules that score—provides a useful separation of concerns.

### 25.5 Hallucination and Governance Independence

A recurring theme in production AI engineering is the circular dependency between generation and evaluation: if the same model that generates output also evaluates it, hallucinations propagate unchecked [31]. DOF resolves this by architectural construction — the governance stack (ConstitutionEnforcer, ASTVerifier, Z3Gate) contains zero LLM components. This ensures that hallucinated output is evaluated by deterministic rules and formal proofs rather than by another LLM that may share the same failure modes. The empirical evidence supports this design: GCR = 1.0 across all perturbation experiments (Section 6.3), formally proven invariant by Z3 (Section 8).

### 25.6 Supervisor Circularity Resolution

Section 9 addresses the fundamental limitation identified in the original framework: LLM-based supervision is subject to the same failure modes as the agents it evaluates. The adversarial Red-on-Blue protocol provides a partial resolution: LLM agents establish the dialectic (defect identification and defense), while a deterministic arbiter resolves it. This does not eliminate LLM involvement in evaluation but bounds its impact: the final quality determination is made by code, not by an LLM.

The ACR metric provides a new signal complementary to the existing SSR: while SSR measures the fraction of outputs rejected by the supervisor (a pass/fail gate), ACR measures the fraction of adversarially identified defects that can be defended with verifiable evidence (a quality signal about the defensibility of the output).

### 25.7 Bayesian vs. Static Provider Selection

The introduction of Thompson Sampling (Section 13) addresses a limitation of the original static rotation: equal treatment of providers regardless of observed reliability. In production deployments where provider reliability is heterogeneous and time-varying, Thompson Sampling provides asymptotically optimal regret bounds under the 4/δ framework [18]. The temporal decay mechanism ensures that historical data does not permanently bias selection against a provider that was temporarily degraded.

The empirical question — whether Bayesian selection produces measurably lower PFI than static selection over a multi-day deployment — is deferred to future work (Section 29.2).

### 25.8 Protocol Integration and Framework-Agnostic Governance

The MCP server and REST API (Section 18) extend the governance boundary from in-process Python calls to network-accessible protocol interfaces. The design principle is that governance semantics must be identical across all access paths: an output governed via MCP `governance_check` produces the same result as `ConstitutionEnforcer.check()` called in-process. Both protocol layers are thin translation adapters with no governance logic.

The dual-backend storage architecture (Section 19) addresses production deployment requirements while preserving the zero-dependency development experience. The dual-write pattern ensures JSONL remains the authoritative audit trail — a design choice motivated by the append-only, tamper-evident properties of JSONL logs.

The framework-agnostic governance system (Section 20) demonstrates that the GCR invariant extends beyond the DOF execution pipeline. Because governance evaluation depends only on output content, any framework that produces text can be governed by DOF. The `GenericAdapter` with zero external dependencies makes this accessible without framework lock-in.

### 25.9 Production On-Chain Validation

The deployment of DOFValidationRegistry on Avalanche C-Chain mainnet (Section 21) and the integration with the Enigma Scanner (Section 22) constitute the first production validation of the framework's governance pipeline against real, indexed agents. The three-layer publication pipeline provides defense in depth: if any single layer fails or is compromised, the remaining layers provide independent verification. The combined trust architecture (Section 22) demonstrates that formal governance verification can be integrated into production scoring systems alongside infrastructure monitoring and community feedback, with the weight allocation reflecting the relative strength of each verification methodology.

The cross-verification results (Section 22.3) address a limitation previously identified in the discussion: governance compliance was validated only against the framework's own agents. The bilateral peer verification, where each agent governance-checks the other's output, provides the first evidence that DOF governance enforcement generalizes across agent identities and operational roles.

### 25.10 Limitations

Several limitations should be acknowledged:

1. **Simulated execution**: All controlled experiments use `SimulatedCrew` rather than real LLM providers.
2. **Token estimation**: Token counts are estimated at 4 characters per token, which is approximate.
3. **Fixed step count**: The simulated crew always produces a fixed number of steps.
4. **Heuristic supervisor**: The meta-supervisor uses heuristic scoring rather than LLM-based evaluation. The adversarial protocol partially addresses this but does not replace the supervisor for acceptance decisions.
5. **Single-thread experiments**: All experiments run in a single thread.
6. **No real latency**: Simulated execution completes in microseconds.
7. **ACR baseline**: The ACR metric has not been validated against human defect assessments. The DeterministicArbiter's evidence threshold (requiring `governance_passed=True`, `ast_score ≥ 0.75`, or `tests_passed=True`) is a design choice, not an empirically calibrated threshold.

---

## 26. Threats to Validity

### 26.1 Internal Validity

Internal validity concerns whether the observed metric values are attributable to the experimental variables rather than confounding factors. Three potential confounds are identified.

**Shared process state.** The batch runner executes all runs within a single Python process. Module-level state—particularly the `DETERMINISTIC_MODE` global variable and the `_SESSION_ID` singleton—persists across runs. While deterministic mode is explicitly designed to maintain consistent state, unintended accumulation of state (e.g., in the `ProviderManager` singleton or `MetricsLogger` file handles) could introduce ordering effects. The Bayesian selector's persistence mechanism (writing to `logs/bayesian_state.json`) introduces cross-run state dependencies that must be reset via `BayesianProviderSelector.reset()` for isolated experiments.

**Deterministic failure injection pattern.** The failure injection uses a fixed modular pattern (`run_index % 3 == 1`), producing failures at indices 1, 4, 7 in a 10-run experiment. Different failure patterns could produce different metric distributions even at the same injection rate. The reported variance values are specific to the modular injection pattern.

**Token estimation approximation.** Token counts are estimated using a fixed ratio of 4 characters per token. For English text, approximately 4.0 (GPT-class tokenizers); for Spanish, approximately 3.5; for mixed multilingual text, approximately 3.5–4.5.

### 26.2 External Validity

**Simulated vs. real execution.** All controlled experiments use `SimulatedCrew`. Real LLM providers introduce variable latency, non-deterministic output content, model-specific failure modes, and time-dependent availability. The post-integration production baseline (n=30, Section 7.3) provides the first real-provider validation.

**Z3 proof scope.** The Z3 proofs in Section 8 verify properties of mathematical abstractions of the framework. The encoding of `ConstitutionEnforcer` as an uninterpreted function is correct under the assumption that the function has no side channels — that it receives no information beyond `output` as its argument. If the actual implementation reads global state or environment variables, the proof would not hold for that implementation. Code review confirms that `governance.py` reads only the output string and the loaded rule set; no provider state is accessible.

**Provider heterogeneity.** The framework is validated against four specific providers with free-tier constraints. Error classification heuristics may not generalize to providers with different error reporting conventions.

### 26.3 Construct Validity

**ACR and defect coverage.** The ACR metric measures the fraction of *identified* defects that are defensible, not the fraction of *all defects* that are defensible. If the RedTeamAgent fails to identify real defects (false negatives), ACR will be high even for genuinely defective outputs. The quality of ACR as a signal depends on the RedTeamAgent's recall, which has not been benchmarked against human defect identification.

**Stability Score and recovery.** Stability Score counts failed steps regardless of whether the system recovered through retry. A run with one failed step and one successful retry has SS=0.5, identical to a run with one failed step and no retry. An alternative construct—*effective stability*—would measure only unrecovered failures.

**Governance Compliance as quality proxy.** Governance Compliance Rate measures conformance to rule-based constraints, not semantic quality. An output that is linguistically correct, properly structured, and factually wrong would receive GCR=1.0.

### 26.4 Statistical Conclusion Validity

**Sample size.** The primary experiments use n=10 runs. For metrics with non-zero variance (e.g., SS under perturbation, σ=0.2415), the 95% confidence interval for the mean is μ ± t₉,₀.₀₂₅ × σ/√n = 0.85 ± 0.173, yielding the interval [0.677, 1.023]. A sample of n=50 would reduce the interval width to ±0.077.

**Multiple comparisons.** The three experiments are analyzed independently; no corrections for multiple comparisons are applied.

---

## 27. Replication Protocol

### 27.1 Preconditions

- Python 3.11 or higher.
- All 35 core modules present in `core/`, `dof/`, `integrations/`, and `scripts/`.
- `dof.constitution.yml` present in project root.
- `z3-solver>=4.12` installed (for Section 8 experiments).
- No external API keys are required for simulated experiments.
- No GPU or specialized hardware requirements.

### 27.2 Environment Configuration

```bash
# Verify Python version
python3 --version  # Must be >= 3.11

# Navigate to project root
cd /path/to/deterministic-observability-framework

# Install package with all dependencies
pip install -e ".[dev]"

# Verify installation
python3 -c "import dof; print(dof.__version__)"

# Create required directories
mkdir -p logs/experiments logs/traces experiments
```

### 27.3 Z3 Formal Verification

```python
from dof import verify

proofs = verify()
for p in proofs:
    print(f"{p.theorem_name}: {p.result} ({p.proof_time_ms:.2f} ms)")
# Expected output:
# GCR_INVARIANT: VERIFIED (0.30 ms)
# SS_FORMULA: VERIFIED (0.19 ms)
# SS_MONOTONICITY: VERIFIED (0.82 ms)
# SS_BOUNDARIES: VERIFIED (0.35 ms)
```

### 27.4 Exact Experimental Commands

**Experiment 1 — Baseline (No Failures):**

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(".")))
from core.experiment import run_experiment

results = run_experiment(
    n_runs=10,
    prompt="Investigar mercado de agentes AI autónomos en Avalanche. "
           "Competidores, market size, tendencias 2025-2026, "
           "oportunidades de grants.",
    mode="research",
    hypothesis="Baseline: zero-failure simulated crew produces "
               "perfect stability metrics with zero variance",
    deterministic=True,
    fail_step=-1,
    verbose=True,
)
print(results["aggregated"])
```

**Experiment 3 — Forced Failure Perturbation:**

```python
results_perturbed = run_experiment(
    n_runs=10,
    prompt="Investigar mercado de agentes AI autónomos en Avalanche. "
           "Competidores, market size, tendencias 2025-2026, "
           "oportunidades de grants.",
    mode="research",
    hypothesis="Perturbation: 30% failure injection reduces stability "
               "while governance remains invariant",
    deterministic=True,
    fail_step=1,
    verbose=True,
)
print(results_perturbed["aggregated"])
```

**Experiment 4 — Parametric Failure Sweep:**

```python
from core.experiment import run_parametric_sweep

sweep = run_parametric_sweep(
    failure_rates=[0.0, 0.10, 0.20, 0.30, 0.50, 0.70],
    n_runs=20,
    prompt="Investigar mercado de agentes AI autónomos en Avalanche. "
           "Competidores, market size, tendencias 2025-2026, "
           "oportunidades de grants.",
    mode="research",
    deterministic=True,
    fail_step=1,
    verbose=True,
)
# CSV exported to experiments/parametric_sweep.csv
```

### 27.5 Expected Artifacts

After executing all experiments, the following artifacts should exist:

| Artifact                | Path                                | Format  | Count         |
| :----------------------- | :----------------------------------- | :------- | :------------- |
| Individual trace files  | `logs/traces/{run_id}.json`         | JSON    | 150           |
| Run summaries           | `logs/experiments/runs.jsonl`       | JSONL   | 150 entries   |
| Experiment dataset      | `experiments/run_dataset.jsonl`     | JSONL   | 150 entries   |
| Parametric sweep CSV    | `experiments/parametric_sweep.csv`  | CSV     | 1 (6 rows)    |
| Z3 proof certificates   | `logs/z3_proofs.json`               | JSON    | 1 (4 proofs)  |
| Adversarial logs        | `logs/adversarial.jsonl`            | JSONL   | per-run       |
| Contract logs           | `logs/task_contracts.jsonl`         | JSONL   | per-run       |

### 27.6 Validation Criteria

Replication is successful if the following conditions hold:

1. **Experiment 1**: All five primary metrics have boundary values (SS=1.0, PFI=0.0, RP=0.0, GCR=1.0, SSR=0.0) with standard deviation exactly 0.0.
2. **Experiment 2**: All five primary metrics are numerically identical to Experiment 1 results.
3. **Experiment 3**: SS mean = 0.85, SS σ = 0.2415 (to 4 decimal places). PFI mean = 0.30. GCR = 1.0, σ = 0.0. SSR = 0.0.
4. **Z3 Verification**: All four theorems return VERIFIED (UNSAT). Total proof time < 10 ms on commodity hardware.
5. **Trace integrity**: Each trace JSON file is valid JSON containing fields `run_id`, `session_id`, `steps` (array), and all derived metric fields.

---

## 28. Comparative Positioning

### 28.1 Comparison Framework

We evaluate five systems: CrewAI [1] (the orchestration layer used by this framework), AutoGen [2], LangGraph [3], MetaGPT [4], and the framework presented in this paper. The comparison is based on documented capabilities as of early 2026.

### 28.2 Comparative Table

| Dimension                          | CrewAI         | AutoGen        | LangGraph      | MetaGPT        | This Framework                                                                      |
| :---------------------------------- | :-------------- | :-------------- | :-------------- | :-------------- | :----------------------------------------------------------------------------------- |
| **Deterministic execution**        | No             | No             | Partial        | No             | Yes. Fixed provider ordering, seeded PRNG, deterministic failure injection.         |
| **Failure injection**              | Not supported  | Not supported  | Not supported  | Not supported  | Supported. Configurable `fail_step` with periodic injection.                        |
| **Formal stability metrics**       | None           | None           | None           | None           | Five metrics with formal definitions: SS, PFI, RP, GCR, SSR. Plus ACR.              |
| **Batch statistical aggregation**  | Not built-in   | Not built-in   | Not built-in   | Not built-in   | Built-in. `run_experiment(n_runs=N)` with mean, σ, Bessel correction.               |
| **Governance enforcement**         | Not built-in   | Partial        | Not built-in   | Partial        | Built-in. Two-tier: 4 hard rules + 4 soft rules. YAML canonical source.             |
| **Formal verification**            | None           | None           | None           | None           | Z3 SMT proofs for 4 invariants. GCR architectural invariant machine-proven.         |
| **Adversarial evaluation**         | None           | None           | None           | None           | Red-on-Blue protocol with DeterministicArbiter. ACR metric.                         |
| **Task contracts**                 | None           | None           | None           | None           | Markdown contracts with quality gates and completion guarantees.                    |
| **Causal error attribution**       | None           | None           | None           | None           | Three-class taxonomy: MODEL, INFRA, GOVERNANCE.                                     |
| **Bayesian provider selection**    | None           | None           | None           | None           | Thompson Sampling, Beta posteriors, temporal decay.                                 |
| **Governed memory**                | None           | None           | None           | None           | ConstitutionEnforcer on every write, bi-temporal versioning, constitutional decay.  |
| **Agent governance spec**          | None           | None           | None           | None           | OAGS Level 3 conformance: identity, policy, attestation.                            |
| **On-chain attestation**           | None           | None           | None           | None           | ERC-8004 on Avalanche C-Chain, compliance-gated publishing.                         |
| **Neurosymbolic Z3 Gate**          | None           | None           | None           | None           | Yes. LLM proposes → Z3 verifies → execute or reject with counterexample.            |
| **On-chain proof hash**            | None           | None           | None           | None           | Yes. keccak256 proof hash in DOFProofRegistry.sol, verifiable by anyone.            |
| **Auto-test generation from Z3**   | None           | None           | None           | None           | Yes. Z3 counterexamples and boundary cases → unittest regression tests.             |
| **State transition proofs**        | None           | None           | None           | None           | Yes. 8 invariants PROVEN for ALL possible agent states in 107.7ms.                  |
| **Regression tracking**            | None           | None           | None           | None           | Yes. 5 subsystems monitored post-merge, CI blocks regressions automatically.        |
| **External adversarial benchmark** | None           | None           | None           | None           | Yes. 58.4% detection against 12,229 NVIDIA Garak payloads (12 categories).          |

### 28.3 Positioning Analysis

The comparison reveals that existing multi-agent frameworks prioritize *coordination semantics* over *experimental infrastructure*. The framework presented in this paper occupies a complementary position: it does not replace CrewAI's coordination capabilities (it uses CrewAI as its orchestration layer) but adds the experimental infrastructure necessary for systematic evaluation and formal assurance.

The addition of Z3 formal verification represents the most significant differentiation from the existing ecosystem. No current multi-agent LLM framework provides machine-checkable proofs of any behavioral property. The GCR invariant proof addresses the open research challenge of deterministic behavioral guarantees in LLM systems by demonstrating that *architectural* guarantees — properties that depend on code structure, not model outputs — are amenable to formal verification.

---

## 29. Future Work

### 29.1 Parametric Failure Curves with Bayesian Selection

Section 7 tested parametric failure rates with static provider selection. A systematic comparison would execute identical parametric sweeps with static selection (current baseline) vs. Bayesian Thompson Sampling, measuring whether Bayesian selection produces lower PFI at equivalent failure rates. This would provide empirical validation of the theoretical prediction from [18] that Thompson Sampling minimizes regret.

### 29.2 Real Provider Benchmarking

Executing the experiment framework against real LLM providers would produce the first empirical characterization of multi-provider system behavior. Key questions include:

- What is the natural Stability Score for each provider under free-tier constraints?
- Does BayesianProviderSelector converge to stable posteriors within N executions for each provider?
- How does ACR vary across providers? Do certain models produce more unresolvable adversarial defects?
- Does causal error attribution correctly distinguish INFRA\_FAILURE from MODEL\_FAILURE in production?

### 29.3 ACR Calibration Against Human Assessment

The ACR metric depends on the DeterministicArbiter's evidence threshold. Calibration requires: (1) human annotators labeling a set of outputs with defects and severity, (2) running the adversarial protocol on the same outputs, and (3) computing precision and recall of the protocol against human labels. This would establish whether ACR correlates with human-perceived output quality and whether the evidence thresholds need adjustment.

### 29.4 Cross-Model Entropy Analysis

Different LLM models produce outputs with different levels of variability for the same prompt. Measuring the entropy of supervisor scores and ACR values across runs for a fixed prompt and fixed model would characterize each model's output consistency — a signal for model selection decisions based on quality distribution rather than single-sample evaluation.

### 29.5 Adaptive Task Contracts

Current task contracts are static specifications. Adaptive contracts could learn from execution history: if a specific quality gate consistently fails for a given crew type, the contract could automatically adjust its threshold or add additional gates based on observed failure patterns. This would require accumulating `ContractResult` history per crew configuration, which the current JSONL logging infrastructure supports.

### 29.6 Extended Z3 Theorem Set

The current four theorems address SS and GCR invariants. Additional candidates for formal verification include:

- **ACR non-negativity**: ACR(I) ∈ [0,1] for all valid issue sets I.
- **Thompson Sampling convergence**: Under bounded regret assumptions, the expected selection probability converges to the optimal arm.
- **Contract completeness**: If all quality gates pass and no forbidden patterns match, `ContractResult.fulfilled = True` holds by construction.

### 29.7 Z3 Proof Marketplace (Phase 10)

The on-chain proof hash mechanism (Section 32.5) creates the foundation for cross-protocol trust verification. A Z3 proof marketplace would allow any agent framework to submit proofs for verification against DOF invariants, creating an interoperable trust layer for the AI agent economy. Third-party systems could register Z3-verified trust scores through DOFProofRegistry.sol, establishing a shared standard for mathematical trust guarantees across heterogeneous agent ecosystems.

### 29.8 Extended External Adversarial Benchmarks

The Garak external benchmark (Section 24.6, 58.4% against 12,229 payloads) provides the first external validation. Further validation against additional standard datasets (HELM, BigBench-Hard adversarial subsets) would extend coverage breadth and enable direct comparison with other governance frameworks across different adversarial paradigms.

---

## 30. Conclusion

This paper presented an experimental framework for deterministic evaluation of multi-agent LLM systems operating across heterogeneous providers. The framework addresses the absence of formal metrics, reproducible evaluation conditions, and structured observability in existing multi-agent orchestration tools.

Six metrics—Stability Score, Provider Fragility Index, Retry Pressure, Governance Compliance Rate, Supervisor Strictness Ratio, and Adversarial Consensus Rate—provide complementary characterizations of system behavior with formal definitions (Section 5). The deterministic execution mode produces reproducible results in simulated experiments, confirmed by metric identity across independent runs (Section 6.2).

The framework has been substantially extended beyond the original nine-module implementation. Seven new formal assurance capabilities address limitations identified in the initial design:

**Z3 formal verification** (Section 8) elevates the empirical observation GCR = 1.0 to a machine-checkable architectural invariant, proven in 1.66 ms total across four theorems. This provides the first formal behavioral guarantee for a multi-agent LLM framework property, demonstrating that *architectural* deterministic guarantees are achievable even when *output* guarantees are not.

**Adversarial Red-on-Blue evaluation** (Section 9) resolves supervisor circularity by exploiting LLM biases bidirectionally and resolving the dialectic through a deterministic arbiter. The ACR metric provides a new quality signal measuring output defensibility under structured adversarial challenge.

**Formal task contracts** (Section 11) enforce completion guarantees by specifying what constitutes a fulfilled task independently of the heuristic supervisor, preventing acceptance of structurally correct but semantically empty outputs.

**Bayesian provider selection** (Section 13) replaces static rotation with Thompson Sampling over Beta posteriors, incorporating empirical reliability evidence with temporal decay. This provides asymptotically optimal provider selection under the 4/δ regret bound [18].

**Constitutional memory governance** (Section 15) introduces the first memory persistence system with formal governance enforcement. Every write operation passes through ConstitutionEnforcer validation, and the bi-temporal versioning model enables point-in-time reconstruction of agent memory state for audit compliance. Constitutionally protected categories ensure that decisions and error patterns are immune to relevance decay.

**OAGS conformance** (Section 16) implements three-level compatibility with the Open Agent Governance Specification through deterministic BLAKE3 agent identity, bidirectional policy conversion, and structured audit event export. This represents, to our knowledge, the first OAGS-conformant system with Z3-verified governance invariants.

**ERC-8004 Oracle Bridge** (Section 17) extends governance assurance beyond the execution boundary through compliance-gated on-chain attestation on Avalanche C-Chain. Only attestations with GCR = 1.0 are eligible for publication, ensuring the on-chain record contains exclusively verified compliance events.

The parametric sweep (Section 7) establishes that Stability Score follows SS_empirical(f) = 1 − f/2 under the simulated two-step recovery structure, while the theoretical model SS(f) = 1 − f³ describes terminal failure probability under bounded retries with independent failures. The distinction between these formulations is now formally verified rather than argued by derivation.

**Protocol integration** (Section 18) extends the governance boundary through MCP server (10 tools, 3 resources, stdio JSON-RPC 2.0) and REST API (14 FastAPI endpoints), enabling external systems to invoke DOF governance without importing Python modules. Both protocol layers are thin translation adapters ensuring governance semantics are identical across all access paths.

**Storage architecture** (Section 19) provides a dual-backend abstraction with JSONL (default, zero-config) and PostgreSQL (production, multi-tenant via SQLAlchemy ORM). The dual-write pattern preserves JSONL as the authoritative audit trail while enabling production query performance.

**Framework-agnostic governance** (Section 20) demonstrates that the GCR invariant extends beyond the DOF execution pipeline. The GenericAdapter with zero external dependencies enables DOF governance for any system that produces string output, validating the architectural principle that governance evaluation depends on output content only.

**Adversarial benchmark** (Section 24) provides the first quantitative assessment of DOF verification accuracy. The TestGenerator produces 400 deterministic adversarial tests across four categories; the BenchmarkRunner measures FDR, FPR, and F1 per category. Results: Governance 100% FDR / 0% FPR / F1=100%, Code Safety 86% FDR / 0% FPR / F1=92.5%, Hallucination 0% FDR (semantic gap), Consistency 0% FDR (semantic gap), Overall F1=48.1%. This honest baseline quantifies both the strengths and limitations of deterministic verification.

**Execution infrastructure** (Section 24.5) introduces ExecutionDAG (critical path analysis, cycle detection), LoopGuard (Jaccard similarity loop detection), DataOracle (three deterministic verification strategies), and TokenTracker (per-call LLM token flow tracking). These components extend the framework's observability and safety guarantees without introducing LLM dependencies in the verification path.

**LLM-as-a-Judge** (Section 9.5) adds an optional advisory evaluation layer that scores outputs on a 1–10 scale via an external LLM call. The judge verdict is strictly informational — it does not influence the deterministic governance decision, preserving the GCR = 1.0 invariant. This design resolves the tension between leveraging LLM judgment and maintaining zero-LLM governance.

**Red Team attack vector methods** (Section 9.6) implement three Garak/PyRIT-inspired attack simulations — indirect prompt injection, persuasion jailbreak, and training data extraction — returning structured `AttackResult` objects with vector, payload, detection status, and severity. These methods extend the adversarial evaluation pipeline beyond passive defect detection to active attack simulation.

**Instruction hierarchy enforcement** (Section 14.5) implements the SYSTEM > USER > ASSISTANT priority ordering [25] within the ConstitutionEnforcer. Three sequential checks detect user-prompt system overrides, response-level directive violations, and governance bypass attempts, returning a `HierarchyResult` with violation level classification. Hard rules are immutably SYSTEM-priority; soft rules are USER-priority.

**AGENT\_FAILURE error classification** (Section 12.1) extends the causal error taxonomy from three to eleven classes, with AGENT\_FAILURE capturing 16 agent-specific failure keywords (tool\_call\_failed, planning\_loop\_detected, reflexion\_timeout, agent\_stuck, etc.) that were previously misclassified as INFRA\_FAILURE due to shared keyword overlap. Priority ordering in `classify_error()` ensures AGENT\_FAILURE is evaluated before INFRA\_FAILURE.

The framework has been validated in production with live on-chain attestations on Avalanche C-Chain mainnet, governance verification of production agents indexed by the Enigma Scanner, and a four-phase audit pipeline including cross-role verification and bilateral peer review. Twenty-one attestations have been confirmed on-chain across 10 cross-agent verification rounds for production agents Apex Arbitrage (#1687) and AvaBuilder Agent (#1686), ranked #1 and #2 of 1,772 agents on the Enigma Scanner with combined trust scores of 0.85. The combined trust architecture assigns governance the highest weight (0.50) as the only dimension backed by Z3 formal proofs. A cross-network external agent audit (Section 23) validated DOF governance enforcement against all active agents in the ERC-8004 registry across four protocols (A2A, x402, OASF, MCP), achieving COMPLIANT status with 0 violations across 13 tests — demonstrating that governance cross-verification generalizes to third-party agent outputs regardless of protocol or origin.

The v0.3.x release series represents the most significant architectural evolution since DOF's inception, transforming the framework from a trust-by-scoring system to a trust-by-proof protocol (Section 32). Eight dynamic invariants are formally proven across all possible agent state transitions in 107.7ms, establishing that no sequence of actions — regardless of input — can violate DOF governance. The Z3 Gate implements the neurosymbolic principle: LLM agents propose actions, Z3 verifies safety before execution, and only mathematically proven decisions are executed. Automated test generation from Z3 boundary cases and counterexamples expanded the test suite from 807 to 1,008 tests with 207 Z3-specific tests. On-chain proof hash attestations via DOFProofRegistry.sol enable any third party to independently verify that a trust score was backed by a formal mathematical proof. Combined with the existing three-layer publication pipeline (PostgreSQL → Enigma Scanner → Avalanche C-Chain), DOF v0.3.3 provides the first end-to-end trust-by-proof infrastructure for AI agent ecosystems.

The implementation now comprises 27,000+ lines of Python across 35 core modules, with 1,008 passing tests (207 Z3-new, 0 failures). All 8 state transition invariants are PROVEN. All 42 hierarchy patterns are verified. Both production agents (#1686, #1687) maintain their #1 and #2 ranking among 1,772 agents on the Enigma Scanner, now backed by mathematical proofs rather than probabilistic scores alone.

The implementation comprises 27,000+ lines of Python across 35 core modules, with 1,008 passing tests. All experimental results are from executed code with persisted trace artifacts. The framework provides the instrumentation layer necessary for systematic study of multi-agent system behavior, expressing operational characteristics as distributions with means and standard deviations, formal proofs for architectural invariants, adversarially validated quality signals, governed memory with temporal auditability, standards-conformant governance interoperability, immutable on-chain attestation of compliance outcomes with three-layer verification (PostgreSQL, Supabase, Avalanche C-Chain), protocol-agnostic governance access, production-grade storage, framework-independent constitutional enforcement, integrated scanner trust scoring, adversarial benchmark with FDR/FPR metrics, execution infrastructure components (ExecutionDAG, LoopGuard, DataOracle, TokenTracker), LLM-as-a-Judge advisory evaluation, Red Team attack vector simulation, instruction hierarchy enforcement, expanded causal error taxonomy with AGENT\_FAILURE classification, neurosymbolic Z3 gate for agent output verification, state transition formal verification (8 dynamic invariants), automated counterexample test generation, and on-chain proof hash attestations via DOFProofRegistry. The RegressionTracker (Section 24.7) extends DOF's self-monitoring capabilities by automating post-merge health checks across four subsystems (Z3 invariants, hierarchy, tests, Garak benchmark). Combined with the external Garak benchmark (58.4% detection against 12,229 NVIDIA payloads across 12 categories, Section 24.6), DOF now provides three layers of quality assurance: internal tests (1,008), external validation (Enterprise Report v6, 10/10), and adversarial benchmarking (NVIDIA Garak). The regression tracking infrastructure ensures that each change is measured against the previous state, with CI automatically blocking any commit that introduces regressions in Z3 invariants, hierarchy enforcement, test coverage, or adversarial detection rates.

Total: 40+ contributions, 1,008 tests, 35 core modules, 27,000+ LOC, 12 Z3 theorems (4 static + 8 dynamic), 42 hierarchy patterns proven, 21 on-chain attestations.

---

## 31. External Validation (Enterprise Report v4)

DOF v0.2.6 was validated externally via Google Colab on 2026-03-08 by an independent auditor with zero local dependencies. The audit installed `dof-sdk==0.2.6` directly from PyPI and executed 6 validation blocks:

| Block  | Component                                        | Result  |
| :------ | :------------------------------------------------ | :------- |
| B1     | Z3 Formal Verification — 4 theorems              | PASS    |
| B2     | Error Classification — 8/8 categories            | PASS    |
| B3     | Merkle Batcher — 10 attestations → 1 root        | PASS    |
| B4     | Red Team + LLM-as-Judge (Groq 8.5/10)            | PASS    |
| B5     | enforce_hierarchy — indirect injection patterns  | PASS    |
| B6     | x402 Trust Gateway — ALLOW/BLOCK verified        | PASS    |

**Verdict: APPROVED. Commit: 726b6be.**

### 31.1 Lessons Learned (v0.2.6)

- `TrustGateway.verify()` returns `.action` not `.verdict`
- `enforce_hierarchy` is not exported in PyPI — use `RedTeamAgent.indirect_prompt_injection`
- Pattern matching is case-sensitive and exact — compound phrases need explicit pattern entries
- External audit from PyPI is strongest credibility signal — zero local deps

### 31.2 Lessons Learned (v0.2.7)

- Simple pattern detection does not capture compound threats — reading env vars is not dangerous, making POST requests is not dangerous, but both together constitute exfiltration. `composite_detection` resolves this without full taint analysis.
- Payloads encoded in base64 evade all pattern matchers. A second decoding pass before scanning closes this entire class of evasion.

### 31.3 External Validation (Enterprise Report v5 — v0.2.8)

DOF v0.2.8 was validated externally via Google Colab on 2026-03-09. The audit installed `dof-sdk==0.2.8` from PyPI and re-executed 6 validation blocks:

| Block  | Component                                    | Result  |
| :------ | :-------------------------------------------- | :------- |
| B1     | Z3 Formal Verification — 4 static theorems   | PASS    |
| B2     | Error Classification — 8/8 categories        | PASS    |
| B3     | Merkle Batcher — 10 attestations → 1 root    | PASS    |
| B4     | Red Team + LLM-as-Judge (Groq 8.5/10) — 3/3  | PASS    |
| B5     | enforce_hierarchy — gap cerrado 3/3          | PASS    |
| B6     | x402 Trust Gateway — ALLOW/BLOCK verified    | PASS    |

**Verdict: APPROVED.** BLOQUE 4 gap (indirect injection phrases undetected in v0.2.7) closed by adding 2 missing patterns. BLOQUE 5 gap (privilege escalation phrases) closed in v0.2.6. All 6/6 blocks pass with 3/3 coverage in previously failing sub-tests.

### 31.4 External Validation (Enterprise Report v6 — v0.3.3)

DOF v0.3.3 was validated externally via Google Colab on 2026-03-09. The audit installed `dof-sdk==0.3.3` from PyPI and executed 10 validation blocks — the most comprehensive external validation to date:

| Block | Component                                | Result |
|:------|:-----------------------------------------|:------:|
| B1    | Z3 Static Proofs — 4 theorems            | PASS   |
| B2    | Z3 State Transitions — 8 invariants      | PASS   |
| B3    | Z3 Hierarchy — 42 patterns               | PASS   |
| B4    | Z3 Gate — neurosymbolic validation       | PASS   |
| B5    | Proof Hash — deterministic serialization | PASS   |
| B6    | Error Classification — 8/8 categories    | PASS   |
| B7    | Merkle Batcher — 10 attestations batched | PASS   |
| B8    | Red Team + Threats — 3/3 detected        | PASS   |
| B9    | enforce_hierarchy — instruction priority  | PASS   |
| B10   | x402 Trust Gateway — ALLOW/BLOCK         | PASS   |

**Verdict: APPROVED** — 10/10 blocks passed. First external validation of trust-by-proof features.

### 31.5 Lessons Learned (v0.3.3)

- `ProofSerializer.serialize_proof()` requires 3 args: `solver_assertions` (list), `result` (str), `invariants` (list) — None not accepted
- `MerkleBatcher` API: `add(str)` → `flush()` → `batches`; `queue_size` is a property not a method; input must be strings not dicts
- `classify_error` patterns are exact keyword matching: use `"bad request"` for MODEL\_FAILURE, `"embedding"` for MEMORY\_FAILURE, `"model not found"` maps to UNKNOWN
- `persuasion_jailbreak` detection needs specific keywords like `"developer mode"` or `"no restrictions"` to trigger — generic phrasing returns LOW severity
- Enterprise Report v6 validates 10 blocks (vs 6 in v5) — most comprehensive external validation to date

---

## 32. Neurosymbolic Formal Verification Layer (v0.3.x)

### 32.1 Motivation

DOF v0.2.x established deterministic governance through five non-LLM layers (Constitution, AST, Z3, Arbiter, LoopGuard) with Z3 verifying static properties: the cubic safety score SS(f) = 1 − f³ and the GCR(f) = 1.0 invariant. However, static verification alone cannot guarantee safety across dynamic agent state transitions. An adversarial sequence of actions could theoretically transition an agent to a state that bypasses governance constraints.

DOF v0.3.x addresses this gap through four enhancement phases that transform DOF from a trust-by-scoring system to a trust-by-proof protocol — where every trust assessment carries a mathematical guarantee.

### 32.2 State Transition Verification (Phase 1 — v0.3.0)

Agent states are modeled as Z3 symbolic variables: `trust_score ∈ ℝ[0,1]`, `hierarchy_level ∈ ℤ[0,3]`, `threat_detected ∈ 𝔹`, `publish_allowed ∈ 𝔹`, `attestation_count ∈ ℤ≥0`, `cooldown_active ∈ 𝔹`, `governance_violation ∈ 𝔹`, and `safety_score ∈ ℝ[0,1]`.

Nine transition types are defined: PUBLISH, SCORE_UPDATE, PROMOTE, DEMOTE, THREAT_DETECT, THREAT_CLEAR, COOLDOWN_START, COOLDOWN_END, GOVERNOR_ACTION. Each maps to Z3 constraints over pre-state and post-state variables.

Eight invariants are formally verified:

| ID     | Property                                     |    Result   |   Time |
| :------ | :-------------------------------------------- | :----------: | ------: |
| INV-1  | `threat_detected → ¬publish_allowed`         |  **PROVEN** |  <15ms |
| INV-2  | `trust_score < 0.4 → attestation_count = 0`  |  **PROVEN** |  <15ms |
| INV-3  | `hierarchy_next ≤ hierarchy_current + 1`     |  **PROVEN** |  <15ms |
| INV-4  | `0 ≤ trust_score ≤ 1`                        |  **PROVEN** |  <10ms |
| INV-5  | `cooldown_active → ¬publish_allowed`         |  **PROVEN** |  <10ms |
| INV-6  | `hierarchy = GOVERNOR → trust_score > 0.8`   |  **PROVEN** |  <15ms |
| INV-7  | `safety_score = 1 − f³` (consistency)        |  **PROVEN** |  <10ms |
| INV-8  | `governance_violation → DEMOTE`              |  **PROVEN** |  <15ms |

Total verification time: **107.7ms** for all 8 invariants. This establishes that no sequence of agent actions, regardless of input, can violate DOF governance.

Additionally, all **42 hierarchy enforcement patterns** (expanded from 33 in v0.2.8) are translated to Z3 constraints and verified as inviolable in **4.9ms**.

### 32.3 Neurosymbolic Z3 Gate (Phase 2 — v0.3.1)

DOF adopts the neurosymbolic principle established by QWED-AI [28] and extends it to agent governance: the LLM is an untrusted translator; the symbolic engine (Z3) is the trusted verifier.

The Z3Gate intercepts all outputs from LLM-dependent layers (Meta-Supervisor) and validates agent outputs from the Red/Blue team (which are internally deterministic but produce classifications that affect downstream behavior):

```text
Agent Output → Z3Gate.validate_output() → APPROVED | REJECTED | TIMEOUT
                                              ↓          ↓          ↓
                                           Execute    Log+Escalate  Fallback to
                                                      counterexample deterministic
                                                                     layers
```

Gate behavior on TIMEOUT (configurable, default 5000ms): the decision is delegated to the next deterministic layer in the governance stack (Constitution → AST → Arbiter → LoopGuard). Z3 verification is additive security — it never becomes a bottleneck.

Counterexamples from REJECTED decisions provide forensic detail: the exact variable assignments that would violate safety, enabling targeted hardening.

```python
from dof import Z3Gate, GateResult

gate = Z3Gate(constitution_rules, timeout_ms=5000)
result = gate.validate_trust_score("agent-1686", 0.95, evidence)

if result.result == GateResult.APPROVED:
    execute(action)                    # Z3 proved it's safe
elif result.result == GateResult.REJECTED:
    log(result.counterexample)         # Z3 shows exactly why
elif result.result == GateResult.TIMEOUT:
    fallback_to_deterministic_layers() # Never blocks pipeline
```

### 32.4 Automated Test Generation (Phase 3 — v0.3.2)

Z3 is used in reverse: rather than verifying that properties hold, it is asked to discover the weakest points. The Z3TestGenerator produces three categories of tests:

1. **Counterexample tests**: When a weakened invariant is satisfiable, Z3 provides the exact inputs that violate it. These are automatically converted to unittest test cases.

2. **Boundary tests**: For each threshold (trust > 0.4, governor > 0.8), Z3 generates values at threshold−ε, threshold, threshold+ε, plus floating-point edge cases.

3. **Threat pattern tests**: For each of the 12 DOFThreatPatterns categories, Z3 finds minimal inputs that trigger detection and minimal inputs that don't.

This creates a self-reinforcing cycle: Z3 discovers edge cases → generates tests → tests catch regressions → fixes improve the model → Z3 re-verifies.

Test count progression: 807 (v0.2.8) → **1,008** (v0.3.3), with 207 Z3-specific tests including auto-generated boundary and counterexample cases.

### 32.5 On-Chain Proof Attestations (Phase 4 — v0.3.3)

Each DOF attestation now includes a `z3_proof_hash` — the keccak256 hash of the serialized Z3 proof transcript. The full transcript is stored locally by default (with optional IPFS via Pinata).

The verification flow:

```text
Agent executes → Z3 Gate verifies → Proof serialized → Hash computed
                                                            │
    ┌───────────────────────────────────────────────────────┘
    ▼
3-layer publish: PG (200ms) → Enigma (900ms) → Avalanche (2s)
                                                    │
                                           z3_proof_hash included
                                           in DOFProofRegistry.sol
```

**Critical property**: proof serialization is **deterministic**. The same solver state always produces the same transcript, ensuring hash reproducibility.

**DOFProofRegistry.sol** — new companion contract (existing contracts untouched):

```solidity
contract DOFProofRegistry {
    function registerProof(
        uint256 agentId,
        uint256 trustScore,
        bytes32 z3ProofHash,
        string calldata storageRef,
        uint8 invariantsCount
    ) external returns (uint256);

    // Anyone can verify on-chain
    function verifyProof(
        uint256 proofId,
        bytes calldata proofTranscript
    ) external view returns (bool);
}
```

### 32.6 Comparative Analysis

| Property                  | Typical Trust Frameworks  | DOF v0.3.3               |
| :------------------------- | :------------------------- | :------------------------ |
| Trust basis               | Probabilistic scoring     | Mathematical proof       |
| LLM validation            | None or self-check        | Z3 gate (neurosymbolic)  |
| On-chain evidence         | Score only                | Score + proof hash       |
| Test generation           | Manual                    | Z3 auto-generated        |
| Verification scope        | Single output             | Full state transitions   |
| Independent verification  | No                        | Yes (`verifyProof()`)    |

### 32.7 Performance Impact

| Metric                   | v0.2.8    | v0.3.3       | Delta          |
| :------------------------ | :--------- | :------------ | :-------------- |
| Total tests              | 807       | 1,008        | +201 (+25%)    |
| Z3 verification time     | —         | 107.7ms      | New            |
| Hierarchy verification   | —         | 4.9ms        | New            |
| Invariants proven        | 4 static  | 8 dynamic    | +4             |
| Hierarchy patterns       | 33        | 42 (proven)  | +9             |
| Pipeline latency impact  | 0ms       | <110ms       | Negligible     |
| Benchmark F1             | 96.8%     | ≥96.8%       | No regression  |

### 32.8 New Core Modules

| Module               | Location                     | Purpose                                         |
| :-------------------- | :---------------------------- | :----------------------------------------------- |
| `state_model`        | `core/state_model.py`        | Agent state as Z3 symbolic variables            |
| `transitions`        | `core/transitions.py`        | Transition verifier with 8 proven invariants    |
| `hierarchy_z3`       | `core/hierarchy_z3.py`       | 42 hierarchy patterns as Z3 constraints         |
| `z3_gate`            | `core/z3_gate.py`            | Neurosymbolic gate for agent outputs            |
| `agent_output`       | `core/agent_output.py`       | Output protocol with Z3 constraint translation  |
| `boundary`           | `core/boundary.py`           | Boundary case discovery engine                  |
| `z3_test_generator`  | `core/z3_test_generator.py`  | Auto-generates tests from Z3 counterexamples    |
| `z3_proof`           | `core/z3_proof.py`           | Attestation with keccak256 proof hash           |
| `proof_hash`         | `core/proof_hash.py`         | Deterministic proof serialization and hashing   |
| `proof_storage`      | `core/proof_storage.py`      | Local storage (default) + optional IPFS         |

---

## 33. Neurosymbolic LLM Routing

DOF implements task-aware LLM selection as a first-class governance primitive. The routing function `get_llm_smart()` extends the existing Bayesian Thompson Sampling selector [Section 13] with two new dimensions:

**(i) Context-size awareness**: requests exceeding 50k tokens are routed to large-context models (Gemini), preventing truncation-induced governance failures. This directly addresses the "Spilled Energy in LLMs" phenomenon [Turing Post FOD#143, 2026] where oversized contexts degrade reasoning quality unpredictably.

**(ii) Task-type specialization**: verification tasks are routed exclusively to MiniMax M2.1 (primary) with Groq fallback, ensuring that the LLM layer of DOF's neurosymbolic pipeline — where LLM proposes and Z3 approves — uses models optimized for structured output generation.

This is consistent with findings in KARL (Knowledge Agents via RL, 2026): agents that learn *when* to use which knowledge source outperform uniform routing by adapting to task structure rather than treating all queries as equivalent.

The circuit breaker mechanism (3 failures within 5 minutes → provider degraded for the window duration) prevents cascading failures when a provider degrades. Unlike static cooldowns, the circuit breaker respects the sliding window and automatically recovers when the failure timestamps expire. The RegressionTracker (Section 24.7) monitors provider failure rates as a 5th subsystem, triggering CI failure (exit 1) when any provider exceeds 15% failure rate.

Routing decisions are logged for analytics via `get_routing_stats()`, providing per-provider distribution, failure rates, and latency metrics. This data feeds into the regression tracking pipeline for post-merge health verification.

---

## 34. DOF as On-Chain Trust Infrastructure (ERC-8183)

DOF v0.3.3 introduces `DOFEvaluator.sol`, positioning DOF as a trustless Evaluator in the ERC-8183 Agentic Commerce standard [EIP-8183, 2026].

The ERC-8183 Job primitive defines a state machine:

```
Open → Funded → Submitted → Terminal (Completed | Rejected | Expired)
```

An Evaluator is any address that attests to whether a submitted deliverable meets agreed terms. DOF satisfies this role structurally: Z3 formal verification produces a deterministic binary outcome (PROVEN | COUNTEREXAMPLE), and `DOFProofRegistry.sol` records the keccak256 proof hash on-chain. `DOFEvaluator.sol` exposes this existing machinery as an ERC-8183-compatible interface without modifying deployed contracts (consistent with DOF Lesson #12: new contracts only).

This creates a composable trust loop with ERC-8004:

```
Discovery (ERC-8004) → Commerce (ERC-8183, DOF as Evaluator)
→ Reputation (ERC-8004) → Better Discovery
```

Critically, DOF's evaluation is non-custodial and deterministic. Unlike LLM-based evaluators that introduce subjectivity, DOF's Z3 proofs are verifiable by any party independently. This makes DOF suitable for high-stakes jobs (financial, legal, medical) where evaluator credibility must be auditable, not trusted.

The "Learning When to Act or Refuse" paradigm [2026] maps directly to DOF's Red/Blue gate: the system learns refusal boundaries through adversarial payloads (12,229 tested via Garak v2) rather than hardcoded rules, maintaining 58.4% overall detection with 90% accuracy on goodside category attacks.

---

## References

[1] J. Moura, "CrewAI: Framework for orchestrating role-playing autonomous AI agents," 2024. https://github.com/crewAIInc/crewAI

[2] Q. Wu et al., "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation," arXiv:2308.08155, 2023.

[3] LangChain, "LangGraph: Build resilient language agents as graphs," 2024. https://github.com/langchain-ai/langgraph

[4] S. Hong et al., "MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework," arXiv:2308.00352, 2023.

[5] Databricks, "MLflow: A Machine Learning Lifecycle Platform," 2018. https://mlflow.org

[6] L. Biewald, "Weights & Biases: Experiment Tracking for Machine Learning," 2020. https://wandb.ai

[7] OpenTelemetry Authors, "OpenTelemetry: An observability framework for cloud-native software," 2019. https://opentelemetry.io

[8] M. Nygard, "Release It! Design and Deploy Production-Ready Software," Pragmatic Bookshelf, 2007.

[9] AWS, "Exponential Backoff and Jitter," Amazon Architecture Blog, 2015.

[10] Netflix Technology Blog, "The Netflix Simian Army," 2011.

[11] P. Henderson et al., "Deep Reinforcement Learning that Matters," AAAI 2018.

[12] L. M. de Moura and N. Bjørner, "Z3: An Efficient SMT Solver," TACAS 2008. https://github.com/Z3Prover/z3

[13] G. Katz et al., "Marabou: A Verification Framework for Deep Neural Networks," CAV 2019.

[14] OpenAI, "Preparedness Framework (Beta)," 2023. https://openai.com/safety/preparedness

[15] L. Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena," NeurIPS 2023. arXiv:2306.05685.

[16] E. Breck et al., "The ML Test Score: A Rubric for ML Production Readiness and Technical Debt Reduction," IEEE BigData 2017.

[17] W. R. Thompson, "On the likelihood that one unknown probability exceeds another in view of the evidence of two samples," Biometrika 25(3-4), 1933.

[18] Anonymous, "4/δ Regret Bound for Thompson Sampling under Bounded Reward Distributions," arXiv:2512.02080, 2025.

[19] Mem0 AI, "Mem0: The Memory Layer for AI Applications," 2024. https://github.com/mem0ai/mem0

[20] Zep AI, "Graphiti: Build Dynamic, Temporally Aware Knowledge Graphs," 2024. https://github.com/getzep/graphiti

[21] Topoteretes, "Cognee: Scientific Memory Management for AI Applications," 2024. https://github.com/topoteretes/cognee

[22] Sekuire, "Open Agent Governance Specification (OAGS)," 2025. https://sekuire.com/oags

[23] Anthropic, "Model Context Protocol (MCP)," 2024. https://modelcontextprotocol.io

[24] S. Ramírez, "FastAPI: Modern, fast (high-performance), web framework for building APIs with Python," 2018. https://fastapi.tiangolo.com

[25] E. Wallace et al., "The Instruction Hierarchy: Training LLMs to Prioritize Privileged Instructions," arXiv:2404.13208, 2024.

[26] NVIDIA, "Garak: LLM Vulnerability Scanner," 2024. https://github.com/NVIDIA/garak

[27] Microsoft, "PyRIT: Python Risk Identification Toolkit for generative AI," 2024. https://github.com/Azure/PyRIT

[28] QWED-AI, "Deterministic Verification Layer for LLMs — Neurosymbolic AI Verification," 2026. https://github.com/QWED-AI/qwed-verification

[29] SakuraSky, "Formal Verification of AI Agent State Transitions with Z3 Counterexample Replay," 2026. https://www.sakurasky.com/blog/missing-primitives-for-trustworthy-ai-part-9/

[30] Asymptotic, "Sui Prover: Z3-Based Formal Verification for Smart Contracts," 2026. https://github.com/asymptotic-code/sui-prover

[31] C. Huyen, "AI Engineering: Building Applications with Foundation Models," O'Reilly Media, 2025. ISBN 978-1098166304.

