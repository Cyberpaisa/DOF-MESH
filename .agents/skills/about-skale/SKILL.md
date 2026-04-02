---
name: about-skale
description: Learn about SKALE Network - what it is, chain types, gas models. Use for understanding SKALE architecture.
---

# About SKALE

SKALE is a network of elastic blockchain networks. Each SKALE Chain is an independent EVM-compatible chain with its own validators.

## Chain Types

### SKALE Base (Credit Chain)
Uses **Compute Credits** - prepaid credits that can be purchased.

| Network | Chain ID | RPC |
|---------|----------|-----|
| Testnet | 324705682 | `https://base-sepolia-testnet.skalenodes.com/v1/jubilant-horrible-ancha` |
| Mainnet | 1187947933 | `https://skale-base.skalenodes.com/v1/base` |

### Zero Gas Fee Chains (sFUEL)
Uses **sFUEL** - valueless gas token. Users pay ~0, validators stake SKL to cover costs.

| Chain | Chain ID | RPC |
|-------|----------|-----|
| Europa Hub | 2046399126 | `https://mainnet.skalenodes.com/v1/elated-tan-skat` |
| Calypso Hub | 1564830818 | `https://mainnet.skalenodes.com/v1/honorable-steel-rasalhague` |
| Nebula Hub | 1482601649 | `https://mainnet.skalenodes.com/v1/green-giddy-denebola` |

## Gas Models

| Model | Description | User Pays | Chains |
|-------|------------|-----------|--------|
| sFUEL | Valueless gas token | ~0 | Europa, Calypso, Nebula |
| Compute Credits | Prepaid credits | Credits | SKALE Base |
| Proof-of-Work | Solve PoW puzzle | ~0 | Optional |
| Gas Chain | Real token as gas | Token | Configurable |

## Key Concepts

- **sFUEL**: Valueless gas token for EVM compatibility
- **Compute Credits**: Prepaid compute units on SKALE Base
- **Validator Nodes**: 3t+1 nodes secure each chain
- **Message Proxy**: Cross-chain messaging via IMA

## Architecture

- **Elastic**: Chains can scale resources dynamically
- **Independent**: Each chain has its own validators
- **EVM-Compatible**: Works with standard Ethereum tooling

## When to Use SKALE

- High-frequency transactions (zero/low fees)
- Gaming and NFT apps (no gas per transaction)
- AI agents with micropayments (x402)
- Privacy-sensitive apps (BITE Protocol)
- Building where fees would be a bottleneck

## SKALE vs Other Chains

| Feature | SKALE | Ethereum L1 | Optimism/Arbitrum |
|---------|-------|-------------|-------------------|
| Block time | ~1s | ~12s | ~2s |
| Gas fees | ~0 | High | Low |
| Independence | Full | N/A | Shared |

For deployment info, see `deploy-to-skale` skill.
For privacy (BITE), see `build-with-bite` skill.
For AI agent payments (x402), see `x402-on-skale` skill.

Reference: [Docs](https://docs.skale.space)
