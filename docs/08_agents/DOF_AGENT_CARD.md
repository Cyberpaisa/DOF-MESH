# DOF — AI Agent for Deterministic Governance & Formal Verification

## What is DOF?
The Deterministic Observability Framework (DOF) is a zero-LLM governance engine for AI agent systems. It provides mathematical guarantees — not opinions — for agent output safety, privacy, and compliance.

## Core Capabilities

### 1. Governance Verification ($0.01/check)
Check any text against 50+ deterministic governance rules.
- **Hard rules** block dangerous outputs (violence, PII leaks, code injection)
- **Soft rules** warn on quality issues (length, complexity, tone)
- **Speed**: <30ms per check, zero LLM tokens consumed
- **Input**: Any text string
- **Output**: `{passed: bool, score: float, violations: [], warnings: []}`

### 2. Z3 Formal Proofs ($0.05/proof)
Mathematically prove state transition correctness using Z3 theorem prover.
- 8 core theorems: monotonicity, bounded transitions, convergence, reachability
- Proof hash: keccak256 for on-chain attestation
- **Input**: State definition with transitions
- **Output**: `{proofs: [{theorem, result, time_ms}], all_proven: bool}`

### 3. Privacy Leak Detection ($0.10/scan)
Test any LLM agent for data leakage vulnerabilities.
- PII detection, API key exposure, memory leaks, tool input leaks
- Detection rate: 71%+ on benchmark suite
- **Input**: Text corpus or agent endpoint
- **Output**: `{detection_rate: float, leaked_items: [], risk_level: str}`

### 4. Smart Contract Security ($0.50/scan)
Solidity vulnerability scanner.
- Detects: reentrancy, tx.origin auth, selfdestruct, unchecked calls
- EVM audit: 500+ checklist items
- **Input**: Solidity source code
- **Output**: `{vulnerabilities: [{type, severity, line, description}]}`

### 5. Code Architecture Review ($1.00/review)
Comprehensive code quality and security analysis.
- Architecture patterns, anti-patterns, OWASP top 10
- Quality score with actionable recommendations
- **Input**: Code snippet or repo description
- **Output**: Structured review with quality score

### 6. Market Research ($2.00/report)
AI-powered market analysis with Go/No-Go recommendation.
- Competitive landscape, market sizing, trend analysis
- **Input**: Topic or question
- **Output**: Structured research report

## Technical Details
- **Version**: 0.4.1
- **License**: BSL-1.1
- **PyPI**: `pip install dof-sdk`
- **Tests**: 986 passing
- **Core modules**: 52+
- **Lines of code**: 27,000+
- **Z3 theorems**: 207
- **On-chain**: Avalanche C-Chain (DOFProofRegistry.sol)

## Why DOF?
- **Deterministic**: No LLM randomness in governance decisions
- **Formal**: Z3 mathematical proofs, not heuristics
- **Fast**: <30ms governance checks
- **Auditable**: Full JSONL trace logging
- **Battle-tested**: 986 tests, 55/55 audit score

## Creator
Juan Carlos Quiceno Vasquez — Solo developer, Synthesis Hackathon 2026
