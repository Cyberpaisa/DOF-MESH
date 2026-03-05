// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

/// @title DOF Validation Registry
/// @notice Stores governance attestation hashes from the Deterministic Observability Framework
/// @author Cyber Paisa / Enigma Group

contract DOFValidationRegistry {
    struct Attestation {
        bytes32 certificateHash;
        bytes32 agentId;
        bool compliant;
        uint256 timestamp;
        address submitter;
    }

    // Attestations by certificate hash
    mapping(bytes32 => Attestation) public attestations;

    // All certificate hashes for enumeration
    bytes32[] public attestationHashes;

    // Agent attestation count
    mapping(bytes32 => uint256) public agentAttestationCount;

    // Latest attestation per agent
    mapping(bytes32 => bytes32) public latestAttestation;

    // Owner
    address public owner;

    // Events
    event AttestationRegistered(
        bytes32 indexed certificateHash,
        bytes32 indexed agentId,
        bool compliant,
        uint256 timestamp,
        address submitter
    );

    event AttestationRevoked(
        bytes32 indexed certificateHash,
        bytes32 indexed agentId,
        address revoker
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /// @notice Register a governance attestation
    /// @param certificateHash BLAKE3 hash of the full attestation certificate
    /// @param agentId BLAKE3 hash of the agent identity (from OAGS)
    /// @param compliant Whether GCR == 1.0
    function registerAttestation(
        bytes32 certificateHash,
        bytes32 agentId,
        bool compliant
    ) external {
        require(attestations[certificateHash].timestamp == 0, "Already registered");

        attestations[certificateHash] = Attestation({
            certificateHash: certificateHash,
            agentId: agentId,
            compliant: compliant,
            timestamp: block.timestamp,
            submitter: msg.sender
        });

        attestationHashes.push(certificateHash);
        agentAttestationCount[agentId]++;
        latestAttestation[agentId] = certificateHash;

        emit AttestationRegistered(certificateHash, agentId, compliant, block.timestamp, msg.sender);
    }

    /// @notice Register a batch of attestations (gas optimization)
    /// @param certHashes Array of certificate hashes
    /// @param agentIds Array of agent IDs
    /// @param compliants Array of compliance flags
    function registerBatch(
        bytes32[] calldata certHashes,
        bytes32[] calldata agentIds,
        bool[] calldata compliants
    ) external {
        require(certHashes.length == agentIds.length && agentIds.length == compliants.length, "Length mismatch");

        for (uint i = 0; i < certHashes.length; i++) {
            if (attestations[certHashes[i]].timestamp == 0) {
                attestations[certHashes[i]] = Attestation({
                    certificateHash: certHashes[i],
                    agentId: agentIds[i],
                    compliant: compliants[i],
                    timestamp: block.timestamp,
                    submitter: msg.sender
                });
                attestationHashes.push(certHashes[i]);
                agentAttestationCount[agentIds[i]]++;
                latestAttestation[agentIds[i]] = certHashes[i];

                emit AttestationRegistered(certHashes[i], agentIds[i], compliants[i], block.timestamp, msg.sender);
            }
        }
    }

    /// @notice Revoke an attestation (owner only)
    function revokeAttestation(bytes32 certificateHash) external onlyOwner {
        require(attestations[certificateHash].timestamp != 0, "Not found");
        bytes32 agentId = attestations[certificateHash].agentId;
        attestations[certificateHash].compliant = false;
        emit AttestationRevoked(certificateHash, agentId, msg.sender);
    }

    /// @notice Get total number of attestations
    function totalAttestations() external view returns (uint256) {
        return attestationHashes.length;
    }

    /// @notice Verify if an attestation exists and is compliant
    function isCompliant(bytes32 certificateHash) external view returns (bool) {
        return attestations[certificateHash].compliant;
    }

    /// @notice Get attestation details
    function getAttestation(bytes32 certificateHash) external view returns (
        bytes32 agentId, bool compliant, uint256 timestamp, address submitter
    ) {
        Attestation memory a = attestations[certificateHash];
        return (a.agentId, a.compliant, a.timestamp, a.submitter);
    }
}
