#!/bin/bash
# DOF Mesh Legion — Deploy DOFProofRegistry a todas las testnets
# Uso: source ~/.dof/wallet.env && bash scripts/deploy_multichain.sh
#
# PREREQUISITOS:
#   1. forge instalado (foundryup)
#   2. ~/.dof/wallet.env con DOF_PRIVATE_KEY
#   3. Tokens de testnet en la wallet (ver faucets en DEPLOY_GUIDE.md)

set -e

if [ -z "$DOF_PRIVATE_KEY" ]; then
    echo "❌ DOF_PRIVATE_KEY no está configurada"
    echo "   Ejecuta: source ~/.dof/wallet.env"
    exit 1
fi

CONTRACT="contracts/DOFProofRegistry.sol:DOFProofRegistry"
RESULTS_FILE="contracts/deploy/deploy_results.json"

echo "╔══════════════════════════════════════════════╗"
echo "║  DOF Mesh Legion — Multichain Deploy         ║"
echo "║  Contrato: DOFProofRegistry                   ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Compilar una vez
echo "🔨 Compilando..."
forge build --contracts contracts/DOFProofRegistry.sol --quiet
echo "✅ Compilación exitosa"
echo ""

# Inicializar resultados JSON
echo '{"deploys": [], "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' > "$RESULTS_FILE"

deploy_chain() {
    local CHAIN_NAME=$1
    local CHAIN_ID=$2
    local RPC_URL=$3

    echo "━━━ Deploying: $CHAIN_NAME (chain $CHAIN_ID) ━━━"

    RESULT=$(forge create $CONTRACT \
        --rpc-url "$RPC_URL" \
        --private-key "$DOF_PRIVATE_KEY" \
        --broadcast 2>&1) || {
        echo "  ❌ FALLÓ: $CHAIN_NAME"
        echo "  Error: $RESULT"
        echo ""
        return 1
    }

    # Extraer address del output de forge
    ADDRESS=$(echo "$RESULT" | grep "Deployed to:" | awk '{print $3}')
    TX_HASH=$(echo "$RESULT" | grep "Transaction hash:" | awk '{print $3}')

    echo "  ✅ Address: $ADDRESS"
    echo "  📝 Tx: $TX_HASH"
    echo ""

    # Agregar al JSON de resultados
    python3 -c "
import json
with open('$RESULTS_FILE') as f:
    data = json.load(f)
data['deploys'].append({
    'chain': '$CHAIN_NAME',
    'chain_id': $CHAIN_ID,
    'contract_address': '$ADDRESS',
    'tx_hash': '$TX_HASH',
    'rpc_url': '$RPC_URL'
})
with open('$RESULTS_FILE', 'w') as f:
    json.dump(data, f, indent=2)
"

    # Actualizar chains_config.json
    python3 -c "
import json
with open('core/chains_config.json') as f:
    config = json.load(f)
# Buscar la chain por chain_id
for key, chain in config['chains'].items():
    if chain['chain_id'] == $CHAIN_ID:
        chain['contract_address'] = '$ADDRESS'
        chain['status'] = 'testnet' if 'testnet' in key or 'sepolia' in key or 'amoy' in key or 'alfajores' in key else 'mainnet'
        break
with open('core/chains_config.json', 'w') as f:
    json.dump(config, f, indent=2)
"
}

# ═══ TESTNETS ═══
echo "═══ FASE 1: TESTNETS ═══"
echo ""

deploy_chain "Base Sepolia"      84532    "https://sepolia.base.org"
deploy_chain "Celo Alfajores"    44787    "https://alfajores-forno.celo-testnet.org"
deploy_chain "Polygon Amoy"      80002    "https://rpc-amoy.polygon.technology"
deploy_chain "Arbitrum Sepolia"  421614   "https://sepolia-rollup.arbitrum.io/rpc"
deploy_chain "Ethereum Sepolia"  11155111 "https://ethereum-sepolia-rpc.publicnode.com"

echo ""
echo "═══ RESULTADOS ═══"
cat "$RESULTS_FILE" | python3 -m json.tool
echo ""
echo "✅ Deploy completado. Resultados en: $RESULTS_FILE"
echo "📝 chains_config.json actualizado automáticamente"
