"""
DOF Mesh Legion — Complete Technical Architecture
===============================================

1. General Overview
-------------------
DOF Mesh (Deterministic Observability Framework Mesh) is a distributed
multi-agent system for intelligent LLM orchestration. It solves the problem of
latency, cost, and reliability in AI systems through adaptive routing,
circuit breaking, and auto-scaling.

ASCII Topology:
    [Client]
        |
    [mesh_orchestrator] ←→ [mesh_consensus]
        |        |
    [mesh_router_v2]    [mesh_auto_scaler]
        |        |
    [Providers]  [mesh_circuit_breaker]
    ├── OpenAI
    ├── Anthropic
    ├── DeepSeek
    └── Local LLMs

2. Message Protocol
------------------------
JSON Format:
{
    "message_id": "uuid4",
    "task_id": "uuid4",
    "timestamp": "ISO8601",
    "source_node": "node_id",
    "target_node": "node_id",
    "message_type": "TASK|RESP|ERROR|HEARTBEAT",
    "payload": {
        "model": "gpt-4",
        "prompt": "text",
        "max_tokens": 1000,
        "temperature": 0.7
    },
    "metadata": {
        "priority": 1-10,
        "specialty": "code|math|creative",
        "cost_limit": 0.05
    }
}

Lifecycle:
1. TASK created → processing/<task_id>.json
2. Processing → rename to .processing
3. RESP generated → rename to .done
4. Error → rename to .error

Race conditions resolved with:
    try:
        os.rename(tmp_path, final_path)
    except FileExistsError:
        pass  # Another worker already processed

3. Core Modules (Phase 8+9)
---------------------------
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import time
import json
import os
from pathlib import Path
import uuid
from datetime import datetime
import statistics
import math

# ============================================================================
# Module: mesh_router_v2.py
# ============================================================================

class NodeSpecialty(Enum):
    CODE = "code"
    MATH = "math"
    CREATIVE = "creative"
    REASONING = "reasoning"
    GENERAL = "general"

@dataclass
class NodeMetrics:
    node_id: str
    response_time_ewma: float = 0.0
    error_rate_ewma: float = 0.0
    success_count: int = 0
    error_count: int = 0
    specialty_scores: Dict[NodeSpecialty, float] = field(default_factory=dict)
    last_used: float = field(default_factory=time.time)

    def update_ewma(self, response_time: float, alpha: float = 0.3):
        """Update EWMA for response time."""
        if self.response_time_ewma == 0:
            self.response_time_ewma = response_time
        else:
            self.response_time_ewma = alpha * response_time + (1 - alpha) * self.response_time_ewma

    def update_error_rate(self, success: bool, alpha: float = 0.3):
        """Update EWMA for error rate."""
        rate = 0.0 if success else 1.0
        if self.error_rate_ewma == 0:
            self.error_rate_ewma = rate
        else:
            self.error_rate_ewma = alpha * rate + (1 - alpha) * self.error_rate_ewma

        if success:
            self.success_count += 1
        else:
            self.error_count += 1

    def get_score(self, specialty: NodeSpecialty) -> float:
        """Calculate composite score for routing."""
        base_score = 100.0

        # Penalize high error rate
        error_penalty = self.error_rate_ewma * 50
        base_score -= error_penalty

        # Penalize slow response (normalized to 1s baseline)
        time_penalty = min(self.response_time_ewma / 10.0, 30.0)
        base_score -= time_penalty

        # Add specialty bonus
        specialty_bonus = self.specialty_scores.get(specialty, 0.0) * 20
        base_score += specialty_bonus

        # Recency bonus (prefer recently used nodes)
        recency = time.time() - self.last_used
        recency_bonus = max(0, 10 - (recency / 60))  # Decays over 10 minutes
        base_score += recency_bonus

        return max(0.1, base_score)

class MeshRouterV2:
    """Intelligent router with EWMA and specialty scoring."""

    def __init__(self):
        self.node_metrics: Dict[str, NodeMetrics] = {}
        self.specialty_mapping: Dict[NodeSpecialty, List[str]] = {}

    def register_node(self, node_id: str, specialties: List[NodeSpecialty]):
        """Register a node with its specialties."""
        if node_id not in self.node_metrics:
            self.node_metrics[node_id] = NodeMetrics(node_id=node_id)

        # Initialize specialty scores
        for specialty in specialties:
            self.node_metrics[node_id].specialty_scores[specialty] = 1.0

            if specialty not in self.specialty_mapping:
                self.specialty_mapping[specialty] = []
            if node_id not in self.specialty_mapping[specialty]:
                self.specialty_mapping[specialty].append(node_id)

    def update_metrics(self, node_id: str, response_time: float, success: bool):
        """Update metrics after a node completes a task."""
        if node_id in self.node_metrics:
            metrics = self.node_metrics[node_id]
            metrics.update_ewma(response_time)
            metrics.update_error_rate(success)
            metrics.last_used = time.time()

    def route(self, specialty: NodeSpecialty, exclude_nodes: List[str] = None) -> Optional[str]:
        """Route to best node for given specialty."""
        if exclude_nodes is None:
            exclude_nodes = []

        candidates = []
        for node_id in self.specialty_mapping.get(specialty, []):
            if node_id in exclude_nodes:
                continue
            if node_id in self.node_metrics:
                score = self.node_metrics[node_id].get_score(specialty)
                candidates.append((score, node_id))

        if not candidates:
            return None

        # Weighted random selection based on scores
        scores, nodes = zip(*candidates)
        total = sum(scores)
        if total == 0:
            return nodes[0]

        weights = [s / total for s in scores]
        import random
        return random.choices(nodes, weights=weights, k=1)[0]

# ============================================================================
# Module: mesh_circuit_breaker.py
# ============================================================================

class CircuitState(Enum):
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Fail fast
    HALF_OPEN = "HALF_OPEN" # Testing recovery

@dataclass
class CircuitConfig:
    failure_threshold: int = 5
    reset_timeout: float = 30.0  # seconds
    half_open_max_attempts: int = 3

class MeshCircuitBreaker:
    """Circuit breaker pattern for fault tolerance."""

    _instances = {}

    def __new__(cls, node_id: str):
        if node_id not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[node_id] = instance
        return cls._instances[node_id]

    def __init__(self, node_id: str):
        if not hasattr(self, '_initialized'):
            self.node_id = node_id
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.last_failure_time = 0
            self.half_open_attempts = 0
            self.config = CircuitConfig()
            self._initialized = True

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.config.reset_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_attempts = 0
            else:
                raise CircuitOpenError(f"Circuit open for node {self.node_id}")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
