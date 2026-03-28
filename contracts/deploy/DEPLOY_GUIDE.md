# DOF Mesh Legion — Guía de Deploy Multichain

## Contrato: DOFProofRegistry.sol

Contrato único, compatible con cualquier EVM. Registra attestations de verificación Z3 on-chain.

## Chains Target

| Chain | Chain ID | Testnet | Faucet | Estado |
|-------|----------|---------|--------|--------|
| Avalanche | 43114 | Fuji (43113) | https://core.app/tools/testnet-faucet/ | ✅ LIVE |
| Conflux eSpace | 1030 | Testnet (71) | https://efaucet.confluxnetwork.org/ | ✅ Testnet deployado |
| Base | 8453 | Sepolia (84532) | https://www.coinbase.com/faucets/base-ethereum-goerli-faucet | 🟡 Pendiente |
| Celo | 42220 | Alfajores (44787) | https://faucet.celo.org/ | 🟡 Pendiente |
| Polygon | 137 | Amoy (80002) | https://faucet.polygon.technology/ | 🟡 Pendiente |
| Arbitrum | 42161 | Sepolia (421614) | https://www.alchemy.com/faucets/arbitrum-sepolia | 🟡 Pendiente |
| Ethereum | 1 | Sepolia (11155111) | https://sepoliafaucet.com/ | 🟡 Pendiente |
| Tempo (Stripe) | 4217 | — | Stripe dashboard | ✅ LIVE |

## Deploy Rápido por Chain

### Requisitos
```bash
# Instalar forge (Foundry)
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

### Deploy con Forge
```bash
# Variables de entorno (NUNCA commitear)
export PRIVATE_KEY="tu_private_key"
export RPC_URL="rpc_de_la_chain"

# Compilar
forge build --contracts contracts/DOFProofRegistry.sol

# Deploy
forge create contracts/DOFProofRegistry.sol:DOFProofRegistry \
  --rpc-url $RPC_URL \
  --private-key $PRIVATE_KEY \
  --broadcast
```

### Deploy por chain (copiar y pegar cambiando RPC_URL):

```bash
# Base Sepolia (testnet)
export RPC_URL="https://sepolia.base.org"
forge create contracts/DOFProofRegistry.sol:DOFProofRegistry --rpc-url $RPC_URL --private-key $PRIVATE_KEY --broadcast

# Celo Alfajores (testnet)
export RPC_URL="https://alfajores-forno.celo-testnet.org"
forge create contracts/DOFProofRegistry.sol:DOFProofRegistry --rpc-url $RPC_URL --private-key $PRIVATE_KEY --broadcast

# Polygon Amoy (testnet)
export RPC_URL="https://rpc-amoy.polygon.technology"
forge create contracts/DOFProofRegistry.sol:DOFProofRegistry --rpc-url $RPC_URL --private-key $PRIVATE_KEY --broadcast

# Arbitrum Sepolia (testnet)
export RPC_URL="https://sepolia-rollup.arbitrum.io/rpc"
forge create contracts/DOFProofRegistry.sol:DOFProofRegistry --rpc-url $RPC_URL --private-key $PRIVATE_KEY --broadcast

# Ethereum Sepolia (testnet)
export RPC_URL="https://ethereum-sepolia-rpc.publicnode.com"
forge create contracts/DOFProofRegistry.sol:DOFProofRegistry --rpc-url $RPC_URL --private-key $PRIVATE_KEY --broadcast

# Conflux eSpace (mainnet)
export RPC_URL="https://evm.confluxrpc.com"
forge create contracts/DOFProofRegistry.sol:DOFProofRegistry --rpc-url $RPC_URL --private-key $PRIVATE_KEY --broadcast
```

## Después del Deploy

1. Copiar la address del contrato
2. Actualizar `core/chains_config.json` → campo `contract_address`
3. Actualizar status de "planned" a "testnet" o "mainnet"
4. Verificar contrato en el explorer de la chain

## Verificar Contrato en Explorer

```bash
forge verify-contract <CONTRACT_ADDRESS> contracts/DOFProofRegistry.sol:DOFProofRegistry \
  --chain-id <CHAIN_ID> \
  --etherscan-api-key <API_KEY>
```

## Wallet DOF

**IMPORTANTE:** Usar UNA sola wallet EVM para todos los deploys.
La misma private key funciona en todas las chains EVM.
NUNCA guardar la private key en git ni en archivos del proyecto.

Guardar en: `~/.dof/wallet.env` (fuera del repo)

```bash
# ~/.dof/wallet.env (NO commitear)
DOF_DEPLOYER_ADDRESS=0x...
DOF_PRIVATE_KEY=0x...
```

Para cargar:
```bash
source ~/.dof/wallet.env
export PRIVATE_KEY=$DOF_PRIVATE_KEY
```

## Faucets — Obtener Tokens de Testnet

Visitar cada faucet con la wallet DOF:

1. **Base Sepolia:** https://www.coinbase.com/faucets/base-ethereum-goerli-faucet
2. **Celo Alfajores:** https://faucet.celo.org/
3. **Polygon Amoy:** https://faucet.polygon.technology/
4. **Arbitrum Sepolia:** https://www.alchemy.com/faucets/arbitrum-sepolia
5. **Ethereum Sepolia:** https://sepoliafaucet.com/
6. **Conflux Testnet:** https://efaucet.confluxnetwork.org/
7. **Avalanche Fuji:** https://core.app/tools/testnet-faucet/

## Estado de Deploys

| Chain | Testnet | Contract Address | Mainnet | Contract Address |
|-------|---------|------------------|---------|------------------|
| Avalanche | — | — | ✅ | `0x88f6043B...` |
| Conflux | ✅ | `0x554cCa8c...` | 🟡 | — |
| Tempo | — | — | ✅ | ver tempo/broadcast/ |
| Base | 🟡 | — | 🟡 | — |
| Celo | 🟡 | — | 🟡 | — |
| Polygon | 🟡 | — | 🟡 | — |
| Arbitrum | 🟡 | — | 🟡 | — |
| Ethereum | 🟡 | — | 🟡 | — |

---
*DOF Mesh Legion v0.5.1 — Chain Agnostic*
*Un contrato. Cualquier EVM. Soberanía total.*
