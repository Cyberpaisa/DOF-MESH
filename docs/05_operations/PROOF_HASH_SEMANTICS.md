# Proof Hash Semantics

## 1. Purpose

This document defines the canonical hash semantics for DOF-MESH after PR #37, which added compatibility coverage for `ProofSerializer.hash_proof`, `Web3.keccak`, and `hashlib.sha3_256`.

Its goal is to prevent ambiguity between EVM proof hashes, SHA3/FIPS hashes, Merkle integrity hashes, certificate hashes, and authentication signatures.

## 2. Canonical Rule

- For EVM, Avalanche, and Solidity compatibility, use **Keccak-256 compatible with `Web3.keccak`**.
- Python `hashlib.sha3_256` is **not equivalent** to EVM `keccak256`.

## 3. Hash Semantics Table

| Hash family | Canonical use in DOF-MESH | Notes |
|---|---|---|
| `Web3.keccak` / EVM `keccak256` | On-chain proof attestations, `z3ProofHash`, `DOFProofRegistry` | This is the canonical proof-hash domain for Solidity/EVM compatibility. |
| `hashlib.sha3_256` | SHA3/FIPS domain only | Not equivalent to EVM keccak. Do not describe it as EVM-compatible. |
| `hashlib.sha256` | Merkle roots, internal integrity checks, non-EVM identifiers | Valid for internal integrity domains, but distinct from `z3ProofHash`. |
| `BLAKE3` / `certificateHash` | Separate certificate/identity domain where explicitly defined | Treat as a separate domain, not interchangeable with EVM proof hashes. |
| `HMAC-SHA256` | Authentication and integrity of signed payloads | Not an on-chain proof hash and not interchangeable with EVM keccak. |

## 4. Current State of `core/proof_hash.py`

The current implementation behaves as follows:

- If `Web3` is available, `ProofSerializer.hash_proof()` uses `Web3.keccak`.
- If `Web3` is not available, it falls back to `hashlib.sha3_256`.

That fallback exists for local resilience, but it must **not** be interpreted as semantic equivalence with EVM `keccak256`.

## 5. What PR #37 Proved

PR #37 added explicit compatibility coverage and confirmed:

- `ProofSerializer.hash_proof(transcript) == Web3.keccak(...)` when `Web3` is active.
- `Web3.keccak(text=transcript) == Web3.keccak(transcript.encode("utf-8"))` for UTF-8 proof transcripts.
- `hashlib.sha3_256(...) != Web3.keccak(...)`.
- The empty transcript behavior remains `b"\\x00" * 32`.

These tests make the hash-family distinction explicit instead of leaving it as an implicit assumption.

## 6. Operational Rules

- Any hash that will be sent to Solidity or `DOFProofRegistry` must be **EVM keccak**.
- Do not call `sha3_256` “keccak-compatible”.
- Do not mix `sha256` / Merkle integrity hashes with `z3ProofHash`.
- Before publishing anything on-chain, document which domain and hash family it belongs to.

## 7. Pending Risk

The `sha3_256` fallback in `core/proof_hash.py` remains an open risk and should be resolved in a separate implementation PR.

Until that happens, developers should assume that:

- environments with `Web3` available can produce canonical EVM-compatible proof hashes;
- environments without `Web3` may produce hashes that are deterministic but not Solidity-compatible.

## 8. Recommended Next PR

Recommended follow-up:

- `fix/test: enforce EVM keccak proof hash policy`

That follow-up should decide whether the fallback remains allowed, becomes explicit error behavior, or is replaced with a truly EVM-compatible implementation path.
