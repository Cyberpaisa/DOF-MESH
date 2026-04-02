# SDK

Install: `npm install @skalenetwork/bite`

```typescript
import { BITE } from '@skalenetwork/bite';
const bite = new BITE('https://base-sepolia-testnet.skalenodes.com/v1/jubilant-horrible-ancha');

// Encrypt transaction
const encrypted = await bite.encryptTransaction({ 
    to: "0xContractAddress", 
    data: "0xCalldata" 
});

// Send with wallet
const tx = await wallet.sendTransaction({
    ...encrypted,
    gasLimit: 300_000  // CRITICAL: always set manually
});
```

## Get Decrypted Data

```typescript
const { data, to } = await bite.getDecryptedTransactionData(txHash);
```

## Committee Info

```typescript
const committees = await bite.getCommitteesInfo();
// length === 2 means rotation in progress (3 min window)
```

Reference: [npm](https://www.npmjs.com/package/@skalenetwork/bite)
