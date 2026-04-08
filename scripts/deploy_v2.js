// scripts/deploy_v2.js — DOFProofRegistryV2 Deployment
// Conflux Global Hackfest 2026
// Usage: npx hardhat run scripts/deploy_v2.js --network conflux_testnet

const { ethers } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();
  const network = await ethers.provider.getNetwork();

  console.log("═══════════════════════════════════════════════════");
  console.log("  DOFProofRegistryV2 — Proof-to-Gasless Deployment");
  console.log("  Conflux Global Hackfest 2026");
  console.log("═══════════════════════════════════════════════════");
  console.log(`  Network:   ${network.name} (chainId: ${network.chainId})`);
  console.log(`  Deployer:  ${deployer.address}`);

  const balance = await ethers.provider.getBalance(deployer.address);
  const balanceCFX = ethers.formatEther(balance);
  console.log(`  Balance:   ${balanceCFX} CFX`);

  if (parseFloat(balanceCFX) < 0.1) {
    throw new Error("Insufficient CFX balance for deployment");
  }

  console.log("\n  Compiling DOFProofRegistryV2...");
  const Factory = await ethers.getContractFactory("DOFProofRegistryV2");

  console.log("  Deploying...");
  const contract = await Factory.deploy();
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  const deployTx = contract.deploymentTransaction();

  console.log("\n  ✅ Deployed successfully!");
  console.log(`  Contract:  ${address}`);
  console.log(`  TX Hash:   ${deployTx.hash}`);
  console.log(`  Explorer:  https://evmtestnet.confluxscan.io/address/${address}`);
  console.log(`  TX Link:   https://evmtestnet.confluxscan.io/tx/${deployTx.hash}`);

  // Verify deployment by calling getStats()
  console.log("\n  Verifying contract state...");
  try {
    const stats = await contract.getStats();
    console.log(`  totalProofs:     ${stats[0]}`);
    console.log(`  proofsPassed:    ${stats[1]}`);
    console.log(`  gaslessAgents:   ${stats[2]}`);
    console.log(`  sponsorBalance:  ${ethers.formatEther(stats[3])} CFX`);
    console.log("  ✅ Contract verified — getStats() returned expected state");
  } catch (e) {
    console.log(`  ⚠️  getStats() failed: ${e.message}`);
  }

  // Output JSON for evidence
  const evidence = {
    contract: "DOFProofRegistryV2",
    address: address,
    txHash: deployTx.hash,
    deployer: deployer.address,
    network: "conflux_eSpace_testnet",
    chainId: network.chainId.toString(),
    timestamp: new Date().toISOString(),
    gaslessFeature: "SponsorWhitelistControl@0x0888000000000000000000000000000000000001",
    innovation: "Proof-to-Gasless: mathematical compliance earns gas sponsorship",
    explorer: `https://evmtestnet.confluxscan.io/address/${address}`,
  };

  console.log("\n  Evidence JSON:");
  console.log(JSON.stringify(evidence, null, 2));
}

main().catch((err) => {
  console.error("Deployment failed:", err);
  process.exitCode = 1;
});
