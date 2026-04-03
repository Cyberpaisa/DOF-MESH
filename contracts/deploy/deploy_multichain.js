// contracts/deploy/deploy_multichain.js
// Deploya DOFProofRegistry en cualquier EVM configurada en chains_config.json
//
// Uso:
//   npx hardhat run contracts/deploy/deploy_multichain.js --network conflux_testnet
//   npx hardhat run contracts/deploy/deploy_multichain.js --network base_sepolia
//   npx hardhat run contracts/deploy/deploy_multichain.js --network arbitrum_sepolia

const { ethers, network } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
    const chainId = network.config.chainId;
    const networkName = network.name;

    console.log(`\n🚀 DOF Multichain Deploy`);
    console.log(`   Network: ${networkName}`);
    console.log(`   Chain ID: ${chainId}`);

    const [deployer] = await ethers.getSigners();
    console.log(`   Deployer: ${deployer.address}`);

    const balance = await ethers.provider.getBalance(deployer.address);
    console.log(`   Balance: ${ethers.formatEther(balance)} (native token)\n`);

    if (balance === 0n) {
        throw new Error("Balance cero — consigue tokens del faucet primero");
    }

    // Deploy DOFProofRegistry
    const DOFProofRegistry = await ethers.getContractFactory("DOFProofRegistry");
    const registry = await DOFProofRegistry.deploy();
    await registry.waitForDeployment();

    const address = await registry.getAddress();
    console.log(`✅ DOFProofRegistry deployado: ${address}`);

    // Actualizar chains_config.json automáticamente
    const configPath = path.join(__dirname, "../../core/chains_config.json");
    let config;
    try {
        config = JSON.parse(fs.readFileSync(configPath, "utf8"));
    } catch (e) {
        console.error(`No route found for config file: ${configPath}`);
        return;
    }

    // Mapeo de network name → chain key en config
    const networkToKey = {
        "conflux_testnet": "conflux_testnet",
        "conflux": "conflux_espace",
        "base_sepolia": "base_sepolia",
        "base": "base",
        "arbitrum_sepolia": "arbitrum_sepolia",
        "arbitrum": "arbitrum",
        "polygon_amoy": "polygon_amoy",
        "polygon": "polygon",
        "celo_alfajores": "celo_alfajores",
        "celo": "celo",
        "sepolia": "ethereum_sepolia",
        "mainnet": "ethereum",
        "fuji": "avalanche_testnet",
        "avalanche": "avalanche",
        "skale_europa": "skale_europa"
    };

    const chainKey = networkToKey[networkName];
    if (chainKey && config.chains[chainKey]) {
        config.chains[chainKey].contract_address = address;
        if (config.chains[chainKey].status === "planned") {
            config.chains[chainKey].status = "testnet";
        }
        fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
        console.log(`✅ chains_config.json actualizado (${chainKey})`);
    } else {
        console.warn(`⚠  Network '${networkName}' no encontrada en networkToKey — actualiza manualmente`);
    }

    // Verificación básica adaptada a la ABI real (verifica length)
    console.log(`\n🔍 Verificando contrato...`);
    try {
        const val = await registry.getProofCount();
        console.log(`   getProofCount() = ${val} (esperado: 0 = correcto)`);
    } catch (err) {
        console.log(`   Hubo un error verificando: ${err.message}`);
    }

    console.log(`\n📋 Resumen:`);
    console.log(`   Contract: ${address}`);
    console.log(`   Chain: ${networkName} (${chainId})`);
    console.log(`   Explorer: verifica en el explorador de la chain`);
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
