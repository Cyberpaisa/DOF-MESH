# DOF-MESH — Conflux Ecosystem Grant Proposal

**Project:** DOF-MESH — Deterministic Governance for Autonomous AI Agents  
**Applicant:** Juan Carlos Quiceno (Cyber Paisa) — Medellín, Colombia  
**GitHub:** github.com/Cyberpaisa/DOF-MESH  
**Docs:** dofmesh.com  
**Submitted:** April 2026 — Conflux Global Hackfest 2026  

---

## Executive Summary

DOF-MESH is the first framework that mathematically proves autonomous AI agents behaved correctly — before they act. It combines Z3 SMT formal verification, deterministic governance (zero LLM in the decision path), and on-chain attestation to produce tamper-proof compliance records on Conflux.

Conflux's native **Gas Sponsorship** (`SponsorWhitelistControl`) is what makes DOF-MESH viable at production scale: agents register compliance proofs at zero gas cost, removing the operational burden of gas management from autonomous agent fleets.

We are requesting a grant to accelerate the Conflux-specific roadmap: eSpace mainnet deployment, Core Space transaction integration, and cross-space proof synchronization.

---

## Problem Statement

Autonomous AI agents are acting with increasing autonomy — executing financial transactions, managing DAO treasuries, calling external APIs. The current answer to "did this agent behave correctly?" is: *trust us*.

Existing approaches fail:
- **Prompt-based rules** can be overridden at inference time
- **LLM-based validators** hallucinate — a validator that can lie cannot validate
- **Audit logs** can be altered after the fact
- **No cryptographic proof** exists that an agent followed its governance contract before acting

The result: billions of dollars in autonomous agent activity with no verifiable compliance record. This is a critical gap as AI agents expand into DeFi, treasury management, and cross-chain operations.

---

## Solution

DOF-MESH verifies agent compliance before execution using three deterministic layers:

1. **Constitution** — HARD/SOFT rules (regex + AST). Zero LLM. Blocks violations deterministically.
2. **Z3 SMT Verification** — Microsoft Research SMT solver. 4 theorems proven for ALL possible inputs (not just tested cases).
3. **TRACER Score** — 5-dimensional quality scoring across Quality, Accuracy, Compliance, Format, Communication.

Output: a keccak256 proof hash published on-chain to Conflux DOFProofRegistry. Permanent. Tamper-proof. Independent of DOF-MESH infrastructure.

---

## Why Conflux

Conflux has one native feature that no other EVM chain has: **Gas Sponsorship**.

For autonomous agent infrastructure, this is architecturally critical. An agent registering compliance proofs every cycle cannot be expected to hold CFX or manage gas. With Conflux's `SponsorWhitelistControl` (deployed at `0x0888000000000000000000000000000000000001`), the protocol operator sponsors gas and agents operate friction-free.

Additionally:
- **Tree-Graph consensus** provides higher throughput for high-frequency attestation workloads
- **eSpace + Core Space** dual architecture allows governance proofs at EVM layer with future Core Space native throughput
- **Conflux ecosystem** is growing in DeFi and AI — DOF-MESH is positioned as the governance infrastructure layer

---

## Traction (Verified, On-Chain)

| Metric | Value | Verification |
|--------|-------|-------------|
| On-chain proofs — Conflux Testnet | 100+ | [ConfluxScan](https://evmtestnet.confluxscan.io/address/0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83) |
| On-chain proofs — All chains | 80+ | 8 chains active |
| Z3 formal theorems proven | 4/4 | `python3 -m dof verify-states` |
| Autonomous agent cycles | 238+ | logs/daemon/cycles.jsonl |
| Tests passing | 4,308 | CI: GitHub Actions |
| LLM calls in governance path | 0 | Deterministic only |
| SDK on PyPI | dof-sdk v0.6.0 | pip install dof-sdk |
| Docs live | 23 pages | dofmesh.com |

---

## Conflux-Specific Work Completed

### DOFProofRegistry (Conflux eSpace Testnet)
- Contract: `0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83`
- Chain ID: 71 (eSpace Testnet)
- 100+ proofs registered

### ConfluxGateway (`core/adapters/conflux_gateway.py`)
- Native Gas Sponsorship integration via `SponsorWhitelistControl`
- `dry_run` mode for testing without wallet
- Full test coverage: `tests/test_conflux_gateway.py`

### ConfluxCoreGateway (`core/adapters/conflux_core_gateway.py`)
- Core Space `cfx_*` RPC awareness
- `get_epoch_number()`, `get_balance()`, `get_status()`, `get_gas_price()`
- Foundation for future Core Space TX signing

### Batch Attestation (`scripts/conflux_batch_attest.py`)
- Run N governance cycles + publish proofs in sequence
- Configurable delay, dry_run mode, JSONL output

### Demo Script (`scripts/conflux_demo.py`)
- 6-step governance cycle with real on-chain attestation
- Verified TX: [bf98ea58...](https://evmtestnet.confluxscan.io/tx/bf98ea58265dcd8433f594376d0d679fde65d93ae8cc18d841627308bebf740c)

---

## Grant Budget Request

| Item | Description | Amount |
|------|-------------|--------|
| eSpace Mainnet Deployment | DOFProofRegistry on Conflux eSpace Mainnet | $2,000 |
| Core Space Integration | Full cfx_* TX signing, cfx: address support | $3,000 |
| Gas Sponsorship Automation | Automatic whitelist management for agent fleets | $2,000 |
| Cross-Space Proof Sync | Bridge governance proofs between eSpace and Core Space | $3,000 |
| **Total** | | **$10,000** |

---

## Roadmap

### Phase 1 — Hackathon (Apr 2026) ✅
- [x] eSpace Testnet deployment
- [x] Gas Sponsorship integration
- [x] 100+ on-chain proofs
- [x] Core Space RPC awareness
- [x] dof-sdk v0.6.0 on PyPI

### Phase 2 — Production (Q2 2026)
- [ ] eSpace Mainnet deployment
- [ ] Gas Sponsorship automation for agent fleets
- [ ] Core Space TX signing (cfx_sendRawTransaction)

### Phase 3 — Ecosystem (Q3-Q4 2026)
- [ ] Cross-Space proof synchronization
- [ ] Conflux DeFi integrations (DAO treasury governance)
- [ ] ERC-8004 + DOF compliance bundle on Conflux

---

## Team

**Juan Carlos Quiceno** (solo builder)  
- Medellín, Colombia  
- GitHub: [@Cyberpaisa](https://github.com/Cyberpaisa)  
- X: [@Cyber_paisa](https://x.com/Cyber_paisa)  
- ERC-8004 proposal: [ethereum-magicians.org/t/erc-formal-governance-proof-registry/28152](https://ethereum-magicians.org/t/erc-formal-governance-proof-registry/28152)

---

## Contact

- **GitHub:** github.com/Cyberpaisa/DOF-MESH  
- **Docs:** dofmesh.com  
- **Demo:** youtube.com/watch?v=WwpqXdYYID8  
- **Contract on Conflux:** [ConfluxScan](https://evmtestnet.confluxscan.io/address/0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83)

---

*"The majority of frameworks verify what happened. DOF verifies what is about to happen."*
