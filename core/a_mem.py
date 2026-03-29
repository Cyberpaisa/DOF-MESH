"""
A-Mem — Agentic Memory with Zettelkasten Knowledge Graph.

Implements the A-Mem pattern (NeurIPS 2025) for interconnected agent memory:
  - Semantic links between memory nodes (bidirectional)
  - Fisher-Rao similarity for retrieval
  - Temporal decay (recent memories weighted higher)
  - Memory types: episodic, semantic, procedural
  - Graph traversal for multi-hop reasoning

Zero LLM for storage/retrieval. Deterministic. JSONL persistence.

Reference:
  - A-Mem: Agentic Memory for LLM Agents (NeurIPS 2025)
  - SuperLocalMemory V3 (arXiv:2603.14588) — Fisher-Rao validation
"""

import json
import logging
import math
import os
import time
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger("core.a_mem")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR = os.path.join(BASE_DIR, "logs", "a_mem")
NODES_FILE = os.path.join(MEMORY_DIR, "nodes.jsonl")
EDGES_FILE = os.path.join(MEMORY_DIR, "edges.jsonl")


# --- Data Classes ---

@dataclass
class MemoryNode:
    """A single memory node in the knowledge graph."""
    id: str
    content: str
    memory_type: str  # episodic, semantic, procedural
    tags: list[str] = field(default_factory=list)
    source: str = ""  # agent name, tool, user
    importance: float = 0.5  # 0.0-1.0
    access_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = hashlib.sha256(
                f"{self.content[:100]}:{self.created_at}".encode()
            ).hexdigest()[:12]


@dataclass
class MemoryEdge:
    """A semantic link between two memory nodes."""
    source_id: str
    target_id: str
    relation: str  # supports, contradicts, elaborates, causes, follows
    weight: float = 1.0  # Link strength 0.0-1.0
    created_at: float = field(default_factory=time.time)


@dataclass
class SearchResult:
    """Result from a memory search."""
    node: MemoryNode
    similarity: float
    connected_nodes: list[str]  # IDs of connected nodes
    hop_distance: int = 0


# --- Fisher-Rao Integration ---

def _fisher_rao_similarity(text_a: str, text_b: str) -> float:
    """Inline Fisher-Rao similarity (avoids circular import)."""
    import re
    from collections import Counter

    def tokenize(t):
        return re.findall(r'\b\w+\b', t.lower())

    def tf(tokens):
        if not tokens:
            return {}
        c = Counter(tokens)
        total = len(tokens)
        return {t: n / total for t, n in c.items()}

    ta, tb = tokenize(text_a), tokenize(text_b)
    if not ta or not tb:
        return 0.0

    tfa, tfb = tf(ta), tf(tb)
    all_terms = set(tfa) | set(tfb)

    bc = sum(
        math.sqrt(tfa.get(t, 0.0) * tfb.get(t, 0.0))
        for t in all_terms
    )
    bc = max(0.0, min(1.0, bc))
    dist = 2.0 * math.acos(bc)
    return 1.0 - (dist / math.pi)


# --- A-Mem Knowledge Graph ---

class AMem:
    """Agentic Memory with Zettelkasten-style knowledge graph.

    Core operations:
      - add(): Store a memory node
      - link(): Create semantic edge between nodes
      - search(): Fisher-Rao retrieval with graph traversal
      - traverse(): Multi-hop graph exploration
      - decay(): Apply temporal decay to access patterns
    """

    def __init__(self, memory_dir: str | None = None):
        self._dir = memory_dir or MEMORY_DIR
        os.makedirs(self._dir, exist_ok=True)
        self._nodes_file = os.path.join(self._dir, "nodes.jsonl")
        self._edges_file = os.path.join(self._dir, "edges.jsonl")
        self._nodes: dict[str, MemoryNode] = {}
        self._edges: list[MemoryEdge] = []
        self._adjacency: dict[str, list[str]] = {}  # node_id → [connected_ids]
        self._load()

    def _load(self):
        """Load nodes and edges from JSONL."""
        if os.path.exists(self._nodes_file):
            try:
                with open(self._nodes_file) as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            node = MemoryNode(**data)
                            self._nodes[node.id] = node
            except Exception as e:
                logger.error(f"Error loading nodes: {e}")

        if os.path.exists(self._edges_file):
            try:
                with open(self._edges_file) as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            edge = MemoryEdge(**data)
                            self._edges.append(edge)
                            # Build adjacency
                            self._adjacency.setdefault(edge.source_id, []).append(edge.target_id)
                            self._adjacency.setdefault(edge.target_id, []).append(edge.source_id)
            except Exception as e:
                logger.error(f"Error loading edges: {e}")

    def add(self, content: str, memory_type: str = "semantic",
            tags: list[str] | None = None, source: str = "",
            importance: float = 0.5, metadata: dict | None = None) -> MemoryNode:
        """Add a memory node to the graph."""
        node = MemoryNode(
            id="",
            content=content,
            memory_type=memory_type,
            tags=tags or [],
            source=source,
            importance=importance,
            metadata=metadata or {},
        )
        self._nodes[node.id] = node
        self._persist_node(node)

        # Auto-link to similar existing nodes
        self._auto_link(node)

        logger.info(f"Added memory node {node.id}: {content[:50]}...")
        return node

    def link(self, source_id: str, target_id: str,
             relation: str = "related", weight: float = 1.0) -> MemoryEdge | None:
        """Create a semantic edge between two nodes."""
        if source_id not in self._nodes or target_id not in self._nodes:
            logger.warning(f"Cannot link: node not found ({source_id} → {target_id})")
            return None

        edge = MemoryEdge(
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            weight=weight,
        )
        self._edges.append(edge)
        self._adjacency.setdefault(source_id, []).append(target_id)
        self._adjacency.setdefault(target_id, []).append(source_id)
        self._persist_edge(edge)

        logger.info(f"Linked {source_id} --[{relation}]--> {target_id}")
        return edge

    def search(self, query: str, top_k: int = 5,
               memory_type: str | None = None,
               include_connected: bool = True) -> list[SearchResult]:
        """Search memory using Fisher-Rao similarity with graph expansion.

        Steps:
          1. Compute Fisher-Rao similarity for all nodes
          2. Apply temporal decay (recent = boosted)
          3. Apply importance weighting
          4. Optionally expand to connected nodes (1-hop)
          5. Return top-K ranked results
        """
        if not self._nodes:
            return []

        now = time.time()
        scored: list[tuple[float, MemoryNode]] = []

        for node in self._nodes.values():
            # Filter by type if specified
            if memory_type and node.memory_type != memory_type:
                continue

            # Base similarity (Fisher-Rao)
            sim = _fisher_rao_similarity(query, node.content)

            # Tag boost: if query contains any tag word
            query_lower = query.lower()
            tag_boost = sum(0.05 for t in node.tags if t.lower() in query_lower)
            sim = min(1.0, sim + tag_boost)

            # Temporal decay: newer memories get slight boost
            age_hours = (now - node.created_at) / 3600
            recency_factor = 1.0 / (1.0 + math.log1p(age_hours / 24))  # Decay over days
            sim *= (0.8 + 0.2 * recency_factor)

            # Importance weighting
            sim *= (0.7 + 0.3 * node.importance)

            scored.append((sim, node))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        seen_ids = set()

        for sim, node in scored[:top_k]:
            # Update access
            node.access_count += 1
            node.last_accessed = now

            connected = self._adjacency.get(node.id, [])
            results.append(SearchResult(
                node=node,
                similarity=round(sim, 4),
                connected_nodes=connected[:5],
                hop_distance=0,
            ))
            seen_ids.add(node.id)

        # 1-hop expansion: add connected nodes not already in results
        if include_connected and results:
            for r in list(results):
                for connected_id in r.connected_nodes:
                    if connected_id not in seen_ids and connected_id in self._nodes:
                        connected_node = self._nodes[connected_id]
                        hop_sim = r.similarity * 0.6  # Decay by hop
                        results.append(SearchResult(
                            node=connected_node,
                            similarity=round(hop_sim, 4),
                            connected_nodes=self._adjacency.get(connected_id, [])[:3],
                            hop_distance=1,
                        ))
                        seen_ids.add(connected_id)

        # Re-sort after expansion
        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:top_k]

    def traverse(self, start_id: str, max_hops: int = 3) -> list[tuple[MemoryNode, int]]:
        """BFS traversal from a starting node. Returns (node, distance) pairs."""
        if start_id not in self._nodes:
            return []

        visited = {start_id}
        queue = [(start_id, 0)]
        result = [(self._nodes[start_id], 0)]

        while queue:
            current_id, depth = queue.pop(0)
            if depth >= max_hops:
                continue

            for neighbor_id in self._adjacency.get(current_id, []):
                if neighbor_id not in visited and neighbor_id in self._nodes:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, depth + 1))
                    result.append((self._nodes[neighbor_id], depth + 1))

        return result

    def get_contradictions(self) -> list[tuple[MemoryNode, MemoryNode, MemoryEdge]]:
        """Find all contradiction edges — foundation for sheaf cohomology."""
        contradictions = []
        for edge in self._edges:
            if edge.relation == "contradicts":
                src = self._nodes.get(edge.source_id)
                tgt = self._nodes.get(edge.target_id)
                if src and tgt:
                    contradictions.append((src, tgt, edge))
        return contradictions

    def decay(self, half_life_hours: float = 72.0, floor: float = 0.1) -> int:
        """Apply temporal decay to node importance based on time since last access.

        Uses exponential decay: importance *= e^(-λ * hours_idle)
        where λ = ln(2) / half_life_hours so importance halves every
        ``half_life_hours`` hours of inactivity.

        Args:
            half_life_hours: Hours of inactivity before importance halves.
                             Default 72 h (3 days).
            floor: Minimum importance after decay (prevents erasure).
                   Default 0.1.

        Returns:
            Number of nodes whose importance was actually reduced.
        """
        now = time.time()
        lam = math.log(2.0) / max(half_life_hours, 1.0)
        decayed = 0

        for node in self._nodes.values():
            idle_hours = (now - node.last_accessed) / 3600.0
            if idle_hours < 1.0:
                continue  # too recent — skip
            factor = math.exp(-lam * idle_hours)
            new_importance = max(floor, node.importance * factor)
            if new_importance < node.importance:
                node.importance = round(new_importance, 4)
                decayed += 1

        logger.info(f"Decay applied: {decayed}/{len(self._nodes)} nodes reduced")
        return decayed

    def _auto_link(self, new_node: MemoryNode, threshold: float = 0.4):
        """Auto-create links to similar existing nodes."""
        for node_id, existing in self._nodes.items():
            if node_id == new_node.id:
                continue
            sim = _fisher_rao_similarity(new_node.content, existing.content)
            if sim >= threshold:
                self.link(new_node.id, node_id, "related", weight=round(sim, 3))

    def _persist_node(self, node: MemoryNode):
        """Append node to JSONL."""
        try:
            with open(self._nodes_file, "a") as f:
                f.write(json.dumps(asdict(node), default=str) + "\n")
        except Exception as e:
            logger.error(f"Node persist error: {e}")

    def _persist_edge(self, edge: MemoryEdge):
        """Append edge to JSONL."""
        try:
            with open(self._edges_file, "a") as f:
                f.write(json.dumps(asdict(edge), default=str) + "\n")
        except Exception as e:
            logger.error(f"Edge persist error: {e}")

    def stats(self) -> dict:
        """Return memory graph statistics."""
        type_counts = {}
        for n in self._nodes.values():
            type_counts[n.memory_type] = type_counts.get(n.memory_type, 0) + 1

        relation_counts = {}
        for e in self._edges:
            relation_counts[e.relation] = relation_counts.get(e.relation, 0) + 1

        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "types": type_counts,
            "relations": relation_counts,
            "avg_connections": (
                len(self._edges) * 2 / max(len(self._nodes), 1)
            ),
        }

    def report(self) -> str:
        """Human-readable memory report."""
        s = self.stats()
        lines = [
            "=== A-Mem Knowledge Graph ===",
            f"Nodes: {s['total_nodes']} | Edges: {s['total_edges']}",
            f"Avg connections per node: {s['avg_connections']:.1f}",
            f"Types: {s['types']}",
            f"Relations: {s['relations']}",
        ]

        contradictions = self.get_contradictions()
        if contradictions:
            lines.append(f"Contradictions detected: {len(contradictions)}")
            for src, tgt, _ in contradictions[:3]:
                lines.append(f"  '{src.content[:40]}...' vs '{tgt.content[:40]}...'")

        return "\n".join(lines)


# --- Convenience ---

def create_memory(memory_dir: str | None = None) -> AMem:
    """Create a new A-Mem instance."""
    return AMem(memory_dir)


# --- Quick test ---

if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        mem = AMem(tmpdir)

        # Add memories
        n1 = mem.add("Fisher-Rao distance improves retrieval by 15-20% over cosine",
                      tags=["memory", "fisher-rao", "metric"], source="research",
                      importance=0.9)
        n2 = mem.add("Z3 theorem prover verifies 8/8 invariants in 109ms",
                      tags=["z3", "verification", "proof"], source="benchmark",
                      importance=0.95)
        n3 = mem.add("Qwen3 32B Q4 runs at 60 tok/s on M4 Max with MLX",
                      tags=["local", "inference", "mlx"], source="agentmeet",
                      importance=0.8)
        n4 = mem.add("Cosine similarity is standard but Fisher-Rao is more accurate",
                      tags=["memory", "cosine", "comparison"], source="paper")

        # Manual link
        mem.link(n1.id, n4.id, "elaborates", 0.9)

        # Search
        print("=== Search: 'memory retrieval accuracy' ===\n")
        results = mem.search("memory retrieval accuracy", top_k=3)
        for r in results:
            print(f"  [{r.similarity}] (hop={r.hop_distance}) {r.node.content[:60]}...")
            if r.connected_nodes:
                print(f"    Connected: {r.connected_nodes}")

        print()
        print(mem.report())
