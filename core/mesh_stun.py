import socket
import struct
import time
import random
import threading
from enum import Enum
from typing import Optional, Tuple

class NATType(Enum):
    OPEN = "OPEN"
    RESTRICTED = "RESTRICTED"
    SYMMETRIC = "SYMMETRIC"
    BLOCKED = "BLOCKED"

class STUNClient:
    _instance: Optional['STUNClient'] = None
    _lock = threading.Lock()
    
    DEFAULT_STUN_SERVER = ("stun.l.google.com", 19302)
    STUN_MAGIC_COOKIE = 0x2112A442
    BINDING_REQUEST = 0x0001
    BINDING_RESPONSE = 0x0101
    CACHE_TTL = 60  # seconds
    
    def __init__(self):
        self._public_endpoint: Optional[Tuple[str, int]] = None
        self._nat_type: Optional[NATType] = None
        self._last_update: float = 0.0
        self._local_socket: Optional[socket.socket] = None
    
    @classmethod
    def get_stun_client(cls) -> 'STUNClient':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = STUNClient()
        return cls._instance
    
    def _create_stun_message(self, transaction_id: bytes) -> bytes:
        # STUN header: type(2) + length(2) + magic(4) + transaction_id(12)
        header = struct.pack('!HHI12s',
                             self.BINDING_REQUEST,
                             0,  # length (no attributes)
                             self.STUN_MAGIC_COOKIE,
                             transaction_id)
        return header
    
    def _parse_stun_response(self, data: bytes) -> Optional[Tuple[str, int]]:
        if len(data) < 20:
            return None
        msg_type, msg_len, magic, part1, part2, part3 = struct.unpack('!HHIIII', data[:20])
        if magic != self.STUN_MAGIC_COOKIE or msg_type != self.BINDING_RESPONSE:
            return None
        
        offset = 20
        while offset + 4 <= len(data):
            attr_type, attr_len = struct.unpack('!HH', data[offset:offset+4])
            if attr_type == 0x0001:  # MAPPED-ADDRESS
                if offset + 8 + attr_len > len(data):
                    break
                family, port = struct.unpack('!HH', data[offset+4:offset+8])
                if family == 0x01:  # IPv4
                    ip_bytes = data[offset+8:offset+8+4]
                    ip = socket.inet_ntoa(ip_bytes)
                    return (ip, port)
            offset += 4 + ((attr_len + 3) & ~3)  # pad to 4 bytes
        return None
    
    def _ensure_socket(self) -> socket.socket:
        if self._local_socket is None or self._local_socket.fileno() == -1:
            self._local_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._local_socket.settimeout(2.0)
            self._local_socket.bind(('', 0))  # bind to any available port
        return self._local_socket
    
    def discover_public_endpoint(self) -> Tuple[str, int]:
        current_time = time.time()
        if (self._public_endpoint is not None and
                current_time - self._last_update < self.CACHE_TTL):
            return self._public_endpoint

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2.0)
        transaction_id = struct.pack('!III',
                                     random.getrandbits(32),
                                     random.getrandbits(32),
                                     random.getrandbits(32))
        request = self._create_stun_message(transaction_id)
        fallback = ("0.0.0.0", 0)
        try:
            sock.sendto(request, self.DEFAULT_STUN_SERVER)
            data, _ = sock.recvfrom(1024)
            endpoint = self._parse_stun_response(data)
            if endpoint:
                self._public_endpoint = endpoint
                self._last_update = current_time
                self._nat_type = NATType.OPEN
                return endpoint
            # Malformed/unexpected response
            fallback = sock.getsockname()
            self._nat_type = NATType.RESTRICTED
        except socket.timeout:
            self._nat_type = NATType.BLOCKED
        except OSError:
            self._nat_type = NATType.BLOCKED
        finally:
            sock.close()

        self._public_endpoint = fallback
        self._last_update = current_time
        return fallback
    
    def detect_nat_type(self) -> NATType:
        if self._nat_type is not None and time.time() - self._last_update < self.CACHE_TTL:
            return self._nat_type
        
        try:
            sock = self._ensure_socket()
            local_addr = sock.getsockname()
            
            # Test 1: Can we receive response from STUN server?
            public_endpoint = self.discover_public_endpoint()
            
            if public_endpoint[0] == local_addr[0]:
                # Same IP, likely open internet or full-cone NAT
                self._nat_type = NATType.OPEN
            else:
                # Different IP, need more tests for precise classification
                # Simplified: assume restricted for different IP
                self._nat_type = NATType.RESTRICTED
                
                # Test 2: Try second request with different transaction
                transaction_id2 = struct.pack('!III',
                                             random.getrandbits(32),
                                             random.getrandbits(32),
                                             random.getrandbits(32))
                request2 = self._create_stun_message(transaction_id2)
                sock.sendto(request2, self.DEFAULT_STUN_SERVER)
                
                try:
                    sock.settimeout(1.0)
                    data2, _ = sock.recvfrom(1024)
                    # If we get response, it's not symmetric
                    # In real implementation, would compare mapped addresses
                except socket.timeout:
                    # No response might indicate symmetric or blocked
                    self._nat_type = NATType.SYMMETRIC
                
        except Exception:
            self._nat_type = NATType.BLOCKED
        
        self._last_update = time.time()
        return self._nat_type
    
    def close(self):
        if self._local_socket:
            try:
                self._local_socket.close()
            except:
                pass
            self._local_socket = None

# Convenience function
def get_stun_client() -> STUNClient:
    return STUNClient.get_stun_client()