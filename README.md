# DOF-MESH -- Deterministic Observability Framework

<div align="center">

<img src="docs/diagrams/dof_banner.jpeg" alt="DOF-MESH — Deterministic Observability Framework" width="700"/>

### Verify. Prove. Attest. · Mathematics, not promises.

**DOF-MESH v0.6.0 | 8 Chains | Enigma Group · Medellín, Colombia**

[![PyPI](https://img.shields.io/badge/PyPI-DOF--SDK-007acc?style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/dof-sdk/)
[![Github](https://img.shields.io/badge/GitHub-DOF--MESH-24292e?style=for-the-badge&logo=github)](https://github.com/Cyberpaisa/DOF-MESH)
[![On-Chain](https://img.shields.io/badge/Conflux_eSpace-0x58F0126B...6fd1-28c840?style=for-the-badge)](https://evmtestnet.confluxscan.net/address/0x58F0126B647E87a9a49e79971E168ce139326fd1)

[![Tests](https://img.shields.io/badge/Tests-4%2C191_passing-brightgreen?style=flat-square)]()
[![PyPI](https://img.shields.io/pypi/v/dof-sdk?color=blue&style=flat-square)](https://pypi.org/project/dof-sdk/)
[![Python](https://img.shields.io/badge/python-3.11+-blue?style=flat-square)](https://pypi.org/project/dof-sdk/)
[![Modules](https://img.shields.io/badge/Modules-142-blue?style=flat-square)]()
[![Z3](https://img.shields.io/badge/Z3-4_theorems_PROVEN-critical?style=flat-square)]()
[![Chains](https://img.shields.io/badge/Chains-8-gold?style=flat-square)]()
[![Attestations](https://img.shields.io/badge/Attestations-30%2B-orange?style=flat-square)]()
[![LOC](https://img.shields.io/badge/LOC-57K%2B-lightgrey?style=flat-square)]()
[![License](https://img.shields.io/badge/License-BSL--1.1-purple?style=flat-square)](LICENSE)

[PyPI](https://pypi.org/project/dof-sdk/) | [Getting Started](docs/05_operations/GETTING_STARTED.md) | [Documentation](docs/INDEX.md) | [On-Chain Proof](https://snowtrace.io/address/0x154a3F49a9d28FeCC1f6Db7573303F4D809A26F6) | [@Cyber_paisa](https://t.me/Cyber_paisa)

</div>

---

## The Problem

Your AI agent just made a decision. You have logs.
Logs the agent wrote about itself.

That is not proof. That is testimony.

The industry's fix is AI watching AI — until your watchdog hallucinates that everything is fine while an attacker manipulates your agent. We tested 10 frontier models. None could reliably govern themselves. Every one improved 6% to 50% only when a deterministic layer enforced the rules from outside.

Regulators are already asking: *"How do you prove your AI made that decision correctly?"*
Nobody has a standard answer yet.

## Our Solution

A deterministic verification layer for autonomous AI agents.

Every decision is translated into formal constraints, verified mathematically in under 30ms, and anchored on-chain as a cryptographic receipt. Not logs. Not monitoring. A proof.

```
Identity → Task → LLM → Governance → Z3 Proof → On-Chain → Supervisor
```

Z3 is the theorem prover used in safety-critical systems where failure is not an option. It doesn't estimate compliance. It proves it.

**Verified** by formal constraints. **Auditable** by anyone. **Immutable** once recorded.

> DOF doesn't monitor. DOF proves.

---

## What DOF-MESH Is — and Is Not

DOF-MESH is not an agent framework. You don't replace your agents with ours.

It is a verification layer. Your agent runs. DOF intercepts the output, checks it against deterministic rules and Z3 formal proofs, and writes a cryptographic receipt on-chain before the result is accepted. One layer on top of whatever you already have.

LangChain. CrewAI. AutoGen. A custom agent. It doesn't matter. DOF governs it.

The framework is what you install. Everything else in this repo is validation that it works.

---

## Quick Install

```bash
pip install dof-sdk
```

```python
from dof import DOFVerifier

verifier = DOFVerifier()
result = verifier.verify_action(
    agent_id="apex-1687",
    action="transfer",
    params={"amount": 500, "token": "USDC"}
)
# → verdict: "APPROVED"
# → z3_proof: "4/4 VERIFIED [GCR_INVARIANT:VERIFIED | SS_FORMULA:VERIFIED | ...]"
# → latency_ms: 8.2
# → attestation: "0x44b45cd026916c..."
```

Or run the full mesh:

```bash
git clone https://github.com/Cyberpaisa/DOF-MESH.git && cd DOF-MESH
cp .env.example .env
docker-compose up -d --build
```

---

## Architecture

```
+=====================================================================+
|                        DOF-MESH  v0.5.0                             |
|                                                                     |
|  +---------------------------------------------------------------+  |
|  |                      INTERFACE LAYER                          |  |
|  |    CLI | A2A Server | Telegram | Streamlit Dashboard | Voice  |  |
|  +---------------------------------------------------------------+  |
|                                  |                                  |
|  +---------------------------------------------------------------+  |
|  |                     EXPERIMENT LAYER                          |  |
|  |   ExperimentDataset | BatchRunner | Schema | Parametric Sweep |  |
|  +---------------------------------------------------------------+  |
|                                  |                                  |
|  +---------------------------------------------------------------+  |
|  |                    OBSERVABILITY LAYER                        |  |
|  |    RunTrace | StepTrace | 5 Derived Metrics | JSONL Audit     |  |
|  +---------------------------------------------------------------+  |
|                                  |                                  |
|  +-------------------------------+-------------------------------+  |
|  |       GOVERNANCE CORE         |      VERIFICATION CORE        |  |
|  |                               |                               |  |
|  |  ConstitutionEnforcer         |  Z3Verifier (4/4 PROVEN)      |  |
|  |  HARD rules: block            |  Formal invariant proofs      |  |
|  |  SOFT rules: warn             |  keccak256 proof hashes       |  |
|  |  Zero LLM in governance       |  ASTVerifier + Z3Gate         |  |
|  +-------------------------------+-------------------------------+  |
|                                  |                                  |
|  +---------------------------------------------------------------+  |
|  |                    CORE INFRASTRUCTURE                        |  |
|  |                                                               |  |
|  |  crew_runner.py       Orchestration, retry x3, crew_factory   |  |
|  |  providers.py         TTL backoff (5/10/20m), provider chains |  |
|  |  supervisor.py        MetaSupervisor weighted scoring         |  |
|  |  memory_manager.py    ChromaDB + HuggingFace embeddings       |  |
|  |  autonomous_daemon.py Perceive, Decide, Execute, Evaluate     |  |
|  |  node_mesh.py         NodeRegistry + MessageBus + MeshDaemon  |  |
|  +---------------------------------------------------------------+  |
|                                  |                                  |
|  +-------------------------------+-------------------------------+  |
|  |      AGENT RUNTIME LAYER      |       ON-CHAIN LAYER          |  |
|  |      (any framework)          |                               |  |
|  |                               |  DOFProofRegistry             |  |
|  |      LangChain · CrewAI       |  Avalanche · Base · Celo      |  |
|  |      AutoGen · Custom         |  Polygon · SKALE · Conflux    |  |
|  |                               |  8 chains · 30+ attestations  |  |
|  +-------------------------------+-------------------------------+  |
+=====================================================================+
```

---

## Core Components

| Component | What It Does |
|:----------|:-------------|
| **ConstitutionEnforcer** | Deterministic governance -- HARD rules block, SOFT rules warn. Zero LLM involvement. ~50 token constitution injected per agent. |
| **Z3Verifier** | 4 mathematical theorems formally PROVEN every cycle. Generates keccak256 proof hashes for on-chain recording. |
| **Z3Gate** | Neurosymbolic gate -- LLM proposes, Z3 verifies. APPROVED / REJECTED / TIMEOUT / FALLBACK. |
| **MetaSupervisor** | Weighted quality scoring: Q(0.40) + A(0.25) + C(0.20) + F(0.15). Outputs ACCEPT, RETRY, or ESCALATE. |
| **DOFProofRegistry** | Multi-chain attestation engine. Writes proof receipts to 8 chains. Verifiable by any third party. |
| **MeshDaemon** | 29 nodes + threshold consensus. Byzantine guard, CRDT memory, constitution hash beacon. |
| **ProviderManager** | LiteLLM router across 7+ LLMs. TTL backoff, automatic failover, Thompson Sampling. |

---

## The Numbers

We wrote 4,308 tests before calling it a framework.
Most projects write them after something breaks.

The proofs aren't in our database. They're on 8 public blockchains.
Go check — nobody has to take our word for it.

We tested 10 of the best AI models in the world.
None could govern themselves. All improved 6% to 50% the moment
a deterministic layer enforced the rules.

The same verification engine used to certify commercial aircraft
and nuclear reactors now certifies your agents.
The one technology where "probably correct" was never an option.

No model decides if your agent broke a rule.
A deterministic function does. Every time. Same answer.

| Metric | Value |
|:-------|------:|
| Unit tests | **4,191** |
| Autonomous cycles | **238+** |
| On-chain attestations | **30+** |
| Chains (mainnets) | **7** |
| Core modules | **142** |
| Lines of code | **57,000+** |
| Z3 theorems | **4/4 PROVEN** |
| Hierarchy patterns (Z3) | **42 PROVEN** |
| LLM providers | **7+ (Cerebras, Groq, DeepSeek, Gemini, NVIDIA, SambaNova, Zhipu)** |
| Governance mode | **100% deterministic, 0% LLM** |

---

## Pre-Execution Governance — The Architectural Leap

Most AI governance frameworks check what happened.
DOF checks what's *about to* happen.

Every tool call passes through a 3-layer pipeline before
execution is permitted:

```
Agent proposes action
        │
        ▼
┌─────────────────────┐
│  Layer 1            │   ConstitutionEnforcer
│  HARD BLOCK         │   Blocked tools rejected instantly.
│                     │   No LLM. No tokens. No exceptions.
└─────────┬───────────┘
          │ PASS
          ▼
┌─────────────────────┐
│  Layer 2            │   Z3Gate (neurosymbolic)
│  FORMAL VERIFY      │   4 invariants proven mathematically.
│                     │   keccak256 proof hash generated.
└─────────┬───────────┘
          │ APPROVED
          ▼
┌─────────────────────┐
│  Layer 3            │   PostToolUse
│  ATTEST             │   Attestation written to JSONL + chain.
│                     │   Immutable. Auditable. Verifiable.
└─────────────────────┘
```

```python
from core.tool_hooks import ToolHookPipeline, GovernanceViolation

hook = ToolHookPipeline()

# Before any tool executes:
pre = hook.pre_tool_use("transfer", "amount=500 token=USDC", "apex-1687")
if not pre.allowed:
    raise GovernanceViolation(pre.reason)

# After execution:
post = hook.post_tool_use("transfer", result, "apex-1687", pre_result=pre)
print(post.attestation_hash)  # 0x44b45cd026916c...
```

**34 tests. 0 failures. Every tool call governed before it runs.**

---

## Tech Stack

| Layer | Technology |
|:------|:-----------|
| Core Framework | Python 3.11+ |
| Formal Verification | Z3 Theorem Prover -- 4/4 invariants PROVEN |
| Blockchain | web3.py · Avalanche · Base · Celo · Polygon · SKALE · Conflux |
| LLM Routing | LiteLLM Router (7+ providers, TTL backoff, Thompson Sampling) |
| SDK | `dof-sdk` on PyPI -- `pip install dof-sdk` |
| Vector Memory | ChromaDB + HuggingFace embeddings (all-MiniLM-L6-v2) |
| Persistence | JSONL audit logs -- zero external telemetry dependencies |
| Protocols | A2A · MCP · ERC-8004 · ERC-8183 · x402 |
| Container | Docker Citadel (OrbStack) -- read-only agent sandbox |

---

## On-Chain Attestation

**DOFProofRegistry** deployed on 8 chains (3 mainnet + 5 testnet). Verified on-chain 03 Apr 2026.

| Chain | Contract | Status |
|:------|:---------|:-------|
| Avalanche C-Chain (43114) | `0x154a3F49a9d28FeCC1f6Db7573303F4D809A26F6` | ✅ mainnet |
| Base Mainnet (8453) | `0x4e54634d0E12f2Fa585B6523fB21C7d8AaFC881D` | ✅ mainnet |
| Celo Mainnet (42220) | `0x35B320A06DaBe2D83B8D39D242F10c6455cd809E` | ✅ mainnet |
| Avalanche Fuji (43113) | `0x0b65d10FEcE517c3B6c6339CdE30fF4A8363751c` | ✅ testnet |
| Base Sepolia (84532) | `0x7e0f0D0bC09D14Fa6C1F79ab7C0EF05b5e4F1f59` | ✅ testnet |
| Conflux Testnet (71) | `0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83` | ✅ testnet |
| Polygon Amoy (80002) | `0x0b65d10FEcE517c3B6c6339CdE30fF4A8363751c` | ✅ testnet |
| SKALE Base Sepolia (324705682) | `0x4e54634d0E12f2Fa585B6523fB21C7d8AaFC881D` | ✅ testnet · zero gas |

**Roadmap:** Polygon mainnet · Conflux eSpace · SKALE Base mainnet

```
ERC-8004 Agent:    #1687 (Apex) · #1686 (AvaBuilder)
ERC-8183:          DOFEvaluator.sol → complete() / reject()
Proof hash:        keccak256(Z3 proof transcript) -- verifiable via verifyProof()
Gas cost:          $0.01/tx · SKALE chains: zero gas · Merkle batch: 10K attestations = 1 tx
```

---

## How The Pipeline Works

```
1. IDENTITY        Agent authenticates via ERC-8004 identity
                   |
2. TASK            Discovery loop finds next task (or via A2A / Telegram)
                   |
3. LLM INFERENCE   LiteLLM routes to best available provider
                   Fallback chain: Cerebras → Groq → DeepSeek → Gemini → NVIDIA
                   |
4. GOVERNANCE      ConstitutionEnforcer evaluates output
                   HARD rules: block on violation | SOFT rules: warn and log
                   ZERO LLM in this step -- purely deterministic
                   |
5. Z3 PROOF        Z3Verifier generates formal mathematical proof
                   4 invariants checked, proof hash = keccak256(proof)
                   |
6. ON-CHAIN        DOFProofRegistry writes attestation to 8 chains
                   ERC-8004 receipt with agent ID + proof hash
                   |
7. SUPERVISOR      MetaSupervisor scores: Q(0.40)+A(0.25)+C(0.20)+F(0.15)
                   Decision: ACCEPT → next cycle | RETRY → re-execute | ESCALATE → human
```

---

## Winston Experiment — Multi-Model Validation

10 frontier models evaluated with and without the Winston framework. Deterministic scorer, 0 LLMs. Externally validated on Adaline (200M+ API calls/day).

```
Model               BLUE(Winston)  RED(baseline)  Delta
────────────────────────────────────────────────────────
DeepSeek-V3           88.7          38.7         +50.0
GLM-4.5               90.0          42.7         +47.3
Mistral-Large         78.7          41.3         +37.4
Claude Sonnet         90.0          56.0         +34.0
ChatGPT-4o            88.7          63.0         +25.7
Gemini-2.5Pro         84.7          71.3         +13.4
────────────────────────────────────────────────────────
Average                                          +26.1
```

Full data: [`experiments/winston_vs_baseline/`](experiments/winston_vs_baseline/)

---

## Documentation

| Document | Description |
|:---------|:------------|
| [Getting Started](docs/05_operations/GETTING_STARTED.md) | Installation, first run, environment setup |
| [System Architecture](docs/01_architecture/SYSTEM_ARCHITECTURE.md) | Full governance pipeline with latency per layer |
| [Case Study — Apex #1687](docs/02_research/CASE_STUDY_APEX_1687.md) | 238 autonomous cycles · 0 incidents · 30+ attestations |
| [Winston Experiment](docs/02_research/EXPERIMENT_WINSTON_VS_BASELINE.md) | Raw data: +26.1% average across 10 frontier models |
| [Multichain Deployment](docs/05_operations/MULTICHAIN.md) | Deploy DOFProofRegistry to 8 chains |
| [SKALE Integration](docs/04_strategy/SKALE_INTEGRATION.md) | Zero-gas chains · x402 · BITE · IMA bridge |
| [Attestations](docs/05_operations/ATTESTATIONS.md) | On-chain proof records — publicly verifiable |
| [Full Index](docs/INDEX.md) | All public documentation |

---

## Repository Structure

```
equipo-de-agentes/
  core/                     # 142 modules -- the framework engine
    governance.py            # ConstitutionEnforcer, HARD/SOFT rules
    z3_verifier.py           # 4 theorems formally PROVEN
    z3_gate.py               # Neurosymbolic gate (APPROVED/REJECTED/TIMEOUT)
    supervisor.py            # MetaSupervisor weighted scoring
    providers.py             # LiteLLM router, TTL backoff
    autonomous_daemon.py     # 4 phases: Perceive→Decide→Execute→Evaluate
    node_mesh.py             # NodeRegistry + MessageBus + MeshDaemon
    claude_commander.py      # 5 modes: SDK, Spawn, Team, Debate, Peers
    ...
  agents/                   # agents running on DOF (validation, not the product)
  contracts/                # DOFProofRegistry.sol (deployed on 8 chains — 3 mainnet + 5 testnet)
  integrations/             # CrewAI, AgentKit, Virtuals, SKALE, Tempo
  tests/                    # 4,308 unit tests
  docs/                     # public documentation
  logs/                     # JSONL audit trails (append-only)
  experiments/              # Winston vs baseline raw data
```

---

## Built By

**@Cyber_paisa** · [Telegram](https://t.me/Cyber_paisa)

**DOF-MESH** -- The production laboratory where deterministic AI governance is built. 4,308 tests. 8 chains (3 mainnet + 5 testnet). 142 modules. Mathematics, not promises.

---

<div align="center">

**DOF-MESH -- Deterministic Observability Framework**

*Verify. Prove. Attest. · Mathematics, not promises.*

**Enigma Group · Medellín, Colombia**

[![PyPI](https://img.shields.io/badge/Install-pip_install_dof--sdk-blue?style=for-the-badge&logo=pypi)](https://pypi.org/project/dof-sdk/)
[![GitHub](https://img.shields.io/badge/GitHub-DOF--MESH-181717?style=for-the-badge&logo=github)](https://github.com/Cyberpaisa/DOF-MESH)
[![On-Chain](https://img.shields.io/badge/On--Chain_Proof-8_chains-e84142?style=for-the-badge&logo=ethereum)](https://snowtrace.io/address/0x154a3F49a9d28FeCC1f6Db7573303F4D809A26F6)

</div>
