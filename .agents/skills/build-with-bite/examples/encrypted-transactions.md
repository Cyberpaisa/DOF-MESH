# BITE Protocol Examples

## Complete Encrypted Transaction Flow

```typescript
import { BITE } from '@skalenetwork/bite';
import { ethers } from 'ethers';

// Initialize BITE SDK
const bite = new BITE('https://base-sepolia-testnet.skalenodes.com/v1/jubilant-horrible-ancha');

// Setup wallet
const provider = new ethers.JsonRpcProvider('https://base-sepolia-testnet.skalenodes.com/v1/jubilant-horrible-ancha');
const wallet = new ethers.Wallet(process.env.PRIVATE_KEY!, provider);

async function sendEncryptedTransaction() {
    // Contract interaction data
    const contractAddress = "0x1234567890123456789012345678901234567890";
    const data = "0x..."; // Your contract call data
    
    // Encrypt the transaction
    const encrypted = await bite.encryptTransaction({
        to: contractAddress,
        data: data,
        value: "0"
    });
    
    // Send with manual gas limit (REQUIRED for BITE)
    const tx = await wallet.sendTransaction({
        ...encrypted,
        gasLimit: 300_000  // Always set manually - estimateGas doesn't work
    });
    
    console.log("Transaction sent:", tx.hash);
    const receipt = await tx.wait();
    console.log("Confirmed in block:", receipt?.blockNumber);
    
    return tx.hash;
}

// Get decrypted data after execution
async function viewDecryptedTransaction(txHash: string) {
    const { data, to } = await bite.getDecryptedTransactionData(txHash);
    console.log("Decrypted to:", to);
    console.log("Decrypted data:", data);
}

// Check committee status
async function checkCommitteeStatus() {
    const committees = await bite.getCommitteesInfo();
    console.log("Active committees:", committees.length);
    
    if (committees.length === 2) {
        console.log("⚠️ Committee rotation in progress (3 min window)");
    }
}
```

## Complete CTX (Conditional Transaction) Contract

```solidity
// SPDX-License-Identifier: MIT
pragma solidity >=0.8.27;

import { BITE } from "@skalenetwork/bite-solidity/BITE.sol";
import { IBiteSupplicant } from "@skalenetwork/bite-solidity/interfaces/IBiteSupplicant.sol";

contract SecretRevealer is IBiteSupplicant {
    bytes public revealedSecret;
    address public owner;
    
    event SecretSubmitted(bytes32 indexed ctxId);
    event SecretRevealed(bytes secret);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }
    
    constructor() {
        owner = msg.sender;
    }
    
    // Submit encrypted secret for conditional revelation
    function submitSecret(bytes calldata encryptedSecret) external payable onlyOwner {
        require(msg.value >= tx.gasprice * 100000, "Insufficient gas payment");
        
        BITE.submitCTX(
            BITE.SUBMIT_CTX_ADDRESS,
            msg.value / tx.gasprice,
            encryptedSecret,
            new bytes[](0)
        );
        
        emit SecretSubmitted(keccak256(encryptedSecret));
    }
    
    // Called by BITE protocol when secret is decrypted
    function onDecrypt(
        bytes[] calldata decrypted, 
        bytes[] calldata
    ) external override {
        require(msg.sender == BITE.SUBMIT_CTX_ADDRESS, "Only BITE");
        
        revealedSecret = decrypted[0];
        emit SecretRevealed(decrypted[0]);
    }
    
    function getSecret() external view returns (bytes memory) {
        require(revealedSecret.length > 0, "Secret not yet revealed");
        return revealedSecret;
    }
}
```

## Foundry.toml for BITE Contracts

```toml
[profile.default]
src = "src"
out = "out"
libs = ["lib"]

# Required for BITE/CTX contracts
solc_version = "0.8.27"
evm_version = "istanbul"

[rpc_endpoints]
skale_base_sepolia = "https://base-sepolia-testnet.skalenodes.com/v1/jubilant-horrible-ancha"
skale_base = "https://skale-base.skalenodes.com/v1/base"
```
