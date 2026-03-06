"""
DOF SDK — Deterministic Observability Framework.

Thin public API wrapping the core/ modules. No files are moved;
dof/ re-exports the existing infrastructure for external consumption.

Quick start:
    from dof import register, verify, Metrics, Constitution

    # Initialize governance from constitution YAML
    register(constitution="dof.constitution.yml")

    # Run formal Z3 proofs
    results = verify()

    # Access runtime metrics
    metrics = Metrics()
    report = metrics.compute_all(window=100)

    # Access governance rules
    constitution = Constitution()
    result = constitution.check(output_text)
"""

__version__ = "0.1.0"

import os as _os

_BASE_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))

# ─────────────────────────────────────────────────────────────────────
# Governance
# ─────────────────────────────────────────────────────────────────────

from core.governance import (
    ConstitutionEnforcer as Constitution,
    GovernanceResult,
    load_constitution,
    get_constitution,
    HARD_RULES,
    SOFT_RULES,
)

# ─────────────────────────────────────────────────────────────────────
# Metrics (Runtime Observer)
# ─────────────────────────────────────────────────────────────────────

from core.runtime_observer import (
    RuntimeObserver as Metrics,
    MetricResult,
)

# ─────────────────────────────────────────────────────────────────────
# Observability (Traces, Sessions, Error Classification)
# ─────────────────────────────────────────────────────────────────────

from core.observability import (
    RunTrace,
    StepTrace,
    RunTraceStore,
    ErrorClass,
    classify_error,
    causal_trace,
    compute_derived_metrics,
    estimate_tokens,
    set_deterministic,
    get_session_id,
    reset_session,
)

# ─────────────────────────────────────────────────────────────────────
# AST Verifier
# ─────────────────────────────────────────────────────────────────────

from core.ast_verifier import ASTVerifier

# ─────────────────────────────────────────────────────────────────────
# Adversarial Evaluation
# ─────────────────────────────────────────────────────────────────────

from core.adversarial import (
    AdversarialEvaluator,
    RedTeamAgent,
    GuardianAgent,
    DeterministicArbiter,
)

# ─────────────────────────────────────────────────────────────────────
# Task Contracts
# ─────────────────────────────────────────────────────────────────────

from core.task_contract import TaskContract, ContractResult

# ─────────────────────────────────────────────────────────────────────
# Provider Selection (Bayesian)
# ─────────────────────────────────────────────────────────────────────

from core.providers import BayesianProviderSelector

# ─────────────────────────────────────────────────────────────────────
# Memory Governance
# ─────────────────────────────────────────────────────────────────────

from core.memory_governance import (
    GovernedMemoryStore,
    TemporalGraph,
    MemoryClassifier,
    ConstitutionalDecay,
    MemoryEntry,
    ConflictError,
)

# ─────────────────────────────────────────────────────────────────────
# OAGS Bridge
# ─────────────────────────────────────────────────────────────────────

from core.oags_bridge import (
    OAGSIdentity,
    OAGSPolicyBridge,
    OAGSAuditBridge,
)

# ─────────────────────────────────────────────────────────────────────
# Oracle Bridge (ERC-8004)
# ─────────────────────────────────────────────────────────────────────

from core.oracle_bridge import (
    OracleBridge,
    AttestationCertificate,
    AttestationRegistry,
    CertificateSigner,
)

# ─────────────────────────────────────────────────────────────────────
# Enigma Bridge (trust_scores → erc-8004scan.xyz)
# ─────────────────────────────────────────────────────────────────────

from core.enigma_bridge import EnigmaBridge, DOFTrustScore, TrustScore

# ─────────────────────────────────────────────────────────────────────
# Avalanche Bridge (on-chain DOFValidationRegistry)
# ─────────────────────────────────────────────────────────────────────

from core.avalanche_bridge import AvalancheBridge

# ─────────────────────────────────────────────────────────────────────
# Merkle Tree (batch attestations)
# ─────────────────────────────────────────────────────────────────────

from core.merkle_tree import MerkleTree, MerkleBatcher, MerkleBatch

# ─────────────────────────────────────────────────────────────────────
# Execution DAG
# ─────────────────────────────────────────────────────────────────────

from core.execution_dag import ExecutionDAG, DAGNode, DAGEdge

# ─────────────────────────────────────────────────────────────────────
# Loop Guard
# ─────────────────────────────────────────────────────────────────────

from core.loop_guard import LoopGuard, LoopGuardResult

# ─────────────────────────────────────────────────────────────────────
# Storage
# ─────────────────────────────────────────────────────────────────────

from core.storage import StorageFactory, JSONLBackend, PostgreSQLBackend

# ─────────────────────────────────────────────────────────────────────
# Framework-Agnostic Governance
# ─────────────────────────────────────────────────────────────────────

from integrations.langgraph_adapter import (
    DOFGovernanceNode,
    DOFASTNode,
    DOFMemoryNode,
    DOFObservabilityNode,
    FrameworkAdapter,
    GenericAdapter,
    CrewAIAdapter,
    LangGraphAdapter,
    create_governed_pipeline,
)

# ─────────────────────────────────────────────────────────────────────
# Crew Runner
# ─────────────────────────────────────────────────────────────────────

from core.crew_runner import run_crew


# ─────────────────────────────────────────────────────────────────────
# Top-level convenience functions
# ─────────────────────────────────────────────────────────────────────

def register(constitution: str = "dof.constitution.yml") -> dict:
    """Initialize governance from a constitution YAML file.

    Args:
        constitution: Path to the YAML file (relative to project root
                      or absolute).

    Returns:
        The parsed constitution dict.
    """
    path = constitution
    if not _os.path.isabs(path):
        path = _os.path.join(_BASE_DIR, path)
    return load_constitution(path)


def verify() -> list:
    """Run formal Z3 proofs on DOF invariants.

    Returns:
        List of ProofResult objects from Z3Verifier.verify_all().
    """
    from core.z3_verifier import Z3Verifier
    verifier = Z3Verifier()
    return verifier.verify_all()


__all__ = [
    # Top-level functions
    "register",
    "verify",
    # Governance
    "Constitution",
    "GovernanceResult",
    "load_constitution",
    "get_constitution",
    "HARD_RULES",
    "SOFT_RULES",
    # Metrics
    "Metrics",
    "MetricResult",
    # Observability
    "RunTrace",
    "StepTrace",
    "RunTraceStore",
    "ErrorClass",
    "classify_error",
    "causal_trace",
    "compute_derived_metrics",
    "estimate_tokens",
    "set_deterministic",
    "get_session_id",
    "reset_session",
    # Verification
    "ASTVerifier",
    "AdversarialEvaluator",
    "RedTeamAgent",
    "GuardianAgent",
    "DeterministicArbiter",
    # Contracts
    "TaskContract",
    "ContractResult",
    # Providers
    "BayesianProviderSelector",
    # Memory Governance
    "GovernedMemoryStore",
    "TemporalGraph",
    "MemoryClassifier",
    "ConstitutionalDecay",
    "MemoryEntry",
    "ConflictError",
    # OAGS Bridge
    "OAGSIdentity",
    "OAGSPolicyBridge",
    "OAGSAuditBridge",
    # Oracle Bridge
    "OracleBridge",
    "AttestationCertificate",
    "AttestationRegistry",
    "CertificateSigner",
    # Enigma Bridge
    "EnigmaBridge",
    "DOFTrustScore",
    "TrustScore",
    # Avalanche Bridge
    "AvalancheBridge",
    # Merkle Tree
    "MerkleTree",
    "MerkleBatcher",
    "MerkleBatch",
    # Execution DAG
    "ExecutionDAG",
    "DAGNode",
    "DAGEdge",
    # Loop Guard
    "LoopGuard",
    "LoopGuardResult",
    # Storage
    "StorageFactory",
    "JSONLBackend",
    "PostgreSQLBackend",
    # Framework-Agnostic Governance
    "DOFGovernanceNode",
    "DOFASTNode",
    "DOFMemoryNode",
    "DOFObservabilityNode",
    "FrameworkAdapter",
    "GenericAdapter",
    "CrewAIAdapter",
    "LangGraphAdapter",
    "create_governed_pipeline",
    # Crew
    "run_crew",
]
