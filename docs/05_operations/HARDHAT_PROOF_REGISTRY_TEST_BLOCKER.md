# Hardhat Proof Registry Test Blocker

## Purpose

This document records the current blocker preventing safe Hardhat-based Solidity tests for the proof registry contracts.

The goal is to preserve evidence before adding contract-level behavior tests.

## Context

The intended next test scope is:

- `DOFProofRegistry.registerProof`
- `DOFProofRegistry.verifyProof`
- `DOFProofRegistry.getProof`
- `DOFProofRegistry.getProofCount`
- `DOFEvaluator.verifyProof`

However, root-level Hardhat compilation is currently risky because the source tree includes a non-Solidity file with a `.sol` extension.

## Hardhat source configuration

The root `hardhat.config.js` defines this source path:

    paths.sources = "./contracts"
    paths.cache = "./cache"
    paths.artifacts = "./artifacts"

This means Hardhat is expected to treat files inside `contracts/` as Solidity sources.

## Blocker

The file `contracts/ERC8004Attestation.openpgp` is not valid Solidity source.

Local inspection identified it as:

    OpenPGP Public Key

Because it has a `.sol` extension and lives inside the root Hardhat source directory, Hardhat may attempt to parse it during compilation.

## Risk

Running root-level Hardhat compilation may fail before reaching the target contracts:

- `contracts/DOFProofRegistry.sol`
- `contracts/DOFValidationRegistry.sol`
- `contracts/DOFEvaluator.sol`

This blocks safe creation of Hardhat contract tests until the source tree or compile harness is clarified.

## Existing artifacts

Compiled artifacts already exist for:

- `artifacts/contracts/DOFProofRegistry.sol/DOFProofRegistry.json`
- `artifacts/contracts/DOFValidationRegistry.sol/DOFValidationRegistry.json`
- `artifacts/contracts/DOFEvaluator.sol/DOFEvaluator.json`

These artifacts show that the target contracts were compiled at some point, but they do not prove that the current source tree compiles cleanly today.

## Current test layout

No root-level Hardhat test files were confirmed in `test/`.

The existing test suite is primarily Python-based under `tests/`.

## Decision

Do not add Hardhat Solidity behavior tests until the compile blocker is resolved.

Do not run `npx hardhat compile` against the current root source tree without first deciding how to handle `contracts/ERC8004Attestation.openpgp`.

## Safe options

### Option 1: scoped Hardhat harness

Create a scoped Hardhat test harness that compiles only the intended contracts.

This avoids moving files but requires deliberate test infrastructure.

### Option 2: relocate non-Solidity artifact

Move or rename `contracts/ERC8004Attestation.openpgp` in a separate PR if it is confirmed to be an artifact/key and not Solidity source.

This would restore the expectation that all `.sol` files in `contracts/` are Solidity contracts.

### Option 3: Python-level compatibility tests first

Add Python tests for hash compatibility and payload semantics before adding Solidity tests.

This does not validate Solidity behavior directly, but it can reduce ambiguity around `keccak256`, `sha3_256`, `sha256`, `BLAKE3`, `z3ProofHash`, `proofHash`, and `certificateHash`.

## Recommended next step

Recommended order:

1. Document this blocker.
2. Decide whether `contracts/ERC8004Attestation.openpgp` should be relocated or excluded.
3. Add direct Solidity behavior tests only after Hardhat compile behavior is safe.
4. Add Python hash compatibility tests if contract test infrastructure remains blocked.

## Final inspection state

At the time of inspection:

- branch: `test/proof-registry-behavior`
- working tree before this document: clean
- no compile was executed
- no contract logic was modified
- no deployment script was modified

