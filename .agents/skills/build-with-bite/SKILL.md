---
name: build-with-bite
description: Build with BITE Protocol for privacy on SKALE. Covers encrypted transactions, CTX, SDK usage. Use for privacy dApps, confidential voting, encrypted transfers.
---

# Build with BITE

BITE Protocol provides threshold encryption on SKALE chains. Encrypts transaction data so mempool only sees encrypted bytes.

## What is BITE?

- Encrypts `to` + `calldata` in transactions
- Threshold decryption: 2t+1 of 3t+1 validators needed
- Works on all Solidity contracts (no contract changes needed)
- MEV-resistant

## Primitives

| Primitive | Description | Chains |
|-----------|-------------|--------|
| Encrypted TX | Encrypt `to` + `calldata` | SKALE Base, SKALE Base Sepolia |
| CTX | Conditional Transactions | BITE V2 Sandbox 2 |

## Chain Requirements

**Encrypted Transactions:**
- SKALE Base (1187947933)
- SKALE Base Sepolia (324705682)

**CTX:**
- BITE V2 Sandbox 2 (coordinate with SKALE team)

## SDK Usage

Install: `npm install @skalenetwork/bite`

```typescript
import { BITE } from '@skalenetwork/bite';
const bite = new BITE('https://base-sepolia-testnet.skalenodes.com/v1/jubilant-horrible-ancha');

// Encrypt transaction
const encrypted = await bite.encryptTransaction({ 
    to: "0xContractAddress", 
    data: "0xCalldata" 
});

// Send with wallet - CRITICAL: set gas manually
const tx = await wallet.sendTransaction({
    ...encrypted,
    gasLimit: 300_000
});
```

### Get Decrypted Data

```typescript
const { data, to } = await bite.getDecryptedTransactionData(txHash);
```

### Committee Info

```typescript
const committees = await bite.getCommitteesInfo();
// length === 2 means rotation in progress (3 min window)
```

## Solidity (CTX)

Install: `forge install skalenetwork/bite-solidity`

```solidity
pragma solidity >=0.8.27;

import { BITE } from "@skalenetwork/bite-solidity/BITE.sol";
import { IBiteSupplicant } from "@skalenetwork/bite-solidity/interfaces/IBiteSupplicant.sol";

contract Secret is IBiteSupplicant {
    bytes public message;
    
    function reveal(bytes calldata encrypted) external payable {
        BITE.submitCTX(
            BITE.SUBMIT_CTX_ADDRESS,
            msg.value / tx.gasprice,
            encrypted,
            new bytes[](0)
        );
    }
    
    function onDecrypt(bytes[] calldata decrypted, bytes[] calldata) external override {
        message = decrypted[0];
    }
}
```

### Compiler Settings

For CTX contracts:
- Solidity >=0.8.27
- EVM istanbul

```toml
solc_version = "0.8.27"
evm_version = "istanbul"
```

## Key Rules

- **Gas**: Always set manually (default 300k) - estimateGas doesn't work with BITE
- **Committee**: 3t+1 nodes, 2t+1 to decrypt
- **Rotation**: SDK handles dual encryption automatically
- **Sender**: Always public (transaction is signed)
- **Encrypted**: `to` address and `calldata`
- **Public**: sender, value, gas used

## Visibility Summary

| Data | Encrypted |
|------|-----------|
| Recipient (to) | ✅ |
| Calldata | ✅ |
| Sender | ❌ |
| Value | ❌ |
| Gas used | ❌ |

Reference: [Encrypted Transactions](https://docs.skale.space/developers/bite-protocol/encrypted-transactions.md)
Reference: [CTX](https://docs.skale.space/developers/bite-protocol/conditional-transactions.md)
Reference: [npm](https://www.npmjs.com/package/@skalenetwork/bite)
