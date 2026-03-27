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

__version__ = "0.5.0"

import os as _os
import logging as _logging

_BASE_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_logger = _logging.getLogger("dof")

# ─────────────────────────────────────────────────────────────────────
# Governance (core — stdlib only)
# ─────────────────────────────────────────────────────────────────────

try:
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
except ImportError:
    _logger.debug("core.governance not available")
    Constitution = ConstitutionEnforcer = GovernanceResult = None
    load_constitution = get_constitution = None
    HARD_RULES = SOFT_RULES = PII_PATTERNS = None

# ─────────────────────────────────────────────────────────────────────
# Metrics (Runtime Observer)
# ─────────────────────────────────────────────────────────────────────

try:
    from core.runtime_observer import (
        RuntimeObserver as Metrics,
        MetricResult,
    )
except ImportError:
    _logger.debug("core.runtime_observer not available")
    Metrics = MetricResult = None

# ─────────────────────────────────────────────────────────────────────
# Observability (Traces, Sessions, Error Classification)
# ─────────────────────────────────────────────────────────────────────

try:
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
except ImportError:
    _logger.debug("core.observability not available")
    RunTrace = StepTrace = RunTraceStore = ErrorClass = None
    classify_error = causal_trace = compute_derived_metrics = None
    estimate_tokens = set_deterministic = get_session_id = reset_session = None
    TokenTracker = None

# ─────────────────────────────────────────────────────────────────────
# AST Verifier
# ─────────────────────────────────────────────────────────────────────

try:
    from core.ast_verifier import ASTVerifier
except ImportError:
    _logger.debug("core.ast_verifier not available")
    ASTVerifier = None

try:
    from core.entropy_detector import EntropyDetector
except ImportError:
    _logger.debug("core.entropy_detector not available")
    EntropyDetector = None

# ─────────────────────────────────────────────────────────────────────
# Adversarial Evaluation
# ─────────────────────────────────────────────────────────────────────

try:
    from core.adversarial import (
        AdversarialEvaluator,
        RedTeamAgent,
        GuardianAgent,
        DeterministicArbiter,
    )
except ImportError:
    _logger.debug("core.adversarial not available")
    AdversarialEvaluator = RedTeamAgent = GuardianAgent = DeterministicArbiter = None

# ─────────────────────────────────────────────────────────────────────
# Task Contracts
# ─────────────────────────────────────────────────────────────────────

try:
    from core.task_contract import TaskContract, ContractResult
except ImportError:
    _logger.debug("core.task_contract not available")
    TaskContract = ContractResult = None

# ─────────────────────────────────────────────────────────────────────
# Provider Selection (Bayesian)
# ─────────────────────────────────────────────────────────────────────

try:
    from core.providers import BayesianProviderSelector
except ImportError:
    _logger.debug("core.providers not available")
    BayesianProviderSelector = None

# ─────────────────────────────────────────────────────────────────────
# Memory Governance
# ─────────────────────────────────────────────────────────────────────

try:
    from core.memory_governance import (
        GovernedMemoryStore,
        TemporalGraph,
        MemoryClassifier,
        ConstitutionalDecay,
        MemoryEntry,
        ConflictError,
    )
except ImportError:
    _logger.debug("core.memory_governance not available")
    GovernedMemoryStore = TemporalGraph = MemoryClassifier = None
    ConstitutionalDecay = MemoryEntry = ConflictError = None

# ─────────────────────────────────────────────────────────────────────
# OAGS Bridge
# ─────────────────────────────────────────────────────────────────────

try:
    from core.oags_bridge import (
        OAGSIdentity,
        OAGSPolicyBridge,
        OAGSAuditBridge,
    )
except ImportError:
    _logger.debug("core.oags_bridge not available")
    OAGSIdentity = OAGSPolicyBridge = OAGSAuditBridge = None

# ─────────────────────────────────────────────────────────────────────
# Oracle Bridge (ERC-8004)
# ─────────────────────────────────────────────────────────────────────

try:
    from core.oracle_bridge import (
        OracleBridge,
        AttestationCertificate,
        AttestationRegistry,
        CertificateSigner,
    )
except ImportError:
    _logger.debug("core.oracle_bridge not available")
    OracleBridge = AttestationCertificate = AttestationRegistry = CertificateSigner = None

# ─────────────────────────────────────────────────────────────────────
# Enigma Bridge (trust_scores → erc-8004scan.xyz)
# ─────────────────────────────────────────────────────────────────────

try:
    from core.enigma_bridge import EnigmaBridge, DOFTrustScore, TrustScore
except ImportError:
    _logger.debug("core.enigma_bridge not available")
    EnigmaBridge = DOFTrustScore = TrustScore = None

# ─────────────────────────────────────────────────────────────────────
# Avalanche Bridge (on-chain DOFValidationRegistry)
# ─────────────────────────────────────────────────────────────────────

try:
    from core.avalanche_bridge import AvalancheBridge
except ImportError:
    _logger.debug("core.avalanche_bridge not available")
    AvalancheBridge = None

# ─────────────────────────────────────────────────────────────────────
# Merkle Tree (batch attestations)
# ─────────────────────────────────────────────────────────────────────

try:
    from core.merkle_tree import MerkleTree, MerkleBatcher, MerkleBatch
except ImportError:
    _logger.debug("core.merkle_tree not available")
    MerkleTree = MerkleBatcher = MerkleBatch = None

# ─────────────────────────────────────────────────────────────────────
# Execution DAG
# ─────────────────────────────────────────────────────────────────────

try:
    from core.execution_dag import ExecutionDAG, DAGNode, DAGEdge
except ImportError:
    _logger.debug("core.execution_dag not available")
    ExecutionDAG = DAGNode = DAGEdge = None

# ─────────────────────────────────────────────────────────────────────
# Loop Guard
# ─────────────────────────────────────────────────────────────────────

try:
    from core.loop_guard import LoopGuard, LoopGuardResult
except ImportError:
    _logger.debug("core.loop_guard not available")
    LoopGuard = LoopGuardResult = None

# ─────────────────────────────────────────────────────────────────────
# Data Oracle
# ─────────────────────────────────────────────────────────────────────

try:
    from core.data_oracle import DataOracle, OracleVerdict, FactClaim
except ImportError:
    _logger.debug("core.data_oracle not available")
    DataOracle = OracleVerdict = FactClaim = None

# ─────────────────────────────────────────────────────────────────────
# Storage
# ─────────────────────────────────────────────────────────────────────

try:
    from core.storage import StorageFactory, JSONLBackend, PostgreSQLBackend
except ImportError:
    _logger.debug("core.storage not available")
    StorageFactory = JSONLBackend = PostgreSQLBackend = None

# ─────────────────────────────────────────────────────────────────────
# Framework-Agnostic Governance
# ─────────────────────────────────────────────────────────────────────

try:
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
except ImportError:
    _logger.debug("integrations.langgraph_adapter not available")
    DOFGovernanceNode = DOFASTNode = DOFMemoryNode = DOFObservabilityNode = None
    FrameworkAdapter = GenericAdapter = CrewAIAdapter = LangGraphAdapter = None
    create_governed_pipeline = None

# ─────────────────────────────────────────────────────────────────────
# Crew Runner (optional — requires crewai)
# ─────────────────────────────────────────────────────────────────────

try:
    from core.crew_runner import run_crew
except ImportError:
    _logger.debug("core.crew_runner not available")
    run_crew = None

# ─────────────────────────────────────────────────────────────────────
# Test Generator + Benchmark
# ─────────────────────────────────────────────────────────────────────

try:
    from core.test_generator import TestGenerator, BenchmarkRunner, BenchmarkResult
except ImportError:
    _logger.debug("core.test_generator not available")
    TestGenerator = BenchmarkRunner = BenchmarkResult = None

# ─────────────────────────────────────────────────────────────────────
# AgentLeak Privacy Benchmark
# ─────────────────────────────────────────────────────────────────────

try:
    from core.agentleak_benchmark import (
        AgentLeakMapper,
        PrivacyLeakGenerator,
        PrivacyBenchmarkRunner,
    )
except ImportError:
    _logger.debug("core.agentleak_benchmark not available")
    AgentLeakMapper = PrivacyLeakGenerator = PrivacyBenchmarkRunner = None

# ─────────────────────────────────────────────────────────────────────
# Z3 Test Generator + Boundary Engine (v0.3.2)
# ─────────────────────────────────────────────────────────────────────

try:
    from core.z3_test_generator import Z3TestGenerator, GenerationReport
except ImportError:
    _logger.debug("core.z3_test_generator not available")
    Z3TestGenerator = GenerationReport = None

try:
    from core.boundary import BoundaryEngine
except ImportError:
    _logger.debug("core.boundary not available")
    BoundaryEngine = None

# ─────────────────────────────────────────────────────────────────────
# Z3 Proof Attestations (v0.3.3)
# ─────────────────────────────────────────────────────────────────────

try:
    from core.z3_proof import Z3ProofAttestation
except ImportError:
    _logger.debug("core.z3_proof not available")
    Z3ProofAttestation = None

try:
    from core.proof_hash import ProofSerializer
except ImportError:
    _logger.debug("core.proof_hash not available")
    ProofSerializer = None

try:
    from core.proof_storage import ProofStorage
except ImportError:
    _logger.debug("core.proof_storage not available")
    ProofStorage = None

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

try:
    from core.otel_bridge import OTelBridge, LAYER_NAMES, METRIC_NAMES
except ImportError:
    _logger.debug("core.otel_bridge not available")
    OTelBridge = None
    LAYER_NAMES = METRIC_NAMES = None

# ─────────────────────────────────────────────────────────────────────
# Regression Tracker (v0.3.3)
# ─────────────────────────────────────────────────────────────────────

try:
    from core.regression_tracker import RegressionTracker, RegressionReport, ChangeType
except ImportError:
    _logger.debug("core.regression_tracker not available")
    RegressionTracker = RegressionReport = ChangeType = None

# ─────────────────────────────────────────────────────────────────────
# Event Stream
# ─────────────────────────────────────────────────────────────────────

try:
    from core.event_stream import (
        EventBus,
        EventBackend,
        InMemoryBackend,
        EventType,
        Event,
    )
except ImportError:
    _logger.debug("core.event_stream not available")
    EventBus = EventBackend = InMemoryBackend = EventType = Event = None

# ─────────────────────────────────────────────────────────────────────
# Mesh Scheduler
# ─────────────────────────────────────────────────────────────────────

try:
    from core.mesh_scheduler import MeshScheduler, TaskSlot, HIGH, NORMAL, LOW
except ImportError:
    MeshScheduler = TaskSlot = None
    HIGH, NORMAL, LOW = 1, 2, 3

# ─────────────────────────────────────────────────────────────────────
# x402 Trust Gateway (optional)
# ─────────────────────────────────────────────────────────────────────

try:
    from dof.x402_gateway import TrustGateway, GatewayVerdict, GatewayAction
except ImportError:
    TrustGateway = GatewayVerdict = GatewayAction = None

# ─────────────────────────────────────────────────────────────────────
# Local AGI — zero-token autonomous execution (v0.6.1)
# ─────────────────────────────────────────────────────────────────────

try:
    from core.autonomous_executor import AutonomousExecutor, ExecutionResult, ToolCall
except ImportError:
    AutonomousExecutor = ExecutionResult = ToolCall = None

try:
    from core.local_orchestrator import LocalOrchestrator, OrchestratorResult, LOCAL_MODELS
except ImportError:
    LocalOrchestrator = OrchestratorResult = None
    LOCAL_MODELS = []


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
    if load_constitution is None:
        raise ImportError("core.governance is required but not available")
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
    # Z3 Gate (v0.3.1)
    "Z3Gate",
    "GateResult",
    "GateVerification",
    "AgentOutput",
    "OutputType",
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
    # Mesh Scheduler
    "MeshScheduler",
    "TaskSlot",
    "HIGH",
    "NORMAL",
    "LOW",
    # Regression Tracker
    "RegressionTracker",
    "RegressionReport",
    "ChangeType",
    # x402 Trust Gateway
    "TrustGateway",
    "GatewayVerdict",
    "GatewayAction",
    # Local AGI (v0.6.1)
    "AutonomousExecutor",
    "ExecutionResult",
    "ToolCall",
    "LocalOrchestrator",
    "OrchestratorResult",
    "LOCAL_MODELS",
]
