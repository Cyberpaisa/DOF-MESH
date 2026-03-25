"""
dof_raft.py — Raft Consensus para DOF Mesh Hyperion.

Implementación in-process de leader election y log replication.
Compatible con DistributedMeshQueue: el leader del shard es quien procesa tareas.

Algoritmo Raft (Ongaro & Ousterhout 2014):
  1. Leader Election  — term numbers, RequestVote
  2. Log Replication  — AppendEntries, commit cuando quorum
  3. Heartbeat        — líder envía cada 150ms; follower timeout 300-600ms

Uso:
    nodes = [RaftNode(f"node-{i}", peers=[]) for i in range(3)]
    for n in nodes:
        for m in nodes:
            if n is not m:
                n.add_peer(m)
    for n in nodes:
        n.start()
    time.sleep(1)
    leader = next(n for n in nodes if n.is_leader())
"""
import logging
import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("core.dof_raft")


# ── Tipos ─────────────────────────────────────────────────────────────────────

class RaftRole(Enum):
    FOLLOWER  = "follower"
    CANDIDATE = "candidate"
    LEADER    = "leader"


@dataclass
class LogEntry:
    term:    int
    index:   int
    command: Any


@dataclass
class RequestVoteArgs:
    term:           int
    candidate_id:   str
    last_log_index: int
    last_log_term:  int


@dataclass
class RequestVoteResult:
    term:         int
    vote_granted: bool


@dataclass
class AppendEntriesArgs:
    term:          int
    leader_id:     str
    prev_log_index: int
    prev_log_term:  int
    entries:       list[LogEntry]
    leader_commit: int


@dataclass
class AppendEntriesResult:
    term:    int
    success: bool


# ── RaftNode ──────────────────────────────────────────────────────────────────

class RaftNode:
    """
    Nodo Raft in-process.
    Comunicación directa entre objetos (no red) — ideal para testing y swarm local.
    """

    HEARTBEAT_MS      = 150
    ELECTION_TIMEOUT_MIN_MS = 300
    ELECTION_TIMEOUT_MAX_MS = 600

    def __init__(self, node_id: str, peers: list["RaftNode"] = None):
        self.node_id = node_id
        self._peers: list["RaftNode"] = list(peers or [])
        self._lock  = threading.Lock()

        # Raft state (persistent in real impl — here in-memory)
        self._current_term = 0
        self._voted_for:   Optional[str] = None
        self._log:         list[LogEntry] = []

        # Volatile state
        self._role:         RaftRole = RaftRole.FOLLOWER
        self._commit_index: int = 0
        self._last_applied: int = 0
        self._leader_id:    Optional[str] = None

        # Leader volatile state
        self._next_index:  dict[str, int] = {}
        self._match_index: dict[str, int] = {}

        # Applied commands (state machine)
        self._state_machine: list[Any] = []

        # Timers
        self._election_deadline: float = self._new_election_deadline()
        self._running = False
        self._thread:  Optional[threading.Thread] = None

        logger.debug("RaftNode %s created", node_id)

    # ── Public API ────────────────────────────────────────────────────────────

    def add_peer(self, peer: "RaftNode"):
        with self._lock:
            if peer not in self._peers and peer is not self:
                self._peers.append(peer)

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name=f"raft-{self.node_id}")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def is_leader(self) -> bool:
        return self._role == RaftRole.LEADER

    def leader_id(self) -> Optional[str]:
        return self._leader_id

    def term(self) -> int:
        return self._current_term

    def role(self) -> RaftRole:
        return self._role

    def submit(self, command: Any) -> Optional[int]:
        """
        Enviar comando al leader. Retorna el índice del log o None si no es leader.
        """
        with self._lock:
            if self._role != RaftRole.LEADER:
                return None
            idx = len(self._log) + 1
            entry = LogEntry(term=self._current_term, index=idx, command=command)
            self._log.append(entry)
            logger.debug("Leader %s appended entry idx=%d", self.node_id, idx)
            return idx

    def committed_commands(self) -> list[Any]:
        return list(self._state_machine)

    def status(self) -> dict:
        with self._lock:
            return {
                "node_id":      self.node_id,
                "role":         self._role.value,
                "term":         self._current_term,
                "leader":       self._leader_id,
                "log_len":      len(self._log),
                "commit_index": self._commit_index,
                "peers":        len(self._peers),
            }

    # ── RPC handlers (called by peers directly) ───────────────────────────────

    def request_vote(self, args: RequestVoteArgs) -> RequestVoteResult:
        with self._lock:
            # If we see a higher term, become follower
            if args.term > self._current_term:
                self._become_follower(args.term)

            if args.term < self._current_term:
                return RequestVoteResult(term=self._current_term, vote_granted=False)

            # Already voted this term for someone else
            if self._voted_for is not None and self._voted_for != args.candidate_id:
                return RequestVoteResult(term=self._current_term, vote_granted=False)

            # Candidate log must be at least as up-to-date as ours
            my_last_term  = self._log[-1].term  if self._log else 0
            my_last_index = len(self._log)
            log_ok = (
                args.last_log_term > my_last_term or
                (args.last_log_term == my_last_term and args.last_log_index >= my_last_index)
            )
            if not log_ok:
                return RequestVoteResult(term=self._current_term, vote_granted=False)

            self._voted_for = args.candidate_id
            self._election_deadline = self._new_election_deadline()
            logger.debug("%s votes for %s (term %d)", self.node_id, args.candidate_id, args.term)
            return RequestVoteResult(term=self._current_term, vote_granted=True)

    def append_entries(self, args: AppendEntriesArgs) -> AppendEntriesResult:
        with self._lock:
            if args.term > self._current_term:
                self._become_follower(args.term)

            if args.term < self._current_term:
                return AppendEntriesResult(term=self._current_term, success=False)

            # Valid heartbeat from leader
            self._leader_id = args.leader_id
            self._election_deadline = self._new_election_deadline()
            if self._role == RaftRole.CANDIDATE:
                self._role = RaftRole.FOLLOWER

            # Check prev log consistency
            if args.prev_log_index > 0:
                if len(self._log) < args.prev_log_index:
                    return AppendEntriesResult(term=self._current_term, success=False)
                if self._log[args.prev_log_index - 1].term != args.prev_log_term:
                    # Conflict — truncate
                    self._log = self._log[:args.prev_log_index - 1]
                    return AppendEntriesResult(term=self._current_term, success=False)

            # Append new entries
            for entry in args.entries:
                idx = entry.index - 1
                if idx < len(self._log):
                    if self._log[idx].term != entry.term:
                        self._log = self._log[:idx]
                        self._log.append(entry)
                else:
                    self._log.append(entry)

            # Update commit
            if args.leader_commit > self._commit_index:
                self._commit_index = min(args.leader_commit, len(self._log))
                self._apply_committed()

            return AppendEntriesResult(term=self._current_term, success=True)

    # ── Internal loop ─────────────────────────────────────────────────────────

    def _run_loop(self):
        while self._running:
            with self._lock:
                role = self._role

            if role == RaftRole.LEADER:
                self._leader_tick()
                time.sleep(self.HEARTBEAT_MS / 1000)
            else:
                time.sleep(0.01)
                with self._lock:
                    if time.time() >= self._election_deadline:
                        if self._role != RaftRole.LEADER:
                            self._start_election()

    def _leader_tick(self):
        """Enviar heartbeats y replicar log a todos los peers."""
        with self._lock:
            if self._role != RaftRole.LEADER:
                return
            peers   = list(self._peers)
            term    = self._current_term
            log     = list(self._log)
            commit  = self._commit_index
            nxt     = {p.node_id: self._next_index.get(p.node_id, len(log) + 1) for p in peers}
            node_id = self.node_id

        successes = 0
        for peer in peers:
            ni = nxt[peer.node_id]
            prev_index = ni - 1
            prev_term  = log[prev_index - 1].term if prev_index > 0 and prev_index <= len(log) else 0
            entries    = log[ni - 1:] if ni <= len(log) else []

            args = AppendEntriesArgs(
                term=term,
                leader_id=node_id,
                prev_log_index=prev_index,
                prev_log_term=prev_term,
                entries=entries,
                leader_commit=commit,
            )
            try:
                result = peer.append_entries(args)
                if result.term > term:
                    with self._lock:
                        self._become_follower(result.term)
                    return
                if result.success:
                    successes += 1
                    new_match = prev_index + len(entries)
                    with self._lock:
                        self._match_index[peer.node_id] = new_match
                        self._next_index[peer.node_id]  = new_match + 1
                else:
                    with self._lock:
                        self._next_index[peer.node_id] = max(1, ni - 1)
            except Exception as e:
                logger.debug("AppendEntries to %s failed: %s", peer.node_id, e)

        # Advance commit index if quorum has replicated
        with self._lock:
            if self._role == RaftRole.LEADER:
                quorum = (len(self._peers) + 1) // 2 + 1
                for idx in range(len(self._log), self._commit_index, -1):
                    replicated = 1 + sum(
                        1 for p in self._peers
                        if self._match_index.get(p.node_id, 0) >= idx
                    )
                    if replicated >= quorum and self._log[idx - 1].term == self._current_term:
                        self._commit_index = idx
                        self._apply_committed()
                        break

    def _start_election(self):
        """Iniciar elección — ya dentro de lock."""
        self._current_term += 1
        self._role         = RaftRole.CANDIDATE
        self._voted_for    = self.node_id
        self._leader_id    = None
        self._election_deadline = self._new_election_deadline()

        term       = self._current_term
        peers      = list(self._peers)
        last_index = len(self._log)
        last_term  = self._log[-1].term if self._log else 0
        node_id    = self.node_id

        logger.info("%s starting election term=%d", node_id, term)

        votes = 1  # vote for self
        for peer in peers:
            try:
                args   = RequestVoteArgs(term, node_id, last_index, last_term)
                result = peer.request_vote(args)
                if result.term > term:
                    self._become_follower(result.term)
                    return
                if result.vote_granted:
                    votes += 1
            except Exception as e:
                logger.debug("RequestVote to %s failed: %s", peer.node_id, e)

        quorum = (len(peers) + 1) // 2 + 1
        if votes >= quorum and self._role == RaftRole.CANDIDATE and self._current_term == term:
            self._become_leader()

    def _become_leader(self):
        """Asumir rol de leader."""
        self._role      = RaftRole.LEADER
        self._leader_id = self.node_id
        log_len = len(self._log)
        for peer in self._peers:
            self._next_index[peer.node_id]  = log_len + 1
            self._match_index[peer.node_id] = 0
        logger.info("🏆 %s becomes LEADER (term=%d)", self.node_id, self._current_term)

    def _become_follower(self, term: int):
        """Degradar a follower."""
        self._current_term = term
        self._role         = RaftRole.FOLLOWER
        self._voted_for    = None
        self._election_deadline = self._new_election_deadline()
        logger.debug("%s becomes FOLLOWER (term=%d)", self.node_id, term)

    def _apply_committed(self):
        """Aplicar entradas committed a la state machine."""
        while self._last_applied < self._commit_index:
            self._last_applied += 1
            entry = self._log[self._last_applied - 1]
            self._state_machine.append(entry.command)
            logger.debug("%s applied cmd idx=%d: %s", self.node_id, self._last_applied, entry.command)

    def _new_election_deadline(self) -> float:
        ms = random.randint(self.ELECTION_TIMEOUT_MIN_MS, self.ELECTION_TIMEOUT_MAX_MS)
        return time.time() + ms / 1000


# ── Cluster helper ────────────────────────────────────────────────────────────

def create_raft_cluster(n: int = 3) -> list[RaftNode]:
    """Crear un cluster Raft de n nodos ya conectados."""
    nodes = [RaftNode(f"raft-node-{i}") for i in range(n)]
    for a in nodes:
        for b in nodes:
            if a is not b:
                a.add_peer(b)
    return nodes


def wait_for_leader(nodes: list[RaftNode], timeout: float = 3.0) -> Optional[RaftNode]:
    """Esperar a que haya exactamente un leader."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        leaders = [n for n in nodes if n.is_leader()]
        if len(leaders) == 1:
            return leaders[0]
        time.sleep(0.05)
    return None
