# Fuji Burner Manual Execution Runbook

## 1. Purpose

This runbook prepares the first real manual transaction on Avalanche Fuji using a burner wallet.

It does not authorize Codex or any agent to execute transactions. Codex audits and writes dry-runs; Juan controls secrets and real execution.

## 2. Scope

- One network: Avalanche Fuji.
- One burner wallet.
- One minimal operation.
- Manual execution by Juan.
- Public evidence captured only after execution.

Out of scope:

- deploys;
- mainnet;
- multi-chain execution;
- admin operations;
- agent-controlled wallets;
- any broadcast from Codex or autonomous agents.

## 3. Current readiness

- Offline dry-run exists from PR #49.
- Read-only RPC health-check exists from PR #51.
- Testnet burner execution checklist exists from PR #53.
- Single-testnet manual execution template exists from PR #54.
- Tests baseline: `4802 collected`.

## 4. Network target

| Field | Value |
| --- | --- |
| chain key | `avalanche_testnet` |
| chain ID | `43113` |
| network | `Avalanche Fuji Testnet` |
| RPC | `https://api.avax-test.network/ext/bc/C/rpc` |
| explorer | `https://testnet.snowtrace.io` |
| contract | `0x0b65d10FEcE517c3B6c6339CdE30fF4A8363751c` |
| native token | `AVAX` |
| status | `testnet` |

## 5. Secret handling policy

- no .env in Codex.
- no private key in ChatGPT.
- no seed phrase in GitHub.
- no keys in logs.
- no keys in commits.
- Private key only in Juan's local terminal under Juan's direct control.
- Prefer a burner wallet with minimal funds.

Never paste a private key, seed phrase, `.env`, RPC secret, wallet file, or signing payload into ChatGPT, GitHub, docs, issue comments, PR descriptions, screenshots, logs, or commits.

## 6. Manual prechecks

These prechecks are read-only or local documentation/test checks. They do not send transactions and do not require secrets.

```bash
git checkout main
git pull dof-mesh main
git status
npm run test:collect
python3 scripts/audit/onchain_readiness_dry_run.py
python3 scripts/audit/rpc_health_check_read_only.py --timeout 2 --json | python3 -m json.tool
python3 scripts/audit/single_testnet_manual_execution_template.py
```

Expected baseline:

- `npm run test:collect` reports `4802 tests collected`.
- RPC health check confirms Fuji chain ID `43113`.
- Manual template produces guidance only; it must not execute a transaction.

## 7. Wallet burner prechecks

Before any real transaction, Juan manually confirms:

- the address is a burner wallet;
- the burner has only minimal Fuji AVAX;
- the burner is not a production wallet;
- the burner contains no relevant assets;
- the private key was not pasted into AI, GitHub, docs, logs, screenshots, or shell transcripts intended for publication.

If any item is false or uncertain, abort.

## 8. Operation selection

The first permitted operation is one minimal write, such as proof or attestation registration, only if the exact ABI and method are confirmed.

Prohibited operations:

- deploy;
- admin;
- ownership transfer;
- upgrade;
- pause/unpause;
- `grantRole` / `revokeRole`;
- batch execution;
- multi-chain execution;
- mainnet execution.

If the ABI or method is not confirmed, abort and create a separate PR to confirm the ABI/method before any transaction.

## 9. Manual command pattern

Pattern only. Do not paste real secrets into docs.

```bash
cast send <CONTRACT_ADDRESS> <METHOD_SIGNATURE> <ARGS> --rpc-url <FUJI_RPC_URL> --private-key <LOCAL_BURNER_PRIVATE_KEY>
```

Rules:

- no private key in docs;
- no private key in ChatGPT;
- avoid saving secrets in shell history where possible;
- review chain ID before sending;
- review gas estimate before sending;
- use only the Fuji RPC URL;
- use only the confirmed Fuji contract address.

## 10. Gas and simulation gate

Before sending:

- estimate gas or simulate with a local tool;
- abort if gas is abnormally high;
- abort if chain ID is not `43113`;
- abort if the contract address does not match `0x0b65d10FEcE517c3B6c6339CdE30fF4A8363751c`;
- abort if the selected method differs from the confirmed minimal method;
- abort if simulation shows revert or unexpected state impact.

## 11. Execution approval gate

Juan must manually confirm all items before execution:

- network: Avalanche Fuji;
- chain ID: `43113`;
- contract: `0x0b65d10FEcE517c3B6c6339CdE30fF4A8363751c`;
- method;
- args;
- burner address;
- balance;
- gas estimate;
- no secrets exposed.

No agent may provide approval on Juan's behalf.

## 12. Evidence capture

After manual execution, record only public evidence:

- tx hash;
- block number;
- explorer URL;
- gas used;
- status;
- timestamp;
- contract address;
- method class;
- no private key;
- no .env;
- no seed phrase.

Do not capture terminal history, `.env`, local wallet paths, private RPC URLs, or raw signing material.

## 13. Failure handling

If the transaction fails:

- do not repeat automatically;
- capture public revert reason if available;
- review method, ABI, gas, RPC, chain ID and contract address;
- create a docs-only report;
- do not pass to mainnet;
- do not switch to another wallet without restarting the checklist.

## 14. Post-run report template

Use this template in a future evidence PR after Juan executes manually.

```markdown
# Fuji Burner Execution Evidence

- date:
- network: Avalanche Fuji Testnet
- chain_id: 43113
- contract: 0x0b65d10FEcE517c3B6c6339CdE30fF4A8363751c
- tx_hash:
- explorer_url:
- status:
- gas_used:
- notes:
- secrets_exposed: no
```

## 15. Abort conditions

Abort conditions:

- `.env` requested by Codex;
- private key requested by AI;
- branch dirty;
- `main` not updated;
- chain ID mismatch;
- contract mismatch;
- wallet is not burner;
- burner balance is high;
- method is admin;
- deploy;
- batch;
- mainnet;
- gas is high;
- logs contain secrets.

Any abort condition stops execution until a separate review resolves it.

## 16. Next step after runbook

Next PR after manual execution:

- `docs: record Fuji burner execution evidence`

That PR happens only after Juan performs the manual execution and public evidence exists. It must not include `.env`, private keys, seed phrases, private RPC endpoints, wallet files, local machine paths containing secrets, or raw signing payloads.

