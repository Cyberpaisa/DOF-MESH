// SPDX-License-Identifier: MIT
// NUEVO CONTRATO — NO modifica DOFProofRegistry.sol ni otros contratos existentes
//
// DOFEvaluator: ERC-8183 Evaluator interface for DOF.
// Receives job submissions, verifies Z3 proofs via DOFProofRegistry,
// and calls complete() or reject() on the job contract.
//
// TODO paper — "Learning When to Act or Refuse" (KARL):
// DOFEvaluator embodies the neurosymbolic evaluation pattern:
// submission arrives → deterministic proof lookup → approve or reject.
// No LLM in the critical path. Pure Z3 proof verification.

pragma solidity ^0.8.20;

/// @title IERC8183Job — Minimal interface for ERC-8183 Job contracts
/// @notice Defines the functions an Evaluator calls to resolve a job
interface IERC8183Job {
    /// @notice Mark a job as completed (submission accepted)
    /// @param jobId The job identifier
    function complete(uint256 jobId) external;

    /// @notice Reject a job submission with a reason
    /// @param jobId The job identifier
    /// @param reason Human-readable rejection reason
    function reject(uint256 jobId, string calldata reason) external;
}

/// @title IDOFProofRegistry — Read-only interface to existing DOFProofRegistry
/// @notice Used to query proof records without modifying the registry contract
interface IDOFProofRegistry {
    struct ProofRecord {
        uint256 agentId;
        uint256 trustScore;
        bytes32 z3ProofHash;
        string storageRef;
        uint8 invariantsCount;
        uint256 timestamp;
        bool verified;
    }

    /// @notice Get a proof record by ID
    /// @param proofId The proof ID to look up
    /// @return The proof record
    function getProof(uint256 proofId) external view returns (ProofRecord memory);

    /// @notice Get the total number of registered proofs
    /// @return The proof count
    function getProofCount() external view returns (uint256);
}

/// @title DOFEvaluator — ERC-8183 Evaluator powered by Z3 proof verification
/// @author Cyber Paisa / DOF Framework
/// @notice Acts as a trustless Evaluator in the ERC-8183 agentic commerce standard.
///         Every Z3 proof becomes an on-chain attestation. Every agent job gets a
///         verifiable outcome. Zero LLM in the evaluation path.
/// @dev References DOFProofRegistry (read-only). Never modifies existing contracts.
///      The proof hash must be keccak256 of the Z3 proof transcript, consistent
///      with the existing attestation format in DOFProofRegistry.
contract DOFEvaluator {
    // ─────────────────────────────────────────────────────────────────
    // State
    // ─────────────────────────────────────────────────────────────────

    /// @notice Address of the deployed DOFProofRegistry contract
    address public immutable proofRegistry;

    /// @notice Contract owner (deployer)
    address public owner;

    /// @notice Tracks which jobs have been evaluated to prevent double-evaluation
    mapping(uint256 => mapping(address => bool)) public evaluated;

    // ─────────────────────────────────────────────────────────────────
    // Events
    // ─────────────────────────────────────────────────────────────────

    /// @notice Emitted when a job evaluation is completed
    /// @param jobId The job that was evaluated
    /// @param proofHash The Z3 proof hash used for verification
    /// @param passed Whether the submission passed verification
    event EvaluationCompleted(
        uint256 indexed jobId,
        bytes32 proofHash,
        bool passed
    );

    // ─────────────────────────────────────────────────────────────────
    // Errors
    // ─────────────────────────────────────────────────────────────────

    /// @notice Thrown when caller is not the contract owner
    error Unauthorized();

    /// @notice Thrown when a job has already been evaluated
    error AlreadyEvaluated();

    /// @notice Thrown when the job contract address is invalid
    error InvalidJobContract();

    // ─────────────────────────────────────────────────────────────────
    // Modifiers
    // ─────────────────────────────────────────────────────────────────

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    // ─────────────────────────────────────────────────────────────────
    // Constructor
    // ─────────────────────────────────────────────────────────────────

    /// @notice Deploy the DOFEvaluator with a reference to DOFProofRegistry
    /// @param _proofRegistry Address of the deployed DOFProofRegistry contract
    constructor(address _proofRegistry) {
        require(_proofRegistry != address(0), "DOFEvaluator: zero registry address");
        proofRegistry = _proofRegistry;
        owner = msg.sender;
    }

    // ─────────────────────────────────────────────────────────────────
    // Core Functions
    // ─────────────────────────────────────────────────────────────────

    /// @notice Evaluate a job submission by verifying its Z3 proof
    /// @dev Looks up the submissionHash in DOFProofRegistry. If a matching
    ///      verified proof exists, calls complete() on the job contract.
    ///      Otherwise, calls reject() with a descriptive reason.
    /// @param jobContract Address of the ERC-8183 Job contract
    /// @param jobId The job identifier to evaluate
    /// @param submissionHash keccak256 hash of the submission (must match a
    ///        z3ProofHash in the registry)
    function evaluate(
        address jobContract,
        uint256 jobId,
        bytes32 submissionHash
    ) external onlyOwner {
        if (jobContract == address(0)) revert InvalidJobContract();
        if (evaluated[jobId][jobContract]) revert AlreadyEvaluated();

        evaluated[jobId][jobContract] = true;

        bool proofValid = verifyProof(submissionHash);

        if (proofValid) {
            IERC8183Job(jobContract).complete(jobId);
            emit EvaluationCompleted(jobId, submissionHash, true);
        } else {
            IERC8183Job(jobContract).reject(
                jobId,
                "DOFEvaluator: Z3 proof not found or not verified in registry"
            );
            emit EvaluationCompleted(jobId, submissionHash, false);
        }
    }

    /// @notice Verify that a proof hash exists and is verified in DOFProofRegistry
    /// @dev Iterates through all registered proofs looking for a matching
    ///      z3ProofHash that has been verified. Gas-intensive for large registries;
    ///      consider off-chain indexing for production.
    /// @param proofHash The keccak256 proof hash to look up
    /// @return True if a matching verified proof exists
    function verifyProof(bytes32 proofHash) public view returns (bool) {
        IDOFProofRegistry registry = IDOFProofRegistry(proofRegistry);
        uint256 count = registry.getProofCount();

        for (uint256 i = 0; i < count; i++) {
            IDOFProofRegistry.ProofRecord memory record = registry.getProof(i);
            if (record.z3ProofHash == proofHash && record.verified) {
                return true;
            }
        }

        return false;
    }

    // ─────────────────────────────────────────────────────────────────
    // Admin
    // ─────────────────────────────────────────────────────────────────

    /// @notice Transfer ownership of the evaluator
    /// @param newOwner Address of the new owner
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "DOFEvaluator: zero address");
        owner = newOwner;
    }
}
