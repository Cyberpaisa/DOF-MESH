from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


class ConsensusState(Enum):
    FOLLOWER = "FOLLOWER"
    CANDIDATE = "CANDIDATE"
    LEADER = "LEADER"


@dataclass
class LogEntry:
    term: int
    index: int
    value: Any


class ConsensusNode:
    _instances: Dict[str, 'ConsensusNode'] = {}
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.state = ConsensusState.FOLLOWER
        self.term = 0
        self.voted_for: Optional[str] = None
        self.log: List[LogEntry] = []
        self.leader_id: Optional[str] = None
    
    @classmethod
    def get_consensus_node(cls, node_id: str) -> 'ConsensusNode':
        if node_id not in cls._instances:
            cls._instances[node_id] = cls(node_id)
        return cls._instances[node_id]
    
    def propose(self, value: Any) -> bool:
        if self.state != ConsensusState.LEADER:
            return False
        
        new_index = len(self.log) + 1
        entry = LogEntry(term=self.term, index=new_index, value=value)
        self.log.append(entry)
        
        return True
    
    def vote(self, candidate_id: str, term: int) -> bool:
        if term < self.term:
            return False
        
        if term > self.term:
            self.term = term
            self.state = ConsensusState.FOLLOWER
            self.voted_for = None
        
        if self.voted_for is None or self.voted_for == candidate_id:
            self.voted_for = candidate_id
            self.leader_id = candidate_id
            if term > self.term:
                self.term = term
            return True
        
        return False
    
    def append_entry(self, entry: LogEntry) -> bool:
        if entry.term < self.term:
            return False
        
        self.log.append(entry)
        self.leader_id = None  # Reset leader since we received entry from unknown source
        if entry.term > self.term:
            self.term = entry.term
            self.state = ConsensusState.FOLLOWER
        
        return True
    
    def get_state(self) -> ConsensusState:
        return self.state
    
    def get_leader(self) -> Optional[str]:
        if self.state == ConsensusState.LEADER:
            return self.node_id
        return self.leader_id
    
    def _become_candidate(self) -> None:
        self.state = ConsensusState.CANDIDATE
        self.term += 1
        self.voted_for = self.node_id
    
    def _become_leader(self) -> None:
        self.state = ConsensusState.LEADER
        self.leader_id = self.node_id
    
    def _become_follower(self) -> None:
        self.state = ConsensusState.FOLLOWER
        self.voted_for = None


if __name__ == "__main__":
    node1 = ConsensusNode.get_consensus_node("node1")
    node2 = ConsensusNode.get_consensus_node("node2")
    
    print(f"Node1 state: {node1.get_state()}")
    print(f"Node2 state: {node2.get_state()}")
    
    node1._become_candidate()
    vote_result = node2.vote("node1", node1.term)
    print(f"Node2 voted for node1: {vote_result}")
    
    if vote_result:
        node1._become_leader()
    
    print(f"Node1 state after election: {node1.get_state()}")
    print(f"Node1 leader: {node1.get_leader()}")
    print(f"Node2 leader: {node2.get_leader()}")
    
    proposal_result = node1.propose("test_value")
    print(f"Node1 proposed value: {proposal_result}")
    print(f"Node1 log length: {len(node1.log)}")
    
    entry = LogEntry(term=node1.term, index=1, value="test_value")
    append_result = node2.append_entry(entry)
    print(f"Node2 appended entry: {append_result}")
    print(f"Node2 log length: {len(node2.log)}")
def get_consensus_node(node_id: str) -> 'ConsensusNode':
    return ConsensusNode.get_consensus_node(node_id)
