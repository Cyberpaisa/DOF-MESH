# DOF Proof Registry Consistency Audit

## Purpose

This document records the consistency audit for the DOF proof registry, governance attestation registry, evaluator contract, and related off-chain proof modules.

The goal is not to change contract logic yet.

The goal is to preserve evidence, identify naming/hash mismatches, separate confirmed facts from assumptions, and define the safest next engineering path.

## Scope

Audited components:

- `contracts/DOFProofRegistry.sol`
- `contracts/DOFValidationRegistry.sol`
- `contracts/DOFEvaluator.sol`
- `contracts/DOFGaslessProof.sol`
- `contracts/ERC8004Attestation.sol`
- `core/z3_proof.py`
- `core/zk_governance_proof.py`
- `core/proof_hash.py`
- `core/proof_storage.py`
- `core/oracle_bridge.py`
- `core/avalanche_bridge.py`
- `core/chain_adapter.py`
- `core/tool_hooks.py`
- `core/zk_batch_prover.py`
- `core/merkle_attestation.py`
- related tests and documentation

Excluded from this audit:

- generated artifacts;
- `contracts/tempo/out`;
- `contracts/tempo/cache`;
- vendored libraries;
- `node_modules`;
- `__pycache__`;
- historical evidence files;
- deployment secrets;
- private endpoints;
- wallets;
- private keys.

## Executive summary

The proof and attestation surface is functional but not semantically aligned end-to-end.

The system currently mixes multiple related concepts:

- Z3 proof transcript attestations;
- governance certificate attestations;
- local tool-hook attestations;
- Merkle/batch attestations;
- off-chain proof payloads;
- on-chain contract registries.

The main technical concern is not that these flows exist separately. The concern is that naming and hash semantics overlap across components.

The audit found multiple hash families in use:

- EVM `keccak256`;
- Python `sha3_256`;
- `sha256`;
- `BLAKE3`;
- `HMAC-SHA256`.

The audit also found multiple similarly named fields:

- `z3ProofHash`;
- `proofHash`;
- `certificateHash`;
- `attestationHash`;
- `inputHash`.

These names are close, but they do not always represent the same object or the same hash family.

## Confirmed facts

### DOFProofRegistry

`DOFProofRegistry` is the on-chain registry for Z3 proof attestations.

It stores:

- `agentId`;
- `trustScore`;
- `z3ProofHash`;
- `storageRef`;
- `invariantsCount`;
- `timestamp`;
- `verified`.

Its verification path is transcript-based:

1. A proof is registered with `z3ProofHash`.
2. A proof transcript is later submitted.
3. The contract computes `keccak256(proofTranscript)`.
4. If the computed hash matches the stored `z3ProofHash`, the proof is marked as `verified`.

Important notes:

- `registerProof()` is open.
- `verifyProof()` is open.
- The contract does not validate author signatures.
- The contract does not enforce owner-only registration.
- The contract exposes `getProof()` and `getProofCount()`.

### DOFValidationRegistry

`DOFValidationRegistry` is a governance attestation registry.

It stores:

- `certificateHash`;
- `agentId`;
- `compliant`;
- `timestamp`;
- `submitter`.

It supports:

- single attestation registration;
- batch attestation registration;
- owner-only revocation;
- compliance lookup;
- attestation detail lookup.

Important notes:

- `registerAttestation()` is open.
- `registerBatch()` is open.
- `revokeAttestation()` is owner-only.
- The contract accepts `bytes32` hashes but does not recompute or cryptographically verify the hash contents.
- Comments describe `certificateHash` and `agentId` as BLAKE3 hashes, but the contract itself only sees `bytes32`.

### DOFEvaluator

`DOFEvaluator` is a read-only consumer of `DOFProofRegistry`.

Its flow:

1. Receive a job contract, job ID, and submission hash.
2. Search `DOFProofRegistry` for a matching `z3ProofHash`.
3. Require the matching proof to be `verified`.
4. Call `complete()` if the proof is found and verified.
5. Call `reject()` if no verified proof is found.

Important notes:

- `evaluate()` is owner-only.
- `verifyProof()` loops over all registered proofs.
- The contract itself warns that this can be gas-intensive for large registries.
- `submissionHash` is compared against `z3ProofHash`, which creates a semantic question: is this the hash of the submission or the hash of the Z3 proof transcript?

## Off-chain hash and payload findings

### core/z3_proof.py

`core/z3_proof.py` creates `Z3ProofAttestation` objects.

It maps naturally to `DOFProofRegistry`:

- `agent_id` -> `agentId`;
- `trust_score_scaled` -> `trustScore`;
- `z3_proof_hash` -> `z3ProofHash`;
- `storage_ref` -> `storageRef`;
- `invariants_count` -> `invariantsCount`.

Concern:

`z3_proof.py` depends on `core/proof_hash.py`, where the preferred path may use Web3 keccak, but fallback behavior may use Python `sha3_256`.

### core/proof_hash.py

`core/proof_hash.py` uses Web3 keccak when available.

Concern:

Fallback behavior uses `hashlib.sha3_256`, which is not identical to EVM `keccak256`.

This matters if a proof hash generated in fallback mode is expected to match Solidity `keccak256(proofTranscript)`.

### core/zk_governance_proof.py

`core/zk_governance_proof.py` creates governance proof payloads with:

- `proofHash`;
- `inputHash`;
- `verdict`;
- `timestamp`;
- `ruleCount`;
- `score`.

Concern:

It uses Python `hashlib.sha3_256` while describing the result as SHA3-256 / keccak-compatible.

This should not be assumed to match EVM `keccak256`.

### core/oracle_bridge.py

`core/oracle_bridge.py` creates signed governance metric attestations.

Hash behavior:

- uses BLAKE3 if installed;
- falls back to SHA256;
- signs certificates with HMAC-SHA256.

Concern:

This aligns more naturally with `DOFValidationRegistry` certificate attestations than with raw Z3 transcript proofs.

### core/tool_hooks.py

`core/tool_hooks.py` creates local tool-level attestations.

Concern:

Comments reference keccak256, but the implementation uses SHA256 for local `attestation_hash`.

This may be acceptable for local audit trail hashes, but it should not be confused with on-chain `z3ProofHash`.

### core/chain_adapter.py

`core/chain_adapter.py` interacts with `DOFProofRegistry`.

Confirmed behavior:

- ABI includes `registerProof`;
- ABI includes `getProofCount`;
- ABI includes `getProof`;
- publish path can submit proof hashes;
- verify path searches records.

Concern:

The adapter verification semantics may differ from `DOFEvaluator`, especially around whether `record.verified` is required.

## Evidence matrix

| Component | Code evidence | Test evidence | Documentation evidence | Risk | Recommended path |
|---|---|---|---|---|---|
| `DOFProofRegistry` | Registers and verifies Z3 proof hashes with EVM `keccak256` | No direct Solidity tests confirmed | Docs describe it as proof registry | Medium-high: open registration, no signature validation, no direct contract tests | Tests first |
| `DOFValidationRegistry` | Registers governance certificate attestations | Bridge tests exist, no direct Solidity tests confirmed | Docs/scripts reference governance attestations | High: BLAKE3 comments vs runtime fallback ambiguity | Docs audit + tests |
| `DOFEvaluator` | Owner-only evaluator, read-only registry scan | No direct Solidity tests confirmed | Docs describe ERC-8183 evaluator | High: O(n) lookup, submissionHash/z3ProofHash ambiguity | Tests before refactor |
| `core/z3_proof.py` | Produces Z3 proof attestation payload | Python tests exist | Docs generally align | Medium: fallback hash may not match EVM keccak | Cross-check hash tests |
| `core/zk_governance_proof.py` | Produces governance proof payload | Python tests exist | Docs mention governance proof attestations | High: no clear matching Solidity contract in this audit | Docs audit |
| `core/proof_hash.py` | Web3 keccak preferred, sha3_256 fallback | Python tests exist | Docs say deterministic proof hashing | Medium: fallback mismatch risk | Explicit compatibility tests |
| `core/oracle_bridge.py` | BLAKE3 or SHA256 certificate hashes, HMAC signatures | Bridge tests exist | Docs mention ERC-8004/on-chain attestation | Medium-high: hash family changes by dependency availability | Clarify hash policy |
| `core/avalanche_bridge.py` | Uses `registerAttestation` / `isCompliant` | Bridge tests exist | Docs mention Avalanche attestations | Medium: depends on upstream certificate hash semantics | Tests + docs |
| `core/chain_adapter.py` | Uses `DOFProofRegistry` ABI | Adapter tests exist | Multichain docs mention proof registry | High: verification semantics need comparison with evaluator | Tests |
| `core/tool_hooks.py` | Local SHA256 attestation hash | Tool hook tests exist | Limited docs evidence | Medium: comments say keccak | Fix comments or document |
| `core/zk_batch_prover.py` | Batch/Merkle attestation payloads | Python coverage likely via governance proof tests | Docs mention batching | Medium: matching Solidity interface unclear | Audit docs before code |

## Key risks

### Hash-family mismatch

The system uses multiple hash families:

- EVM `keccak256`;
- Python `sha3_256`;
- SHA256;
- BLAKE3;
- HMAC-SHA256.

These are not interchangeable.

Any path that expects Python fallback `sha3_256` or SHA256 to match Solidity `keccak256` is unsafe.

### Naming drift

The following names are semantically close but not equivalent:

- `z3ProofHash`;
- `proofHash`;
- `certificateHash`;
- `attestationHash`;
- `inputHash`.

A future refactor should preserve these distinctions or explicitly normalize them.

### Registry-role confusion

`DOFProofRegistry` and `DOFValidationRegistry` are related but not equivalent.

`DOFProofRegistry` verifies proof transcripts.

`DOFValidationRegistry` records compliance/certificate attestations.

### Missing direct contract tests

The audit did not confirm direct Solidity tests for:

- `DOFProofRegistry.registerProof`;
- `DOFProofRegistry.verifyProof`;
- invalid transcript rejection;
- `DOFValidationRegistry.registerAttestation`;
- duplicate attestation rejection;
- `DOFEvaluator.verifyProof`.

### DOFEvaluator scalability

`DOFEvaluator.verifyProof()` iterates over all registered proofs.

This is acceptable for demos and small registries, but should not be treated as production-scale without indexing or alternative lookup design.

### Documentation drift

Some docs mix:

- Avalanche;
- Conflux;
- ERC-8004;
- ERC-8183;
- `registerProof`;
- `registerAttestation`;
- SHA-256;
- keccak256.

This may be historical, but it should be clearly labeled before external use.

## Open questions

1. Should `submissionHash` in `DOFEvaluator.evaluate()` represent the Z3 transcript hash or the job submission hash?
2. Should `DOFValidationRegistry` enforce BLAKE3, or is `bytes32` intentionally hash-family agnostic?
3. Which chain is canonical for current production attestation: Avalanche, Conflux, or multichain?
4. Is there a Solidity contract for `submitGovernanceProof` or `submitBatchAttestation`?
5. Is `DOFGaslessProof.sol` part of the production path or a demo/hackathon artifact?
6. Should `core/tool_hooks.py` comments be updated to say SHA256 instead of keccak256 for local hashes?
7. Should `proof_hash.py` fail closed when Web3 keccak is unavailable instead of falling back to `sha3_256`?

## Recommended next path

### Immediate next PR

Recommended:

`docs: add proof registry consistency audit`

Reason:

The repo needs a durable audit artifact before tests or refactors.

This document should be used as the basis for deciding which tests to add.

### Next technical PR after this audit

Recommended:

`test: add proof registry behavior coverage`

Priority tests:

- `DOFProofRegistry.registerProof`;
- `DOFProofRegistry.verifyProof` with valid transcript;
- `DOFProofRegistry.verifyProof` with invalid transcript;
- `DOFProofRegistry.getProof`;
- `DOFProofRegistry.getProofCount`;
- `DOFEvaluator.verifyProof` against verified proof;
- `DOFEvaluator.verifyProof` against unverified proof;
- Python hash compatibility against EVM `keccak256`.

### Not recommended yet

Do not refactor contracts yet.

Do not change registry ABI yet.

Do not change hash families yet.

Do not modify production deployment scripts yet.

## Final audit state

At the time of this audit:

- branch: `audit/dof-proof-registry`;
- working tree: clean;
- `npm run test:collect`: `4797 tests collected`;
- no files modified;
- no commits created;
- no pushes performed.

