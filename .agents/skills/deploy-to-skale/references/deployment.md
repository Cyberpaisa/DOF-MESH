# Deployment

## Foundry

```bash
forge install dirtroad/skale-rng

forge script script/Deploy.s.sol \
  --rpc-url $SKALE_RPC \
  --private-key $PRIVATE_KEY \
  --legacy \
  --broadcast
```

## Hardhat

```typescript
const config: HardhatUserConfig = {
    networks: {
        skaleBaseSepolia: {
            url: process.env.SKALE_RPC,
            chainId: 324705682,
            accounts: [process.env.PRIVATE_KEY]
        }
    }
};
```

## CTX Contracts

Requires:
- Solidity >=0.8.27
- EVM istanbul

```toml
solc_version = "0.8.27"
evm_version = "istanbul"
```

Reference: [Setup Foundry](https://docs.skale.space/cookbook/deployment/setup-foundry.md)
