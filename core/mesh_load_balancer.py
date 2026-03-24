
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

    def __init__(self):
        self._nodes: Dict[str, NodeStats] = {}
        self._node_list: List[str] = []
        self._rr_index: int = 0

    @staticmethod
    def get_load_balancer():
        if LoadBalancer._instance is None:
            LoadBalancer._instance = LoadBalancer()
        return LoadBalancer._instance

    def add_node(self, node_id: str):
        if node_id not in self._nodes:
            self._nodes[node_id] = NodeStats(node_id, 0, 0.0, 1.0, 0.0)
            self._node_list.append(node_id)

    def remove_node(self, node_id: str):
        if node_id not in self._nodes:
            raise ValueError(f"Node '{node_id}' not found")
        del self._nodes[node_id]
        self._node_list.remove(node_id)
        if self._rr_index >= len(self._node_list):
            self._rr_index = 0

    def get_next_node(self) -> str:
        if not self._node_list:
            raise IndexError("No nodes available")
        node = self._node_list[self._rr_index % len(self._node_list)]
        self._rr_index = (self._rr_index + 1) % len(self._node_list)
        return node

    def get_nodes(self) -> List[str]:
        return list(self._node_list)

    def get_nodes(self) -> List[str]:
        return list(self._node_list)

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

def get_load_balancer() -> 'LoadBalancer':
    return LoadBalancer.get_load_balancer()


if __name__ == '__main__':
    # Example usage:
    load_balancer = LoadBalancer.get_load_balancer()
    node_stats = NodeStats('node1', 10, 50.0, 0.9, 1643723400)
    load_balancer.update_stats('node1', node_stats)
    print(load_balancer.get_best_node(['node1', 'node2'], strategy='least_loaded'))