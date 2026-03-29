<p align="center">
  <img src="docs/diagrams/dof_banner.jpeg" alt="DOF — Deterministic Observability Framework" width="700"/>
</p>

<h1 align="center">VERIFY. PROVE. ATTEST.</h1>

<p align="center">
  <strong>Deterministic Observability Framework (DOF-MESH)</strong><br/>
  Deterministic governance for multi-agent LLM systems.<br/>
  Constitutional rules · Formal Z3 proofs · On-chain attestation on Avalanche.
</p>

<p align="center">
  Python 3.11+ · Z3 SMT Solver · web3.py · BLAKE3 · Avalanche C-Chain · PostgreSQL
</p>

<p align="center">
  <img src="https://img.shields.io/badge/tests-4%2C036%20passed-brightgreen" alt="tests"/>
  <img src="https://img.shields.io/badge/modules-142-blue" alt="modules"/>
  <img src="https://img.shields.io/badge/Z3-4%20theorems%20PROVEN-critical" alt="Z3"/>
  <img src="https://img.shields.io/badge/chains-5%20(Avalanche%2C%20Base%2C%20Celo%2C%20ETH%2C%20Tempo)-gold" alt="chains"/>
  <img src="https://img.shields.io/badge/attestations-21%2B-red" alt="attestations"/>
  <img src="https://img.shields.io/pypi/v/dof-sdk" alt="PyPI"/>
  <img src="https://img.shields.io/badge/LOC-51K%2B-purple" alt="LOC"/>
  <img src="https://img.shields.io/badge/license-BSL--1.1-orange" alt="license"/>
  <a href="https://eips.ethereum.org/EIPS/eip-8183"><img src="https://img.shields.io/badge/ERC--8183-Evaluator-blue?logo=ethereum" alt="ERC-8183 Evaluator"/></a>
</p>

---

## The Problem

Autonomous AI agents are managing real money — DeFi treasuries, automated payments, enterprise decisions. When something goes wrong, you get logs the agent wrote about itself.

That's not proof. That's testimony.

**685 projects** were analyzed at the largest autonomous agent hackathon in the world (Synthesis 2026, $100K in prizes, 1,500 participants). **Zero use formal verification for governance.** Every single one trusts another LLM to watch the first LLM.

That's like hiring the thief's cousin as the security guard.

> The obvious solution is using AI to watch AI. It sounds logical — until your watchdog LLM hallucinates that everything is fine while an attacker drains your treasury with a prompt injection. An LLM can't prove anything. It can only guess.
>
> **DOF doesn't monitor. DOF proves.** Z3 — the same formal verification engine used to certify aircraft and nuclear reactors — now certifies your agents. Not statistically. Mathematically.

---

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

30ms. Zero LLM tokens. Works with CrewAI, LangGraph, AutoGen, or anything that produces text.

---

## Contents

[Highlights](#highlights) · [Architecture](#architecture) · [Z3 Verification](#z3-formal-verification) · [On-Chain](#on-chain-attestation) · [Benchmarks](#benchmark-results) · [Winston Experiment](#winston-experiment) · [Limitations](#honest-limitations) · [Citation](#citation)

---

## Highlights

- **12 governance layers** — Constitution → AST → Supervisor → Adversarial → Z3 → ZK Proofs → Sentinel → Mesh → Blockchain → Prompt Lifecycle → Continuous Eval → Tracing
- **Neurosymbolic Z3 Gate** — LLM proposes → Z3 verifies → execute or reject with counterexample
- **4 theorems PROVEN** — state transitions formally verified for ALL possible inputs (~7ms)
- **42 hierarchy patterns** — `enforce_hierarchy` verified inviolable via Z3 (5ms)
- **DOFVerifier public API** — `verify_action()` pipeline: Z3Gate → Z3Verifier → Constitution → keccak256 attestation in <10ms
- **SS(f) = 1 − f³** — Z3-verified stability formula under bounded retries
- **GCR(f) = 1.0** — governance invariant under any failure rate (Z3 proven)
- **On-chain proof hash** — keccak256 of Z3 proof transcript, verifiable via DOFProofRegistry
- **21+ on-chain attestations** on Avalanche C-Chain mainnet
- **Merkle batching** — 10,000 attestations = 1 tx ≈ $0.01
- **238 autonomous cycles** — Apex Arbitrage Agent #1687, zero incidents
- **Winston Experiment** — +26.1% average quality improvement across 10 frontier models (deterministic scorer, 0 LLMs)
- **Framework agnostic** — CrewAI, LangGraph, AutoGen, or raw Python
- **4,036 tests**, 51K+ LOC, 142 core modules, 12 governance layers

---

## Architecture

```
+----------------------------------------------------------+
| ERC-8183   DOFEvaluator.sol → complete() / reject()      |
+----------------------------------------------------------+
| L12  Tracing       Typed spans (llm/gov/z3/sentinel)     |
+----------------------------------------------------------+
| L11  Continuous Eval  5 rubrics + CI gate                |
+----------------------------------------------------------+
| L10  Prompt Lifecycle  version control + deploy pipeline |
+----------------------------------------------------------+
| L9   Blockchain    5 chains + DOFProofRegistry           |
+----------------------------------------------------------+
| L8   Mesh          11 nodes + threshold consensus (FROST)|
+----------------------------------------------------------+
| L7   Sentinel      10 parallel checks + TRACER 6D        |
+----------------------------------------------------------+
| L6   ZK Proofs     keccak256 + Merkle batch    <1ms      |
+----------------------------------------------------------+
| L5   Z3 Formal     4 theorems + Z3 Gate        ~7ms      |
+----------------------------------------------------------+
| L4   Adversarial   Red team + injection detect  <3ms     |
+----------------------------------------------------------+
| L3   Supervisor    Q(0.4)+A(0.25)+C(0.2)+F(0.15) <2ms   |
+----------------------------------------------------------+
| L2   AST Verifier  eval/exec/secrets detection  <5ms     |
+----------------------------------------------------------+
| L1   Constitution  4 HARD + 5 SOFT rules        <1ms     |
+----------------------------------------------------------+
| Engine   DAG + LoopGuard + TokenTracker                  |
+----------------------------------------------------------+
| Data Oracle   6 verification strategies         <1ms     |
+----------------------------------------------------------+

         ↕ cross-cutting (all layers)
+----------------------------------------------------------+
| LLM Router   TTL backoff + provider chains + 7+ LLMs     |
|              Thompson Sampling + circuit breaker         |
+----------------------------------------------------------+
```

Total governance latency: **<30ms** (layers 1-6). On-chain signing adds ~2s when enabled.
With Z3 cache active (default), 95% of verifications complete in <1ms.

---

## Quick Start

```bash
pip install dof-sdk==0.5.0
dof verify-states          # 4 theorems → PROVEN
dof verify-hierarchy       # 42 patterns → PROVEN
dof health --json          # full system status
```

```python
from dof import DOFVerifier

verifier = DOFVerifier()

# Approved action:
result = verifier.verify_action(
    agent_id="apex-1687",
    action="transfer",
    params={"amount": 500, "token": "USDC"}
)
print(result.verdict)       # "APPROVED"
print(result.z3_proof)      # "4/4 VERIFIED [GCR_INVARIANT:VERIFIED | SS_FORMULA:VERIFIED | ...]"
print(result.latency_ms)    # 8.2
print(result.attestation)   # "0x44b45cd026916c..."

# Rejected action (governor with insufficient trust):
result = verifier.verify_action(
    agent_id="governor-007",
    action="propose_rule",
    params={"current_level": 3},   # governor level requires score > 0.8
    trust_score=0.50
)
print(result.verdict)    # "REJECTED"
print(result.violations) # ["[Z3_GATE] SAT: counterexample found: {...}"]
```

**Z3 Gate (neurosymbolic):**

```python
from dof import Z3Gate, GateResult

gate = Z3Gate()
result = gate.validate_trust_score("agent-1687", 0.95, evidence)
# APPROVED → execute | REJECTED → blocked with counterexample | TIMEOUT → fallback
```

**On-chain proof verification:**

```python
from dof import Z3ProofAttestation

proof = Z3ProofAttestation.from_gate_verification(result, "agent-1687", 0.95)
# proof.z3_proof_hash → verifiable on Avalanche via DOFProofRegistry.verifyProof()
```

**CLI:**

```bash
python -m dof verify "your text here"     # governance check
python -m dof verify-code "code"          # AST verification
python -m dof check-facts "text"          # DataOracle fact-check
python -m dof prove                       # Z3 formal verification
python -m dof benchmark                   # adversarial benchmark
python -m dof health                      # component status
python -m dof verify-states               # Z3 state transitions (4/4 PROVEN)
python -m dof verify-hierarchy            # hierarchy enforcement (42 patterns)
python -m dof regression-baseline         # capture current state
python -m dof regression-check            # compare vs baseline (exit 1 if regressed)
python -m dof version
```

---

## Z3 Formal Verification

### Static Proofs

| Theorem | Formula | Z3 Result |
|---------|---------|-----------|
| GCR Invariant | ∀f∈[0,1]: GCR(f)=1.0 | **PROVEN** |
| SS Cubic | ∀f∈[0,1]: SS(f)=1−f³ | **PROVEN** |
| SS Monotonicity | f₁<f₂ ⟹ SS(f₁)>SS(f₂) | **PROVEN** |
| SS Boundaries | SS(0)=1.0 ∧ SS(1)=0.0 | **PROVEN** |

### Dynamic Invariants (Z3Gate)

| ID | Invariant | Status |
|----|-----------|--------|
| INV-4 | Trust score always in [0,1] | **PROVEN** |
| INV-6 | Governor requires trust > 0.8 | **PROVEN** |
| INV-3 | No hierarchy jumps without auth | **PROVEN** |
| INV-1 | Threat detected → publish blocked | **PROVEN** |

42 hierarchy patterns verified in 4.9ms. Total: ~7ms for all 4 static theorems.

```bash
dof verify-states      # 4/4 PROVEN (~7ms)
dof verify-hierarchy   # 42 patterns PROVEN (5ms)
```

---

## On-Chain Attestation

**DOFValidationRegistry** on Avalanche C-Chain (mainnet). 21+ attestations live across 5 chains.

| Chain | Contract | Purpose |
|-------|----------|---------|
| Avalanche C-Chain | `0x8004B663056A597Dffe9eCcC1965A193B7388713` | Reputation Registry |
| Avalanche C-Chain | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` | ERC-8004 Identity |
| Tempo (Stripe) | `0x94e8Ed614Cb051D9212c7610ECcbAEA58BE02f4e` | DOF Identity |
| Tempo (Stripe) | `0x432E2ab9d11544A8767559675996e34756E32790` | DOF Reputation |

Three layers: PostgreSQL (200ms) → Enigma Scanner (900ms) → Avalanche (2-3s, immutable).

**DOFProofRegistry.sol (v0.4.1)** — every attestation includes `z3_proof_hash` (keccak256), verifiable on-chain via `verifyProof()`.

$0.01/tx ($0.01 per Merkle batch of 10,000 attestations).

---

## Benchmark Results

**Latency (MacBook Pro M3 Pro, 18GB RAM, Python 3.11):**

| Operation | Latency | Notes |
|-----------|---------|-------|
| Z3Verifier — 4 theorems | **6.7ms** | First call, no cache |
| Z3Verifier — cached | **0.0ms** | Cache hit |
| Z3Gate — trust score | **0.8ms** | SMT solver |
| ConstitutionEnforcer — clean | **1.1ms** | HARD + SOFT + AST |
| ConstitutionEnforcer — override | **0.1ms** | Fail-fast on first match |
| DOFVerifier.verify_action() | **4.5ms** | Z3 proofs cached |
| Batch 5 actions | **3.7ms** (0.7ms/action) | Z3 runs once |

```bash
python3 demo_dof_capabilities.py   # reproduces all latency measurements
```

**Adversarial (internal, 400 tests):** Governance 100%, Hallucination 90%, Consistency 100% FDR, 0% FPR. Overall F1: 96.8%.

**Production (Apex #1687, n=238 cycles):** SS=0.90, GCR=1.00, PFI=0.61, zero incidents.

---

## Sentinel Engine — TRACER Scoring

| Check | Weight | Measures |
|-------|--------|----------|
| Health | 25% | Endpoint response <5s |
| Identity | 20% | Valid ERC-8004 format |
| TLS | — | SSL certificate grade |
| Latency | 10% | Response time (<200ms=100) |
| A2A | 15% | Agent-to-Agent capability |
| MCP | 10% | Exposed tools |
| x402/MPP | 5% | Payment capability |
| On-chain | — | eth_getCode via JSON-RPC |
| Ratings | 15% | Community reputation |

**TRACER:** Trust(20%) + Reliability(20%) + Autonomy(15%) + Capability(20%) + Economics(10%) + Reputation(15%)

**Classifications:** Excellent ≥80 | Good ≥65 | Acceptable ≥50 | Poor ≥35 | Unreliable <35

---

## Winston Experiment — Multi-Model Validation

10 frontier models evaluated with and without the Winston communication framework. Deterministic scorer (0 LLMs): Clarity + Relevance + Structure + Surprise + Actionable close.

**Externally validated on Adaline** — 67 independent traces across 3 sessions (March 28-29, 2026). Adaline is a professional AI monitoring platform (200M+ API calls/day, 5B tokens/day, 99.998% uptime) with no connection to Enigma Group.

<p align="center">
  <img src="experiments/winston_vs_baseline/adaline_monitor_dashboard_24h.png" alt="Adaline Monitor — DOF Winston Experiment · 24h dashboard" width="700"/>
  <br/><em>Adaline monitor dashboard — 19 live runs · P95 latency 25s · cost $0.0004/run · March 28, 2026</em>
</p>

<p align="center">
  <img src="experiments/winston_vs_baseline/adaline_prompt_setup_gemini_20260328.png" alt="Adaline — DOF Mesh Legion prompt with gemini-2.0-flash" width="700"/>
  <br/><em>DOF Mesh Legion prompt configured on Adaline with gemini-2.0-flash · Winston + Governance rules active</em>
</p>

```
Model               BLUE(Winston)  RED(baseline)  Delta
────────────────────────────────────────────────────────
DeepSeek-V3           88.7          38.7         +50.0
GLM-4.5               90.0          42.7         +47.3
Mistral-Large         78.7          41.3         +37.4
Claude Sonnet         90.0          56.0         +34.0
ChatGPT-4o            88.7          63.0         +25.7
Gemini-2.5Pro         84.7          71.3         +13.4
Perplexity-Sonar      82.0          70.0         +12.0
MiniMax-M2            76.0          66.7          +9.3
Kimi-K2               64.0          58.0          +6.0
────────────────────────────────────────────────────────
Average                                          +26.1
```

Full data: [`experiments/winston_vs_baseline/`](experiments/winston_vs_baseline/)

---

## Case Study — Apex Arbitrage Agent #1687

238 autonomous cycles. 0 incidents. 21 verifiable on-chain attestations.

The agent operates with real USDC on Avalanche C-Chain. Every action passes through `DOFVerifier.verify_action()` before execution. Every decision is keccak256-hashed and recorded on-chain — verifiable by any third party without trusting Enigma Group.

**→ [Full case study](docs/02_research/CASE_STUDY_APEX_1687.md)**

---

## Distributed Scaling Modules (v0.5.1)

Implemented after the Winston Experiment — 10 frontier models independently converged on this architecture:

| Module | Impact |
|--------|--------|
| **Z3 Proof Caching** | SMT memoization: identical constraints not re-solved (−40% latency) |
| **Z3 Portfolio Solving** | Multiple Z3 strategies in parallel, short-circuit on first result |
| **Z3 Fast Path** | Already-verified policies served without Z3 (~70% of queries) |
| **Adaptive Circuit Breaker** | Quarantine agents with >15% block rate (60s window) |
| **Byzantine Node Guard** | Per-node reputation 0.0–1.0, auto-quarantine <0.3 |
| **Constitution Hash Beacon** | Canonical hash broadcast every N blocks, auto-HALT if diverged |
| **Merkle Attestation Batching** | N decisions → 1 Merkle root on-chain (−70% gas) |
| **CRDT Memory Layer** | GCounter + LWW-Register: consensus-free synchronization |
| **Context Epoch System** | Stale-epoch nodes reject queries until synchronized |

> **Validation:** These architectures were proposed independently by 7–10 frontier models without coordination. When 10 minds reach the same design separately, the design is probably correct.

---

## Integrations

Your agents already live in CrewAI, LangGraph, or AgentKit. Rewiring them for governance is months of work nobody does — which is why most agents run unverified.

DOF integrates in **one line**. No rewrites. No new infrastructure. The agent keeps running exactly as before — now with a Z3 formal proof on every action.

| Integration | Install | What it does |
|---|---|---|
| **CrewAI** | `from integrations.dof_crewai import dof_verify` | `@dof_verify` decorator + `DOFCrewAI` wrapper + `DOFCallback` |
| **Coinbase AgentKit** | `from integrations.dof_agentkit import DOFAgentKit` | `DOFWalletGuard` — blocks payments Z3 doesn't approve |
| **Alchemy** | `from integrations.dof_alchemy import AlchemyDOF` | Reliable RPC + webhooks + gas estimation on Base/Avalanche |
| **Virtuals Protocol** | `from integrations.dof_virtuals import VirtualsDOF` | Trust score (0–100) + badge for tokenized agents on Base |
| **Tempo (Stripe L1)** | `from integrations.dof_tempo import TempoDOF` | Z3-verified pathUSD payments before any transfer executes |
| **LangGraph** | `from integrations.langgraph_adapter import DOFGovernanceNode` | Governance node for LangGraph state machines |

```python
# CrewAI — one decorator
from integrations.dof_crewai import dof_verify

@dof_verify(agent_id="my-agent", action="research")
def run_research(task: str) -> str:
    ...

# Tempo — verify before spending pathUSD
from integrations.dof_tempo import TempoDOF

dof = TempoDOF(chain="testnet")
result = dof.verify_payment("apex-1687", "0xRecipient...", amount=100.0)
# → verdict: "APPROVED" | "REJECTED"
# → z3_proof: formal proof
# → attestation: keccak256 hash on Tempo chain

# Virtuals — trust score for tokenized agents
from integrations.dof_virtuals import VirtualsDOF

dof = VirtualsDOF(agent_token_address="0x...")
score = dof.get_trust_score()
print(score.badge)   # "🛡️ DOF VERIFIED" | "⚠️ DOF PARTIAL" | "❌ DOF UNVERIFIED"
```

---

## Key Exports

`DOFVerifier` · `VerifyResult` · `verify` · `classify_error` · `register` · `run_crew` · `MerkleBatcher` · `AdversarialEvaluator` · `RedTeamAgent` · `ConstitutionEnforcer` · `Z3Gate` · `GateResult` · `TransitionVerifier` · `DOFAgentState` · `Z3ProofAttestation` · `ProofSerializer` · `ProofStorage` · `RegressionTracker` · `EntropyDetector`

---

## The Synthesis Hackathon — External Validation

**Winner — Privacy & x402 categories** · The Synthesis 2026 · $100K in prizes · 1,500 participants

The Synthesis was organized around the x402 + ERC-8004 stack — the exact ecosystem where DOF operates. Governance protocols for agent payments need formal verification because they handle real value.

Winning in Privacy & x402 was not coincidental. The judges recognized that **DOF fills the gap ERC-8004 and x402 leave open**:

| Layer | Protocol | Solves |
|---|---|---|
| Identity | ERC-8004 | Who is the agent? |
| Payments | x402 | How does the agent pay? |
| Communication | A2A | How do agents coordinate? |
| Models | MCP | How does it access tools? |
| **Governance** | **DOF** | **Did the agent act correctly?** |

ERC-8004 defines *where* to store reputation. It doesn't define *how to prove the agent deserves it*. DOF generates that proof.

---

## Evolution — Three Layers, One Argument

DOF is not one project. It's an evolving argument built in three visible iterations:

```
DOF v1 (main branch)          →  The Scientific Thesis
  4 commits · 9 core modules     Formal metrics: SS, PFI, RP, GCR, SSR
  SS(f) = 1 − f³ (Z3 proven)    Real problem: LLM agents on free-tier providers
  GCR(f) = 1.0 ∀f∈[0,1]        52 documented production runs
  Published on DEV.to            Irrefutable proof: constitutional governance is invariant

Hackathon branch               →  Competitive Validation
  The Synthesis 2026             Won: Privacy & x402 categories
  x402 + ERC-8004 ecosystem      Judges confirmed: DOF fills the gap the stack leaves open
  Demo-grade subset              External signal that the hypothesis is correct

DOF-MESH (this repo)           →  Experimental Platform
  340+ commits · 142 modules     12 governance layers · 4,036 tests
  5 chains mainnet               29 mesh nodes · SDK on PyPI
  Active evolution               The laboratory where production DOF is born
```

The v1 repo is the scientific paper — keep it stable. The hackathon branch is the competitive credential. DOF-MESH is the production laboratory.

---

## Who DOF Is For

**AI startup CTO:**
> Your autonomous agent can hallucinate, be manipulated by prompt injection, or simply do the wrong thing — with no way to prove it afterward. DOF adds a layer of mathematical verification before each decision. If Z3 passes: it executes. If not: blocked, with a cryptographic proof of why. `pip install dof-sdk` — in production in 24 hours.

**Developer building on ERC-8004/x402:**
> ERC-8004 solves your agent's identity. x402 solves how it pays. DOF solves the problem neither addresses: can I mathematically prove my agent acted correctly? Without DOF, your agent has identity and can pay — but can't prove it behaved.

**Hackathon judge / VC:**
> The AI governance market is $1.8B today → $12.4B in 2028. Every existing player does probabilistic monitoring. DOF is the only one with formal verification + on-chain proof. Winner at The Synthesis (Privacy & x402). 4,036 tests. 5 chains. New market category with real technical moat.

**Regulator / auditor:**
> When regulation requires AI agents to be auditable (EU AI Act, SEC AI disclosure), the question will be: *"Can you prove what your agent decided?"* With DOF: yes. The keccak256 hash of every decision lives on Avalanche C-Chain. Immutable. Third-party verifiable. Independent of the provider.

---

## Honest Limitations

- Hallucination detection is regex-based — 90% FDR, misses semantic hallucinations
- SS(f)=1−f³ assumes independent failures — no correlated failure modeling
- Supervisor contains an LLM — circularity bounded, not eliminated
- `<30ms` claim applies to first call with Z3; cached calls <1ms; complex constraints may exceed 30ms
- 21 on-chain attestations are from internal agents (Apex #1687, AvaBuilder #1686) — no external client case yet

---

## Documentation

> **123 documents** organized in 9 categories. Full index: [docs/INDEX.md](docs/INDEX.md)

### Architecture

| Document | Description |
|---|---|
| [System Architecture](docs/01_architecture/SYSTEM_ARCHITECTURE.md) | 12-layer governance pipeline with latency per layer |
| [Architectural Redesign v1](docs/01_architecture/ARCHITECTURAL_REDESIGN_v1.md) | Design decisions and module conventions — read before coding |
| [Determinism Checklist](docs/01_architecture/DETERMINISM_CHECKLIST.md) | Verification checklist for zero-LLM governance |
| [Mesh Scaling Guide](docs/01_architecture/MESH_SCALING_GUIDE.md) | Distributed mesh node configuration |

### Research & Experiments

| Document | Description |
|---|---|
| [Case Study — Apex #1687](docs/02_research/CASE_STUDY_APEX_1687.md) | **238 autonomous cycles · 0 incidents · 21 on-chain attestations** |
| [Winston Experiment](docs/02_research/EXPERIMENT_WINSTON_VS_BASELINE.md) | Raw data: +26.1% average across 10 frontier models |
| [Multi-Model Mesh Paper](docs/02_research/PAPER_MULTI_MODEL_MESH.md) | Academic paper draft |
| [Degradation Curves](docs/02_research/BLOG_DEGRADATION_CURVES.md) | How agent quality degrades without governance |

### Operations & Setup

| Document | Description |
|---|---|
| [Getting Started](docs/05_operations/GETTING_STARTED.md) | Installation, first run, environment setup |
| [Free Providers Guide](docs/05_operations/FREE_PROVIDERS_GUIDE.md) | Run DOF-MESH at $0/month with free LLM tiers |
| [MCP Setup](docs/05_operations/MCP_SETUP.md) | Model Context Protocol server configuration |
| [Attestations](docs/05_operations/ATTESTATIONS.md) | All 21+ on-chain attestation records |
| [Multichain Deployment](docs/05_operations/MULTICHAIN.md) | Deploy to Avalanche, Base, Celo, ETH, Tempo |
| [Tempo Deploy Guide](docs/07_integrations/TEMPO_DEPLOY_GUIDE.md) | Step-by-step deploy on Stripe's L1 |

### Strategy & Competitive

| Document | Description |
|---|---|
| [Competition Bible](docs/04_strategy/COMPETITION_BIBLE.md) | 685 projects analyzed — DOF's unique position |
| [Monetization Strategy](docs/04_strategy/DOF_MONETIZATION_STRATEGY.md) | Pricing tiers, ICP, revenue model |
| [Phase 2 Execution Plan](docs/04_strategy/DOF_PHASE2_EXECUTION_PLAN.md) | Roadmap: integrations → distribution → SaaS |

### Security

| Document | Description |
|---|---|
| [Security Report](docs/06_security/SECURITY_REPORT_2026-03-27.md) | Full security audit — March 2026 |
| [Mesh Security Hardening](docs/06_security/SECURITY_MESH_HARDENING.md) | Node security, key management, threat model |

### Logs & Runtime Outputs

```
logs/
├── traces/          # RunTrace JSON — one file per execution
├── experiments/     # runs.jsonl — aggregated metrics per run
├── metrics/         # Agent steps, governance decisions, supervisor scores
├── checkpoints/     # JSONL per step — crash recovery
├── commander/       # commands.jsonl, sessions.json, queue/*.json
├── daemon/          # cycles.jsonl — autonomous daemon cycles
└── mesh/            # nodes.json, messages.jsonl, inbox/<node>/*.json

output/              # Crew task results (plain text + JSON)
experiments/         # Raw experiment data (winston_vs_baseline/, etc.)
docs/evidence/       # Documented learnings, test results, session snapshots
```

All logs are append-only JSONL. No external observability dependencies.

---

## Contributing

DOF-MESH enforces mandatory double-review before every commit:

1. `git diff --cached` — verify NO secrets, private keys, or API tokens
2. Run `python3 -m unittest discover -s tests` — all must pass
3. If touching prompts: CI gate evaluates automatically

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

---

## Citation

```bibtex
@article{cyberpaisa2026deterministic,
  title={Deterministic Observability and Resilience Engineering for
         Multi-Agent LLM Systems: An Experimental Framework
         with Formal Verification},
  author={Cyber Paisa and Enigma Group},
  year={2026},
  note={51K+ LOC, 4036 tests, 142 modules, 4 Z3 theorems PROVEN,
        42 hierarchy patterns, 21+ Avalanche attestations,
        neurosymbolic Z3 Gate, on-chain proof hash,
        BSL 1.1, pip install dof-sdk}
}
```

---

## License

This project is licensed under the **Business Source License 1.1**. Free for non-commercial use, research, and personal projects. Commercial use requires a separate agreement.

On **2028-03-08** this project converts to **Apache License 2.0**.

Contact: [@Cyber_paisa](https://t.me/Cyber_paisa) on Telegram.

---

<p align="center">
  <strong>Before reading this, the only way to know if your agent behaved correctly was to trust logs the agent wrote about itself.</strong><br/><br/>
  Now you have an alternative: mathematical proof, immutable, verifiable by any third party.<br/><br/>
  <code>pip install dof-sdk</code> · 30 seconds · First verification free.<br/><br/>
  The next time someone asks <em>"how do you know your agent did the right thing?"</em><br/>
  you'll have an answer no other team in the world can give.<br/><br/>
  <em>Mathematics, not promises.</em><br/><br/>
  Cyber Paisa — Enigma Group — Medellín, Colombia<br/>
  BSL-1.1 · <a href="LICENSE">License</a> · <a href="https://pypi.org/project/dof-sdk/">PyPI</a> · <a href="https://snowtrace.io/address/0x8004B663056A597Dffe9eCcC1965A193B7388713">Snowtrace</a> · <a href="https://t.me/Cyber_paisa">@Cyber_paisa</a>
</p>
