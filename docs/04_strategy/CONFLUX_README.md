# DOF-MESH x Conflux — Global Hackfest 2026

**Deterministic Governance + Formal Proofs + On-Chain Attestation on Conflux**

---

## What DOF-MESH Does

DOF-MESH is a governance framework for autonomous AI agents. Before an agent executes any action, DOF-MESH mathematically verifies its compliance — without trusting another LLM to do the check.

Most frameworks verify what happened. DOF-MESH verifies what is about to happen.

```
Agent Output → Constitution → Z3 Formal Proof → TRACER Score → Proof Hash → Conflux TX
```

---

## Live on Conflux Testnet

**DOFProofRegistry** — deployed and operational:

| Field | Value |
|---|---|
| Contract | `0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83` |
| Chain | Conflux eSpace Testnet (chain ID 71) |
| Proofs registered | 36+ |
| Explorer | https://evmtestnet.confluxscan.io/address/0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83 |

---

## The 6-Step Governance Cycle

Run it yourself:

```bash
git clone https://github.com/Cyberpaisa/deterministic-observability-framework
cd deterministic-observability-framework
pip install -r requirements.txt
python3 scripts/conflux_demo.py --dry-run
```

**What each step does:**

| Step | Component | What it proves |
|---|---|---|
| 1 | **Constitution** | HARD/SOFT rules — zero LLM, pure deterministic logic |
| 2 | **Z3 Verifier** | 4 formal theorems PROVEN: GCR_INVARIANT, SS_FORMULA, SS_MONOTONICITY, SS_BOUNDARIES |
| 3 | **TRACER Score** | Multi-dimensional quality score (Quality, Accuracy, Compliance, Format) |
| 4 | **Proof Hash** | keccak256 of the full governance payload — immutable fingerprint |
| 5 | **Conflux Attestation** | Proof hash published on-chain via DOFProofRegistry |
| 6 | **Summary** | Explorer link + full audit trail |

---

## Conflux Integration

### ConfluxGateway (`core/adapters/conflux_gateway.py`)

- Connects to Conflux eSpace Testnet RPC
- Handles Gas Sponsorship via `SponsorWhitelistControl` (internal contract `0x0888...0001`)
- dry_run mode for testing without a wallet
- Compatible with web3.py v7.x (`ExtraDataToPOAMiddleware`)

### DOFChainAdapter

```python
from core.chain_adapter import DOFChainAdapter

# One line to connect to Conflux
adapter = DOFChainAdapter.from_chain_name("conflux_testnet", dry_run=True)

# Publish a governance proof on-chain
result = adapter.publish_attestation(
    proof_hash="0x...",
    agent_id=1687,
    metadata="dof-v0.6.0 z3=4/4 tracer=0.91"
)
# → {"tx_hash": "0x...", "chain": "conflux_testnet"}
```

---

## Verified Numbers

| Metric | Value | How to verify |
|---|---|---|
| Autonomous cycles | 238+ | `logs/daemon/cycles.jsonl` |
| Z3 theorems PROVEN | 4/4 | `python3 -m dof verify-states` |
| On-chain proofs (Conflux) | 36+ | ConfluxScan explorer |
| On-chain proofs (all chains) | 80+ | 8 chains total |
| Tests passing | 4,308 | `python3 -m unittest discover -s tests` |
| Zero LLM in governance path | ✅ | `grep -r "llm_call" core/governance.py` → 0 matches |

---

## Test the Conflux Integration

```bash
python3 -m unittest tests.test_conflux_gateway tests.test_conflux_integration -v
# → 9/9 tests OK
```

---

## Why Conflux

Conflux eSpace is the right chain for verifiable AI governance:

1. **Gas Sponsorship** — agents can register proofs without holding CFX. The `SponsorWhitelistControl` internal contract lets DOF sponsor proof registration for whitelisted agents. This is native to Conflux, not a wrapper.

2. **EVM compatible** — DOFProofRegistry.sol deploys as-is. No changes needed.

3. **Fast finality** — governance proofs need to be on-chain before the agent acts, not minutes later.

4. **Traceable** — every attestation is indexed and verifiable on ConfluxScan.

---

## Architecture

```
DOF-MESH v0.6.0
├── 7-layer governance (Constitution → AST → Tool Hook → Supervisor → Adversarial → Memory → Z3)
├── Z3 SMT formal verification — 4/4 invariants PROVEN
├── 8 active chains — Avalanche, Base, Celo, Conflux, Polygon, SKALE, Fuji, Base Sepolia
├── 238+ autonomous cycles logged
├── ConfluxGateway with Gas Sponsorship support
└── DOFProofRegistry.sol — identical contract on all 8 chains
```

---

## Contact

**Cyber Paisa** — Enigma Group, Medellín  
GitHub: [Cyberpaisa/deterministic-observability-framework](https://github.com/Cyberpaisa/deterministic-observability-framework)  
Docs: [dofmesh.com](https://dofmesh.com)

> "Agent acted autonomously. Math proved it. Blockchain recorded it. On Conflux."
