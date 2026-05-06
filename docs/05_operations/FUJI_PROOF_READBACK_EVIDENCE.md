# Fuji Proof Readback Evidence

## 1. Summary

DOF-MESH completed a read-only on-chain readback of the Fuji proof registered during the first controlled manual burner execution.

This document confirms that the proof written in the Fuji burner execution evidence is readable from the deployed DOFProofRegistry contract and matches the expected payload.

No transaction was sent during this readback.

No wallet, private key, seed phrase, `.env`, signer, or broadcast was used.

## 2. Network

| Field | Value |
|---|---|
| Network | Avalanche Fuji Testnet |
| Chain ID | 43113 |
| Contract | 0x0b65d10FEcE517c3B6c6339CdE30fF4A8363751c |
| Read method | getProof(uint256) |
| Proof ID | 3 |

## 3. Related write transaction

| Field | Value |
|---|---|
| Previous evidence PR | docs: add Fuji burner execution evidence |
| Transaction hash | 0x9e337e37a9448bac6249d656762f848d869f35b58c50b6312b33a4e8b7a2a696 |
| Block number | 55029036 |
| Method used for write | registerProof(uint256,uint256,bytes32,string,uint8) |
| Proof count before write | 3 |
| Proof count after write | 4 |

## 4. Readback command class

The readback used read-only calls:

```bash
cast chain-id --rpc-url "$FUJI_RPC"

cast call \
  "$DOF_FUJI_CONTRACT" \
  "getProofCount()(uint256)" \
  --rpc-url "$FUJI_RPC"

cast call \
  "$DOF_FUJI_CONTRACT" \
  "getProof(uint256)((uint256,uint256,bytes32,string,uint8,uint256,bool))" \
  3 \
  --rpc-url "$FUJI_RPC"
