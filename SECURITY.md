# Security Policy

## Supported Versions

| Version | Supported            |
|---------|----------------------|
| 0.2.x   | ✅ Current           |
| 0.1.x   | ⚠️ Critical fixes    |
| < 0.1   | ❌ Not supported     |

## Reporting a Vulnerability

If you discover a security vulnerability in DOF, please report it responsibly:

1. **Email:** Send details to jquiceva@gmail.com
2. **Telegram:** Contact [@Cyber_paisa](https://t.me/Cyber_paisa)
3. **Do NOT** open a public GitHub issue for security vulnerabilities

We will acknowledge receipt within 48 hours and provide a fix timeline within 7 days.

## Security Design

DOF's governance pipeline is designed with security as a core principle:

| Layer | Security Property |
|-------|-------------------|
| Constitution | Deterministic — no LLM in enforcement path |
| AST Verifier | Blocks eval(), exec(), subprocess, hardcoded secrets |
| Z3 Proofs | Formally verified — UNSAT (no counterexample exists) |
| Red/Blue | DeterministicArbiter — zero LLM in final adjudication |
| Memory | Constitutional validation on every write |
| Signer | HMAC-SHA256 + BLAKE3 certificate hashing |
| On-Chain | Avalanche C-Chain — immutable attestation |

## Key Management

- Private keys are NEVER committed to the repository
- `keys/` directory is in `.gitignore`
- HMAC secrets are loaded from environment variables
- Connection strings are loaded from `.env` (not tracked)

## Known Incidents

| Date | Incident | Resolution |
|------|----------|------------|
| 2026-03-06 | oracle_key.json accidentally committed via `git add -A` | Key rotated within 3 minutes, file removed from tracking, `keys/` added to `.gitignore` |

## Dependencies

Optional dependencies with security implications:

| Package | Purpose | Risk |
|---------|---------|------|
| z3-solver | Formal verification | None — read-only mathematical proofs |
| web3.py | Blockchain transactions | Requires private key — loaded from env |
| opentelemetry | Observability | Optional — no data leaves system unless configured |

## PII Detection

DOF includes soft rules for PII pattern detection (added in v0.2.0):
- Email addresses
- Phone numbers
- SSN patterns
- Credit card numbers
- API keys (OpenAI, AWS, GitHub, Ethereum)

These patterns are detected and flagged but not stored or logged.
