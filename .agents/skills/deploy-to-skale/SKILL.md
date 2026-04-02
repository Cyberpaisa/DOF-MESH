---
name: deploy-to-skale
description: Deploy contracts to SKALE chains. Covers chain selection, RNG, bridge, deployment setup. Use for deploying smart contracts to SKALE.
---

# Deploy to SKALE

This guide covers deploying smart contracts to SKALE chains.

## Chain Selection

### Default: SKALE Base (Recommended)

| Network | Chain ID | RPC | Explorer |
|---------|----------|-----|----------|
| Testnet | 324705682 | `https://base-sepolia-testnet.skalenodes.com/v1/jubilant-horrible-ancha` | `https://base-sepolia-testnet-explorer.skalenodes.com/` |
| Mainnet | 1187947933 | `https://skale-base.skalenodes.com/v1/base` | `https://skale-base-explorer.skalenodes.com/` |

### Ethereum-connected

| Chain | Chain ID | RPC | Explorer |
|-------|----------|-----|----------|
| Europa Hub | 2046399126 | `https://mainnet.skalenodes.com/v1/elated-tan-skat` | `https://elated-tan-skat.explorer.mainnet.skalenodes.com/` |
| Calypso Hub | 1564830818 | `https://mainnet.skalenodes.com/v1/honorable-steel-rasalhague` | `https://honorable-steel-rasalhague.explorer.mainnet.skalenodes.com/` |
| Nebula Hub | 1482601649 | `https://mainnet.skalenodes.com/v1/green-giddy-denebola` | `https://green-giddy-denebola.explorer.mainnet.skalenodes.com/` |

## Gas Models

- **SKALE Base**: Compute Credits (prepaid)
- **Others**: sFUEL (~0 cost)

## Deployment

### Foundry

```bash
# Install Foundry if needed
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Install SKALE RNG library
forge install dirtroad/skale-rng

# Deploy
forge script script/Deploy.s.sol \
  --rpc-url $SKALE_RPC \
  --private-key $PRIVATE_KEY \
  --legacy \
  --broadcast
```

### Hardhat

```typescript
// hardhat.config.ts
const config: HardhatUserConfig = {
    networks: {
        skaleBaseSepolia: {
            url: process.env.SKALE_RPC,
            chainId: 324705682,
            accounts: [process.env.PRIVATE_KEY]
        },
        skaleBase: {
            url: process.env.SKALE_RPC,
            chainId: 1187947933,
            accounts: [process.env.PRIVATE_KEY]
        }
    },
    solidity: { version: "0.8.27" }
};

export default config;
```

```bash
npx hardhat run scripts/deploy.ts --network skaleBaseSepolia
```

### CTX Contracts (Conditional Transactions)

Requires:
- Solidity >=0.8.27
- EVM istanbul

```toml
# foundry.toml
solc_version = "0.8.27"
evm_version = "istanbul"
```

## RNG (Random Numbers)

Native random via precompile at `0x18`:

```solidity
import "@dirtroad/skale-rng/contracts/RNG.sol";

contract MyContract is RNG {
    function random() external view returns (uint256) {
        return getRandomNumber();
    }
    
    function randomRange(uint256 min, uint256 max) external view returns (uint256) {
        return getNextRandomRange(min, max);
    }
}
```

Notes:
- RNG is native to SKALE (relies on SKALE Consensus)
- On local testing or other chains, returns 0
- Multiple calls in same block return same value

## Bridge

### Token Bridge

```typescript
const token = new Contract(tokenAddress, ERC20_ABI, signer);
const bridge = new Contract(bridgeAddress, BRIDGE_ABI, signer);

await token.approve(bridgeAddress, amount);
await bridge.depositERC20(tokenAddress, amount, targetChain, receiver);
```

### IMA Messaging

MessageProxy: `0xd2AAa00100000000000000000000000000000000`

## x402 (AI Agent Payments)

For x402 payments, see `x402-on-skale` skill.

Quick setup:

```bash
npm install @x402/core @x402/evm @x402/hono
```

```typescript
import { paymentMiddleware, x402ResourceServer } from "@x402/hono";
import { HTTPFacilitatorClient } from "@x402/core/server";

const client = new HTTPFacilitatorClient({ url: "https://facilitator.payai.network" });
const server = new x402ResourceServer(client);

app.use(paymentMiddleware({
    "GET /api/premium": {
        accepts: [{
            scheme: "exact",
            network: "eip155:324705682",
            payTo: "0xYourAddress",
            price: { 
                amount: "10000",
                asset: "0x2e08028E3C4c2356572E096d8EF835cD5C6030bD"
            }
        }]
    }
}, server));
```

Payment tokens:
- Bridged USDC: `0x2e08028E3C4c2356572E096d8EF835cD5C6030bD`
- Axios USD: `0x61a26022927096f444994dA1e53F0FD9487EAfcf`

## BITE (Privacy)

For encrypted transactions, see `build-with-bite` skill.

Key points:
- Gas: Always set manually (300k default)
- estimateGas doesn't work with BITE
- Chains: SKALE Base, SKALE Base Sepolia

Reference: [Docs](https://docs.skale.space/llms.txt.md)
