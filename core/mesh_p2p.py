import socket
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List
import uuid

class ConnectionStatus(Enum):
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"

@dataclass
class P2PConnection:
    conn_id: str
    peer_ip: str
    peer_port: int
    status: ConnectionStatus
    created_at: datetime
    _sock: Optional[socket.socket] = None

class P2PManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_manager()
            return cls._instance
    
    def _init_manager(self):
        self.connections = {}
        self.manager_lock = threading.Lock()
    
    def connect(self, peer_ip: str, peer_port: int, shared_secret: str) -> Optional[P2PConnection]:
        """Establish a P2P connection with authentication."""
        conn_id = str(uuid.uuid4())
        connection = P2PConnection(
            conn_id=conn_id,
            peer_ip=peer_ip,
            peer_port=peer_port,
            status=ConnectionStatus.CONNECTING,
            created_at=datetime.now()
        )
        
        try:
            # Create socket and attempt connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            
            # In real implementation, shared_secret would be used for authentication
            # For this example, we'll just attempt connection
            sock.connect((peer_ip, peer_port))
            
            # Send authentication (simplified)
            auth_msg = f"AUTH:{shared_secret}".encode()
            sock.send(auth_msg)
            
            response = sock.recv(1024)
            if response != b"AUTH_OK":
                raise ConnectionError("Authentication failed")
            
            connection.socket = sock
            connection.status = ConnectionStatus.CONNECTED
            
            with self.manager_lock:
                self.connections[conn_id] = connection
            
            return connection
            
        except Exception as e:
            connection.status = ConnectionStatus.ERROR
            if 'sock' in locals():
                sock.close()
            return None
    
    def disconnect(self, conn_id: str) -> bool:
        """Disconnect a P2P connection."""
        with self.manager_lock:
            connection = self.connections.get(conn_id)
            if not connection:
                return False
            
            if connection.socket:
                try:
                    connection.socket.close()
                except:
                    pass
            
            connection.status = ConnectionStatus.DISCONNECTED
            del self.connections[conn_id]
            return True
    
    def get_connections(self) -> List[P2PConnection]:
        """Get all active connections."""
        with self.manager_lock:
            return list(self.connections.values())
    
    def broadcast(self, data: bytes) -> int:
        """Broadcast data to all connected peers."""
        sent_count = 0
        failed_connections = []
        
        with self.manager_lock:
            connections_copy = list(self.connections.values())
        
        for connection in connections_copy:
            if connection.status != ConnectionStatus.CONNECTED or not connection.socket:
                continue
                
            try:
                connection.socket.sendall(data)
                sent_count += 1
            except:
                connection.status = ConnectionStatus.ERROR
                failed_connections.append(connection.conn_id)
        
        # Clean up failed connections
        for conn_id in failed_connections:
            self.disconnect(conn_id)
        
        return sent_count

def get_p2p_manager() -> P2PManager:
    """Singleton accessor for P2PManager."""
    return P2PManager()