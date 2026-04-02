---
name: conflux-integration
description: Comprehensive toolkit and knowledge base for the Conflux Network ecosystem. Use this skill when developing, deploying, or interacting with smart contracts on Conflux (eSpace or Core), integrating Gas Sponsorship for gasless agent operations, configuring RPCs, or building cross-space bridges. This skill provides the architectural foundation for the DOF Mesh Legion's Sovereign Gateway.
---

# Conflux Integration Skill (Super Skill)

This skill provides the Legion Mesh with the comprehensive technical knowledge required to operate autonomously on the **Conflux Network**. It acts as the central intelligence repository for building the `Conflux Sovereign Gateway`.

## 1. Quick Start / Setup (Human Instructions)
To use this skill within the mesh, ensure you are connected to the correct RPC endpoints and have standard EVM tooling (Hardhat/Foundry) installed. Ensure you have the `conflux_gateway` active in the node.
- **Mainnet RPC:** `https://evm.confluxrpc.com` (Chain ID: 1030)
- **Testnet RPC:** `https://evmtestnet.confluxrpc.com` (Chain ID: 71)

## 2. Capabilities & System Instructions (AI Instructions)
**Target Environment:** Agents MUST default to **eSpace** (EVM-compatible) for smart contract logic, utilizing **Core Space** exclusively for the `SponsorWhitelistControl` mechanism via cross-space internal contracts.

**Critical EVM Differences:**
- **Contract Size Limit:** 49,152 bytes (Double Ethereum's limit).
- **Block Time & `NUMBER` Opcode:** ~1.25s per block. `NUMBER` returns the Epoch Number, NOT the block count. Do not rely on `block.number` for time locks.
- **EIP-4844:** `BLOBHASH` and `BLOBBASEFEE` return zero.

## 3. Workflow Pattern: Deploying a Gasless Contract
When instructed to deploy an application on Conflux, Agents must adhere strictly to this checklist:
1. **[  ] Deploy Logic:** Deploy the smart contract to eSpace using Hardhat or Foundry.
2. **[  ] Fund Sponsor Account:** Ensure the Sovereign Funding Treasury has bridged CFX to the Sponsor account.
3. **[  ] Call SponsorWhitelistControl:** 
   - Interact with internal contract `0x0888000000000000000000000000000000000001`.
   - Call `setSponsorForGas(contractAddr, upperBound)` + deposit CFX.
   - Call `setSponsorForCollateral(contractAddr)` + deposit CFX.
4. **[  ] Whitelist Global:** Call `addPrivilegeByAdmin` using `0x00...` to allow all users.

## 4. Examples
**Scenario: Registering Gas Sponsorship for myAppAddress:**
```javascript
const sponsorContract = new ethers.Contract("0x0888...", ABI, sponsorWallet);
// Fund gas (Requires sending CFX value)
await sponsorContract.setSponsorForGas(myAppAddress, "100000", { value: ethers.utils.parseEther("10") });
// Whitelist all users (Zero address)
await sponsorContract.addPrivilegeByAdmin(myAppAddress, [ethers.constants.AddressZero]);
```

## 5. Gotchas & Anti-patterns (IMPORTANT)
- **Gotcha (Time Bounds):** Never use `block.number` for lockups or duration logic due to epochs. Use `block.timestamp`.
- **Anti-pattern (Over-complexity):** Do not attempt to write complex dApps directly in Core Space. Always use eSpace for EVM compat.
- **Gotcha (Sponsorship Limits):** If a user's TX costs more than `upperBound`, the TX reverts if they have no CFX. Always calculate a high upper bound.

## 6. Official Resource Reference Library (The Source of Truth)
*El Soberano ha proporcionado el siguiente índice exhaustivo. Los agentes deben consultar estos URLs para cualquier implementación específica:*

### Network Overviews & Core Mechanisms
- [Conflux Overview](https://doc.confluxnetwork.org/docs/overview)
- [Core Space Overview](https://doc.confluxnetwork.org/docs/core/Overview)
- [eSpace Overview](https://doc.confluxnetwork.org/docs/espace/Overview/)
- [eSpace User Guide](https://doc.confluxnetwork.org/docs/espace/UserGuide)
- [Tree-Graph, GHAST & Consensus](https://doc.confluxnetwork.org/docs/general/conflux-basics/conflux-governance/cips)
- [Hardforks History](https://doc.confluxnetwork.org/docs/general/hardforks/)

### eSpace Specifics & EVM Compatibility
- [EVM Compatibility Details](https://doc.confluxnetwork.org/docs/espace/build/evm-compatibility)
- [JSON-RPC Compatibility](https://doc.confluxnetwork.org/docs/espace/build/jsonrpc-compatibility)
- [eSpace Deployed Contracts](https://doc.confluxnetwork.org/docs/espace/build/deployed-contracts)
- [Digital Signature: ECDSA](https://doc.confluxnetwork.org/docs/espace/tutorials/digitalSignature/ECDSA)
- [Digital Signature: EIP712](https://doc.confluxnetwork.org/docs/espace/tutorials/digitalSignature/EIP712)

### Core Space Specifics & Sponsorship
- [Core Space Internal Contracts (Sponsorship)](https://doc.confluxnetwork.org/docs/core/core-space-basics/internal-contracts/)
- [Core JSON-RPC Methods](https://doc.confluxnetwork.org/docs/core/build/json-rpc/)

### Contract Deployment & Toolchains
- [Developer Quickstart eSpace](https://doc.confluxnetwork.org/docs/espace/DeveloperQuickstart)
- [Deployment Tools Category](https://doc.confluxnetwork.org/docs/category/deployment)
- [Hardhat & Foundry Deployment](https://doc.confluxnetwork.org/docs/espace/tutorials/deployContract/hardhatAndFoundry)
- [Remix Deployment](https://doc.confluxnetwork.org/docs/espace/tutorials/deployContract/remix)
- [Thirdweb Deployment](https://doc.confluxnetwork.org/docs/espace/tutorials/deployContract/thirdweb)
- [Brownie Deployment](https://doc.confluxnetwork.org/docs/espace/tutorials/deployContract/brownie)
- [Verify Contracts on Scan](https://doc.confluxnetwork.org/docs/espace/tutorials/VerifyContracts)

### Upgradable Contracts (Proxies)
- [Upgradable Contract Setup](https://doc.confluxnetwork.org/docs/espace/tutorials/upgradableContract/upgrade)
- [Transparent Proxy](https://doc.confluxnetwork.org/docs/espace/tutorials/upgradableContract/transparent-proxy)
- [Transparent Proxy with Foundry](https://doc.confluxnetwork.org/docs/espace/tutorials/upgradableContract/transparent-proxy-foundry)
- [UUPS Proxy](https://doc.confluxnetwork.org/docs/espace/tutorials/upgradableContract/uups)
- [UUPS Proxy with Foundry](https://doc.confluxnetwork.org/docs/espace/tutorials/upgradableContract/uups-foundry)
- [Upgrade Contracts with Foundry](https://doc.confluxnetwork.org/docs/espace/tutorials/upgradableContract/upgrade-foundry)

### SDKs & Frontend Integration
- [Core Space SDKs](https://doc.confluxnetwork.org/docs/core/build/sdks-and-tools/sdks)
- [Core Space Tools](https://doc.confluxnetwork.org/docs/core/build/sdks-and-tools/tools)
- [eSpace Web3.js](https://doc.confluxnetwork.org/docs/espace/tutorials/sdks/web3js)
- [eSpace Web3.py](https://doc.confluxnetwork.org/docs/espace/tutorials/sdks/web3py)
- [eSpace Ethers.js](https://doc.confluxnetwork.org/docs/espace/tutorials/sdks/ethersjs)
- [Scaffold-CFX](https://doc.confluxnetwork.org/docs/espace/tutorials/scaffoldCfx/scaffold)
- [Scaffold-CFX v2](https://doc.confluxnetwork.org/docs/espace/tutorials/scaffoldCfx/scaffold2)
- [eSpace Cookbook](https://doc.confluxnetwork.org/docs/espace/tutorials/cookbook)

### WalletConnect Integration
- [WalletConnect Project Creation](https://doc.confluxnetwork.org/docs/espace/tutorials/walletConnect/project-creation)
- [WalletConnect Next.js](https://doc.confluxnetwork.org/docs/espace/tutorials/walletConnect/nextjs)
- [WalletConnect React.js](https://doc.confluxnetwork.org/docs/espace/tutorials/walletConnect/reactjs)
- [WalletConnect Vue.js](https://doc.confluxnetwork.org/docs/espace/tutorials/walletConnect/vuejs)

### Infrastructure: RPCs, Nodes, APIs & Data
- [eSpace Network Endpoints (RPCs)](https://doc.confluxnetwork.org/docs/espace/network-endpoints)
- [Core RPC Endpoints](https://doc.confluxnetwork.org/docs/core/conflux_rpcs)
- [Node Configuration Files](https://doc.confluxnetwork.org/docs/general/run-a-node/advanced-topics/configuration-files)
- [ConfluxScan API](https://api.confluxscan.org/doc)
- [Read Logs & Indexer](https://doc.confluxnetwork.org/docs/espace/tutorials/readLogs/indexer)
- [The Graph: Setup Node](https://doc.confluxnetwork.org/docs/espace/tutorials/graph/setup-graph-node)
- [The Graph: Create Subgraphs](https://doc.confluxnetwork.org/docs/espace/tutorials/graph/create-subgraphs)
- [Pyth Oracle Price Feed](https://doc.confluxnetwork.org/docs/espace/tutorials/oracle/Pyth/priceFeed)

---
*Legion Gateway Authorized. Ready for gasless deployment.*
