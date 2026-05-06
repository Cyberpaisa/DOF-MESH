# Fuji Burner Execution Evidence

## 1. Summary

DOF-MESH completed its first controlled manual testnet write on Avalanche Fuji using a burner wallet.

This execution followed the previously merged safety path:

- PR #49: offline on-chain readiness dry-run
- PR #51: read-only RPC health check
- PR #53: testnet burner execution checklist
- PR #54: single-testnet manual execution template
- PR #55: Fuji burner manual execution runbook

No Codex/agent-controlled execution was used for the final transaction.

Operational rule preserved:

`Codex audits and writes dry-runs; Juan controls secrets and real execution.`

## 2. Network

| Field | Value |
|---|---|
| Network | Avalanche Fuji Testnet |
| Chain ID | 43113 |
| Native token | AVAX |
| Contract | 0x0b65d10FEcE517c3B6c6339CdE30fF4A8363751c |
| Method | registerProof(uint256,uint256,bytes32,string,uint8) |

## 3. Transaction

| Field | Value |
|---|---|
| Status | success |
| Transaction hash | 0x9e337e37a9448bac6249d656762f848d869f35b58c50b6312b33a4e8b7a2a696 |
| Block number | 55029036 |
| Gas used | 213525 |
| From | 0x43a9Fd328909c659e60d9f8E589bE846c3c0E14e |
| To | 0x0b65d10FEcE517c3B6c6339CdE30fF4A8363751c |
| Explorer | https://testnet.snowtrace.io/tx/0x9e337e37a9448bac6249d656762f848d869f35b58c50b6312b33a4e8b7a2a696 |

## 4. Payload

| Field | Value |
|---|---|
| agentId | 1686 |
| trustScore | 850000000000000000 |
| z3ProofHash | 0x1111111111111111111111111111111111111111111111111111111111111111 |
| storageRef | ipfs://dofmesh/fuji/manual-burner-test/001 |
| invariantsCount | 8 |

## 5. State change

| Check | Value |
|---|---|
| proof_count_before | 3 |
| proof_count_after | 4 |
| expected_delta | +1 |
| observed_delta | +1 |

## 6. Public log evidence

The emitted log references:

- contract: 0x0b65d10fece517c3b6c6339cde30ff4a8363751c
- transactionHash: 0x9e337e37a9448bac6249d656762f848d869f35b58c50b6312b33a4e8b7a2a696
- blockNumber: 55029036
- event topic: 0xeb76776a23294e1f486bffa083169bebd52ed00bf5299f91d6c4ced229e41bc1
- proofId topic: 3
- agentId topic: 1686

## 7. Safety confirmation

This evidence does not include:

- private key
- seed phrase
- `.env`
- private RPC endpoint
- raw signed transaction
- local wallet file
- local secret path

The transaction was manually executed by Juan using a burner wallet.

## 8. Result

The Fuji burner execution succeeded.

DOF-MESH now has a public testnet write confirming that the deployed DOFProofRegistry contract can register a proof on Avalanche Fuji and update on-chain state as expected.
