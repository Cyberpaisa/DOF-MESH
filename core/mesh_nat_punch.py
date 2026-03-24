import socket
import threading
import time
from dataclasses import dataclass
from typing import Optional

@dataclass
class PunchResult:
    success: bool
    latency_ms: float
    attempts: int

class NATPuncher:
    def __init__(self):
        self._lock = threading.Lock()

    def punch(self, local_port: int, peer_public_ip: str, peer_public_port: int) -> bool:
        """Sends 3 concurrent UDP probes to punch a hole in the NAT."""
        attempts = 3
        timeout = 5.0
        success = False
        start_time = time.time()

        def send_probe():
            nonlocal success
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.bind(('', local_port))
                    s.settimeout(timeout)
                    # Send probe
                    s.sendto(b"DOF_PUNCH", (peer_public_ip, peer_public_port))
                    # Wait for echo
                    data, addr = s.recvfrom(1024)
                    if data == b"DOF_PUNCH_ACK":
                        success = True
            except Exception:
                pass

        threads = []
        for _ in range(attempts):
            t = threading.Thread(target=send_probe)
            t.start()
            threads.append(t)

        for t in threads:
            t.join(timeout=timeout)

        return success

    def is_reachable(self, peer_ip: str, peer_port: int) -> bool:
        """Quick connectivity check."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(2.0)
                s.sendto(b"DOF_PING", (peer_ip, peer_port))
                data, addr = s.recvfrom(1024)
                return data == b"DOF_PONG"
        except Exception:
            return False

_puncher = None

def get_nat_puncher() -> NATPuncher:
    global _puncher
    if _puncher is None:
        _puncher = NATPuncher()
    return _puncher

def reset_nat_puncher():
    global _puncher
    _puncher = None
