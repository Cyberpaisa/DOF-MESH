# Fuji Transcript Verification Runbook

## 1. Purpose

This runbook prepares the first real transcript verification test on Avalanche Fuji.

The previous Fuji phase proved that DOF-MESH can perform a minimal manual write and readback on `DOFProofRegistry`. It did not prove `verified=true`, because proofId `3` used a placeholder hash and therefore correctly read back as `verified=false`.

This runbook prepares the transition from placeholder hash to a real `z3ProofHash` derived from an exact deterministic transcript. It does not authorize Codex or any agent to execute transactions.

## 2. Current state

- Expected current `proof_count`: `4`.
- `proofId 3` exists.
- `proofId 3` has `verified=false`.
- Previous write transaction: `0x9e337e37a9448bac6249d656762f848d869f35b58c50b6312b33a4e8b7a2a696`.
- Checkpoint #57 is closed.
- Baseline: `4802 tests collected`.

## 3. Network target

| Field | Value |
| --- | --- |
| network | `Avalanche Fuji Testnet` |
| chain key | `avalanche_testnet` |
| chain ID | `43113` |
| RPC | `https://api.avax-test.network/ext/bc/C/rpc` |
| explorer | `https://testnet.snowtrace.io` |
| contract | `0x0b65d10FEcE517c3B6c6339CdE30fF4A8363751c` |
| contract name | `DOFProofRegistry` |
| write method | `registerProof(uint256,uint256,bytes32,string,uint8)` |
| verify method | `verifyProof(uint256,bytes)` |
| read method | `getProof(uint256)` |
| count method | `getProofCount()` |

Methods involved:

- `registerProof(uint256,uint256,bytes32,string,uint8)`
- `verifyProof(uint256,bytes)`
- `getProof(uint256)`
- `getProofCount()`

## 4. Verification concept

`registerProof` stores a `z3ProofHash`.

`verifyProof(proofId, proofTranscript)` calculates `keccak256(proofTranscript)`.

If `keccak256(proofTranscript)` matches the stored `z3ProofHash`, the registry updates the proof and `verified` becomes `true`.

Therefore the next proof must use a real hash derived from the exact transcript bytes that will later be passed to `verifyProof`. If the transcript changes by one byte, including a space, the computed hash will differ and `verified=true` will not be reached.

## 5. Deterministic transcript proposal

Use this exact transcript:

```text
DOF-MESH Fuji transcript verification test 001 | agentId=1686 | invariants=8 | chainId=43113
```

Do not change any character after calculating the hash. Do not add a trailing newline. Do not change casing, punctuation, spacing, `agentId`, `invariants`, or `chainId`.

## 6. Hash calculation

Read/local only with Foundry:

```bash
cast keccak "DOF-MESH Fuji transcript verification test 001 | agentId=1686 | invariants=8 | chainId=43113"
```

Read/local only with Python:

```bash
python3 - <<'PY'
from Crypto.Hash import keccak

msg = b"DOF-MESH Fuji transcript verification test 001 | agentId=1686 | invariants=8 | chainId=43113"
k = keccak.new(digest_bits=256)
k.update(msg)
print("0x" + k.hexdigest())
PY
```

If `Crypto` is not installed locally, use `cast keccak` as the simple source. The computed hash becomes `<computed_keccak>` for `registerProof`.

## 7. Planned operation sequence

A. Read proof count before.

B. Calculate transcript hash.

C. Register new proof with:

- `agentId`: `1686`
- `trustScore`: `900000000000000000`
- `z3ProofHash`: `<computed_keccak>`
- `storageRef`: `ipfs://dofmesh/fuji/transcript-verification-test/001`
- `invariantsCount`: `8`

D. Read proof count after.

E. Determine new `proofId` as `proof_count_before`.

F. Read `getProof(newProofId)`.

G. Execute `verifyProof(newProofId, transcript)`.

H. Read `getProof(newProofId)` again.

I. Confirm `verified=true`.

## 8. Safety boundaries

- No Codex execution.
- No .env in Codex.
- No private key in ChatGPT.
- No private key in GitHub.
- No seed phrase in docs.
- No mainnet.
- No deploy.
- No admin method.
- No batch.
- No multi-chain.
- No repeated transaction if failure occurs.

Codex may audit and write dry-run documentation. Juan controls secrets and real execution.

## 9. Preflight commands

These commands are safe read-only/local checks. They must be run manually by Juan when preparing execution.

```bash
git checkout main
git pull dof-mesh main
git status
npm run test:collect
cast chain-id --rpc-url "$FUJI_RPC"
cast call "$DOF_FUJI_CONTRACT" "getProofCount()(uint256)" --rpc-url "$FUJI_RPC"
cast call "$DOF_FUJI_CONTRACT" "getProof(uint256)((uint256,uint256,bytes32,string,uint8,uint256,bool))" 3 --rpc-url "$FUJI_RPC"
```

Expected checks:

- `npm run test:collect` reports `4802 tests collected`.
- `cast chain-id` returns `43113`.
- `getProofCount()` is expected to return `4` before the new transcript verification flow.
- `getProof(3)` exists and `verified=false`.

## 10. Gas estimate gate

Estimate gas before sending. Use placeholders only in documentation.

Register estimate pattern:

```bash
cast estimate "$DOF_FUJI_CONTRACT" \
  "registerProof(uint256,uint256,bytes32,string,uint8)" \
  1686 \
  900000000000000000 \
  <computed_keccak> \
  "ipfs://dofmesh/fuji/transcript-verification-test/001" \
  8 \
  --from <BURNER_PUBLIC_ADDRESS> \
  --rpc-url "$FUJI_RPC"
```

Verify estimate pattern:

```bash
cast estimate "$DOF_FUJI_CONTRACT" \
  "verifyProof(uint256,bytes)" \
  <NEW_PROOF_ID> \
  "0x<TRANSCRIPT_BYTES_HEX>" \
  --from <BURNER_PUBLIC_ADDRESS> \
  --rpc-url "$FUJI_RPC"
```

Abort if gas is abnormal, if the chain ID is not `43113`, or if the contract does not match `0x0b65d10FEcE517c3B6c6339CdE30fF4A8363751c`.

## 11. Manual execution commands

Patterns only. These are not commands for Codex to execute.

Before manual execution, Juan may load the burner private key only in the local terminal:

```bash
read -s LOCAL_BURNER_PRIVATE_KEY
```

Register proof pattern:

```bash
cast send "$DOF_FUJI_CONTRACT" \
  "registerProof(uint256,uint256,bytes32,string,uint8)" \
  1686 \
  900000000000000000 \
  <computed_keccak> \
  "ipfs://dofmesh/fuji/transcript-verification-test/001" \
  8 \
  --rpc-url "$FUJI_RPC" \
  --private-key "$LOCAL_BURNER_PRIVATE_KEY"
```

Verify proof pattern:

```bash
cast send "$DOF_FUJI_CONTRACT" \
  "verifyProof(uint256,bytes)" \
  <NEW_PROOF_ID> \
  "0x<TRANSCRIPT_BYTES_HEX>" \
  --rpc-url "$FUJI_RPC" \
  --private-key "$LOCAL_BURNER_PRIVATE_KEY"
```

Rules:

- private key is entered only locally with `read -s`;
- no private key in docs;
- no private key in chat;
- no private key in GitHub;
- no `.env`;
- no Codex execution of `cast send`.

## 12. Evidence expected

For `registerProof`:

- tx hash;
- block number;
- gas used;
- `proof_count_before`;
- `proof_count_after`;
- new `proofId`;
- real `z3ProofHash`.

For `verifyProof`:

- tx hash;
- block number;
- gas used;
- `verified_before`;
- `verified_after=true`.

Evidence must include only public chain data and non-secret local observations.

## 13. Abort conditions

Abort conditions:

- chain ID is not `43113`;
- contract mismatch;
- proof count unexpected;
- hash does not match transcript;
- gas abnormal;
- command includes mainnet;
- command includes deploy;
- command includes admin method;
- private key appears in logs;
- `.env` requested by AI;
- Codex attempts to execute `cast send`;
- `verified` is already `true` before `verifyProof` without explanation.

Do not retry automatically after an abort. Create a docs-only review note first.

## 14. Next step

After this runbook:

- PR #59: script helper local para generar transcript hash y calldata preview sin secrets.
- Then controlled manual execution.
- Then evidence PR documenting public results only.

