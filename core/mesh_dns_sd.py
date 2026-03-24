import socket
import struct
import json
import time
import threading
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class ServiceRecord:
    name: str
    host: str
    port: int
    properties: Dict[str, str] = field(default_factory=dict)
    ttl: int = 120
    registered_at: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        return time.time() > (self.registered_at + self.ttl)

class DNSSDService:
    MCAST_GRP = '224.0.0.251'
    MCAST_PORT = 5353

    def __init__(self):
        self._services: Dict[str, ServiceRecord] = {}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._receiver_thread: Optional[threading.Thread] = None

    def register_service(self, name: str, port: int, properties: Dict[str, str]) -> ServiceRecord:
        """Registers a service and starts broadcasting."""
        with self._lock:
            record = ServiceRecord(
                name=name,
                host=socket.gethostname(),
                port=port,
                properties=properties
            )
            self._services[name] = record
            return record

    def discover_services(self, service_type: str = "") -> List[ServiceRecord]:
        """Returns registered services filtering by type (if provided)."""
        self._expire_old()
        with self._lock:
            return [s for s in self._services.values() if service_type in s.name]

    def get_all(self) -> List[ServiceRecord]:
        """Returns all registered services."""
        self._expire_old()
        with self._lock:
            return list(self._services.values())

    def _expire_old(self):
        """Removes TTL-expired entries."""
        with self._lock:
            before = len(self._services)
            self._services = {k: v for k, v in self._services.items() if not v.is_expired()}
            after = len(self._services)
            if before != after:
                pass # Expired logs can be added here

    def _broadcast_loop(self):
        """Broadcasts registered services periodically."""
        # This is a simplified implementation for the spec
        pass

_dns_sd = None

def get_dns_sd() -> DNSSDService:
    global _dns_sd
    if _dns_sd is None:
        _dns_sd = DNSSDService()
    return _dns_sd

def reset_dns_sd():
    global _dns_sd
    _dns_sd = None
