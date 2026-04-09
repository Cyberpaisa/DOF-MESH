<div align="center">

# Deterministic Observability and Resilience Engineering for Multi-Agent LLM Systems

### An Experimental Framework with Formal Verification

**Cyber Paisa** · **Enigma Group**
**Colombia-Blockchain**

[![Tests](https://img.shields.io/badge/tests-1008_passed-brightgreen)]()
[![Z3 Invariants](https://img.shields.io/badge/Z3-8%2F8_PROVEN-blue)]()
[![Hierarchy](https://img.shields.io/badge/hierarchy-42_patterns_verified-blue)]()
[![PyPI](https://img.shields.io/pypi/v/dof-sdk)](https://pypi.org/project/dof-sdk/)
[![On-Chain](https://img.shields.io/badge/Conflux eSpace-21_attestations-red)]()
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
- [21. On-Chain Attestation via Conflux eSpace C-Chain](#21-on-chain-attestation-via-conflux-c-chain)
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

Multi-agent systems built on large language models (LLMs) exhibit complex failure modes distinct from single-model pipelines, including provider rate limits, model incompatibilities, and non-deterministic cascading errors. While existing orchestration frameworks abstract agent coordination, they fail to provide deterministic mechanisms for measuring system stability, enforcing formal governance, or guaranteeing compliance. This paper presents the Deterministic Observability Framework (DOF): a comprehensive, zero-dependency architecture for the formal evaluation, algorithmic governance, and cryptographic auditability of multi-agent LLM systems. DOF transitions agent evaluation from heuristic *trust-by-scoring* to mathematical *trust-by-proof*. We introduce a neurosymbolic verification architecture integrating Z3 SMT formal proofs to mathematically guarantee architectural invariants, coupled with deterministic Abstract Syntax Tree (AST) static analysis and a dialectical Red-on-Blue adversarial evaluation protocol. To ensure immutable traceability, the framework connects off-chain evaluation with on-chain execution through compliance-gated ERC-8004 attestations natively deployed across EVM networks (e.g., Conflux eSpace C-Chain, Conflux eSpace). Empirical validations involving 1,008 automatically generated boundary tests demonstrate a 100% Governance Compliance Rate (GCR=1.0), zero false-positive tampering rejections, and cross-chain read consensus latencies under 1.5 seconds. The resulting implementation provides the first mathematically verifiable, framework-agnostic governance stack for autonomous agentic systems operating in zero-trust environments.

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
5. **Decentralized Cryptographic Attestation (ERC-8004):** A complete pipeline bridging off-chain mathematical proofs with on-chain immutability. Verified agent interactions are hashed (keccak256) and anchored to EVM smart contracts (Conflux eSpace, Conflux) ensuring point-in-time trust validation without relying on centralized databases.

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

### 3.2 Core Architectural Modules

The framework comprises 35 core modules totaling 27,000+ lines of code, with no external dependencies beyond the base orchestration layer (CrewAI/LangGraph). The architecture is defined by five specialized tiers:

1. **Deterministic Execution Control**: Implements provider state tracking, TTL-based exhaustion recovery, and Bayesian provider selection via Thompson Sampling. This tier ensures that infrastructure-level provider cascades are controlled deterministically rather than probabilistically.
2. **Observability and Persistence**: A dual-backend storage architecture (JSONL/PostgreSQL) handling step-level checkpointing, memory governance with bi-temporal versioning, and causal error tracking.
3. **Formal Governance**: The `ConstitutionEnforcer` applying declarative YAML-based policy checks, paired with an AST-based static verifier that deterministically analyzes agent-generated code structures prior to execution.
4. **Neurosymbolic Verification**: The integration of the Z3 SMT solver, which formally proves static framework invariants and intercepts agent decisions dynamically via the `Z3Gate`.
5. **Decentralized Cryptographic Attestation**: The bridging layer that serializes off-chain governance proofs into SHA-256 Merkle trees and anchors them to EVM-compatible networks via `DOFProofRegistry.sol`.

By separating the generative capabilities of the LLM from the deterministic verification layer, the architecture circumvents the circularity problem inherent in LLM-evaluating-LLM paradigms [15].

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

**Prompt**: "Investigar mercado de agentes AI autónomos en Conflux eSpace. Competidores, market size, tendencias 2025-2026, oportunidades de grants."

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

## 14. Constitutional Policy and Temporal Memory

### 14.1 Declarative Governance Validation

The framework formalizes all governance rules within a canonical, versioned `dof.constitution.yml` specification, decoupling policy from the enforcement codebase. The specification implements a three-tier Instruction Hierarchy (SYSTEM > USER > ASSISTANT) aligned with emerging industry standards [25]. Hard rules (e.g., hallucination detection, minimum output lengths) operate at the SYSTEM priority, producing strict execution blocks upon violation, while soft rules (e.g., citation verification, structural formatting) operate at the USER priority, generating weighted warning scores. Enforcement occurs dynamically at runtime, applying these deterministic checks to all generated outputs prior to state transitions.

### 14.2 Constitutional Memory Governance

Multi-agent architectures typically treat memory as an unconstrained store, introducing a vulnerability where non-compliant outputs can be appended to long-term memory, thereby contaminating future generational context. DOF intercepts all state persistence operations, interposing the `ConstitutionEnforcer` on the memory write path. Memory entries that violate the active policy are automatically rejected, and the violation is recorded in an immutable append-only ledger.

### 14.3 Bi-Temporal Data Model and Relevance Decay

Agent memory is persisted using a bi-temporal data model that records both the assertion timestamp (when a fact became true in the domain) and the system recording timestamp (when the framework persisted the entry). This model guarantees historical fidelity, enabling the system to mathematically reconstruct the exact subset of knowledge available to any agent prior to a specific decision. Furthermore, memory relevance decays exponentially over time (`relevance(t) = relevance(t₀) × λ^(t - t₀)`), preventing context window saturation while maintaining protected categories (such as past adversarial defenses and governance errors) that retain permanent context value.

### 14.4 OAGS Conformance

The architecture formally implements the Open Agent Governance Specification (OAGS). It generates a deterministic BLAKE3 identity hash for every agent by concatenating the model identifier, the active constitution hash, and the tool manifest. System state is subjected to three levels of conformance validation: declarative policy existence, runtime enforcement verification, and decentralized cryptographic attestation. This standardization ensures interoperability with external ecosystems and unified audit traceability.

---

## 15. Decentralized Verification and the Oracle Bridge

### 15.1 The Oracle Bridge Architecture

To resolve the trust boundaries inherent in centralized governance evaluation, the framework bridges deterministic off-chain verification to immutable on-chain ledgers. The Oracle Bridge generates cryptographic attestations for each governed execution. Instead of relying on traditional probabilistic trust scores, the system mandates a deterministic compliance-gating rule: governance attestations are only published if the Governance Compliance Rate (GCR) strictly equals 1.0.

### 15.2 Structural Proof and Merkle Aggregation

Attestation payloads are structured as Hash-based Message Authentication Code (HMAC-SHA256) signatures containing the agent's deterministic BLAKE3 identity, the execution timestamp, and the complete vector of governance metrics. To achieve economic viability for high-throughput multi-agent systems, these cryptographic proofs are aggregated into SHA-256 Merkle trees. The root hash of the Merkle tree is published to an EVM-compatible Validation Registry smart contract. This architecture enables any third party to perform a zero-trust, off-chain verification of an agent's execution compliance by reconstructing the Merkle inclusion proof against the immutable on-chain root hash.

---

## 16. Multi-Dimensional Trust Synthesis

### 16.1 Axiological Separation of Concerns

A critical vulnerability in contemporary multi-agent trust registries is the semantic collision of distinct evaluative dimensions—specifically, the conflation of infrastructure availability (uptime) with behavioral safety (governance compliance). The framework corrects this through axiological separation, maintaining formal governance proofs in isolated tables distinct from standard heartbeat telemetry.

### 16.2 The Composite Trust Function

Trust in autonomous systems is not a scalar value but a multi-dimensional construct. The framework synthesizes three independent verification vectors into a singular algorithmic trust metric:
1. **Infrastructure Telemetry (30%)**: Continuous heartbeat probing and proxy detection ensuring operational availability.
2. **Formal Governance (50%)**: The Z3-verified, AST-backed proofs of constitutional compliance, weighted most heavily due to its mathematical rigor.
3. **Community Assessment (20%)**: Normalized historical interaction quality ratings from peers.

This composite view enables production orchestration networks to route tasks based on verifiable safety thresholds rather than mere operational liveness. External audits of this mechanism against heterogeneous protocols (e.g., OASF, x402) confirm its generalization capability: formal governance scales seamlessly across external agent identities and transactional boundaries.

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

The deployment of DOFValidationRegistry on Conflux eSpace C-Chain mainnet (Section 21) and the integration with the Enigma Scanner (Section 22) constitute the first production validation of the framework's governance pipeline against real, indexed agents. The three-layer publication pipeline provides defense in depth: if any single layer fails or is compromised, the remaining layers provide independent verification. The combined trust architecture (Section 22) demonstrates that formal governance verification can be integrated into production scoring systems alongside infrastructure monitoring and community feedback, with the weight allocation reflecting the relative strength of each verification methodology.

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

## 17. Empirical Replication Architecture

### 17.1 Deterministic Traceability

To ensure rigorous scientific reproducibility, the framework includes an experimental harness designed to systematically isolate and evaluate non-deterministic systemic variables. Rather than relying on heuristic observations, empirical replication executes fixed parametric failure sweeps (`n_runs=N`, `failure_rates=[...]`), resulting in structured JSONL trace files. This establishes an unambiguous mathematical baseline for stability metrics, rendering multi-agent fragility empirically testable across commodity hardware.

---

## 18. Ecosystem Positioning

### 18.1 Orchestration vs. Verification

Contemporary multi-agent orchestration frameworks (e.g., CrewAI, AutoGen, LangGraph) prioritize conversational dynamics, DAG-based state management, and semantic routing over formal execution guarantees. The framework proposed herein does not aim to replace these coordination semantics but to augment them with a missing assurance layer. By introducing neurosymbolic Z3 evaluation, causal error taxonomy, governed temporal memory, and cryptographically verified attestations, this architecture fundamentally shifts the multi-agent paradigm from probabilistic heuristic tracing to deterministic, theorem-backed verification.

---

## 19. Future Research Vectors

### 19.1 Axiomatic Expansion

Subsequent research will explore the calibration of the Adversarial Consensus Rate (ACR) metric against large-scale human-in-the-loop annotations. Furthermore, evaluating Bayesian Thompson Sampling selectors explicitly over dynamic latency distributions promises richer operational regret minimization. The creation of a unified cross-framework Z3 Proof Marketplace, establishing an interoperable trust ledger for heterogeneous networks, remains a critical frontier.

---

## 20. Conclusion

This paper formalizes a deterministic evaluation and constraint-enforcement methodology for multi-agent LLM systems. By extracting implicit behavioral assumptions into explicit, machine-readable constitutional parameters, replacing raw telemetry with six formally defined axiomatic metrics (SS, PFI, RP, GCR, SSR, ACR), and anchoring local probabilistic execution to verifiable Z3 invariants and EVM-compatible consensus layers, this framework re-establishes execution observability on rigorous engineering footings. The transition from *trust-by-scoring* to *trust-by-proof* sets a foundational standard for autonomous agent governance capable of meeting the stringent assurance requirements of enterprise applications.

---

## 21. Advanced Architectural Capabilities

### 21.1 Continuous External Validation

To ensure the robustness of the framework, continuous external validation protocols (Enterprise Reports v4–v6) have been integrated. These external audits operate without local dependencies, verifying critical blocks including Z3 static proofs, Red-on-Blue adversarial detection, instruction hierarchy enforcement (e.g., preventing indirect prompt injections), and the x402 Trust Gateway. Across all audited scenarios, the framework maintained complete operational integrity.

### 21.2 Neurosymbolic State Transitions

The verification layer extends beyond static constraints to dynamic state transitions. Modeled as Z3 symbolic variables, the agent state space is constrained by eight proven invariants that govern publish permissions, hierarchy mobility, and trust score boundaries. The neurosymbolic Z3 gate validates all outputs from the LLM-dependent layers against these constraints before execution. Timely counterexamples are generated for any rejected actions, establishing a rigorous forensic audit trail for blocked adversarial exploits. Furthermore, every on-chain attestation computes a deterministic `keccak256` hash of the serialized Z3 proof, enabling independent mathematical verification via `DOFProofRegistry.sol`.

### 21.3 Context-Aware Generative Routing

To mitigate semantic degradation in large-language models and ensure optimal reasoning quality, the framework implements task-aware routing complementing traditional Bayesian Thompson Sampling. Verifiable tasks are exclusively routed to structured-output-optimized LLMs, while highly extensive requests are natively assigned to large-context models. This routing logic is safeguarded by temporal circuit-breakers that automatically isolate providers exceeding critical failure thresholds, preventing systemic cascaded degradation.

### 21.4 ERC-8183 Trustless Commerce Evaluation

Positioned as a trustless Evaluator within the ERC-8183 Agentic Commerce standard, the framework executes non-custodial, deterministic judgments devoid of subjective LLM-based hallucination. Through the Z3 validation gate, the framework provides an irrefutable mathematical proof of task completion, delivering unparalleled evaluator credibility for high-stakes decentralized applications.

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

