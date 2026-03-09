// SPDX-License-Identifier: BSL-1.1
// NUEVO CONTRATO — NO modifica contratos existentes
// Se comunica con el sistema de attestation existente via eventos
//
// DOFProofRegistry: On-chain registry for Z3 proof attestations.
// Each proof record contains a keccak256 hash of the proof transcript,
// making it verifiable by anyone.

pragma solidity ^0.8.19;

contract DOFProofRegistry {
    struct ProofRecord {
        uint256 agentId;
        uint256 trustScore;       // scaled 1e18
        bytes32 z3ProofHash;
        string storageRef;        // IPFS CID or local reference
        uint8 invariantsCount;
        uint256 timestamp;
        bool verified;
    }

    mapping(uint256 => ProofRecord) public proofs;
    uint256 public proofCount;

    address public owner;

    event ProofRegistered(
        uint256 indexed proofId,
        uint256 indexed agentId,
        bytes32 z3ProofHash,
        string storageRef
    );

    event ProofVerified(
        uint256 indexed proofId,
        bool verified
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "DOFProofRegistry: not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /// @notice Register a new Z3 proof attestation
    /// @param agentId The agent identifier
    /// @param trustScore Trust score scaled by 1e18
    /// @param z3ProofHash keccak256 hash of the proof transcript
    /// @param storageRef IPFS CID or local storage reference
    /// @param invariantsCount Number of invariants verified
    /// @return proofId The ID of the registered proof
    function registerProof(
        uint256 agentId,
        uint256 trustScore,
        bytes32 z3ProofHash,
        string calldata storageRef,
        uint8 invariantsCount
    ) external returns (uint256) {
        uint256 proofId = proofCount;
        proofs[proofId] = ProofRecord({
            agentId: agentId,
            trustScore: trustScore,
            z3ProofHash: z3ProofHash,
            storageRef: storageRef,
            invariantsCount: invariantsCount,
            timestamp: block.timestamp,
            verified: false
        });
        proofCount++;

        emit ProofRegistered(proofId, agentId, z3ProofHash, storageRef);
        return proofId;
    }

    /// @notice Verify a proof by checking that the transcript hash matches
    /// @param proofId The proof ID to verify
    /// @param proofTranscript The full proof transcript
    /// @return True if the hash matches
    function verifyProof(
        uint256 proofId,
        bytes calldata proofTranscript
    ) external returns (bool) {
        require(proofId < proofCount, "DOFProofRegistry: invalid proof ID");

        ProofRecord storage record = proofs[proofId];
        bytes32 computedHash = keccak256(proofTranscript);
        bool isValid = computedHash == record.z3ProofHash;

        if (isValid) {
            record.verified = true;
            emit ProofVerified(proofId, true);
        }

        return isValid;
    }

    /// @notice Get a proof record
    /// @param proofId The proof ID
    /// @return The proof record
    function getProof(uint256 proofId) external view returns (ProofRecord memory) {
        require(proofId < proofCount, "DOFProofRegistry: invalid proof ID");
        return proofs[proofId];
    }

    /// @notice Get the total number of registered proofs
    /// @return The proof count
    function getProofCount() external view returns (uint256) {
        return proofCount;
    }
}
