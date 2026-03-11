# Architecture Stack

## 1. The AI Agent Security Stack

```text
Application Layer          (AI apps, copilots, workflows)
        ↓
Agent Framework Layer      (CrewAI, LangGraph, AutoGen)
        ↓
Identity Layer             (ERC-8004, agent persona, credentials)
        ↓
Execution Integrity Layer  (append-only traces, causal chain, replay)
        ↓
Governance Layer           (DOF — policy enforcement, Z3, attestation)
        ↓
Infrastructure             (models, compute, Avalanche C-Chain)
```

## 2. Where DOF Sits

DOF is strictly the Governance Layer. It does not replace or abstract any of the higher-level frameworks like CrewAI or LangGraph, but acts as a transparent intermediary for output verification.

It operates as a deterministic control boundary between the agent framework and the external world. Every action or payload meant for external execution must successfully pass this boundary before proceeding.

DOF is primarily stateless with respect to the execution layer. The Z3 Gate and internal evaluations operate in isolation and do not read the execution trace during validation. The actual binding between the execution log and the governance decision occurs through the on-chain attestation (a `keccak256` proof hash anchored in Avalanche).

## 3. DOF Internal Architecture

| Layer | Component | Function | Latency |
|-------|-----------|----------|---------|
| L7 | Signer | HMAC + Avalanche | ~2s |
| L6 | Memory Gov | Bi-temporal + decay | <1ms |
| L5 | Red/Blue | Red → Guard → Arb | ~50ms |
| L4 | Z3 Proofs | 8 invariants + Z3 Gate | ~110ms |
| L3 | Supervisor | Q+A+C+F scoring | ~5ms |
| L2 | AST Verifier | eval/exec/secrets | <1ms |
| L1 | Constitution | 4 HARD + 5 SOFT | <1ms |

*Note: 5 of the 7 layers are completely deterministic (zero LLM tokens).*
Total governance latency L1–L6: <180ms. On-chain signing (L7): ~2s. Cross-cutting: LLM Router — get_llm_smart() with Thompson Sampling + circuit breaker.

## 4. Integration Interface

- **`GenericAdapter`**: Wraps any string output, typically executes in ~30ms, requiring zero LLM tokens.
- **`TrustGateway.verify()`**: Principal endpoint that returns a deterministic `verdict.action` resolving to ALLOW, WARN, or BLOCK.
- **`DOFProofRegistry`**: Stores the on-chain `keccak256` proof hash, which is independently verifiable via `verifyProof()` on the Avalanche C-Chain at `0x88f6...C052`.
- **`get_execution_trace(run_id)`**: NEW in v0.3.3 — exposes execution steps, `action_hash`, `trace_hash`, and `proof_hash` for external kernel integration (compatible with append-only trace formats).

## 5. Relation to Adjacent Layers

**Execution Integrity (e.g., `fdo-kernel-mvk`)**:
Records what happened. DOF does not read that log during enforcement. Governance checks are stateless. The cryptographic binding between "what governance approved" and "what the trace recorded" happens via the on-chain attestation written to Avalanche.

**Identity Layer (e.g., ERC-8004 / Enigma Scanner)**:
DOF uses the `token_id` (not the wallet address) as a foreign key for agent identity. This ensures full compatibility with the ERC-8004 registry hosted at erc-8004scan.xyz. The deployed `DOFEvaluator.sol` exposes DOF as a trustless Evaluator complying with the ERC-8183 agentic commerce standard.

## 6. References

- **DOF Paper**: [paper/PAPER_OBSERVABILITY_LAB.md](../paper/PAPER_OBSERVABILITY_LAB.md)
- **Architecture diagram**: [docs/diagrams/01_dof_v12_architecture.mmd](diagrams/01_dof_v12_architecture.mmd)
- **ERC-8004**: [https://eips.ethereum.org/EIPS/eip-8004](https://eips.ethereum.org/EIPS/eip-8004)
- **ERC-8183**: [https://eips.ethereum.org/EIPS/eip-8183](https://eips.ethereum.org/EIPS/eip-8183)
- **Enigma Scanner**: [https://erc-8004scan.xyz](https://erc-8004scan.xyz)
- **PyPI Hub**: [https://pypi.org/project/dof-sdk/](https://pypi.org/project/dof-sdk/)
