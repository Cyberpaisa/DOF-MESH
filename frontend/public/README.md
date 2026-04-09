# DOF — Deterministic Observability Framework

**Math-verified, blockchain-attested autonomous AI agent governance.**

> Zero trust required — only math and blockchain.

[![Live Demo](https://img.shields.io/badge/Live_Demo-dof--agent--web.vercel.app-8b5cf6?style=for-the-badge)](https://dof-agent-web.vercel.app)
[![ERC-8004](https://img.shields.io/badge/ERC--8004-Certified-22c55e?style=for-the-badge)](https://basescan.org/tx/0x7362ef41605e430aba3998b0888e7886c04d65673ce89aa12e1abdf7cffcada4)
[![On-Chain](https://img.shields.io/badge/Conflux_eSpace-0x58F0126B...6fd1-28c840?style=for-the-badge)](https://evmtestnet.confluxscan.net/address/0x58F0126B647E87a9a49e79971E168ce139326fd1)

**Live Demo:** [https://dof-agent-web.vercel.app](https://dof-agent-web.vercel.app)

**Core Framework:** [Cyberpaisa/deterministic-observability-framework](https://github.com/Cyberpaisa/deterministic-observability-framework)

---

## What is DOF?

The **Deterministic Observability Framework (DOF)** is a governance and verification system for autonomous AI agents. Every agent action is:

1. **Governed** — Checked against a deterministic constitution (zero LLM involvement)
2. **Verified** — Proven correct with Z3 formal proofs (8/8 theorems)
3. **Attested** — Recorded on-chain with keccak256 proof hashes

### Key Metrics

| Metric | Value | Verifiable |
|--------|-------|------------|
| Autonomous Cycles | 238+ | Git commit history |
| On-Chain Attestations | 48+ | [Snowtrace](https://evmtestnet.confluxscan.net/address/0x58F0126B647E87a9a49e79971E168ce139326fd1) |
| Z3 Formal Proofs | 8/8 PROVEN | `python3 -c "from core.z3_verifier import Z3Verifier; print(Z3Verifier().verify_all())"` |
| Unit Tests | 986 passing | `python3 -m unittest discover tests/` |
| Core Modules | 35 | Source code |
| LLM Providers | 5 (fallback chain) | Cerebras > Groq > Mistral > SambaNova > NVIDIA |
| Governance Rules | 42 deterministic | Zero LLM involvement |
| ERC-8004 Identity | Token #31013 | [Basescan TX](https://basescan.org/tx/0x7362ef41605e430aba3998b0888e7886c04d65673ce89aa12e1abdf7cffcada4) |

---

## Landing Page Features

### DOF Agent Chat Bot (Enigma #1686)
- Floating chat widget (bottom-right corner)
- Powered by **Groq** (`llama-3.3-70b-versatile`) via secure Next.js API route
- System prompt loaded with full DOF context: architecture, metrics, constitution, tracks
- Every response passes through **DOF governance** (deterministic rules — PII leak detection, max length, empty output)
- Governance badge on each response: `GOV PASSED` / `GOV WARNING`
- Agent persona: **Enigma #1686** — DOF's own AI agent speaking in first person
- API key server-side only (zero exposure to client)

### x402 Protocol — Ultravioleta DAO Integration
- Live connection to the [Ultravioleta Facilitator](https://facilitator.ultravioletadao.xyz/)
- Real-time health check every 60 seconds (`/health` endpoint)
- Network discovery via `/supported` endpoint
- Badge shows `x402 Live` when facilitator is connected, `x402 Active` as fallback
- Enables stateless per-request HTTP 402 payments for agent-to-agent commerce

### A2A Protocol (Agent-to-Agent)
- Badge shows agent-to-agent protocol readiness
- Displays number of supported networks from Ultravioleta facilitator
- Visual indicator of multi-chain A2A capability

### DOF Security Shield
- Real-time governance status indicator
- Shows `42 Rules` — the number of constitutional rules enforced deterministically
- Pulse animation indicating live monitoring
- All governance is zero-LLM — 100% deterministic enforcement

### Theme Toggle (Dark / Light)
- Toggle button in navigation bar
- **Dark theme**: Deep purple/violet palette (default)
- **Light theme**: Soft gray (#e4e7ec) with adapted colors for all components
- Persisted via `localStorage` (`dof-theme`)
- All sections, cards, badges, and the chat widget adapt to both themes

### Language Switcher (i18n)
- Dropdown in navigation bar: **EN** | **ES** | **FR** | **ZH**
- Full translations for all page content (hero, stats, pipeline, tracks, evidence, footer)
- Uses `data-i18n` attributes on HTML elements
- Persisted via `localStorage` (`dof-lang`)
- Agent chat responds in the user's language automatically

---

## Track Pages

### 1. Best Agent on Celo
`/best-agent-celo/` — Governed stablecoin transfers (cUSD, cEUR, cREAL) on Celo. Wallet with chain detection. Auto-running agent terminal with live cycle counter.

### 2. MetaMask Delegations
`/metamask-delegation/` — Delegate governance tokens (ENS, UNI, AAVE, ARB, OP). Address validation. 5-step governance pipeline with MetaMask `personal_sign`.

### 3. Octant Public Goods
`/octant-analysis/` — Real-time ecosystem analytics. Canvas-rendered bar charts, live-updating stats (TVL, users, transactions), public goods funding form, top delegates leaderboard.

### 4. Olas Pearl
`/olas-pearl/` — Deploy specialized agents (Collector, Trader, Analyst, Auditor, Governor) into the Olas network. Start/stop controls. Live cycle counter.

### 5. Locus x402 Payments
`/locus-payments/` — Autonomous HTTP 402 payment protocol. Two agents negotiate, pay, and exchange data in a 7-step flow. **Zero human intervention** — agents pay agents.

### 6. SuperRare Generative Art
`/superrare-art/` — Procedural art via Canvas API with seeded PRNG. 5 styles, 5 palettes. Governance content check. Mint as NFT with MetaMask signature.

### 7. Arkhai Escrow
`/arkhai-escrow/` — Trustless escrow with full state machine (OPEN > FUNDED > SUBMITTED > COMPLETED | REJECTED). localStorage persistence. Stats tracking.

### 8. Private Agents
`/private-agents/` — **Real AES-256-GCM encryption** via Web Crypto API. PBKDF2 key derivation (100K iterations). Privacy Vault. Data never leaves the browser in plaintext.

### 9. Agent Services on Base
`/agent-services-base/` — ERC-8004 proof registry on Base. Submit Z3 verification proofs with 5-step pipeline. Real TX link to Basescan.

### 10. AgentEscrow ERC-8183
`/erc-8183/` — Trustless escrow for agent-to-agent commerce. Job board with state machine. 3 roles (Client, Provider, Evaluator). **Autonomous demo** runs the full escrow lifecycle with zero user input.

---

## Architecture

```
User / MetaMask
    |
DOF Agent (Autonomous)
    |
+-------------------------------------+
|  1. ConstitutionEnforcer            | <- Deterministic, zero LLM
|     12 hard rules (block)           |
|     8 soft rules (warn)             |
+-------------------------------------+
|  2. Z3 Formal Verifier             | <- 8/8 theorems PROVEN
|     Safety invariants               |
|     Payment bounds                  |
|     State transition proofs         |
+-------------------------------------+
|  3. keccak256 Proof Hash            | <- Deterministic hash
+-------------------------------------+
|  4. MetaMask Signature              | <- personal_sign
+-------------------------------------+
|  5. On-Chain Attestation            | <- Conflux eSpace / Base / Celo
|     DOFProofRegistry.sol            |
+-------------------------------------+
```

## Pipeline (Every Agent Action)

```
Identity (ERC-8004 #31013) -> Task Discovery -> LLM Inference -> Governance (Zero LLM) -> Z3 Proof -> On-Chain Attestation -> MetaSupervisor
```

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | Vanilla HTML/CSS/JS | Zero external dependencies |
| Chat Backend | Next.js API Route | Groq `llama-3.3-70b-versatile`, server-side key |
| x402 | Ultravioleta DAO Facilitator | Live health + network discovery |
| Wallet | `window.ethereum.request()` | Native MetaMask API, no Web3.js |
| Encryption | Web Crypto API | AES-256-GCM + PBKDF2 (100K iterations) |
| Art Generation | Canvas API | Seeded PRNG for reproducible provenance |
| Charts | Canvas API | Gradient fills, live animation |
| Persistence | localStorage | Offline-capable, no backend required |
| i18n | data-i18n + JS | EN, ES, FR, ZH — zero dependencies |
| Hosting | Vercel | Static + serverless (Next.js API routes) |
| On-Chain | Conflux eSpace C-Chain, Base, Celo | Multi-chain attestation |

## Smart Contracts

| Contract | Chain | Address | Explorer |
|----------|-------|---------|----------|
| DOFProofRegistry.sol | Conflux eSpace C-Chain | `0x154a3F49a9d28FeCC1f6Db7573303F4D809A26F6` | [Snowtrace](https://evmtestnet.confluxscan.net/address/0x58F0126B647E87a9a49e79971E168ce139326fd1) |
| ERC-8004 Identity | Base Mainnet | Token #31013 | [Basescan](https://basescan.org/tx/0x7362ef41605e430aba3998b0888e7886c04d65673ce89aa12e1abdf7cffcada4) |

## Running Locally

```bash
# Landing page only (static)
npx serve .
# or
python3 -m http.server 8080

# With chat bot (requires Next.js backend)
cd frontend
cp .env.example .env.local  # Add GROQ_API_KEY
npm install && npm run dev
# Visit http://localhost:3000/landing.html
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes (for chat) | Groq API key for LLM inference. Server-side only. |

## Security

- Zero hardcoded credentials or API keys
- Chat API key server-side only via Next.js API route (never exposed to client)
- All wallet operations via MetaMask (user-controlled)
- Client-side encryption with Web Crypto API (AES-256-GCM)
- No external CDN dependencies (eliminates supply chain risk)
- localStorage stores only user-encrypted data
- DOF governance enforced on every chat response (PII detection, output validation)
- `.env` excluded via `.gitignore`

## License

Apache 2.0

---

Built by **[Cyber Paisa](https://github.com/Cyberpaisa)** for the **Synthesis Hackathon 2026**.

*Deterministic governance. Formal verification. On-chain attestation.*
