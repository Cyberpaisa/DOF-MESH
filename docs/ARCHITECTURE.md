# DOF System Architecture

*Extracted from Section 3 of the [full paper](../paper/PAPER_OBSERVABILITY_LAB.md)*

## Layered Architecture

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
│ Selector │ (4 rules)│ (12 proofs│  Arbiter               │
│          │          │  +8 inv.) │                        │
├──────────┴──────────┴───────────┴───────────────────────┤
│               Metrics Logger (JSONL + Rotation)          │
├─────────────────────────────────────────────────────────┤
│             Memory Manager (Short/Long/Episodic)         │
├─────────────────────────────────────────────────────────┤
│                CrewAI + LiteLLM (Execution)              │
│          Groq │ NVIDIA NIM │ Cerebras │ Zhipu AI         │
└─────────────────────────────────────────────────────────┘
```

## Governance Stack (7 Layers)

```text
+----------------------------------------------------+
| L7  Signer       HMAC + Avalanche           ~2s    |
+----------------------------------------------------+
| L6  Memory Gov   Bi-temporal + decay        <1ms   |
+----------------------------------------------------+
| L5  Red/Blue     Red -> Guard -> Arb       ~50ms   |
+----------------------------------------------------+
| L4  Z3 Proofs    8 invariants + Z3 Gate    ~110ms  |
+----------------------------------------------------+
| L3  Supervisor   Q+A+C+F scoring            ~5ms   |
+----------------------------------------------------+
| L2  AST Verifier eval/exec/secrets          <1ms   |
+----------------------------------------------------+
| L1  Constitution 4 HARD + 5 SOFT            <1ms   |
+----------------------------------------------------+
| Engine  DAG + LoopGuard + TokenTracker             |
+----------------------------------------------------+
| Data Oracle  6 verification strategies      <1ms   |
+----------------------------------------------------+
```

Total governance latency: **< 180ms** (layers 1-6). On-chain signing adds ~2s.

## Core Modules (35)

| Module                   | File                        | Purpose                                     |
|:-------------------------|:----------------------------|:--------------------------------------------|
| Provider Manager         | `providers.py`              | TTL backoff, provider chains                 |
| Checkpoint Manager       | `checkpointing.py`         | JSONL step persistence                       |
| Constitution Enforcer    | `governance.py`             | Hard/Soft rule enforcement                   |
| Meta-Supervisor          | `supervisor.py`             | Q+A+C+F weighted scoring                     |
| Metrics Logger           | `metrics.py`                | JSONL events with rotation                   |
| Memory Manager           | `memory_manager.py`         | Short/Long/Episodic tiers                    |
| Observability            | `observability.py`          | RunTrace, StepTrace, ErrorClass              |
| Experiment               | `experiment.py`             | Batch runner, statistical aggregation        |
| Crew Runner              | `crew_runner.py`            | Integration orchestration                    |
| AST Verifier             | `ast_verifier.py`           | Deterministic code analysis                  |
| Z3 Verifier              | `z3_verifier.py`            | 4 static + 8 dynamic theorems                |
| Adversarial Evaluator    | `adversarial.py`            | Red-on-Blue protocol                         |
| Merkle Tree              | `merkle_tree.py`            | SHA-256 batching                             |
| ExecutionDAG             | `execution_dag.py`          | DAG + cycle detection                        |
| LoopGuard                | `execution_dag.py`          | Jaccard similarity detection                 |
| DataOracle               | `data_oracle.py`            | 6 verification strategies                    |
| TokenTracker             | `observability.py`          | Per-call token flow                          |
| TestGenerator            | `test_generator.py`         | Adversarial test datasets                    |
| BenchmarkRunner          | `test_generator.py`         | FDR/FPR/F1 measurement                       |
| Task Contract            | `task_contract.py`          | Completion guarantees                        |
| State Model              | `state_model.py`            | Z3 symbolic agent states                     |
| Transitions              | `transitions.py`            | 8 proven invariants                          |
| Hierarchy Z3             | `hierarchy_z3.py`           | 42 patterns as Z3 constraints                |
| Z3 Gate                  | `z3_gate.py`                | Neurosymbolic output gate                    |
| Agent Output             | `agent_output.py`           | Z3 constraint translation                    |
| Boundary Engine          | `boundary.py`               | Boundary case discovery                      |
| Z3 Test Generator        | `z3_test_generator.py`      | Auto-generated regression tests              |
| Z3 Proof                 | `z3_proof.py`               | keccak256 proof attestations                 |
| Proof Hash               | `proof_hash.py`             | Deterministic serialization                  |
| Proof Storage            | `proof_storage.py`          | Local + optional IPFS                        |

## Key Numbers

| Metric                    | Value                      |
|:--------------------------|:---------------------------|
| Total tests               | 986                        |
| Core modules              | 35                         |
| LOC                       | 27K+                       |
| Z3 static theorems        | 4 VERIFIED                 |
| Z3 dynamic invariants     | 8 PROVEN                   |
| Hierarchy patterns        | 42 verified                |
| On-chain attestations     | 21+                        |
| Benchmark F1              | 96.8%                      |
| PyPI version              | 0.3.3                      |

## Details

For the complete architecture description with all subsections, see [Section 3 of the paper](../paper/PAPER_OBSERVABILITY_LAB.md#3-system-architecture).
