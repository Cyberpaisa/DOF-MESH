import socket
import struct
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.hashes import SHA256
import secrets
import argparse

@dataclass
class TunnelSession:
    session_id: str
    peer_host: str
    peer_port: int
    _key: bytes
    _socket: Optional[socket.socket] = field(default=None, init=False)
    _cipher: AESGCM = field(init=False)
    
    def __post_init__(self):
        self._cipher = AESGCM(self._key)
    
    def _connect_socket(self):
        if self._socket is None:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.connect((self.peer_host, self.peer_port))
    
    def encrypt(self, data: bytes) -> bytes:
        nonce = secrets.token_bytes(12)
        encrypted = self._cipher.encrypt(nonce, data, None)
        return nonce + encrypted
    
    def decrypt(self, data: bytes) -> bytes:
        nonce = data[:12]
        ciphertext = data[12:]
        return self._cipher.decrypt(nonce, ciphertext, None)
    
    def send(self, raw: bytes) -> None:
        self._connect_socket()
        encrypted = self.encrypt(raw)
        length = struct.pack('!I', len(encrypted))
        self._socket.sendall(length + encrypted)
    
    def recv(self) -> bytes:
        self._connect_socket()
        length_data = self._socket.recv(4)
        if len(length_data) < 4:
            raise ConnectionError("Connection closed")
        length = struct.unpack('!I', length_data)[0]
        encrypted = b''
        while len(encrypted) < length:
            chunk = self._socket.recv(min(4096, length - len(encrypted)))
            if not chunk:
                raise ConnectionError("Connection closed")
            encrypted += chunk
        return self.decrypt(encrypted)

class TunnelManager:
    _instance: Optional['TunnelManager'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        self._sessions: Dict[str, TunnelSession] = {}
        self._session_lock = threading.RLock()
    
    @classmethod
    def get_instance(cls) -> 'TunnelManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = TunnelManager()
        return cls._instance
    
    def open_tunnel(self, peer_host: str, peer_port: int, shared_secret: str) -> TunnelSession:
        session_id = secrets.token_hex(16)
        
        # HKDF key derivation
        salt = b'dof-mesh-salt'
        info = b'mesh-tunnel-key'
        hkdf = HKDF(
            algorithm=SHA256(),
            length=32,
            salt=salt,
            info=info
        )
        key_material = shared_secret.encode() + peer_host.encode()
        key = hkdf.derive(key_material)
        
        session = TunnelSession(
            session_id=session_id,
            peer_host=peer_host,
            peer_port=peer_port,
            _key=key
        )
        
        with self._session_lock:
            self._sessions[session_id] = session
        
        return session
    
    def close_tunnel(self, session_id: str) -> bool:
        with self._session_lock:
            session = self._sessions.pop(session_id, None)
        
        if session and session._socket:
            try:
                session._socket.close()
            except:
                pass
            return True
        return False
    
    def get_sessions(self) -> List[TunnelSession]:
        with self._session_lock:
            return list(self._sessions.values())

def get_tunnel_manager() -> TunnelManager:
    return TunnelManager.get_instance()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Run test")
    args = parser.parse_args()
    
    if args.test:
        import time
        
        # Test server function
        def test_server():
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind(('127.0.0.1', 9999))
            server.listen(1)
            conn, _ = server.accept()
            
            # Receive message
            length_data = conn.recv(4)
            length = struct.unpack('!I', length_data)[0]
            encrypted = conn.recv(length)
            
            # Echo back
            conn.sendall(length_data + encrypted)
            conn.close()
            server.close()
        
        # Start test server in background
        import threading
        server_thread = threading.Thread(target=test_server)
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.5)  # Give server time to start
        
        # Test tunnel
        manager = get_tunnel_manager()
        session = manager.open_tunnel(
            peer_host='127.0.0.1',
            peer_port=9999,
            shared_secret='test-secret'
        )
        
        test_message = b"Hello, DOF Mesh!"
        session.send(test_message)
        response = session.recv()
        
        assert response == test_message, "Echo test failed"
        print("Test passed!")
        
        manager.close_tunnel(session.session_id)
        print(f"Active sessions: {len(manager.get_sessions())}")