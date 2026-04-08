// scripts/activate_gasless.js — Activate Gas Sponsorship on Conflux eSpace
// Conflux Global Hackfest 2026
//
// SponsorWhitelistControl: 0x0888000000000000000000000000000000000001
// setSponsorForGas(contractAddr, upperBound): sponsor up to upperBound Drip/tx
// Fund via: send CFX to SponsorWhitelistControl with setSponsorForGas call
//
// Usage: npx hardhat run scripts/activate_gasless.js --network conflux_testnet --config hardhat.config.v2.js

const { ethers } = require("hardhat");

// Conflux native SponsorWhitelistControl ABI (subset needed)
const SPONSOR_ABI = [
  "function setSponsorForGas(address contractAddr, uint256 upperBound) external payable",
  "function setSponsorForCollateral(address contractAddr) external payable",
  "function getSponsorForGas(address contractAddr) external view returns (address)",
  "function getSponsoredBalanceForGas(address contractAddr) external view returns (uint256)",
  "function isWhitelisted(address contractAddr, address user) external view returns (bool)",
  "function addPrivilege(address[] memory) external",
];

const SPONSOR_ADDR = "0x0888000000000000000000000000000000000001";

// Contracts to sponsor:
const V1_ADDR = "0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83";
const V2_ADDR = "0x58F0126B647E87a9a49e79971E168ce139326fd1";

// Sponsorship config:
// upper bound: max gas per sponsored TX = 1,000,000 Drip (very low, just enables the feature)
// fund amount: 0.5 CFX per contract (500_000_000_000_000_000 Drip)
const UPPER_BOUND = ethers.parseUnits("1000000", "wei"); // 1M Drip per TX limit
const FUND_CFX = ethers.parseEther("0.5"); // 0.5 CFX per contract

async function sponsorContract(sponsor, contractAddr, label) {
  console.log(`\n  ─── ${label} (${contractAddr}) ───`);

  // Check current state
  try {
    const currentSponsor = await sponsor.getSponsorForGas(contractAddr);
    const balance = await sponsor.getSponsoredBalanceForGas(contractAddr);
    console.log(`  Current sponsor:  ${currentSponsor === ethers.ZeroAddress ? "None" : currentSponsor}`);
    console.log(`  Current balance:  ${ethers.formatEther(balance)} CFX`);
  } catch (e) {
    console.log(`  ⚠️  Cannot read current state: ${e.message.slice(0, 80)}`);
  }

  // Activate sponsorship
  console.log(`  Calling setSponsorForGas with ${ethers.formatEther(FUND_CFX)} CFX...`);
  try {
    const tx = await sponsor.setSponsorForGas(contractAddr, UPPER_BOUND, {
      value: FUND_CFX,
      gasLimit: 300000,
    });
    console.log(`  TX submitted: ${tx.hash}`);
    const receipt = await tx.wait();
    console.log(`  ✅ Gas sponsor activated!`);
    console.log(`  TX:     ${tx.hash}`);
    console.log(`  Gas:    ${receipt.gasUsed.toString()}`);
    console.log(`  Block:  ${receipt.blockNumber}`);
    console.log(`  Scan:   https://evmtestnet.confluxscan.io/tx/${tx.hash}`);
    return { success: true, txHash: tx.hash, gasUsed: receipt.gasUsed.toString() };
  } catch (e) {
    console.log(`  ❌ Failed: ${e.message.slice(0, 200)}`);
    return { success: false, error: e.message.slice(0, 200) };
  }
}

async function main() {
  const [deployer] = await ethers.getSigners();
  const network = await ethers.provider.getNetwork();

  console.log("═══════════════════════════════════════════════════");
  console.log("  FASE 2 — Activate Gas Sponsorship");
  console.log("  Conflux Global Hackfest 2026");
  console.log("═══════════════════════════════════════════════════");
  console.log(`  Network:   ${network.name} (chainId: ${network.chainId})`);
  console.log(`  Operator:  ${deployer.address}`);

  const balance = await ethers.provider.getBalance(deployer.address);
  console.log(`  Balance:   ${ethers.formatEther(balance)} CFX`);

  const sponsor = new ethers.Contract(SPONSOR_ADDR, SPONSOR_ABI, deployer);

  const results = {};

  // Sponsor V2 (primary — the new Proof-to-Gasless contract)
  results.v2 = await sponsorContract(sponsor, V2_ADDR, "DOFProofRegistryV2");

  // Sponsor V1 (existing — retroactive gasless for already-proven agents)
  results.v1 = await sponsorContract(sponsor, V1_ADDR, "DOFProofRegistryV1");

  console.log("\n═══════════════════════════════════════════════════");
  console.log("  Summary");
  console.log("═══════════════════════════════════════════════════");
  console.log(`  V1 sponsorship: ${results.v1?.success ? "✅ Active" : "❌ " + (results.v1?.error || "unknown")}`);
  console.log(`  V2 sponsorship: ${results.v2?.success ? "✅ Active" : "❌ " + (results.v2?.error || "unknown")}`);

  console.log("\n  Evidence JSON:");
  const evidence = {
    phase: "FASE2_GAS_SPONSORSHIP",
    timestamp: new Date().toISOString(),
    operator: deployer.address,
    network: "conflux_eSpace_testnet",
    chainId: network.chainId.toString(),
    sponsorContract: SPONSOR_ADDR,
    fundPerContract: "0.5 CFX",
    upperBound: "1000000 Drip",
    v1: { address: V1_ADDR, ...results.v1 },
    v2: { address: V2_ADDR, ...results.v2 },
  };
  console.log(JSON.stringify(evidence, null, 2));
}

main().catch((err) => {
  console.error("Failed:", err);
  process.exitCode = 1;
});
