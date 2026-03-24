import random
from raft import Raft

class MeshConsensus:
    def __init__(self):
        self.raft = Raft()

    def start(self):
        self.raft.start()

    def stop(self):
        self.raft.stop()

    def vote(self, candidate):
        self.raft.vote(candidate)

    def get_state(self):
        return self.raft.get_state()