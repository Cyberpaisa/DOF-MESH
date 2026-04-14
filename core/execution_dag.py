from __future__ import annotations
"""
Execution DAG — Directed Acyclic Graph for agent execution tracing.

Traces dependencies between agents, tools, governance layers, and
blockchain operations. Detects cycles, computes critical paths,
and generates Mermaid diagrams for visualization.

Zero external dependencies — pure Python.

Usage:
    from core.execution_dag import ExecutionDAG

    dag = ExecutionDAG()
    dag.add_node("agent_1", "AGENT", {"agent_name": "Apex"})
    dag.add_node("gov_1", "GOVERNANCE", {"rule": "constitution"})
    dag.add_edge("agent_1", "gov_1", "VERIFIES")

    cycles = dag.detect_cycles()  # Should be []
    path = dag.critical_path()
    print(dag.to_mermaid())
"""

import json
import os
import uuid
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

logger = logging.getLogger("core.execution_dag")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs", "execution_dags")

NODE_TYPES = {"AGENT", "TOOL", "GOVERNANCE", "VERIFICATION", "STORAGE", "BLOCKCHAIN"}
EDGE_TYPES = {"DELEGATES", "VERIFIES", "PUBLISHES", "QUERIES", "TRANSFERS"}


class CycleDetectedError(Exception):
    """Raised when a cycle is detected in a DAG that must be acyclic."""

    def __init__(self, cycles: list[list[str]]):
        self.cycles = cycles
        cycle_strs = [" → ".join(c) for c in cycles]
        super().__init__(f"Cycles detected: {cycle_strs}")


@dataclass
class DAGNode:
    """A node in the execution DAG."""
    node_id: str
    node_type: str  # AGENT | TOOL | GOVERNANCE | VERIFICATION | STORAGE | BLOCKCHAIN
    status: str = "PENDING"  # PENDING | RUNNING | COMPLETED | FAILED
    start_time: str = ""
    end_time: str = ""
    duration_ms: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class DAGEdge:
    """A directed edge in the execution DAG."""
    from_id: str
    to_id: str
    edge_type: str  # DELEGATES | VERIFIES | PUBLISHES | QUERIES | TRANSFERS
    latency_ms: float = 0.0
    metadata: dict = field(default_factory=dict)


class ExecutionDAG:
    """Directed Acyclic Graph for tracing agent execution dependencies."""

    def __init__(self):
        self.nodes: dict[str, DAGNode] = {}
        self.edges: list[DAGEdge] = []
        self.start_time: str = datetime.now(timezone.utc).isoformat()
        self.dag_id: str = str(uuid.uuid4())

    def add_node(self, node_id: str, node_type: str,
                 metadata: dict | None = None) -> DAGNode:
        """Add a node to the DAG.

        Args:
            node_id: Unique identifier for this node.
            node_type: One of AGENT, TOOL, GOVERNANCE, VERIFICATION, STORAGE, BLOCKCHAIN.
            metadata: Optional dict with agent_name, provider, timestamp, etc.

        Returns:
            The created DAGNode.
        """
        if node_type not in NODE_TYPES:
            raise ValueError(f"Invalid node_type '{node_type}'. Must be one of {NODE_TYPES}")
        if node_id in self.nodes:
            raise ValueError(f"Node '{node_id}' already exists in DAG")

        node = DAGNode(
            node_id=node_id,
            node_type=node_type,
            metadata=metadata or {},
        )
        self.nodes[node_id] = node
        return node

    def add_edge(self, from_id: str, to_id: str, edge_type: str,
                 metadata: dict | None = None) -> DAGEdge:
        """Add a directed edge to the DAG.

        Args:
            from_id: Source node ID.
            to_id: Target node ID.
            edge_type: One of DELEGATES, VERIFIES, PUBLISHES, QUERIES, TRANSFERS.
            metadata: Optional dict with data_size, latency_ms, protocol.

        Returns:
            The created DAGEdge.

        Raises:
            ValueError: If from_id or to_id are not in the DAG, or invalid edge_type.
        """
        if from_id not in self.nodes:
            raise ValueError(f"Source node '{from_id}' not in DAG")
        if to_id not in self.nodes:
            raise ValueError(f"Target node '{to_id}' not in DAG")
        if edge_type not in EDGE_TYPES:
            raise ValueError(f"Invalid edge_type '{edge_type}'. Must be one of {EDGE_TYPES}")

        meta = metadata or {}
        edge = DAGEdge(
            from_id=from_id,
            to_id=to_id,
            edge_type=edge_type,
            latency_ms=meta.get("latency_ms", 0.0),
            metadata=meta,
        )
        self.edges.append(edge)
        return edge

    def _adjacency(self) -> dict[str, list[str]]:
        """Build adjacency list from edges."""
        adj: dict[str, list[str]] = {nid: [] for nid in self.nodes}
        for edge in self.edges:
            adj[edge.from_id].append(edge.to_id)
        return adj

    def detect_cycles(self) -> list[list[str]]:
        """Detect all cycles in the graph using DFS.

        Returns:
            List of cycles, where each cycle is a list of node_ids.
            Empty list means the graph is a valid DAG.
        """
        adj = self._adjacency()
        cycles: list[list[str]] = []
        visited: set[str] = set()
        on_stack: set[str] = set()
        path: list[str] = []

        def dfs(node: str):
            visited.add(node)
            on_stack.add(node)
            path.append(node)

            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in on_stack:
                    # Found a cycle — extract it from path
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)

            path.pop()
            on_stack.discard(node)

        for node_id in self.nodes:
            if node_id not in visited:
                dfs(node_id)

        return cycles

    def topological_sort(self) -> list[str]:
        """Return topological ordering of nodes.

        Returns:
            List of node_ids in topological order.

        Raises:
            CycleDetectedError: If the graph contains cycles.
        """
        cycles = self.detect_cycles()
        if cycles:
            raise CycleDetectedError(cycles)

        adj = self._adjacency()
        visited: set[str] = set()
        order: list[str] = []

        def dfs(node: str):
            visited.add(node)
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor)
            order.append(node)

        for node_id in self.nodes:
            if node_id not in visited:
                dfs(node_id)

        order.reverse()
        return order

    def critical_path(self) -> dict:
        """Calculate the critical path (longest path by duration).

        Returns:
            Dict with: path (list of node_ids), total_duration_ms, bottleneck_node.
            Empty dict if DAG has no nodes.
        """
        if not self.nodes:
            return {"path": [], "total_duration_ms": 0.0, "bottleneck_node": None}

        cycles = self.detect_cycles()
        if cycles:
            return {"path": [], "total_duration_ms": 0.0, "bottleneck_node": None,
                    "error": "Cycles detected"}

        topo = self.topological_sort()
        adj = self._adjacency()

        # dist[node] = (longest_distance_to_node, predecessor)
        dist: dict[str, tuple[float, str | None]] = {}
        for nid in topo:
            dist[nid] = (self.nodes[nid].duration_ms, None)

        for nid in topo:
            node_dur = self.nodes[nid].duration_ms
            for neighbor in adj.get(nid, []):
                new_dist = dist[nid][0] + self.nodes[neighbor].duration_ms
                if new_dist > dist[neighbor][0]:
                    dist[neighbor] = (new_dist, nid)

        # Find the node with the longest distance
        end_node = max(dist, key=lambda n: dist[n][0])
        total_duration = dist[end_node][0]

        # Reconstruct path
        path = []
        current: str | None = end_node
        while current is not None:
            path.append(current)
            current = dist[current][1]
        path.reverse()

        # Bottleneck = node with max individual duration on the critical path
        bottleneck = max(path, key=lambda n: self.nodes[n].duration_ms)

        return {
            "path": path,
            "total_duration_ms": round(total_duration, 2),
            "bottleneck_node": bottleneck,
        }

    def get_node_depth(self, node_id: str) -> int:
        """Get depth of a node from any root (node with no incoming edges).

        Args:
            node_id: The node to measure depth for.

        Returns:
            Depth as integer (root = 0).

        Raises:
            ValueError: If node_id not in DAG.
        """
        if node_id not in self.nodes:
            raise ValueError(f"Node '{node_id}' not in DAG")

        # Build reverse adjacency (incoming edges)
        incoming: dict[str, list[str]] = {nid: [] for nid in self.nodes}
        for edge in self.edges:
            incoming[edge.to_id].append(edge.from_id)

        # BFS from node backwards
        depth = 0
        current = {node_id}
        visited: set[str] = {node_id}

        while current:
            parents: set[str] = set()
            for nid in current:
                for parent in incoming.get(nid, []):
                    if parent not in visited:
                        parents.add(parent)
                        visited.add(parent)
            if parents:
                depth += 1
            current = parents

        return depth

    def get_dependencies(self, node_id: str) -> list[str]:
        """Get nodes that must complete before this node.

        Args:
            node_id: The node to get dependencies for.

        Returns:
            List of node_ids that are direct predecessors.
        """
        if node_id not in self.nodes:
            raise ValueError(f"Node '{node_id}' not in DAG")

        return [e.from_id for e in self.edges if e.to_id == node_id]

    def get_dependents(self, node_id: str) -> list[str]:
        """Get nodes that depend on this node.

        Args:
            node_id: The node to get dependents for.

        Returns:
            List of node_ids that are direct successors.
        """
        if node_id not in self.nodes:
            raise ValueError(f"Node '{node_id}' not in DAG")

        return [e.to_id for e in self.edges if e.from_id == node_id]

    def to_dict(self) -> dict:
        """Serialize the DAG to a dict for persistence."""
        cycles = self.detect_cycles()
        cp = self.critical_path()
        depth_map = {}
        for nid in self.nodes:
            depth_map[nid] = self.get_node_depth(nid)

        return {
            "dag_id": self.dag_id,
            "start_time": self.start_time,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "nodes": {nid: asdict(node) for nid, node in self.nodes.items()},
            "edges": [asdict(edge) for edge in self.edges],
            "cycles": cycles,
            "critical_path": cp,
            "depth_map": depth_map,
        }

    def to_mermaid(self) -> str:
        """Generate Mermaid diagram code for visualization.

        Each node type has a distinct shape:
          AGENT → rectangle, TOOL → rounded, GOVERNANCE → diamond,
          VERIFICATION → hexagon, STORAGE → cylinder, BLOCKCHAIN → trapezoid.
        """
        lines = ["graph LR"]

        # Node shape map
        shape = {
            "AGENT": ('["', '"]'),
            "TOOL": ('("', '")'),
            "GOVERNANCE": ('{"', '"}'),
            "VERIFICATION": ('{{"', '"}}'),
            "STORAGE": ('[("', '")]'),
            "BLOCKCHAIN": ('["', '"]'),
        }

        # Style classes
        lines.append("    classDef agent fill:#4CAF50,color:#fff")
        lines.append("    classDef tool fill:#2196F3,color:#fff")
        lines.append("    classDef governance fill:#FF9800,color:#fff")
        lines.append("    classDef verification fill:#9C27B0,color:#fff")
        lines.append("    classDef storage fill:#607D8B,color:#fff")
        lines.append("    classDef blockchain fill:#F44336,color:#fff")

        type_to_class = {
            "AGENT": "agent", "TOOL": "tool", "GOVERNANCE": "governance",
            "VERIFICATION": "verification", "STORAGE": "storage",
            "BLOCKCHAIN": "blockchain",
        }

        for nid, node in self.nodes.items():
            s = shape.get(node.node_type, ('["', '"]'))
            label = node.metadata.get("agent_name", nid)
            safe_id = nid.replace("-", "_").replace(" ", "_")
            lines.append(f"    {safe_id}{s[0]}{label}{s[1]}")
            cls = type_to_class.get(node.node_type, "agent")
            lines.append(f"    class {safe_id} {cls}")

        for edge in self.edges:
            from_safe = edge.from_id.replace("-", "_").replace(" ", "_")
            to_safe = edge.to_id.replace("-", "_").replace(" ", "_")
            lines.append(f"    {from_safe} -->|\"{edge.edge_type}\"| {to_safe}")

        return "\n".join(lines)

    @classmethod
    def from_trace_records(cls, records: list[dict]) -> "ExecutionDAG":
        """Build a DAG from TraceRecord dicts (e.g., from agent_10_rounds.json).

        Each record becomes an AGENT node with edges to GOVERNANCE,
        STORAGE (Enigma), and BLOCKCHAIN (on-chain attestation) nodes.

        Args:
            records: List of dicts with round_number, round_type, initiator,
                     target, action_duration_ms, governance_duration_ms, etc.

        Returns:
            Populated ExecutionDAG.
        """
        dag = cls()
        seen_rounds: set = set()

        for idx, rec in enumerate(records):
            rnum = rec.get("round_number", idx)
            # Ensure uniqueness when round_number is missing or repeated
            if rnum in seen_rounds:
                rnum = max(seen_rounds) + 1
            seen_rounds.add(rnum)
            rtype = rec.get("round_type", "UNKNOWN")
            initiator = rec.get("initiator_name", f"agent_{rnum}")
            target = rec.get("target_name", f"target_{rnum}")

            # Support both naming conventions:
            # action_duration_ms (test data) and duration_action_ms (agent_10_rounds)
            action_ms = rec.get("action_duration_ms", rec.get("duration_action_ms", 0.0))
            gov_ms = rec.get("governance_duration_ms", rec.get("duration_governance_ms", 0.0))
            chain_ms = rec.get("onchain_duration_ms", rec.get("duration_onchain_ms", 0.0))
            enigma_ms = rec.get("enigma_duration_ms", rec.get("duration_enigma_ms", 0.0))

            # Agent node (action)
            action_id = f"R{rnum}_action"
            dag.add_node(action_id, "AGENT", {
                "agent_name": f"R{rnum} {initiator}→{target}",
                "round_type": rtype,
            })
            dag.nodes[action_id].duration_ms = action_ms
            dag.nodes[action_id].status = "COMPLETED"

            # Governance node
            gov_id = f"R{rnum}_gov"
            dag.add_node(gov_id, "GOVERNANCE", {
                "agent_name": f"R{rnum} DOF Gov",
            })
            dag.nodes[gov_id].duration_ms = gov_ms
            dag.nodes[gov_id].status = "COMPLETED"
            dag.add_edge(action_id, gov_id, "VERIFIES")

            # Blockchain node (attestation)
            chain_id = f"R{rnum}_chain"
            dag.add_node(chain_id, "BLOCKCHAIN", {
                "agent_name": f"R{rnum} Avalanche",
            })
            dag.nodes[chain_id].duration_ms = chain_ms
            dag.nodes[chain_id].status = "COMPLETED"
            dag.add_edge(gov_id, chain_id, "PUBLISHES")

            # Storage node (Enigma)
            storage_id = f"R{rnum}_enigma"
            dag.add_node(storage_id, "STORAGE", {
                "agent_name": f"R{rnum} Enigma",
            })
            dag.nodes[storage_id].duration_ms = enigma_ms
            dag.nodes[storage_id].status = "COMPLETED"
            dag.add_edge(chain_id, storage_id, "PUBLISHES")

            # Link to previous round if exists
            if rnum > 1:
                prev_storage = f"R{rnum - 1}_enigma"
                if prev_storage in dag.nodes:
                    dag.add_edge(prev_storage, action_id, "DELEGATES")

        return dag

    def save(self, path: str | None = None) -> str:
        """Save DAG to JSON file.

        Args:
            path: Optional file path. Defaults to logs/execution_dags/{dag_id}.json.

        Returns:
            Path to the saved file.
        """
        if path is None:
            os.makedirs(LOGS_DIR, exist_ok=True)
            path = os.path.join(LOGS_DIR, f"{self.dag_id}.json")

        data = self.to_dict()
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"DAG saved: {path}")
        return path
