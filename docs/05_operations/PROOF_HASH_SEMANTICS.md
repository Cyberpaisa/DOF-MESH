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

## 4. Current State of `core/proof_hash.py` After PR #39

The current implementation behaves as follows:

- `Web3.keccak` is the canonical source for EVM-compatible proof hashes.
- If `Web3` is available, `ProofSerializer.hash_proof(non_empty_transcript)` uses `Web3.keccak`.
- If `Web3` is not available and the transcript is non-empty, `ProofSerializer.hash_proof()` raises `RuntimeError`.
- The empty transcript behavior remains `b"\\x00" * 32`.

The previous `hashlib.sha3_256` fallback was removed by PR #39. This is intentional: non-empty EVM-compatible proof hashes must fail closed when EVM Keccak is unavailable.

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

The `sha3_256` fallback in `core/proof_hash.py` has been removed by PR #39.

Remaining risk is now outside the canonical `ProofSerializer.hash_proof` path:

- legacy documentation and comments may still describe `hashlib.sha3_256` as Keccak-compatible;
- some non-`z3ProofHash` domains still use `sha256`, `sha3_256`, HMAC-SHA256, BLAKE3, or certificate hashes for valid local purposes;
- operators must keep those domains separate from EVM proof hashes sent to Solidity or `DOFProofRegistry`.

## 8. Recommended Next PR

Recommended follow-up:

- `docs: audit legacy hash-domain wording`

That follow-up should document legacy hash-domain findings and identify where comments or historical docs still need clarification after PR #39.
