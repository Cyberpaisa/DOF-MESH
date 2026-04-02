---
name: ima-bridging-on-skale
description: Programmatic IMA (Inter-chain Messaging Agent) bridging for SKALE chains. Use for sending and receiving messages between SKALE chains and Ethereum.
---

# IMA Bridging on SKALE

## Overview
The Inter-chain Messaging Agent (IMA) enables communication between SKALE chains and Ethereum, as well as between SKALE chains. Unlike the standard bridge which focuses on asset transfers, IMA is designed for arbitrary message passing and contract interactions.

## Key Concepts
- **MessageProxy Contract**: Standardized address for IMA operations at `0xd2AAa00100000000000000000000000000000000`
- **EXTRA_CONTRACT_REGISTRAR_ROLE**: Required role for registering custom contracts to receive IMA messages
- **Message Format**: Includes source chain, destination chain, sender, destination contract, and data payload

## Prerequisites
Before using IMA bridging programmatically, ensure:
1. Your contract is registered to receive messages (requires `EXTRA_CONTRACT_REGISTRAR_ROLE`)
2. You have the MessageProxy contract ABI
3. You understand gas limitations (estimateGas may not work reliably)

## Contract Registration
To receive IMA messages, your contract must be registered with the MessageProxy:

### Using Ethers.js v6
```typescript
import { ethers } from "ethers";

// MessageProxy ABI (simplified for registration)
const messageProxyAbi = [
  "function grantRole(bytes32 role, address account)",
  "function EXTRA_CONTRACT_REGISTRAR_ROLE() view returns (bytes32)"
];

// Initialize provider and signer
const provider = new ethers.JsonRpcProvider(process.env.SKALE_RPC!);
const signer = new ethers.Wallet(process.env.PRIVATE_KEY!, provider);
const messageProxyAddress = "0xd2AAa00100000000000000000000000000000000";
const messageProxy = new ethers.Contract(messageProxyAddress, messageProxyAbi, signer);

// Your contract address that will receive messages
const yourContractAddress = "0xYourContractAddress";

async function registerContractForIMA() {
  try {
    // Get the role identifier for EXTRA_CONTRACT_REGISTRAR_ROLE
    const role = await messageProxy.EXTRA_CONTRACT_REGISTRAR_ROLE();
    
    // Grant the role to your contract
    const tx = await messageProxy.grantRole(role, yourContractAddress);
    await tx.wait();
    
    console.log("Contract registered for IMA messages:", yourContractAddress);
  } catch (error) {
    console.error("Failed to register contract for IMA:", error);
  }
}

registerContractForIMA();
```

### Using Foundry Scripts
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "./src/YourContract.sol";

contract ImaRegistrationScript is Script {
    // MessageProxy interface
    interface IMessageProxy {
        function grantRole(bytes32 role, address account) external;
        function EXTRA_CONTRACT_REGISTRAR_ROLE() external view returns (bytes32);
    }

    function run() public {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = toAddress(deployerPrivateKey);
        address messageProxy = 0xd2AAa00100000000000000000000000000000000;
        address yourContract = 0xYourContractAddress; // Replace with actual address

        vm.startBroadcast(deployer);
        IMessageProxy proxy = IMessageProxy(messageProxy);
        
        // Get role and grant it
        bytes32 role = proxy.EXTRA_CONTRACT_REGISTRAR_ROLE();
        proxy.grantRole(role, yourContract);
        
        vm.stopBroadcast();
        
        console.log("Contract registered for IMA");
    }
}
```

## Sending Messages
Once registered, you can send messages via IMA:

### Sending a Simple Message
```typescript
import { ethers } from "ethers";

// Simplified MessageProxy ABI for sending messages
const messageProxyAbi = [
  "function sendMessage(
    address destinationContract,
    uint64 destinationChainId,
    bytes calldata data
  ) external payable returns (uint256)"
];

async function sendImaMessage() {
  const provider = new ethers.JsonRpcProvider(process.env.SKALE_RPC!);
  const signer = new ethers.Wallet(process.env.PRIVATE_KEY!, provider);
  const messageProxyAddress = "0xd2AAa00100000000000000000000000000000000";
  const messageProxy = new ethers.Contract(messageProxyAddress, messageProxyAbi, signer);

  // Destination contract on target chain
  const destinationContract = "0xDestinationContractAddress";
  // Destination chain ID (e.g., another SKALE chain or Ethereum)
  const destinationChainId = 324705682; // Example: SKALE Base Sepolia
  
  // Message data (can be any ABI-encoded data)
  const messageData = ethers.AbiCoder.defaultAbiCoder().encode(
    ["string"], 
    ["Hello from SKALE!"]
  );

  try {
    const tx = await messageProxy.sendMessage(
      destinationContract,
      destinationChainId,
      messageData,
      { value: ethers.parseEther("0.001") } // Adjust gas payment as needed
    );
    const receipt = await tx.wait();
    
    console.log("Message sent! Transaction hash:", receipt.hash);
    console.log("Message ID:", receipt.logs[0].topics[1]); // Assuming first log contains message ID
  } catch (error) {
    console.error("Failed to send IMA message:", error);
  }
}

sendImaMessage();
```

### Sending Complex Data Types
```typescript
async function sendComplexImaMessage() {
  const provider = new ethers.JsonRpcProvider(process.env.SKALE_RPC!);
  const signer = new ethers.Wallet(process.env.PRIVATE_KEY!, provider);
  const messageProxyAddress = "0xd2AAa00100000000000000000000000000000000";
  const messageProxy = new ethers.Contract(messageProxyAddress, messageProxyAbi, signer);

  const destinationContract = "0xDestinationContractAddress";
  const destinationChainId = 324705682;
  
  // Encode complex data (e.g., struct or multiple values)
  const messageData = ethers.AbiCoder.defaultAbiCoder().encode(
    ["uint256", "address", "bool", "string"],
    [42, "0x1234567890123456789012345678901234567890", true, "Complex message"]
  );

  try {
    const tx = await messageProxy.sendMessage(
      destinationContract,
      destinationChainId,
      messageData
    );
    await tx.wait();
    console.log("Complex message sent successfully");
  } catch (error) {
    console.error("Failed to send complex IMA message:", error);
  }
}
```

## Receiving Messages
To handle incoming IMA messages, your contract must implement a specific interface:

### Receiver Contract Example
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IMessageProxy {
    function sendMessage(
        address destinationContract,
        uint64 destinationChainId,
        bytes calldata data
    ) external payable returns (uint256);
    
    event MessageSent(
        bytes32 indexed id,
        address indexed sender,
        uint64 srcChainId,
        address srcContract,
        uint64 destChainId,
        address destContract,
        bytes data
    );
}

contract ImaReceiver {
    address public immutable owner;
    
    // Store received messages (for demonstration)
    struct Message {
        bytes32 id;
        address sender;
        uint64 srcChainId;
        address srcContract;
        bytes data;
    }
    
    Message[] public receivedMessages;
    
    modifier onlyMessageProxy() {
        // Verify caller is the authorized MessageProxy
        require(
            msg.sender == 0xd2AAa00100000000000000000000000000000000,
            "Only MessageProxy can call"
        );
        _;
    }
    
    constructor() {
        owner = msg.sender;
    }
    
    // This function is called by the MessageProxy when a message arrives
    function onMessage(
        bytes32 id,
        address sender,
        uint64 srcChainId,
        address srcContract,
        uint64 destChainId,
        address destContract,
        bytes calldata data
    ) external onlyMessageProxy {
        // Store the message
        receivedMessages.push(Message({
            id: id,
            sender: sender,
            srcChainId: srcChainId,
            srcContract: srcContract,
            data: data
        }));
        
        // Process the message data
        handleMessageData(data);
    }
    
    function handleMessageData(bytes calldata data) internal {
        // Decode and process the message data
        // Example: if message contains a string
        if (data.length >= 32) { // Minimum length for a string offset
            // In practice, you'd use proper ABI decoding based on your expected format
            // This is a simplified example
            uint256 strOffset = abi.decode(data[0:32], (uint256));
            if (strOffset < data.length) {
                uint256 strLength = abi.decode(data[strOffset:strOffset+32], (uint256));
                // Extract string (simplified)
                // In real implementation, use proper string decoding
            }
        }
        
        // Add your custom logic here based on the message content
        // For example:
        // if (data == keccak256("DO_SOMETHING")) {
        //     doSomething();
        // }
    }
    
    // Optional: View functions to inspect received messages
    function getMessageCount() public view returns (uint256) {
        return receivedMessages.length;
    }
    
    function getMessage(uint256 index) public view returns (
        bytes32 id,
        address sender,
        uint64 srcChainId,
        address srcContract,
        bytes data
    ) {
        Message memory msg = receivedMessages[index];
        return (msg.id, msg.sender, msg.srcChainId, msg.srcContract, msg.data);
    }
}
```

## Important Considerations

### Gas Limitations
- IMA message sending requires payment in the native token of the source chain
- `estimateGas` may not work reliably for IMA transactions due to cross-chain execution
- Always include a sufficient gas limit when sending messages

### Error Handling
```typescript
async function sendImaMessageWithErrorHandling() {
  try {
    const tx = await messageProxy.sendMessage(
      destinationContract,
      destinationChainId,
      messageData,
      { value: gasPayment }
    );
    
    // Wait for confirmation with timeout
    const receipt = await tx.wait(1); // Wait for 1 confirmation
    
    if (receipt.status === 1) {
      console.log("Message sent successfully");
    } else {
      console.log("Message transaction failed");
      // Handle failure case
    }
  } catch (error) {
    // Handle various error cases
    if (error.code === -32603) {
      console.log("Transaction reverted:", error.message);
      // Check if it's a gas issue, invalid destination, etc.
    } else if (error.code === 4001) {
      console.log("User rejected transaction");
    } else {
      console.log("Unexpected error:", error);
    }
  }
}
```

### Chain IDs Reference
```typescript
// Common SKALE Chain IDs
const SKALE_CHAIN_IDS = {
  // Testnets
  SKALE_BASE_SEPOLIA: 324705682,
  EUROPA_TESTNET: 2046399126,
  CALYPSO_TESTNET: 1564830818,
  NEBULA_TESTNET: 1482601649,
  
  // Mainnets
  SKALE_BASE: 1187947933,
  EUROPA_HUB: 2046399126, // Same as testnet for this example
  CALYPSO_HUB: 1564830818,
  NEBULA_HUB: 1482601649
};
```

## Best Practices
1. Always register your contract before attempting to receive messages
2. Use proper ABI encoding/decoding for message data
3. Implement appropriate access controls on your `onMessage` function
4. Consider using events to track message sending/receiving for debugging
5. Test thoroughly on testnets before deploying to mainnet
6. Monitor transaction statuses as cross-chain transactions may have different confirmation times

## Related Skills
- For general contract deployment to SKALE, see the `deploy-to-skale` skill
- For SKALE basics including chain selection and gas models, see the `about-skale` skill