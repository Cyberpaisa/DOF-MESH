const hre = require("hardhat");

async function main() {
  console.log("Deploying DOFValidationRegistry to", hre.network.name, "...");

  const [deployer] = await hre.ethers.getSigners();
  console.log("Deployer:", deployer.address);

  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("Balance:", hre.ethers.formatEther(balance), "AVAX");

  const Registry = await hre.ethers.getContractFactory("DOFValidationRegistry");
  const registry = await Registry.deploy();
  await registry.waitForDeployment();

  const address = await registry.getAddress();
  console.log("DOFValidationRegistry deployed to:", address);
  console.log("Save this address in your .env as VALIDATION_REGISTRY_ADDRESS");

  // Write address to file for Python integration
  const fs = require("fs");
  fs.writeFileSync("contracts/deployed_address.txt", address);
  fs.writeFileSync("contracts/deployment_info.json", JSON.stringify({
    address: address,
    network: hre.network.name,
    chainId: hre.network.config.chainId,
    deployer: deployer.address,
    timestamp: new Date().toISOString(),
    txHash: registry.deploymentTransaction()?.hash || "unknown"
  }, null, 2));

  console.log("\nDeployment info saved to contracts/deployment_info.json");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
