"""
DOF SDK — Deterministic Observability Framework.

Thin public API wrapping the core/ modules. No files are moved;
dof/ re-exports the existing infrastructure for external consumption.

Quick start:
    from dof import GenericAdapter
    result = GenericAdapter().wrap_output("your agent output here")
    # → {status: "pass", violations: [], score: 8.5}

    from dof.quick import verify, prove, benchmark
    result = verify("Bitcoin was created in 2009")
    proofs = prove()
    bench = benchmark()
"""

__version__ = "0.4.1"

import os as _os

_BASE_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))

# ─────────────────────────────────────────────────────────────────────
# Governance
# ─────────────────────────────────────────────────────────────────────

from core.governance import (
    ConstitutionEnforcer as Constitution,
    ConstitutionEnforcer,
    GovernanceResult,
    load_constitution,
    get_constitution,
    HARD_RULES,
    SOFT_RULES,
    PII_PATTERNS,
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
    TokenTracker,
)

# ─────────────────────────────────────────────────────────────────────
# AST Verifier
# ─────────────────────────────────────────────────────────────────────

from core.ast_verifier import ASTVerifier
from core.entropy_detector import EntropyDetector

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
# Data Oracle
# ─────────────────────────────────────────────────────────────────────

from core.data_oracle import DataOracle, OracleVerdict, FactClaim

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
# Test Generator + Benchmark
# ─────────────────────────────────────────────────────────────────────

from core.test_generator import TestGenerator, BenchmarkRunner, BenchmarkResult

# ─────────────────────────────────────────────────────────────────────
# AgentLeak Privacy Benchmark
# ─────────────────────────────────────────────────────────────────────

from core.agentleak_benchmark import (
    AgentLeakMapper,
    PrivacyLeakGenerator,
    PrivacyBenchmarkRunner,
)

# ─────────────────────────────────────────────────────────────────────
# Z3 Test Generator + Boundary Engine (v0.3.2)
# ─────────────────────────────────────────────────────────────────────

from core.z3_test_generator import Z3TestGenerator, GenerationReport
from core.boundary import BoundaryEngine

# ─────────────────────────────────────────────────────────────────────
# Z3 Proof Attestations (v0.3.3)
# ─────────────────────────────────────────────────────────────────────

from core.z3_proof import Z3ProofAttestation
from core.proof_hash import ProofSerializer
from core.proof_storage import ProofStorage

# ─────────────────────────────────────────────────────────────────────
# Z3 Verifier (optional — requires z3-solver)
# ─────────────────────────────────────────────────────────────────────

try:
    from core.z3_verifier import Z3Verifier
except ImportError:
    Z3Verifier = None

# ─────────────────────────────────────────────────────────────────────
# Z3 State Verification (v0.3.0)
# ─────────────────────────────────────────────────────────────────────

try:
    from core.state_model import DOFAgentState
    from core.transitions import TransitionVerifier, TransitionType, VerificationResult
    from core.hierarchy_z3 import HierarchyZ3
except ImportError:
    DOFAgentState = None
    TransitionVerifier = None
    TransitionType = None
    VerificationResult = None
    HierarchyZ3 = None

# ─────────────────────────────────────────────────────────────────────
# Z3 Gate (v0.3.1)
# ─────────────────────────────────────────────────────────────────────

try:
    from core.z3_gate import Z3Gate, GateResult, GateVerification
    from core.agent_output import AgentOutput, OutputType
except ImportError:
    Z3Gate = None
    GateResult = None
    GateVerification = None
    AgentOutput = None
    OutputType = None

# ─────────────────────────────────────────────────────────────────────
# OpenTelemetry Bridge (optional — requires opentelemetry-api)
# ─────────────────────────────────────────────────────────────────────

from core.otel_bridge import OTelBridge, LAYER_NAMES, METRIC_NAMES

# ─────────────────────────────────────────────────────────────────────
# Regression Tracker (v0.3.3)
# ─────────────────────────────────────────────────────────────────────

from core.regression_tracker import RegressionTracker, RegressionReport, ChangeType

# ─────────────────────────────────────────────────────────────────────
# Event Stream
# ─────────────────────────────────────────────────────────────────────

from core.event_stream import (
    EventBus,
    EventBackend,
    InMemoryBackend,
    EventType,
    Event,
)

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
    if Z3Verifier is None:
        raise ImportError("z3-solver is required: pip install z3-solver")
    verifier = Z3Verifier()
    return verifier.verify_all()


__all__ = [
    # Top-level functions
    "register",
    "verify",
    # Governance
    "Constitution",
    "ConstitutionEnforcer",
    "GovernanceResult",
    "load_constitution",
    "get_constitution",
    "HARD_RULES",
    "SOFT_RULES",
    "PII_PATTERNS",
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
    "TokenTracker",
    # Verification
    "ASTVerifier",
    "EntropyDetector",
    "AdversarialEvaluator",
    "RedTeamAgent",
    "GuardianAgent",
    "DeterministicArbiter",
    # Z3 (optional)
    "Z3Verifier",
    # Z3 State Verification (v0.3.0)
    "DOFAgentState",
    "TransitionVerifier",
    "TransitionType",
    "VerificationResult",
    "HierarchyZ3",
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
    # Data Oracle
    "DataOracle",
    "OracleVerdict",
    "FactClaim",
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
    # Test Generator + Benchmark
    "TestGenerator",
    "BenchmarkRunner",
    "BenchmarkResult",
    # AgentLeak Privacy Benchmark
    "AgentLeakMapper",
    "PrivacyLeakGenerator",
    "PrivacyBenchmarkRunner",
    # Z3 Test Generator + Boundary Engine (v0.3.2)
    "Z3TestGenerator",
    "GenerationReport",
    "BoundaryEngine",
    # Z3 Proof Attestations (v0.3.3)
    "Z3ProofAttestation",
    "ProofSerializer",
    "ProofStorage",
    # OpenTelemetry Bridge
    "OTelBridge",
    "LAYER_NAMES",
    "METRIC_NAMES",
    # Event Stream
    "EventBus",
    "EventBackend",
    "InMemoryBackend",
    "EventType",
    "Event",
    # Regression Tracker
    "RegressionTracker",
    "RegressionReport",
    "ChangeType",
]

from dof.x402_gateway import TrustGateway, GatewayVerdict, GatewayAction
