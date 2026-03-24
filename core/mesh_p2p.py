"""DOF Mesh — P2P Connection Manager (Phase 8)"""
import json
import socket
import threading
import uuid
from typing import Dict, List, Optional


class P2PConnection:
    """A single P2P connection wrapping a socket."""

    def __init__(self, sock: socket.socket, ip: str, port: int):
        self.socket = sock
        self.ip = ip
        self.port = port
        self.conn_id = str(uuid.uuid4())

    def send(self, message: dict) -> None:
        """Send JSON message over socket."""
        data = json.dumps(message).encode()
        self.socket.send(data)

    def close(self) -> None:
        """Close the underlying socket."""
        self.socket.close()

    def __repr__(self):
        return f"P2PConnection(id={self.conn_id[:8]}, {self.ip}:{self.port})"


class P2PManager:
    """Manages multiple P2P connections. Thread-safe."""

    _instance: Optional["P2PManager"] = None
    _lock = threading.Lock()

    def __init__(self):
        self.connections: Dict[str, P2PConnection] = {}
        self._lock = threading.Lock()

    def connect(self, peer_ip: str, peer_port: int, shared_secret: str = "") -> P2PConnection:
        """Open TCP connection to peer, return P2PConnection."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((peer_ip, peer_port))
        conn = P2PConnection(sock, peer_ip, peer_port)
        with self._lock:
            self.connections[conn.conn_id] = conn
        return conn

    def disconnect(self, conn_id: str) -> bool:
        """Close and remove a connection by ID."""
        with self._lock:
            conn = self.connections.pop(conn_id, None)
        if conn:
            conn.close()
            return True
        return False

    def get_connections(self) -> List[P2PConnection]:
        """Return list of active connections."""
        with self._lock:
            return list(self.connections.values())

    def broadcast(self, message: dict) -> int:
        """Send message to all active connections. Returns count sent."""
        sent = 0
        with self._lock:
            conns = list(self.connections.values())
        for conn in conns:
            try:
                conn.send(message)
                sent += 1
            except Exception:
                pass
        return sent


def get_p2p_manager() -> P2PManager:
    """Singleton accessor."""
    if P2PManager._instance is None:
        with P2PManager._lock:
            if P2PManager._instance is None:
                P2PManager._instance = P2PManager()
    return P2PManager._instance
