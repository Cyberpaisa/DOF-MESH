# DOF-MESH: Deterministic Governance for Autonomous AI Agents on Conflux

**Authors:** Juan Carlos Quiceno (@Cyber_paisa) — Colombia Blockchain, Medellín, Colombia  
**Submitted:** Conflux Global Hackfest 2026  
**Repository:** github.com/Cyberpaisa/DOF-MESH — branch: conflux-hackathon  
**Documentation:** dofmesh.com  

---

## Abstract

Autonomous AI agents acting on public blockchains require verifiable proof of correct behavior prior to execution. Existing approaches rely on post-hoc audit logs, LLM-based validators, or prompt-enforced rules — all of which are manipulable or non-deterministic. DOF-MESH presents a five-layer deterministic governance framework that generates cryptographic compliance proofs before agent action, publishes them on Conflux eSpace, and — uniquely — uses Conflux's native Gas Sponsorship to make proof registration gasless for compliant agents. This paper describes the architecture, Conflux-specific optimizations, empirical results from 146 on-chain attestations, and the DOF-LEARN self-learning extension.

---

## 1. Introduction

The deployment of autonomous AI agents in financial systems — DeFi protocols, DAO treasuries, cross-chain arbitrage — creates a class of risk for which no formal verification infrastructure exists at scale. Current governance approaches exhibit one of three failure modes: (1) LLM-based validators are non-deterministic and can be manipulated through adversarial prompting; (2) audit logs are post-hoc and provide no pre-execution guarantee; (3) prompt-based rules operate at inference time and can be overridden.

DOF-MESH addresses this gap by moving verification to the pre-execution phase using three deterministic mechanisms: formal logic (Z3 SMT solver), behavioral scoring (TRACER), and rule-based governance (Constitution). The output is a keccak256 proof hash published to a smart contract registry on Conflux eSpace — permanent, tamper-proof, and independent of DOF-MESH infrastructure.

---

## 2. System Architecture

DOF-MESH implements governance through five sequential, deterministic stages:

```
Agent Proposed Action
        │
        ▼
┌─────────────────────────────────────┐
│  Layer 1: Constitution              │
│  9 governance rules, regex + AST    │
│  Zero LLM — deterministic block     │
└──────────────────┬──────────────────┘
                   ▼
┌─────────────────────────────────────┐
│  Layer 2: Z3 SMT Formal Proof       │
│  4 theorems, proven for ALL inputs  │
│  GCR_INVARIANT, SS_FORMULA,         │
│  SS_MONOTONICITY, SS_BOUNDARIES     │
└──────────────────┬──────────────────┘
                   ▼
┌─────────────────────────────────────┐
│  Layer 3: TRACER Behavioral Score   │
│  5 dimensions: Quality, Accuracy,   │
│  Compliance, Format, Communication  │
└──────────────────┬──────────────────┘
                   ▼
┌─────────────────────────────────────┐
│  Layer 4: Deterministic Proof Hash  │
│  SHA-256 of Z3 + TRACER output      │
│  Same input always → same hash      │
└──────────────────┬──────────────────┘
                   ▼
┌─────────────────────────────────────┐
│  Layer 5: Conflux On-Chain          │
│  DOFProofRegistry — eSpace testnet  │
│  Proof-to-Gasless (V2)              │
└─────────────────────────────────────┘
```

---

## 3. Z3 Formal Verification

DOF-MESH employs the Z3 theorem prover (Microsoft Research) to verify four invariants against all possible agent execution states — not merely tested cases.

| Theorem | Description | Proof time |
|---------|-------------|------------|
| GCR_INVARIANT | Governance compliance rate invariant | 2.6ms |
| SS_FORMULA | Supervisor score formula correctness | 0.4ms |
| SS_MONOTONICITY | Score monotonicity under valid inputs | 1.7ms |
| SS_BOUNDARIES | Score boundary conditions | 0.6ms |

Total verification time: **5.3ms** per governance cycle.  
Status: **4/4 PROVEN** across all 100 batch attestation cycles.

---

## 4. Conflux-Specific Implementation

### 4.1 Gas Sponsorship Integration

Conflux's `SponsorWhitelistControl` (internal contract `0x0888000000000000000000000000000000000001`) enables protocol operators to sponsor gas costs for whitelisted agents. DOF-MESH integrates this natively: agents that register compliance proofs are enrolled in Gas Sponsorship, removing the requirement to hold CFX for governance operations.

### 4.2 EVM Differences and Optimizations

DOF-MESH identified and corrected four Conflux-specific behaviors during development:

**SSTORE cost.** Conflux charges 40,000 gas per SSTORE operation (2× Ethereum's 20,000). `DOFProofRegistryV2` employs packed struct storage, reducing SSTORE operations from ~10 to ~4 per proof registration — a saving of ~240,000 gas per attestation.

**eth_getLogs block range.** Conflux eSpace limits `eth_getLogs` to 1,000 blocks per query. `ConfluxGateway.get_logs_paginated()` implements automatic 900-block chunking with result concatenation, preventing silent event omission in batch readers.

**block.number semantics.** `block.number` returns the Conflux epoch number, not a monotonically increasing block count. All time-sensitive contract logic uses `block.timestamp` exclusively.

**eth_getProof unavailability.** EIP-1186 Merkle proofs are not supported in Conflux eSpace. DOF-MESH uses deterministic proof hashes (SHA-256 of Z3 output) rather than Merkle proofs, maintaining compatibility with Conflux's RPC subset.

### 4.3 DOFProofRegistry Deployment

| Parameter | Value |
|-----------|-------|
| Contract address | `0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83` |
| Network | Conflux eSpace Testnet (Chain ID: 71) |
| Total transactions | 146 (as of 2026-04-08) |
| Contract version | V1 deployed; V2 (Proof-to-Gasless) pending deploy |

---

## 5. DOF-MESH as Conflux Infrastructure

DOF-MESH positions as governance infrastructure for the Conflux ecosystem, operating at a layer below individual dApps. Any autonomous agent operating on Conflux — DeFi protocols, DAO governance, cross-chain bridges — can integrate DOF-MESH to produce verifiable pre-execution compliance records.

The Model Context Protocol server (`mcp_server/dof_conflux_mcp.py`) exposes governance verification as MCP tools consumable by any MCP-compatible AI runtime. This is the first MCP server implementation for Conflux Network.

---

## 5.1 DOF-LEARN: Self-Learning Compliance Memory

DOF-MESH v0.6.0 implements deterministic governance through five
verification stages. DOF-LEARN extends this architecture with a
sixth dimension: accumulated compliance intelligence that enriches
each verification cycle with context from prior agent executions.

### Architecture

DOF-LEARN applies OpenAI's 6-layer context model [1] to agent compliance governance.
Where Dash accumulates SQL query patterns for data agents, DOF-LEARN
accumulates Z3 proof patterns and behavioral corrections for
autonomous on-chain agents.

```
Agent Proposed Action
        │
        ▼
┌─────────────────────────────────────────────────────┐
│               DOF-LEARN CONTEXT RETRIEVAL            │
│                                                      │
│  Layer 1 ─ Constitution        9 governance rules   │
│  Layer 2 ─ Z3 Proven Patterns  verified theorem set │
│  Layer 3 ─ TRACER History      behavioral baseline  │
│  Layer 4 ─ Agent Profile       execution signature  │
│                                                      │
│  Layer 5 ─ Failure Patterns    ← self-learned       │
│            (what failed, why, how to avoid)          │
│  Layer 6 ─ Peer Corrections    ← self-learned       │
│            (anonymized cross-agent knowledge)        │
└────────────────────────┬────────────────────────────┘
                         │ enriched context
                         ▼
               Z3 Formal Verification
                         │
           ┌─────────────┴─────────────┐
           │                           │
         PASS                        FAIL
           │                           │
           ▼                           ▼
  ┌─────────────────┐       ┌──────────────────────┐
  │ Register proof  │       │ Diagnose failure     │
  │ on Conflux      │       │ Save to learnings/   │
  │ Grant gasless   │       │ Anchor to proof hash │
  └─────────────────┘       │ Never repeat         │
                            └──────────────────────┘
```

### Storage Schema

DOF-LEARN requires two PostgreSQL tables. No GPU, no model updates,
no external dependencies beyond the existing DOF-MESH database.

```sql
-- ─────────────────────────────────────────────────────────────────
-- dof_knowledge: curated compliance knowledge
-- Populated by: manual curation + auto-discovery from PASS cycles
-- Queried by: DOF-LEARN context retrieval at verification time
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE dof_knowledge (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id    TEXT        NOT NULL,        -- EVM address of the governed agent
    category    TEXT        NOT NULL,        -- 'z3_pattern' | 'tracer_rule'
                                             -- 'constitution' | 'peer_correction'
    content     JSONB       NOT NULL,        -- structured knowledge payload
                                             -- schema varies by category
    source      TEXT        NOT NULL         -- 'manual' = human-curated
                DEFAULT 'auto-discovered',   -- 'auto-discovered' = agent-generated
    proof_hash  TEXT,                        -- Conflux proof hash if sourced from
                                             -- a verified on-chain attestation
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Fast lookup by agent + category (primary access pattern)
CREATE INDEX idx_knowledge_agent_category
    ON dof_knowledge(agent_id, category);

-- Full-text search over JSONB content (for semantic retrieval)
CREATE INDEX idx_knowledge_content_gin
    ON dof_knowledge USING GIN(content);

-- ─────────────────────────────────────────────────────────────────
-- dof_learnings: self-discovered failure patterns
-- Populated by: auto-diagnosis on every FAIL cycle
-- Queried by: DOF-LEARN at context retrieval to prevent recurrence
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE dof_learnings (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id         TEXT        NOT NULL,   -- EVM address of the failing agent
    failure_type     TEXT        NOT NULL,   -- 'z3_violation' | 'tracer_reject'
                                             -- 'constitution_fail' | 'timeout'
    failure_context  JSONB       NOT NULL,   -- full execution context at failure:
                                             -- action, scores, theorem results
    correction       TEXT,                   -- human or auto-generated fix
                                             -- NULL until resolved
    proof_hash       TEXT,                   -- Conflux proof hash of the failed TX
                                             -- on-chain anchor for audit trail
    resolved_at      TIMESTAMPTZ,            -- NULL = unresolved, set on fix
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Fast lookup by agent + failure type (primary diagnostic query)
CREATE INDEX idx_learnings_agent_type
    ON dof_learnings(agent_id, failure_type);

-- Unresolved failures dashboard index
CREATE INDEX idx_learnings_unresolved
    ON dof_learnings(resolved_at)
    WHERE resolved_at IS NULL;
```

### Key Properties

**GPU-poor continuous learning.** DOF-LEARN improves governance
accuracy through accumulated context, not model weight updates.
A Z3 theorem violation at block 248,350,045 becomes a Layer 5
pattern that prevents the identical failure at block 248,500,000.
The system compounds intelligence across millions of agent executions
without compute infrastructure beyond a standard PostgreSQL instance.

**On-chain anchored memory.** Every entry in `dof_learnings` stores
a Conflux proof hash from the corresponding failed attestation
attempt. This creates a two-way link: the Conflux ledger records
what was attempted; DOF-LEARN records why it failed and what was
learned. Neither side is meaningful without the other. The memory
is not only persistent — it is cryptographically verifiable.

**Agent-specific behavioral profiles.** Each agent accumulates a
distinct compliance history indexed by EVM address. A DeFi
arbitrage agent and a DAO governance agent develop different
Layer 4 profiles over time. The verification context presented
to Z3 for a well-understood agent is materially richer than for
a new agent, improving both speed and accuracy of formal proofs.

### DOF-LEARN vs Existing Approaches

| System | Learns from failures | On-chain anchored | No GPU | Scope |
|--------|---------------------|-------------------|--------|-------|
| **DOF-LEARN** | ✅ Z3/TRACER/Constitution | ✅ Conflux proof hash | ✅ | On-chain agent governance |
| Dash [1] | ✅ SQL query patterns | ❌ | ✅ | Database data agents |
| Traditional monitoring | ❌ Post-hoc only | ❌ | ✅ | General observability |
| Fine-tuned models | ❌ Requires retraining | ❌ | ❌ | General purpose |

[1] agno-agi/dash — https://github.com/agno-agi/dash —
    open-source implementation of OpenAI's 6-layer context architecture.

### Roadmap

DOF-LEARN ships as part of DOF Cloud SaaS (Phase 9), where agents
subscribe to access their own compliance history and benefit from
anonymized cross-agent pattern discovery at scale.

---

## 6. ERC Proposal

DOF-MESH is the reference implementation for ERC-8004 (Formal Governance Proof Registry), an Ethereum Improvement Proposal extending the EVM standard with on-chain governance proof registration.

**Proposal:** ethereum-magicians.org/t/erc-formal-governance-proof-registry/28152  
**Status:** Draft — open for community feedback

ERC-8004 defines three registry interfaces:
- `IGoverned` — agent identity with governance proof reference
- `IProofRegistry` — on-chain proof storage and verification
- `IComplianceOracle` — deterministic compliance query interface

DOFProofRegistry implements the `IProofRegistry` interface and is deployed on 8 chains including Conflux eSpace Testnet.

---

## 7. Empirical Results

### 7.1 Batch Attestation Run (2026-04-08)

| Metric | Value |
|--------|-------|
| Cycles executed | 100 |
| Confirmed on-chain | **100 / 100 (100%)** |
| Z3 4/4 PROVEN | All 100 cycles |
| Governance passed | 20 / 100 |
| Governance blocked (by design) | 80 / 100 |
| Total duration | 1,368s (22.8 min) |
| Average per cycle | 13.7s |
| Min cycle | 8.5s |
| Max cycle | 41.9s |
| Median cycle | 13.3s |

### 7.2 Gas Consumption (Conflux eSpace Testnet)

| Operation | Gas Used | Gas Price | Cost (CFX) |
|-----------|----------|-----------|------------|
| registerProof (V1) | ~373,421 | 40 Gdrip | ~0.015 CFX |
| registerProof (V2 packed) | ~133,000 est. | 40 Gdrip | ~0.005 CFX |
| Savings (V2 vs V1) | ~240,000 gas | — | ~0.010 CFX/proof |

### 7.3 On-Chain State (2026-04-08T04:22 UTC)

- **Total transactions:** 146 on ConfluxScan
- **Contract:** `0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83`
- **Explorer:** evmtestnet.confluxscan.io/address/0x554c...
- **First TX:** `0x8cfd...2c32` (deployment)
- **Latest TX:** `0xf3b5...ac5` (batch cycle 100)

---

## 8. Conclusion

DOF-MESH demonstrates that deterministic governance for autonomous AI agents is technically feasible at production scale on Conflux. The combination of Z3 formal verification, TRACER behavioral scoring, and Conflux's native Gas Sponsorship creates an infrastructure layer where mathematical compliance earns economic privilege — the Proof-to-Gasless mechanism introduced in DOFProofRegistryV2.

The DOF-LEARN extension (§5.1) extends this to a self-improving system: failure patterns become first-class data, anchored to Conflux proof hashes, preventing recurrence without model retraining. The first MCP server for Conflux Network exposes this entire stack to any AI agent runtime via the Model Context Protocol standard.

146 on-chain transactions, 8 passing tests, 4 documented EVM bugs corrected, and zero LLM in the governance decision path.

---

*DOF-MESH — Conflux Global Hackfest 2026*  
*github.com/Cyberpaisa/DOF-MESH | dofmesh.com | @Cyber_paisa*
