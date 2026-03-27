#!/bin/bash
# Deploy DOF-MESH contracts to Tempo blockchain
# Requires: pathUSD in wallet for gas

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONTRACTS_DIR="$SCRIPT_DIR/../contracts/tempo"

echo "═══════════════════════════════════════════════"
echo "  DOF-MESH → Tempo Blockchain Deploy"
echo "  Network: Tempo Testnet (Moderato)"
echo "  Chain ID: 42431"
echo "  RPC: https://rpc.moderato.tempo.xyz"
echo "═══════════════════════════════════════════════"

# Check forge
if ! command -v forge &> /dev/null; then
    echo "ERROR: Foundry not installed. Run: curl -L https://foundry.paradigm.xyz | bash"
    exit 1
fi

# Check private key
if [ -z "$DEPLOYER_PRIVATE_KEY" ]; then
    echo "ERROR: Set DEPLOYER_PRIVATE_KEY environment variable"
    echo "  export DEPLOYER_PRIVATE_KEY=0x..."
    exit 1
fi

cd "$CONTRACTS_DIR"

# Install forge-std if needed
if [ ! -d "lib/forge-std" ]; then
    forge install foundry-rs/forge-std --no-git
fi

# Build
echo ""
echo "[1/3] Building contracts..."
forge build

# Test
echo ""
echo "[2/3] Running tests..."
forge test -vv

# Deploy
echo ""
echo "[3/3] Deploying to Tempo testnet..."
forge script script/Deploy.s.sol:DeployDOF \
    --rpc-url https://rpc.moderato.tempo.xyz \
    --private-key $DEPLOYER_PRIVATE_KEY \
    --broadcast \
    --verify

echo ""
echo "═══════════════════════════════════════════════"
echo "  Deploy complete! Check explorer:"
echo "  https://explore.tempo.xyz"
echo "═══════════════════════════════════════════════"
