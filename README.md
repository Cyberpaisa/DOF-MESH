<p align="center">
  <img src="docs/diagrams/dof_banner.jpeg" alt="DOF - Deterministic Observability Framework" width="700">
</p>

<h3 align="center">VERIFY. PROVE. ATTEST.</h3>

<p align="center">
  <img src="https://github.com/Cyberpaisa/deterministic-observability-framework/actions/workflows/ci.yml/badge.svg" alt="CI">
  <img src="https://img.shields.io/badge/tests-779-green" alt="tests">
  <img src="https://img.shields.io/badge/Z3_proofs-4%2F4-blue" alt="Z3 proofs">
  <img src="https://img.shields.io/badge/attestations-21-red" alt="attestations">
  <img src="https://img.shields.io/pypi/v/dof-sdk" alt="PyPI">
  <img src="https://img.shields.io/badge/license-BSL%201.1-orange" alt="license">
  <img src="https://img.shields.io/badge/LOC-27K%2B-purple" alt="LOC">
  <img src="https://img.shields.io/badge/Avalanche-mainnet-red" alt="Avalanche">
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

### x402 Trust Gateway (v0.2.6)

First formal verification layer for x402 payments. Zero LLM in the critical path.

```python
from dof import TrustGateway

gateway = TrustGateway()
verdict = gateway.verify(response_body=response)
# verdict.action → ALLOW / WARN / BLOCK
# verdict.governance_score → 0.0–1.0
```

### CLI

```bash
python -m dof verify "your text here"   # governance check
python -m dof prove                      # Z3 formal verification
python -m dof health                     # component status
python -m dof benchmark                  # adversarial benchmark
python -m dof privacy                    # privacy benchmark
python -m dof version                    # show version
```

### Key Exports

`verify` · `classify_error` · `register` · `run_crew` · `MerkleBatcher` · `AdversarialEvaluator` · `RedTeamAgent` · `ConstitutionEnforcer` · `TrustGateway` · `GatewayVerdict` · `GatewayAction`

## Contents

[The Problem](#the-problem) · [Highlights](#highlights) · [Architecture](#architecture) · [Governance Layers](#seven-governance-layers) · [Z3 Verification](#formal-verification-z3) · [On-Chain](#on-chain-attestation) · [Benchmarks](#benchmark-results) · [External Validation](#external-validation-google-colab) · [Limitations](#honest-limitations) · [Citation](#citation)

---

## The Problem

LLM agents hallucinate. Nobody catches it deterministically. Using LLMs to verify LLMs is circular — the evaluator shares failure modes with the evaluated. Rate limits, cascading retries, and non-deterministic output quality interact across execution steps, producing unstable system-level behavior that cannot be attributed to specific infrastructure variables.

DOF solves this with 7 deterministic governance layers, formal Z3 proofs, and on-chain attestation — zero LLM tokens in the verification path.

---

## Highlights

- **7 governance layers** — Constitution → AST → Supervisor → Z3 → Red/Blue → Memory → Signer
- **x402 Trust Gateway** — formal verification for agent payments (ALLOW/WARN/BLOCK)
- **SS(f) = 1 − f³** — Z3 verified stability formula under bounded retries
- **GCR(f) = 1.0** — governance invariant under any failure rate (Z3 proven)
- **21 on-chain attestations** on Avalanche C-Chain mainnet
- **Merkle batching** — 10,000 attestations = 1 tx ≈ $0.01
- **Automated benchmark** — Governance 100%, Hallucination 90%, Consistency 100% FDR, 0% FPR
- **Privacy benchmark** — 71% detection rate across 7 AgentLeak channels
- **Framework agnostic** — CrewAI, LangGraph, AutoGen, or raw Python
- **A2A server** (8 skills) + **MCP server** (10 tools) + **REST API** (14 endpoints)
- **DOFThreatPatterns** — 12 threat categories, composite detection (env+POST=exfil, exec+network=revshell, b64+eval=encoded payload), decode_and_scan for encoded evasion
- **779 tests**, 27K+ LOC, 25 core modules, 40 contributions

---

## Architecture

```
+----------------------------------------------------+
| L7  Signer       HMAC + Avalanche           ~2s    |
+----------------------------------------------------+
| L6  Memory Gov   Bi-temporal + decay        <1ms   |
+----------------------------------------------------+
| L5  Red/Blue     Red -> Guard -> Arb       ~50ms   |
+----------------------------------------------------+
| L4  Z3 Proofs    4 theorems UNSAT          ~10ms   |
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

Total governance latency: **< 70ms** (layers 1-6). On-chain signing adds ~2s when enabled.

---

## Seven Governance Layers

| Layer | What | Latency |
|-------|------|---------|
| L1 Constitution | 4 HARD (block) + 5 SOFT (warn). Regex + keywords | <1ms |
| L2 AST Verifier | Blocks eval/exec/subprocess/secrets via `ast` | <1ms |
| L3 Supervisor | S = Q(0.40)+A(0.25)+C(0.20)+F(0.15). ACCEPT ≥ 7.0 | ~5ms |
| L4 Z3 Proofs | 4 theorems (GCR invariance, SS cubic/mono/bounds) | ~10ms |
| L5 Red/Blue | RedTeam → Guardian → DeterministicArbiter. Zero LLM | ~50ms |
| L6 Memory Gov | Bi-temporal versioning, constitutional decay λ=0.99 | <1ms |
| L7 On-Chain | HMAC-SHA256 + Avalanche. Only GCR=1.0 published | ~2s |

---

## Formal Verification (Z3)

| Theorem | Math | Z3 Result |
|---------|------|-----------|
| GCR Invariant | ∀f∈[0,1]: GCR(f)=1.0 | UNSAT |
| SS Cubic | ∀f∈[0,1]: SS(f)=1−f³ | UNSAT |
| SS Monotonicity | f₁<f₂ ⟹ SS(f₁)>SS(f₂) | UNSAT |
| SS Boundaries | SS(0)=1.0 ∧ SS(1)=0.0 | UNSAT |

10ms total. Proof certificates: `logs/z3_proofs.json`.

---

## On-Chain Attestation

Contract [`0x88f6...C052`](https://snowtrace.io/address/0x88f6043B091055Bbd896Fc8D2c6234A47C02C052) on Avalanche C-Chain (43114). 21 attestations. ~$0.01/tx (~$0.01 per Merkle batch of 10,000). Three layers: PostgreSQL (200ms) → Enigma Scanner (900ms) → Avalanche (2-3s, immutable).

---

## Benchmark Results

### Adversarial Benchmark (400 generated tests, deterministic)

| Category | FDR | FPR | F1 | Tests |
|----------|-----|-----|-----|-------|
| Governance | 100.0% | 0.0% | 100.0% | 100 |
| Code Safety | 86.0% | 0.0% | 92.5% | 100 |
| Hallucination | 90.0% | 0.0% | 94.7% | 100 |
| Consistency | 100.0% | 0.0% | 100.0% | 100 |
| **Overall F1** | | | **96.8%** | **400** |

### Production Results (n=30 runs, real infrastructure)

| Metric | Value | Interpretation |
|--------|-------|----------------|
| SS | 0.90 ± 0.31 | 90% execution stability |
| GCR | 1.00 ± 0.00 | Perfect governance invariance |
| PFI | 0.61 ± 0.18 | Provider failures recovered via rotation |
| Supervisor | 27/30 ACCEPT | 90% acceptance rate |

---

## Production Agents

Two DOF-governed agents on Avalanche mainnet, ranked **#1 and #2** of 1,772 agents on [erc-8004scan.xyz](https://erc-8004scan.xyz): Apex Arbitrage (#1687, A2A+OASF) and AvaBuilder (#1686, A2A+OASF). Combined trust score: 0.85.

---

## External Validation (Google Colab)

Tested externally via `pip install dof-sdk` — fresh Colab runtime, zero internal dependencies.

| Version | Test | Result |
|---------|------|--------|
| v0.2.6 | TrustGateway clean endpoint | ALLOW / score=0.85 |
| v0.2.6 | TrustGateway adversarial payload | BLOCK / detected=True |
| v0.2.6 | LLM-as-Judge (score 1-10) | 9.0 / PASS |
| v0.2.6 | RedTeam prompt injection | detected=True / PASS |
| v0.2.6 | InstructionHierarchy | compliant=True / PASS |
| v0.2.2 | Z3 Formal Proofs (4/4) | VERIFIED / 19.25ms |
| v0.2.2 | MerkleBatcher | PASSED / 0.31ms |

Full reports: [`tests/external/`](tests/external/)

---

## Honest Limitations

- **Hallucination detection is regex-based** — 6 deterministic strategies achieve 90% FDR. Misses semantic hallucinations without known-facts coverage.
- **No correlated failure modeling** — SS(f)=1−f³ assumes independent failures.
- **Supervisor is itself an LLM** — mitigated by cross-provider execution and deterministic governance, but circularity is bounded, not eliminated.
- **Free-tier infrastructure** — 3/30 runs fail from provider exhaustion cascades.
- **Finite sample sizes** — n=20-30 per configuration; rare tail events not statistically guaranteed.

---

## Links

| Resource | URL |
|----------|-----|
| PyPI | [pypi.org/project/dof-sdk](https://pypi.org/project/dof-sdk/) |
| GitHub | [github.com/Cyberpaisa/deterministic-observability-framework](https://github.com/Cyberpaisa/deterministic-observability-framework) |
| Snowtrace | [snowtrace.io/address/0x88f6...C052](https://snowtrace.io/address/0x88f6043B091055Bbd896Fc8D2c6234A47C02C052) |
| Enigma Scanner | [erc-8004scan.xyz](https://erc-8004scan.xyz) |
| Paper | [paper/PAPER_OBSERVABILITY_LAB.md](paper/PAPER_OBSERVABILITY_LAB.md) |

---

## Citation

```bibtex
@article{cyberpaisa2026deterministic,
  title={Deterministic Observability and Resilience Engineering for
         Multi-Agent LLM Systems: An Experimental Framework
         with Formal Verification},
  author={Cyber Paisa and Enigma Group},
  year={2026},
  note={27K+ LOC, 779 tests, 25 modules, 4 Z3 theorems,
        21 Avalanche attestations, BSL 1.1, pip install dof-sdk}
}
```

---

## License

This project is licensed under the **Business Source License 1.1**.
Free for non-commercial use, research, and personal projects. Commercial use requires a separate agreement.
Contact: **@Cyber_paisa** on Telegram.

On **2028-03-08** this project converts to Apache License 2.0.
