# The AI Agent Security Stack

This document formalizes the complete security stack for multi-agent systems, positioning the Deterministic Observability Framework (DOF) explicitly within the governance layer.

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
Infrastructure             (models, compute, Avalanche)
```

## 2. Where DOF Sits

DOF operates exclusively at the Governance Layer. It does not replace or abstract any of the higher-level frameworks (like CrewAI or LangGraph), nor does it manage agent memory or continuous execution states. Instead, it serves as an independent oversight mechanism.

It acts as a deterministic control boundary between the agent framework and the external world. Every output produced by the execution layer must pass through this boundary before it is allowed to interact with external APIs, databases, or smart contracts.

Crucially, DOF is stateless with respect to the execution layer. The Z3 Gate and other governance modules do not read the execution trace or maintain long-term context of the agent's internal reasoning. They evaluate the final proposed action in strict isolation against the predefined constitutional constraints.

## 3. What DOF Does at the Governance Layer

DOF processes outputs through seven independent governance layers. Note that 5 of the 7 layers are strictly deterministic (zero LLM calls), providing mathematically verifiable bounds on agent behavior.

| Layer | Component | Function | Latency | Paradigm |
|-------|-----------|----------|---------|----------|
| L7 | Signer | HMAC + Avalanche on-chain signing | ~2s | Crypto |
| L6 | Memory Gov | Bi-temporal versioning + decay | <1ms | Deterministic |
| L5 | Red/Blue | Red Team vs Guardian Arbitration | ~50ms | LLM |
| L4 | Z3 Proofs | 8 invariants + Z3 Gate | ~110ms | Deterministic |
| L3 | Supervisor | Q(0.4) + A(0.25) + C(0.2) + F(0.15) scoring | ~5ms | LLM |
| L2 | AST Verifier | Blocked imports, unsafe calls, secrets | <1ms | Deterministic |
| L1 | Constitution | 4 HARD + 5 SOFT rules enforcement | <1ms | Deterministic |

## 4. Integration Interface

The framework exposes a unified interface pattern for integration:

- `GenericAdapter`: Wraps any string output from an arbitrary agent framework into a processable object.
- `TrustGateway.verify()`: The primary entry point. It receives the adapted output, evaluates it across all configured layers, and returns an actionable result containing an `.action` attribute (e.g., APPROVED, REJECTED).
- `DOFProofRegistry`: Provides on-chain attestation by storing the `keccak256` proof hash of the verification process on the Avalanche network.
- **Upcoming**: `get_execution_trace(run_id)` to facilitate seamless integration with external execution kernels.

## 5. Relation to Adjacent Layers

The Execution Integrity Layer (e.g., `fdo-kernel-mvk`) is responsible for immutably recording what occurred during an agent's runtime, creating a causal chain of events. DOF does not read this execution log. The binding between the execution trace and the governance decision occurs solely through the cryptographic attestation anchored on-chain.

The Identity Layer (e.g., ERC-8004) defines who the agent is and manages its credentials. DOF utilizes the `token_id` from this layer strictly as a foreign key during the verification process. This ensures that governance decisions and attestations are correctly attributed and compatible with registries like the Enigma Scanner, without DOF needing to actively manage agent identities.

## 6. Citation

This architecture stack conceptualization builds upon the foundational principles detailed in the DOF Research Paper and implements the evaluation mechanics defined in ERC-8183.

- **DOF Paper**: [Deterministic Observability Framework for AI Agents](../paper/PAPER_OBSERVABILITY_LAB.md)
- **ERC-8183**: [Evaluator Standard for Agentic Commerce](https://eips.ethereum.org/EIPS/eip-8183)
