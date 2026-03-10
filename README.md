<p align="center">
  <img src="docs/diagrams/dof_banner.jpeg" alt="DOF - Deterministic Observability Framework" width="700">
</p>

<h3 align="center">VERIFY. PROVE. ATTEST.</h3>

<p align="center">
  <img src="https://github.com/Cyberpaisa/deterministic-observability-framework/actions/workflows/ci.yml/badge.svg" alt="CI">
  <img src="https://img.shields.io/badge/tests-1008%20passed-brightgreen" alt="tests">
  <img src="https://img.shields.io/badge/Z3-8%2F8%20PROVEN-blue" alt="Z3 proofs">
  <img src="https://img.shields.io/badge/attestations-21-red" alt="attestations">
  <img src="https://img.shields.io/pypi/v/dof-sdk" alt="PyPI">
  <img src="https://img.shields.io/badge/license-BSL%201.1-orange" alt="license">
  <img src="https://img.shields.io/badge/LOC-27K%2B-purple" alt="LOC">
  <img src="https://img.shields.io/badge/Avalanche-mainnet-red" alt="Avalanche">
  <a href="https://eips.ethereum.org/EIPS/eip-8183"><img src="https://img.shields.io/badge/ERC--8183-Evaluator-blue?logo=ethereum" alt="ERC-8183 Evaluator"></a>
</p>

<h1 align="center">Deterministic Observability Framework (DOF)</h1>

<p align="center">
  Deterministic governance for multi-agent LLM systems. Constitutional rules, formal proofs, and on-chain attestation on Avalanche.
</p>

<p align="center">
  <strong>Built with</strong> Python 3.11+ · Z3 SMT Solver · web3.py · BLAKE3 · Avalanche C-Chain · PostgreSQL
</p>

```bash
pip install dof-sdk
```

```python
from dof import GenericAdapter
result = GenericAdapter().wrap_output("your agent output here")
# → {status: "pass", violations: [], score: 8.5}
```

30ms. Zero LLM tokens. Works with CrewAI, LangGraph, AutoGen, or anything that produces text.

## Z3 Formal Verification (v0.3.3)

DOF provides **mathematical guarantees** — not just test coverage — that governance cannot be violated.

```bash
dof verify-states      # 8/8 PROVEN (107ms)
dof verify-hierarchy   # 42 patterns PROVEN (5ms)
```

**Neurosymbolic Z3 Gate** — LLM proposes, Z3 approves or rejects:
```python
from dof import Z3Gate, GateResult

gate = Z3Gate(constitution_rules)
result = gate.validate_trust_score("agent-1686", 0.95, evidence)
# APPROVED → execute | REJECTED → blocked with counterexample | TIMEOUT → fallback
```

**On-chain proof verification** — every attestation carries a keccak256 proof hash:
```python
from dof import Z3ProofAttestation

proof = Z3ProofAttestation.from_gate_verification(result, "agent-1686", 0.95)
# proof.z3_proof_hash → verifiable on Avalanche via DOFProofRegistry.verifyProof()
```

8 invariants proven for ALL possible inputs: threat→blocked, trust bounds, hierarchy constraints, cooldown enforcement, governor auth, SS(f) consistency, auto-demotion.

### x402 Trust Gateway

First formal verification layer for x402 payments. Zero LLM in the critical path.

```python
from dof import TrustGateway

gateway = TrustGateway()
verdict = gateway.verify(response_body=response)
# verdict.action → ALLOW / WARN / BLOCK
```

### CLI

```bash
python -m dof verify "your text here"   # governance check
python -m dof verify-code "code"        # AST verification
python -m dof check-facts "text"        # DataOracle fact-check
python -m dof prove                     # Z3 formal verification
python -m dof benchmark                 # adversarial benchmark
python -m dof privacy                   # privacy benchmark
python -m dof health                    # component status
python -m dof verify-states             # Z3 state transition verification (8/8 PROVEN)
python -m dof verify-hierarchy          # hierarchy enforcement verification (42 patterns)
python -m dof regression-baseline       # capture current state as regression baseline
python -m dof regression-check          # compare vs baseline (exit 1 if regressed)
python -m dof regression-history        # show last 10 regression reports
python -m dof version                   # show version
```

### Key Exports

`verify` · `classify_error` · `register` · `run_crew` · `MerkleBatcher` · `AdversarialEvaluator` · `RedTeamAgent` · `ConstitutionEnforcer` · `TrustGateway` · `Z3Gate` · `GateResult` · `TransitionVerifier` · `DOFAgentState` · `Z3ProofAttestation` · `ProofSerializer` · `ProofStorage` · `RegressionTracker` · `RegressionReport` · `ChangeType` · `EntropyDetector`

## Contents

[Highlights](#highlights) · [Architecture](#architecture) · [Z3 Verification](#formal-verification-z3) · [On-Chain](#on-chain-attestation) · [Benchmarks](#benchmark-results) · [Limitations](#honest-limitations) · [Citation](#citation)

---

## Highlights

- **7 governance layers** — Constitution → AST → Supervisor → Z3 → Red/Blue → Memory → Signer
- **Neurosymbolic Z3 Gate** — LLM proposes → Z3 verifies → execute or reject with counterexample
- **8 invariants PROVEN** — state transitions formally verified for ALL possible inputs (107ms)
- **42 hierarchy patterns** — enforce_hierarchy verified inviolable via Z3 (5ms)
- **SS(f) = 1 − f³** — Z3 verified stability formula under bounded retries
- **GCR(f) = 1.0** — governance invariant under any failure rate (Z3 proven)
- **On-chain proof hash** — keccak256 of Z3 proof transcript, verifiable via DOFProofRegistry
- **21 on-chain attestations** on Avalanche C-Chain mainnet
- **Merkle batching** — 10,000 attestations = 1 tx ≈ $0.01
- **Automated benchmark** — Governance 100%, Hallucination 90%, Consistency 100% FDR, 0% FPR
- **Privacy benchmark** — 71% detection rate across 7 AgentLeak channels
- **External benchmark** — 58.4% detection against 12,229 NVIDIA Garak payloads (12 categories)
- **Regression tracking** — 4 subsystems monitored post-merge, CI blocks regressions automatically
- **Framework agnostic** — CrewAI, LangGraph, AutoGen, or raw Python
- **1,008 tests**, 27K+ LOC, 35 core modules, 13 CLI commands

---

## Architecture

```
+----------------------------------------------------------+
| ERC-8183 Out   DOFEvaluator.sol  → complete() / reject() |
+----------------------------------------------------------+
| L7  Signer        HMAC + Avalanche               ~2s     |
+----------------------------------------------------------+
| L6  Memory Gov    Bi-temporal + decay            <1ms    |
+----------------------------------------------------------+
| L5  Red/Blue      Red → Guard → Arb              ~50ms   |
+----------------------------------------------------------+
| L4  Z3 Proofs     8 invariants + Z3 Gate         ~110ms  |
+----------------------------------------------------------+
| L3  Supervisor    Q+A+C+F scoring                ~5ms    |
+----------------------------------------------------------+
| L2  AST Verifier  eval/exec/secrets              <1ms    |
+----------------------------------------------------------+
| L1  Constitution  4 HARD + 5 SOFT                <1ms    |
+----------------------------------------------------------+
| Engine   DAG + LoopGuard + TokenTracker                  |
+----------------------------------------------------------+
| Data Oracle   6 verification strategies          <1ms    |
+----------------------------------------------------------+

         ↕ cross-cutting (all layers)
+----------------------------------------------------------+
| LLM Router   get_llm_smart()  task+context aware         |
|              Thompson Sampling + circuit breaker         |
+----------------------------------------------------------+

Total governance latency: < 180ms (layers 1-6).
On-chain signing adds ~2s when enabled.
ERC-8183 evaluation: DOFEvaluator.sol reads DOFProofRegistry
and attests job outcomes trustlessly.

Z3 is cross-cutting in v0.3.x: gates Meta-Supervisor decisions,
validates Red/Blue outputs, verifies state transitions,
proves hierarchy enforcement, and feeds DOFEvaluator attestations.

---

## Formal Verification (Z3)

### Static Proofs (v0.2.x)

| Theorem         | Math                      | Z3 Result |
|-----------------|---------------------------|-----------|
| GCR Invariant   | ∀f∈[0,1]: GCR(f)=1.0      | PROVEN    |
| SS Cubic        | ∀f∈[0,1]: SS(f)=1−f³      | PROVEN    |
| SS Monotonicity | f₁<f₂ ⟹ SS(f₁)>SS(f₂)    | PROVEN    |
| SS Boundaries   | SS(0)=1.0 ∧ SS(1)=0.0     | PROVEN    |

### Dynamic Invariants (v0.3.x)

| ID    | Invariant                            | Status |
|-------|--------------------------------------|--------|
| INV-1 | Threat detected → publish blocked    | PROVEN |
| INV-2 | Low trust → no attestation           | PROVEN |
| INV-3 | No hierarchy jumps without auth      | PROVEN |
| INV-4 | Trust score always in [0,1]          | PROVEN |
| INV-5 | Cooldown prevents re-publish         | PROVEN |
| INV-6 | Governor requires trust > 0.8        | PROVEN |
| INV-7 | SS(f)=1−f³ consistency               | PROVEN |
| INV-8 | Governance violation → auto-demote   | PROVEN |

42 hierarchy patterns verified in 4.9ms. Total: 107.7ms for all proofs.

---

## On-Chain Attestation

Contract [`0x88f6...C052`](https://snowtrace.io/address/0x88f6043B091055Bbd896Fc8D2c6234A47C02C052) on Avalanche C-Chain (43114). 21 attestations. ~$0.01/tx (~$0.01 per Merkle batch of 10,000). Three layers: PostgreSQL (200ms) → Enigma Scanner (900ms) → Avalanche (2-3s, immutable).

**DOFProofRegistry.sol** (v0.3.3) — companion contract for Z3 proof attestations. Every attestation includes `z3_proof_hash` (keccak256), verifiable on-chain via `verifyProof()`. Existing contract untouched.

---

## Benchmark Results

Adversarial (400 tests): Gov 100%, Code 86%, Hallucination 90%, Consistency 100%. **Overall F1: 96.8%**. Zero FPR.

External (NVIDIA Garak v0.14.0): **58.4% detection** against 12,229 payloads across 12 categories. DAN 63.4%, malwaregen 82.5%, goodside 90%. [Full results](tests/external/garak_benchmark_results.json).

Production (n=30): SS=0.90, GCR=1.00, PFI=0.61, 27/30 ACCEPT. Two agents ranked **#1 and #2** of 1,772 on [erc-8004scan.xyz](https://erc-8004scan.xyz).

---

## External Validation (Google Colab)

Tested externally via `pip install dof-sdk` — fresh Colab runtime, zero internal dependencies.

<p align="center">
  <a href="https://colab.research.google.com/drive/1GJQP7itj0d5z0UjWsqcyviSfev358pck?usp=sharing">
    <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab">
  </a>
</p>

**Enterprise Report v6 (v0.3.3) — 10/10 PASS:**

| Block | Component                                | Result |
|:------|:-----------------------------------------|:------:|
| B1    | Z3 Static Proofs — 4 theorems            | PASS   |
| B2    | Z3 State Transitions — 8 invariants      | PASS   |
| B3    | Z3 Hierarchy — 42 patterns               | PASS   |
| B4    | Z3 Gate — neurosymbolic validation       | PASS   |
| B5    | Proof Hash — deterministic serialization | PASS   |
| B6    | Error Classification — 8/8 categories    | PASS   |
| B7    | Merkle Batcher — 10 attestations batched | PASS   |
| B8    | Red Team + Threats — 3/3 detected        | PASS   |
| B9    | enforce_hierarchy — instruction priority  | PASS   |
| B10   | x402 Trust Gateway — ALLOW/BLOCK         | PASS   |

Full reports: [`tests/external/`](tests/external/)

---

## On-chain Integration

DOF acts as a trustless **Evaluator** in the [ERC-8183](https://eips.ethereum.org/EIPS/eip-8183)
agentic commerce standard. Every Z3 proof becomes an on-chain attestation.
Every agent job gets a verifiable outcome. [→ DOFEvaluator.sol](contracts/DOFEvaluator.sol)

---

## Honest Limitations

- **Hallucination detection is regex-based** — 90% FDR, misses semantic hallucinations
- **SS(f)=1−f³ assumes independent failures** — no correlated failure modeling
- **Supervisor is an LLM** — circularity bounded, not eliminated
- **Free-tier infrastructure** — 3/30 runs fail from provider exhaustion

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for full version history.

---

## Links

[PyPI](https://pypi.org/project/dof-sdk/) · [GitHub](https://github.com/Cyberpaisa/deterministic-observability-framework) · [Snowtrace](https://snowtrace.io/address/0x88f6043B091055Bbd896Fc8D2c6234A47C02C052) · [Enigma Scanner](https://erc-8004scan.xyz) · [Paper](paper/PAPER_OBSERVABILITY_LAB.md)

---

## Citation

```bibtex
@article{cyberpaisa2026deterministic,
  title={Deterministic Observability and Resilience Engineering for
         Multi-Agent LLM Systems: An Experimental Framework
         with Formal Verification},
  author={Cyber Paisa and Enigma Group},
  year={2026},
  note={27K+ LOC, 1008 tests, 35 modules, 8 Z3 invariants PROVEN,
        42 hierarchy patterns, 21+ Avalanche attestations,
        neurosymbolic Z3 Gate, on-chain proof hash,
        BSL 1.1, pip install dof-sdk}
}
```

---

## License

This project is licensed under the **Business Source License 1.1**.
Free for non-commercial use, research, and personal projects. Commercial use requires a separate agreement.
Contact: **@Cyber_paisa** on Telegram.

On **2028-03-08** this project converts to Apache License 2.0.
