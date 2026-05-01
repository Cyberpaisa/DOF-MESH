# Hardhat Tempo Foundry Compile Blocker

## Purpose

This document records the second blocker found while preparing Solidity behavior tests for the proof registry contracts.

The previous blocker was a non-Solidity `.sol` artifact under `contracts/`. After that artifact was renamed away from `.sol`, Hardhat progressed further and reached a new source-tree issue.

## Context

Root Hardhat configuration uses:

    paths.sources = "./contracts"
    paths.cache = "./cache"
    paths.artifacts = "./artifacts"

This means root Hardhat scans the entire `contracts/` tree.

The repository also contains a Foundry workspace under:

    contracts/tempo/

That workspace includes Foundry scripts such as:

    contracts/tempo/script/Deploy.s.sol

## Observed result

Calling Hardhat directly through its internal bootstrap worked:

    node node_modules/hardhat/internal/cli/bootstrap.js --version

Observed version:

    2.28.6

However, compilation failed with:

    Error HH411: The library forge-std, imported from contracts/tempo/script/Deploy.s.sol, is not installed.

## Diagnosis

Hardhat root compilation is currently traversing the Foundry workspace under `contracts/tempo/`.

`contracts/tempo/script/Deploy.s.sol` imports `forge-std`, which belongs to the Foundry toolchain, not the root Hardhat dependency graph.

This is a source-tree boundary issue, not a failure in:

- `DOFProofRegistry.sol`;
- `DOFValidationRegistry.sol`;
- `DOFEvaluator.sol`;
- the renamed `ERC8004Attestation.openpgp` artifact.

## Risk

Adding proof registry Hardhat tests before resolving this boundary would be unreliable because root Hardhat compile fails before reaching the intended contract test scope.

## Safe options

### Option 1: isolate Foundry workspace from root Hardhat

Move `contracts/tempo/` outside the root Hardhat `contracts/` source tree or configure a separate source layout.

### Option 2: scoped Hardhat config for proof registry tests

Create a dedicated Hardhat config or test harness that compiles only the target contracts:

- `contracts/DOFProofRegistry.sol`
- `contracts/DOFValidationRegistry.sol`
- `contracts/DOFEvaluator.sol`

### Option 3: continue with Python-level compatibility tests first

Add tests for hash and payload semantics while Solidity test infrastructure remains blocked.

## Recommendation

Do not install `forge-std` through npm as a quick fix for root Hardhat.

The cleaner fix is to separate Hardhat and Foundry source boundaries or create a scoped Hardhat test harness.

## Final diagnostic state

At the time of this diagnostic:

- branch: `chore/hardhat-local-env-diagnostics`
- working tree before this document: clean
- Hardhat internal bootstrap version: `2.28.6`
- root compile blocker: `contracts/tempo/script/Deploy.s.sol` imports `forge-std`
- no contract logic was modified
- no deployment script was modified

