# DOF-MESH: Guia de Deploy en Tempo Blockchain

Deploy de contratos ERC-8004 (Identity + Reputation) en Tempo testnet.

## Prerequisitos

- Foundry instalado (`forge --version`)
- Wallet con pathUSD para gas
- Private key del deployer

## Red Tempo Testnet (Moderato)

| Campo | Valor |
|-------|-------|
| Network Name | Tempo Testnet (Moderato) |
| RPC URL | `https://rpc.moderato.tempo.xyz` |
| Chain ID | `42431` |
| Currency | pathUSD |
| Explorer | `https://explore.tempo.xyz` |

## Paso 1: Obtener pathUSD del Faucet

1. Ir a [faucets.chain.link/tempo-testnet](https://faucets.chain.link/tempo-testnet)
2. Conectar wallet o pegar tu address
3. Solicitar pathUSD de testnet
4. Verificar que llegaron los fondos en el explorer

## Paso 2: Configurar MetaMask

Agregar red custom en MetaMask:

- **Network Name:** Tempo Testnet (Moderato)
- **RPC URL:** `https://rpc.moderato.tempo.xyz`
- **Chain ID:** `42431`
- **Currency Symbol:** pathUSD
- **Block Explorer:** `https://explore.tempo.xyz`

## Paso 3: Exportar Private Key

```bash
export DEPLOYER_PRIVATE_KEY=0xTU_PRIVATE_KEY_AQUI
```

**NUNCA** commitear la private key. Usa variables de entorno o un `.env` que este en `.gitignore`.

## Paso 4: Ejecutar Deploy

```bash
cd ~/DOF-MESH
chmod +x scripts/deploy_tempo.sh
./scripts/deploy_tempo.sh
```

El script hace:
1. Verifica que Foundry este instalado
2. Instala `forge-std` si no existe
3. Compila los contratos
4. Ejecuta tests
5. Deploya a Tempo testnet

## Paso 5: Verificar en Explorer

Despues del deploy, el script imprime las addresses. Verificalas en:

```
https://explore.tempo.xyz/address/0x...
```

## Paso 6: Registrar Agentes DOF

Una vez deployado, registrar agentes con cast:

```bash
# Registrar un agente
cast send <IDENTITY_ADDRESS> \
    "register(string)" \
    "https://metadata.dof-mesh.xyz/agent/1.json" \
    --rpc-url https://rpc.moderato.tempo.xyz \
    --private-key $DEPLOYER_PRIVATE_KEY

# Dar feedback de reputacion
cast send <REPUTATION_ADDRESS> \
    "giveFeedback(address,uint8,string)" \
    0xAGENT_ADDRESS 85 "Excellent performance" \
    --rpc-url https://rpc.moderato.tempo.xyz \
    --private-key $DEPLOYER_PRIVATE_KEY

# Consultar agente
cast call <IDENTITY_ADDRESS> \
    "getAgent(uint256)(address,string,uint256,bool)" 1 \
    --rpc-url https://rpc.moderato.tempo.xyz

# Consultar score promedio
cast call <REPUTATION_ADDRESS> \
    "getAverageScore(address)(uint256)" 0xAGENT_ADDRESS \
    --rpc-url https://rpc.moderato.tempo.xyz
```

## Contratos

### DOFIdentityRegistry
- `register(metadataURI)` — Registrar agente (1 por address)
- `updateMetadata(tokenId, metadataURI)` — Actualizar metadata
- `deactivate(tokenId)` — Desactivar agente
- `getAgent(tokenId)` — Consultar agente
- `isRegistered(address)` — Verificar registro
- `totalAgents()` — Total de agentes registrados

### DOFReputationRegistry
- `giveFeedback(to, score, comment)` — Dar feedback (0-100)
- `getAverageScore(agent)` — Score promedio
- `getFeedbackCount(agent)` — Cantidad de feedbacks
- `getLatestFeedback(agent, count)` — Ultimos N feedbacks

## Troubleshooting

### "Already registered"
Cada address solo puede registrar 1 agente. Usa otra wallet o llama `deactivate()` primero.

### "Insufficient funds"
Necesitas pathUSD para gas. Ve al faucet: `faucets.chain.link/tempo-testnet`

### forge build falla
```bash
cd contracts/tempo
forge install foundry-rs/forge-std --no-commit
forge build
```

### RPC no responde
Verifica que el RPC este activo: `cast chain-id --rpc-url https://rpc.moderato.tempo.xyz`

## Siguiente Paso: Integrar MPP

Despues del deploy, integrar el Mesh Payment Protocol (MPP) para pagos gasless entre agentes usando pathUSD como moneda base en Tempo.
