// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract DOFIdentityRegistry {
    struct Agent {
        address owner;
        string metadataURI;
        uint256 registeredAt;
        bool active;
    }

    mapping(uint256 => Agent) public agents;
    mapping(address => uint256) public addressToTokenId;
    uint256 public nextTokenId;

    event AgentRegistered(uint256 indexed tokenId, address indexed owner, string metadataURI);
    event AgentUpdated(uint256 indexed tokenId, string metadataURI);
    event AgentDeactivated(uint256 indexed tokenId);

    function register(string calldata metadataURI) external returns (uint256) {
        require(addressToTokenId[msg.sender] == 0, "Already registered");
        nextTokenId++;
        agents[nextTokenId] = Agent(msg.sender, metadataURI, block.timestamp, true);
        addressToTokenId[msg.sender] = nextTokenId;
        emit AgentRegistered(nextTokenId, msg.sender, metadataURI);
        return nextTokenId;
    }

    function updateMetadata(uint256 tokenId, string calldata metadataURI) external {
        require(agents[tokenId].owner == msg.sender, "Not owner");
        agents[tokenId].metadataURI = metadataURI;
        emit AgentUpdated(tokenId, metadataURI);
    }

    function deactivate(uint256 tokenId) external {
        require(agents[tokenId].owner == msg.sender, "Not owner");
        agents[tokenId].active = false;
        emit AgentDeactivated(tokenId);
    }

    function getAgent(uint256 tokenId) external view returns (Agent memory) {
        return agents[tokenId];
    }

    function isRegistered(address addr) external view returns (bool) {
        return addressToTokenId[addr] != 0;
    }

    function totalAgents() external view returns (uint256) {
        return nextTokenId;
    }
}
