// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title DOFGaslessProof
 * @dev Simple contract deployed on Status Network Sepolia to demonstrate
 *      gasless transactions for the Synthesis 2026 hackathon bounty.
 *      "Go Gasless: Deploy & Transact on Status Network with Your AI Agent"
 * @author DOF Agent #1686 (Enigma) + Juan Carlos Quiceno (@Cyber_paisa)
 */
contract DOFGaslessProof {
    address public immutable agent;
    uint256 public proofCount;
    
    struct Proof {
        bytes32 actionHash;
        uint256 timestamp;
        string description;
    }
    
    mapping(uint256 => Proof) public proofs;
    
    event ProofRecorded(uint256 indexed id, bytes32 actionHash, string description);
    
    constructor() {
        agent = msg.sender;
    }
    
    modifier onlyAgent() {
        require(msg.sender == agent, "Only DOF Agent can record proofs");
        _;
    }
    
    /**
     * @dev Record a deterministic proof of an autonomous action.
     *      This function is designed to be called gaslessly on Status Network.
     */
    function recordProof(string calldata description) external onlyAgent returns (uint256) {
        uint256 id = proofCount++;
        bytes32 actionHash = keccak256(abi.encodePacked(description, block.timestamp, id));
        
        proofs[id] = Proof({
            actionHash: actionHash,
            timestamp: block.timestamp,
            description: description
        });
        
        emit ProofRecorded(id, actionHash, description);
        return id;
    }
    
    function getProof(uint256 id) external view returns (bytes32, uint256, string memory) {
        Proof memory p = proofs[id];
        return (p.actionHash, p.timestamp, p.description);
    }
    
    function getLatestProof() external view returns (bytes32, uint256, string memory) {
        require(proofCount > 0, "No proofs recorded");
        Proof memory p = proofs[proofCount - 1];
        return (p.actionHash, p.timestamp, p.description);
    }
}
