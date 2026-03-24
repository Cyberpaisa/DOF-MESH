
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class NodeStats:
    node_id: str
    active_tasks: int
    avg_latency_ms: float
    success_rate: float
    last_updated: float

class LoadBalancer:
    _instance = None
    _nodes = {}

    @staticmethod
    def get_load_balancer():
        if LoadBalancer._instance is None:
            LoadBalancer._instance = LoadBalancer()
        return LoadBalancer._instance

    def update_stats(self, node_id: str, stats: NodeStats):
        self._nodes[node_id] = stats

    def round_robin(self, nodes: List[str]) -> str:
        current_node = list(self._nodes.keys())[0]
        self._nodes = {**{current_node: self._nodes[current_node]}, **{node: self._nodes[node] for node in self._nodes if node != current_node}}
        return current_node

    def weighted(self, nodes: List[str], weights: Dict[str, float]) -> str:
        total_weight = sum(weights.values())
        pick = float(hash(nodes[0])) % total_weight
        for node, weight in weights.items():
            if pick < weight:
                return node
            pick -= weight
        return nodes[-1]

    def least_loaded(self, node_ids: List[str]) -> str:
        least_loaded_node = min(node_ids, key=lambda node: self._nodes[node].active_tasks)
        return least_loaded_node

    def get_best_node(self, node_ids: List[str], strategy: str = 'weighted') -> str:
        if strategy == 'weighted':
            weights = {node: 1.0 for node in node_ids}
            return self.weighted(node_ids, weights)
        elif strategy == 'least_loaded':
            return self.least_loaded(node_ids)
        elif strategy == 'round_robin':
            return self.round_robin(node_ids)
        else:
            raise ValueError('Invalid strategy')

# Example usage:
load_balancer = LoadBalancer.get_load_balancer()
node_stats = NodeStats('node1', 10, 50.0, 0.9, 1643723400)
load_balancer.update_stats('node1', node_stats)
print(load_balancer.get_best_node(['node1', 'node2'], strategy='least_loaded'))