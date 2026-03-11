# DOF Multichain Support

DOF is chain-agnostic by design. The Python SDK (Z3 proofs, GenericAdapter,
TrustGateway) is 100% off-chain and never changes. Only the on-chain attestation
layer is chain-specific — configured via `core/chains_config.json`.

## Adding a new EVM chain

1. Add entry to `core/chains_config.json` with chain_id, rpc_url, status
2. Add network to `hardhat.config.js`
3. Run: `npx hardhat run contracts/deploy/deploy_multichain.js --network <name>`
4. Contract address auto-updates in `chains_config.json`

No code changes required. True plug-and-play.

## Supported Chains

| Chain | chain_id | Status | Contract |
|---|---|---|---|
| Avalanche C-Chain | 43114 | ✅ mainnet | 0x88f6...C052 |
| Conflux eSpace | 1030 | 🔄 pending deploy | — |
| Conflux Testnet | 71 | 🧪 testnet | — |
| Ethereum | 1 | 📋 planned | — |
| Ethereum Sepolia | 11155111 | 🧪 testnet | — |
| Base | 8453 | 📋 planned | — |
| Base Sepolia | 84532 | 🧪 testnet | — |
| Arbitrum One | 42161 | 📋 planned | — |
| Arbitrum Sepolia | 421614 | 🧪 testnet | — |
| Polygon | 137 | 📋 planned | — |
| Polygon Amoy | 80002 | 🧪 testnet | — |
| Celo | 42220 | 📋 planned | — |
| Celo Alfajores | 44787 | 🧪 testnet | — |

## Usage

```python
from core.chain_adapter import DOFChainAdapter

# Por nombre
adapter = DOFChainAdapter.from_chain_name("conflux_testnet")

# Por chain_id
adapter = DOFChainAdapter.from_chain_id(71)

# Publicar attestation
result = adapter.publish_attestation(
    proof_hash="0x...",
    agent_id=1687,
    metadata="run_id=abc123"
)

# Verificar
valid = adapter.verify_proof("0x...")

# Listar chains disponibles
chains = DOFChainAdapter.list_supported_chains()
```

## Non-EVM chains

**Stellar (Soroban):** Requires separate Rust contract. Planned for Phase 9.
The Python SDK layer remains identical — only the on-chain adapter differs.

## Gas considerations

Chains with `gas_multiplier > 1.0` have higher storage costs than Ethereum.
Conflux eSpace (2.0x) — benchmark Merkle batch costs before setting pricing.

## Contracts

DOFProofRegistry.sol and DOFEvaluator.sol are identical across all EVM chains.
Deploy with: `npx hardhat run contracts/deploy/deploy_multichain.js --network <name>`
