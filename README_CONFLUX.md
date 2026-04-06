# DOF-MESH × Conflux — Global Hackfest 2026

<div align="center">

![Tests](https://img.shields.io/badge/tests-4%2C308%20passing-brightgreen)
![Z3](https://img.shields.io/badge/Z3%20proofs-4%2F4%20PROVEN-blue)
![Chains](https://img.shields.io/badge/chains-8%20active-purple)
![Conflux](https://img.shields.io/badge/Conflux%20Testnet-live-orange)
![License](https://img.shields.io/badge/license-BSL--1.1-lightgrey)

**Deterministic governance for autonomous AI agents — provably correct, on-chain verified.**

[Live Contract](#live-on-conflux) · [Quick Start](#quick-start) · [Architecture](#architecture) · [Verify It Yourself](#verify-it-yourself)

</div>

---

## The Problem

Autonomous AI agents act on behalf of users — executing transactions, calling APIs, making financial decisions. The current answer to "did this agent behave correctly?" is: *trust us*.

That is not an answer.

Rules encoded as prompts can be overridden. LLM-based validators hallucinate. Audit logs can be altered. There is no cryptographic proof that an agent followed its governance contract before it acted.

## The Solution

DOF-MESH verifies agent compliance **before execution** using three independent layers — none of which uses an LLM for the decision:

```
Agent Output
     │
     ▼
┌─────────────────────────────────────────────────────┐
│  Layer 1 — Constitution                             │
│  Deterministic HARD/SOFT rules (regex + AST)        │
│  HARD rules block. SOFT rules warn. Zero LLM.       │
└──────────────────────┬──────────────────────────────┘
                       │ PASSED
                       ▼
┌─────────────────────────────────────────────────────┐
│  Layer 2 — Z3 SMT Formal Verification               │
│  4 theorems mathematically PROVEN:                  │
│  GCR_INVARIANT · SS_FORMULA · SS_MONOTONICITY       │
│  SS_BOUNDARIES                                      │
│  Not "probably correct." PROVEN.                    │
└──────────────────────┬──────────────────────────────┘
                       │ PROVEN
                       ▼
┌─────────────────────────────────────────────────────┐
│  Layer 3 — TRACER Score                             │
│  Multi-dimensional quality: Quality · Accuracy      │
│  Compliance · Format · Communication                │
└──────────────────────┬──────────────────────────────┘
                       │ SCORED
                       ▼
┌─────────────────────────────────────────────────────┐
│  Proof Hash (keccak256 of full payload)             │
│  → Published on-chain via DOFProofRegistry          │
│  → Conflux eSpace Testnet (chain ID 71)             │
└─────────────────────────────────────────────────────┘
```

The result: a tamper-proof, on-chain record that a specific agent output passed formal governance verification — before any action was taken.

---

## Live on Conflux

**DOFProofRegistry** — deployed and verified:

| | |
|---|---|
| **Contract** | [`0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83`](https://evmtestnet.confluxscan.io/address/0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83) |
| **Chain** | Conflux eSpace Testnet — Chain ID 71 |
| **Proofs registered** | 38+ |
| **Wallet** | `0xEAFdc9C3019fC80620f16c30313E3B663248A655` |

### Verified transactions

| Date | TX Hash | What it proves |
|---|---|---|
| Apr 6, 2026 | [`bf98ea58...bebf740c`](https://evmtestnet.confluxscan.io/tx/bf98ea58265dcd8433f594376d0d679fde65d93ae8cc18d841627308bebf740c) | Full 6-step governance cycle — Agent #1687 |
| Apr 6, 2026 | [`77d4ddea...b12465e5`](https://evmtestnet.confluxscan.io/tx/77d4ddea0043bf6df5a916cd7040886e0a97480ab12465e5842ce7c2f26b4b10) | Direct attestation test |

Every TX contains a `proof_hash` — the keccak256 fingerprint of the complete governance payload (agent ID, Z3 results, TRACER score, timestamp). Immutable. Auditable. Independent of DOF-MESH infrastructure.

---

## Quick Start

```bash
git clone https://github.com/Cyberpaisa/DOF-MESH
cd DOF-MESH
pip install -r requirements.txt

# Run the full 6-step governance cycle (dry-run, no wallet needed)
python3 scripts/conflux_demo.py --dry-run

# Run with real on-chain attestation (requires CONFLUX_PRIVATE_KEY in .env)
python3 scripts/conflux_demo.py

# Run the Conflux test suite
python3 -m unittest tests.test_conflux_gateway tests.test_conflux_integration -v
```

**Expected output:**
```
Constitution:     ✅ PASSED  (score=1.0000)
Z3 Verification:  ✅ 4/4 PROVEN  (44ms)
TRACER Score:     ✅ 0.504/1.0
Proof Hash:       0x...
Attestation:      CONFIRMED
TX Hash:          bf98ea58...
Verify at:        https://evmtestnet.confluxscan.io/tx/...
```

---

## Conflux Integration

### Why Conflux — not just "EVM compatible"

Conflux eSpace has a native feature that matters specifically for AI governance: **Gas Sponsorship**.

Autonomous agents should not need to hold gas tokens to register compliance proofs. With Conflux's `SponsorWhitelistControl` internal contract at `0x0888000000000000000000000000000000000001`, DOF-MESH can sponsor proof registration for whitelisted agents — meaning an agent operating under DOF governance pays zero gas to record its compliance attestation.

This is not a workaround. It is native to the protocol.

### ConfluxGateway

`core/adapters/conflux_gateway.py` — purpose-built for Conflux eSpace:

```python
from core.adapters.conflux_gateway import ConfluxGateway

# Connect — testnet
gw = ConfluxGateway(use_testnet=True, dry_run=False)
print(gw.w3.eth.chain_id)  # 71

# Access Gas Sponsorship
sponsor = gw.get_sponsor_contract()
# → SponsorWhitelistControl at 0x0888...0001

# The DOFProofRegistry address
print(ConfluxGateway.PROOF_REGISTRY_TESTNET)
# → 0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83
```

### Chain Adapter

```python
from core.chain_adapter import DOFChainAdapter

# One-line connection to Conflux
adapter = DOFChainAdapter.from_chain_name("conflux_testnet")

# Publish a governance proof on-chain
result = adapter.publish_attestation(
    proof_hash="0x...",       # keccak256 of governance payload
    agent_id=1687,            # ERC-8004 agent token ID
    metadata="dof-v0.6.0 z3=4/4 tracer=0.504"
)
# → {"tx_hash": "0x...", "chain_id": 71, "gas_used": 373421}
```

---

## Architecture

DOF-MESH has 7 governance layers. The Conflux integration sits at layer 7 — the output of the full stack:

```
Interfaces  ──  CLI · A2A Server (port 8000) · Telegram · Dashboard
                              │
                    ┌─────────┴─────────┐
                    │   7-Layer Stack   │
                    │                  │
                    │  1. Constitution  │  ← HARD/SOFT rules, zero LLM
                    │  2. AST Validator │  ← static analysis of generated code
                    │  3. Tool Hook PRE │  ← intercepts before tool execution
                    │  4. Supervisor    │  ← behavioral monitoring across turns
                    │  5. Adversarial   │  ← red/blue pipeline vs injections
                    │  6. Memory Layer  │  ← reproducible session state
                    │  7. Z3 Verifier   │  ← 4/4 invariants PROVEN
                    └─────────┬─────────┘
                              │
                    ┌─────────┴─────────┐
                    │   Proof Builder   │
                    │  keccak256 hash   │
                    │  of full payload  │
                    └─────────┬─────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         Conflux          Avalanche         Base
         Testnet          C-Chain          Mainnet
         chain 71         chain 43114      chain 8453
```

**DOFProofRegistry.sol** — identical contract deployed on all 8 chains:

```solidity
struct ProofRecord {
    bytes32 proofHash;    // governance payload fingerprint
    uint256 agentId;      // ERC-8004 token ID
    uint256 timestamp;    // block timestamp
    string  metadata;     // version + scores (human readable)
}

function registerProof(bytes32 proofHash, uint256 agentId, string calldata metadata) external;
function verifyProof(bytes32 proofHash) external view returns (bool);
function getProof(bytes32 proofHash) external view returns (ProofRecord memory);
function getProofCount() external view returns (uint256);
```

---

## The Formal Proofs

Z3 is an SMT solver from Microsoft Research. DOF-MESH uses it to mathematically prove four invariants hold for every governance state:

| Theorem | What it proves |
|---|---|
| `GCR_INVARIANT` | Governance Compliance Rate is always exactly 1.0 when all rules pass |
| `SS_FORMULA` | Supervisor Score formula is correctly bounded given its inputs |
| `SS_MONOTONICITY` | Higher-quality outputs always produce higher scores (monotonic) |
| `SS_BOUNDARIES` | Score is always in [0.0, 1.0] — no overflow, no negative |

These are not unit tests. They are mathematical proofs that hold for **all possible inputs**, not just the ones you tested.

```bash
python3 -m dof verify-states
# GCR_INVARIANT:   VERIFIED  (25ms)
# SS_FORMULA:      VERIFIED   (2ms)
# SS_MONOTONICITY: VERIFIED   (9ms)
# SS_BOUNDARIES:   VERIFIED   (1ms)
# Result: 4/4 PROVEN
```

---

## Verify It Yourself

Everything claimed here is independently verifiable:

**On-chain** — no DOF-MESH software required:
```bash
# Read proof count from DOFProofRegistry (Conflux Testnet)
cast call 0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83 \
  "getProofCount()(uint256)" \
  --rpc-url https://evmtestnet.confluxrpc.com

# Verify a specific proof hash exists
cast call 0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83 \
  "verifyProof(bytes32)(bool)" \
  0xb8677b595b7b71f75800000000000000000000000000000000000010a9235d00 \
  --rpc-url https://evmtestnet.confluxrpc.com
```

**Locally** — clone and run:
```bash
# All tests
python3 -m unittest discover -s tests        # 4,308 tests, 0 failures

# Z3 proofs
python3 -m dof verify-states                 # 4/4 PROVEN

# Conflux-specific
python3 -m unittest tests.test_conflux_gateway tests.test_conflux_integration -v

# Full demo with real TX
python3 scripts/conflux_demo.py              # requires CONFLUX_PRIVATE_KEY in .env
```

---

## Metrics

Real numbers, independently verifiable:

| Metric | Value |
|---|---|
| Autonomous agent cycles completed | 238+ |
| Z3 formal theorems proven | 4/4 |
| On-chain attestations (Conflux testnet) | 38+ |
| On-chain attestations (all chains) | 80+ |
| Active chains | 8 (3 mainnet + 5 testnet) |
| Tests passing | 4,308 |
| LLM calls in governance path | 0 |
| Governance decision time (Z3) | ~44ms avg |
| Code base | 57K+ LOC, 142 modules |

---

## Project Structure

```
DOF-MESH/
├── core/
│   ├── adapters/
│   │   └── conflux_gateway.py     ← Conflux eSpace connection + Gas Sponsorship
│   ├── governance.py              ← Constitution: HARD/SOFT rules
│   ├── z3_verifier.py             ← Z3 SMT formal verification
│   ├── supervisor.py              ← TRACER scoring
│   ├── chain_adapter.py           ← Multi-chain attestation publisher
│   └── chains_config.json         ← Chain registry (incl. Conflux testnet)
├── scripts/
│   └── conflux_demo.py            ← 6-step demo script
├── tests/
│   ├── test_conflux_gateway.py    ← 5 gateway tests
│   └── test_conflux_integration.py ← 4 integration tests (incl. full cycle)
├── contracts/
│   └── DOFProofRegistry.sol       ← On-chain proof registry
└── docs/
    └── 04_strategy/
        └── CONFLUX_README.md      ← Judges reference doc
```

---

## Autonomous Agent Demo

The demo registers a governance proof for Agent #1687 — a real autonomous agent that has completed 238+ cycles under DOF-MESH supervision:

```
Agent: DOF-1687
Task:  Evaluate governance compliance before executing DeFi transaction on Conflux

Step 1 — Constitution:     4/4 rules PASSED (score 1.0000)
Step 2 — Z3 Verification:  4/4 theorems PROVEN in 44ms
Step 3 — TRACER Score:     0.504/1.0
Step 4 — Proof Hash:       0xb8677b595b7b71f758... (keccak256 of full payload)
Step 5 — Conflux TX:       CONFIRMED — bf98ea58...bebf740c
Step 6 — Verifiable at:    https://evmtestnet.confluxscan.io/tx/bf98ea58...
```

**The agent acted. The math proved it. The blockchain recorded it. On Conflux.**

---

## Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Agent framework | CrewAI |
| Formal verification | Z3 SMT Solver (Microsoft Research) |
| Blockchain | Conflux eSpace (chain 71) + 7 other EVM chains |
| Smart contracts | Solidity (DOFProofRegistry.sol) |
| Web3 | web3.py v7.x |
| Gas Sponsorship | Conflux SponsorWhitelistControl |
| Agent identity | ERC-8004 (Autonomous Agent Identity Standard) |
| Docs | [dofmesh.com](https://dofmesh.com) |

---

## License

Smart contracts: BSL-1.1  
Documentation: CC0

---

<div align="center">

*Built by [Cyber Paisa](https://github.com/Cyberpaisa) — Enigma Group, Medellín*

**"Correctness is provable, not promisable."**

</div>
