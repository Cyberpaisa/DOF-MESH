# Deploy to SKALE Examples

## Complete Foundry Deployment

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import "forge-std/Script.sol";
import "../src/MyContract.sol";

contract DeployScript is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        
        vm.startBroadcast(deployerPrivateKey);
        
        MyContract contract = new MyContract();
        
        vm.stopBroadcast();
        
        console.log("Contract deployed at:", address(contract));
    }
}
```

Deploy with:
```bash
forge script script/Deploy.s.sol \
  --rpc-url https://base-sepolia-testnet.skalenodes.com/v1/jubilant-horrible-ancha \
  --private-key $PRIVATE_KEY \
  --legacy \
  --broadcast \
  --verify
```

## Complete Hardhat Deployment

```typescript
// scripts/deploy.ts
import { ethers } from "hardhat";

async function main() {
    const [deployer] = await ethers.getSigners();
    console.log("Deploying with account:", deployer.address);

    const ContractFactory = await ethers.getContractFactory("MyContract");
    const contract = await ContractFactory.deploy();
    
    await contract.waitForDeployment();
    console.log("Contract deployed to:", await contract.getAddress());
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
```

```bash
npx hardhat run scripts/deploy.ts --network skaleBaseSepolia
```

## Environment Setup

```bash
# .env
SKALE_RPC=https://base-sepolia-testnet.skalenodes.com/v1/jubilant-horrible-ancha
PRIVATE_KEY=0x...
```

## Hardhat Config

```typescript
// hardhat.config.ts
import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";

const config: HardhatUserConfig = {
    solidity: "0.8.27",
    networks: {
        skaleBaseSepolia: {
            url: process.env.SKALE_RPC || "",
            chainId: 324705682,
            accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : []
        },
        skaleBase: {
            url: process.env.SKALE_RPC || "",
            chainId: 1187947933,
            accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : []
        }
    }
};

export default config;
```
