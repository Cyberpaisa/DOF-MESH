# Hash Domain Legacy Audit

## 1. Purpose

This document records the legacy hash-domain audit performed after PR #39,
which enforced EVM Keccak requirements for `ProofSerializer.hash_proof`.

The purpose is to separate:

- canonical EVM proof hashes used by `DOFProofRegistry` and `z3ProofHash`;
- SHA3/FIPS hashes produced by Python `hashlib.sha3_256`;
- SHA256 Merkle, integrity, identity, checksum, and internal audit hashes;
- HMAC-SHA256 authentication signatures;
- BLAKE3 and `certificateHash` identity/certificate hashes.

This is an audit document, not an implementation change.

## 2. Scope

Reviewed areas:

- `docs/`
- `core/`
- `tests/`

Excluded areas:

- `node_modules`
- generated artifacts and caches
- virtual environments
- binary files
- implementation changes

This audit intentionally does not modify code, tests, contracts, configs, or
runtime behavior.

## 3. Current Canonical Policy After PR #39

After PR #39:

- `ProofSerializer.hash_proof(non_empty_transcript)` requires EVM Keccak via
  `Web3.keccak`.
- If `Web3` is unavailable and the transcript is non-empty,
  `ProofSerializer.hash_proof` raises `RuntimeError`.
- `ProofSerializer.hash_proof("")` preserves the existing empty transcript
  sentinel: `b"\x00" * 32`.
- The previous silent `hashlib.sha3_256` fallback was removed.
- Python `hashlib.sha3_256` is not equivalent to Solidity/EVM `keccak256`.
- Any hash sent as `z3ProofHash` or to `DOFProofRegistry` must be EVM Keccak.

## 4. Critical Findings

### `core/evolve_engine.py`

Finding:

- The on-chain evolution attestation path describes the payload as
  `keccak256`.
- A nearby comment says `keccak256 equivalent using sha3_256`.
- The implementation uses `hashlib.sha3_256`.

Risk:

This falsely implies that Python SHA3-256 is compatible with Solidity/EVM
Keccak. Because the result is passed through an attestation path, operators may
mistake this value for an EVM proof hash.

Recommendation:

Clarify in a documentation/comment-only PR that this is a legacy SHA3/FIPS
evolution payload hash unless a later implementation PR migrates it to EVM
Keccak.

### `core/zk_governance_proof.py`

Finding:

- The module describes hashes as `SHA3-256 / keccak256`.
- `_keccak256` uses `hashlib.sha3_256`.
- The helper docstring says `keccak256-compatible`.
- `GovernanceProof` fields are documented as Keccak hashes.

Risk:

The naming and comments imply EVM compatibility that the implementation does
not provide. This can cause governance proofs to be confused with
`z3ProofHash` or `DOFProofRegistry` proof hashes.

Recommendation:

Clarify that this is a legacy governance proof SHA3/FIPS domain. Any EVM proof
hash migration should be handled in a separate implementation PR.

### `core/zk_layer.py`

Finding:

- `_sha3` uses `hashlib.sha3_256`.
- Its docstring says the hash is `Solidity-compatible`.

Risk:

This is an explicit false compatibility claim.

Recommendation:

Clarify that this helper belongs to an internal ZK commitment domain and is not
Solidity/EVM Keccak.

### `core/audit_log.py`

Finding:

- The module title and class comments describe a `keccak256` or
  `keccak256-compatible` audit hash chain.
- The implementation uses `hashlib.sha3_256`.

Risk:

The audit log hash chain is internal, but the comment can cause operators to
confuse it with EVM Keccak.

Recommendation:

Clarify that the audit chain uses SHA3-256 as an internal tamper-evident hash,
not an EVM proof hash.

### `docs/02_research/EXPERIMENT_EVOLVE_ATTESTATION_20260329.md`

Finding:

- The document says `sha3_256(...)` is equivalent to `keccak256`.

Risk:

This is a direct false equivalence in historical documentation.

Recommendation:

Mark the statement as legacy/incorrect and point readers to
`PROOF_HASH_SEMANTICS.md`.

## 5. High Findings

### `core/scheduler.py`

Finding:

- `proof_hash` is documented as `SHA-256 of output for on-chain attestation`.
- The computed hash uses `hashlib.sha256`.

Risk:

The value may be valid as an internal output digest, but the phrase
`on-chain attestation` can make it look like an EVM proof hash.

Recommendation:

Clarify the domain before using this value as a chain-facing proof hash.

### `core/evolution/attestation.py`

Finding:

- The module computes `proof_hash = "0x" + sha256(payload)`.

Risk:

The `0x` + 32-byte format is ABI-compatible as `bytes32`, but format
compatibility is not semantic equivalence with EVM Keccak.

Recommendation:

Clarify this as an evolution payload hash, not a `z3ProofHash`.

### `tests/integration/test_multichain_e2e.py`

Finding:

- The integration fixture creates a `proof_hash` with SHA256 and passes it to
  `publish_attestation`.

Risk:

The fixture may normalize SHA256 as a valid chain-facing proof hash.

Recommendation:

Leave tests unchanged in this documentation PR. Track separately if fixtures
should distinguish dummy `bytes32` values from canonical EVM proof hashes.

## 6. Medium Findings

### `docs/05_operations/PROOF_HASH_SEMANTICS.md`

Finding:

- The document previously described a `hashlib.sha3_256` fallback in
  `core/proof_hash.py`.

Status:

Superseded by PR #39. The fallback was removed and non-empty proof transcripts
now fail closed when `Web3` is unavailable.

### `docs/05_operations/PROOF_REGISTRY_CONSISTENCY_AUDIT.md`

Finding:

- The prior audit describes the old fallback behavior and asks whether
  `proof_hash.py` should fail closed.

Status:

Superseded by PR #39 for `core/proof_hash.py`. The document remains useful as
historical audit context, but readers should treat fallback references as
legacy.

## 7. Valid Uses / False Positives

Do not treat these as EVM proof-hash errors without additional evidence:

- `ProofSerializer.hash_proof` using `Web3.keccak`.
- Tests that explicitly prove `hashlib.sha3_256 != Web3.keccak`.
- SHA256 Merkle roots in `core/merkle_tree.py` and Merkle batching.
- SHA256 internal identifiers, checksums, nonces, and cache keys.
- HMAC-SHA256 signatures used for authentication and message integrity.
- BLAKE3 identity hashes in OAGS-related flows.
- `certificateHash` values in certificate/identity domains when explicitly
  treated as separate from `z3ProofHash`.
- Dummy `bytes32` test values that are not asserted to be EVM Keccak.

## 8. Hash Domain Map

| Domain | Expected hash | Appears in | Needs correction |
|---|---|---|---|
| EVM proof hash / `z3ProofHash` / `DOFProofRegistry` | EVM Keccak via `Web3.keccak` | `core/proof_hash.py`, `core/z3_proof.py`, proof registry docs | No for `core/proof_hash.py`; audit legacy references elsewhere |
| `ProofSerializer.hash_proof` | `Web3.keccak`; empty transcript is zero hash | `core/proof_hash.py`, proof tests | No |
| Merkle roots / `ProofBatcher` | SHA256 Merkle tree over proof leaves | `core/merkle_tree.py`, `core/proof_hash.py` batching | No |
| Audit log hash chain | Internal SHA3-256 hash chain | `core/audit_log.py` | Yes, wording only |
| Governance proof legacy | Legacy SHA3/FIPS via `hashlib.sha3_256` | `core/zk_governance_proof.py` | Yes, wording now; implementation later if required |
| ZK layer commitments | Internal SHA3/FIPS commitment hash | `core/zk_layer.py` | Yes, wording only |
| Cross-chain identity bridge | SHA256 internal bridge proof | `core/cross_chain_identity.py` | No unless used as `z3ProofHash` |
| HMAC/authentication | HMAC-SHA256 | `core/oracle_bridge.py`, federation docs/tests | No |
| `certificateHash` / BLAKE3 | BLAKE3 or certificate-domain hash | OAGS/oracle/avalanche bridge docs | No if kept separate |
| Internal IDs/checksums | SHA256 or domain-local hash | scheduler, security, checkpoints, fixtures | Clarify only when labeled on-chain proof hash |

## 9. Recommended Remediation Sequence

1. Documentation PR:
   - Add this audit.
   - Update `PROOF_HASH_SEMANTICS.md` for PR #39.
   - Link the audit from `docs/INDEX.md`.

2. Comment/docstring PR:
   - Clarify legacy wording in `core/audit_log.py`, `core/zk_layer.py`,
     `core/zk_governance_proof.py`, `core/evolve_engine.py`,
     `core/scheduler.py`, and `core/evolution/attestation.py`.
   - Do not change runtime behavior in that PR.

3. Test fixture PR:
   - Decide whether chain-facing fixtures should use canonical EVM Keccak or
     be explicitly labeled dummy `bytes32` values.

4. Implementation PR, only if required:
   - Migrate selected legacy chain-facing hashes to EVM Keccak.
   - Keep Merkle, HMAC, certificate, identity, checksum, and internal audit
     domains separate.

## 10. Explicit Non-Implementation Note

This document does not change hash behavior. It does not migrate legacy
`sha3_256` or `sha256` call sites. It records domain boundaries and identifies
where comments or docs can mislead operators after PR #39.
