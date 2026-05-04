# Testnet Burner Execution Checklist

## 1. Purpose

This checklist defines the first controlled on-chain execution path after the offline dry-run and read-only RPC health-check phases.

It is designed for one testnet, one burner wallet, one minimal operation, and manual execution by Juan only.

This document does not authorize agents, Codex, LLMs, or automation tools to execute transactions.

## 2. Current phase

Previous phases completed:

- PR #49: offline on-chain readiness dry-run
- PR #50: memory checkpoint hardening to on-chain readiness
- PR #51: read-only RPC health check

Current phase:

- PR #52: testnet burner execution checklist

Next allowed phase after this checklist:

- manual single-testnet execution with a burner wallet controlled by Juan

## 3. Candidate network

| Field | Value |
|---|---|
| Chain | Avalanche Fuji Testnet |
| Chain key | avalanche_testnet |
| Chain ID | 43113 |
| Native token | AVAX |
| Status | testnet |
| Contract | 0x0b65d10FEcE517c3B6c6339CdE30fF4A8363751c |
| Explorer | https://testnet.snowtrace.io |

Rationale:

- Fuji is a testnet.
- Fuji has a configured DOFProofRegistry contract.
- Fuji passed read-only RPC health-check.
- It uses AVAX, the primary ecosystem context for DOF-MESH.

## 4. Non-negotiable safety rules

Codex may prepare documentation, checklists, read-only scripts, and dry-runs.

Codex must not:

- read .env
- receive private keys
- receive seed phrases
- create wallets for Juan
- sign transactions
- broadcast transactions
- run cast send
- run deploy scripts
- run npx hardhat run contracts/deploy/deploy_multichain.js
- execute wallet-funded commands
- print secrets
- modify hardhat.config.js
- modify core/chains_config.json during execution

Juan controls secrets and real execution.

Operational rule:

Codex audits and writes dry-runs; Juan controls secrets and real execution.

## 5. Preconditions

Before any real testnet transaction:

- main must be clean.
- Latest checkpoints must be pushed.
- RPC health-check must pass for avalanche_testnet.
- Burner wallet must be created and controlled manually by Juan.
- Burner wallet must hold only minimal testnet funds.
- Private key must not be pasted into ChatGPT, Codex, GitHub, docs, commits, logs, or shell history when avoidable.
- Execution must happen in a local terminal under Juan control.
- Output must be reviewed before any follow-up action.

## 6. Burner wallet policy

The first testnet execution must use a burner wallet.

Rules:

- Never use a production wallet.
- Never use a wallet holding meaningful funds.
- Never reuse the burner for mainnet.
- Never commit the burner key.
- Never paste the burner key into AI tools.
- Prefer interactive wallet injection, hardware wallet, local encrypted keystore, or temporary shell session not saved to history.
- Destroy or rotate the burner after the test if exposed.

## 7. Minimum operation policy

The first transaction must be the smallest meaningful operation.

Allowed operation class:

- one testnet proof/attestation registration or equivalent minimal write

Not allowed in first execution:

- multi-chain broadcast
- mainnet execution
- batch execution
- deploy
- ownership transfer
- role assignment
- upgrade
- pause/unpause
- grantRole/revokeRole
- token movement beyond gas
- any emergency/admin function

## 8. Pre-execution checks

Run these before manual execution:

- git checkout main
- git pull dof-mesh main
- git status
- npm run test:collect
- python3 scripts/audit/onchain_readiness_dry_run.py
- python3 scripts/audit/rpc_health_check_read_only.py --timeout 2 --json | python3 -m json.tool

Expected:

- git status clean
- 4802 tests collected
- avalanche_testnet appears in dry-run
- avalanche_testnet RPC is reachable
- observed chain ID equals 43113

## 9. Manual execution boundary

The checklist may document the command pattern, but the final command must be reviewed and executed manually by Juan.

Do not run automatically.
Do not execute from Codex.
Do not execute from a prompt.

Do not execute before Juan confirms:

- network
- chain ID
- contract address
- burner address
- balance
- gas estimate
- payload
- expected result

## 10. Evidence to capture

After execution, capture only non-sensitive evidence:

- chain key
- chain ID
- contract address
- transaction hash
- block number
- explorer URL
- timestamp
- command class used, without secrets
- result status
- revert reason if failed
- gas used
- no private keys
- no .env
- no wallet seed
- no raw signed transaction unless intentionally public and safe

## 11. Abort conditions

Abort if any of these occur:

- git status is dirty
- chain ID mismatch
- RPC returns inconsistent network
- contract address differs from chains_config.json
- wallet is not burner
- balance is too high for a burner
- gas estimate is unexpectedly high
- command includes mainnet
- command includes deploy
- command includes admin method
- command includes private key in visible logs
- Codex or any AI tool requests .env or private key

## 12. Post-execution actions

After a successful testnet transaction:

- verify transaction in explorer
- verify contract state if applicable
- record evidence in a new docs-only report
- do not proceed to another network automatically
- do not proceed to mainnet
- review lessons learned
- create a checkpoint only after merge into main

## 13. Next phase

After this checklist is merged and checkpointed, the next safe PR is:

script: add single-testnet manual execution template

That PR should prepare a command template or script that defaults to no execution unless Juan explicitly supplies local-only execution parameters.

It must still avoid Codex-held secrets.
