# DOF-MESH: Deploy Guide on Tempo Blockchain

Deploy of ERC-8004 contracts (Identity + Reputation) on Tempo testnet.

## Prerequisites

- Foundry installed (`forge --version`)
- Wallet with pathUSD for gas
- Deployer private key

## Tempo Testnet Network (Moderato)

| Field | Value |
|-------|-------|
| Network Name | Tempo Testnet (Moderato) |
| RPC URL | `https://rpc.moderato.tempo.xyz` |
| Chain ID | `42431` |
| Currency | pathUSD |
| Explorer | `https://explore.tempo.xyz` |

## Step 1: Get pathUSD from Faucet

1. Go to [faucets.chain.link/tempo-testnet](https://faucets.chain.link/tempo-testnet)
2. Connect wallet or paste your address
3. Request testnet pathUSD
4. Verify the funds arrived in the explorer

## Step 2: Configure MetaMask

Add custom network in MetaMask:

- **Network Name:** Tempo Testnet (Moderato)
- **RPC URL:** `https://rpc.moderato.tempo.xyz`
- **Chain ID:** `42431`
- **Currency Symbol:** pathUSD
- **Block Explorer:** `https://explore.tempo.xyz`

## Step 3: Export Private Key

```bash
export DEPLOYER_PRIVATE_KEY=0xYOUR_PRIVATE_KEY_HERE
```

**NEVER** commit the private key. Use environment variables or a `.env` file that is in `.gitignore`.

## Step 4: Run Deploy

```bash
cd ~/DOF-MESH
chmod +x scripts/deploy_tempo.sh
./scripts/deploy_tempo.sh
```

The script does:
1. Verifies Foundry is installed
2. Installs `forge-std` if it doesn't exist
3. Compiles the contracts
4. Runs tests
5. Deploys to Tempo testnet

## Step 5: Verify in Explorer

After the deploy, the script prints the addresses. Verify them at:

```
https://explore.tempo.xyz/address/0x...
```

## Step 6: Register DOF Agents

Once deployed, register agents with cast:

```bash
# Register an agent
cast send <IDENTITY_ADDRESS> \
    "register(string)" \
    "https://metadata.dof-mesh.xyz/agent/1.json" \
    --rpc-url https://rpc.moderato.tempo.xyz \
    --private-key $DEPLOYER_PRIVATE_KEY

# Give reputation feedback
cast send <REPUTATION_ADDRESS> \
    "giveFeedback(address,uint8,string)" \
    0xAGENT_ADDRESS 85 "Excellent performance" \
    --rpc-url https://rpc.moderato.tempo.xyz \
    --private-key $DEPLOYER_PRIVATE_KEY

# Query agent
cast call <IDENTITY_ADDRESS> \
    "getAgent(uint256)(address,string,uint256,bool)" 1 \
    --rpc-url https://rpc.moderato.tempo.xyz

# Query average score
cast call <REPUTATION_ADDRESS> \
    "getAverageScore(address)(uint256)" 0xAGENT_ADDRESS \
    --rpc-url https://rpc.moderato.tempo.xyz
```

## Contracts

### DOFIdentityRegistry
- `register(metadataURI)` — Register agent (1 per address)
- `updateMetadata(tokenId, metadataURI)` — Update metadata
- `deactivate(tokenId)` — Deactivate agent
- `getAgent(tokenId)` — Query agent
- `isRegistered(address)` — Verify registration
- `totalAgents()` — Total registered agents

### DOFReputationRegistry
- `giveFeedback(to, score, comment)` — Give feedback (0-100)
- `getAverageScore(agent)` — Average score
- `getFeedbackCount(agent)` — Number of feedbacks
- `getLatestFeedback(agent, count)` — Last N feedbacks

## Troubleshooting

### "Already registered"
Each address can only register 1 agent. Use another wallet or call `deactivate()` first.

### "Insufficient funds"
You need pathUSD for gas. Go to the faucet: `faucets.chain.link/tempo-testnet`

### forge build fails
```bash
cd contracts/tempo
forge install foundry-rs/forge-std --no-commit
forge build
```

### RPC not responding
Verify the RPC is active: `cast chain-id --rpc-url https://rpc.moderato.tempo.xyz`

## Next Step: Integrate MPP

After the deploy, integrate the Mesh Payment Protocol (MPP) for gasless payments between agents using pathUSD as the base currency on Tempo.
