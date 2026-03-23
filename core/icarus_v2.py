"""
Icarus V2 — Behavioral Threat Hunter + Encryption-Aware Anomaly Detector

Delivered by: gpt-legion (PHASE2-004)

Features:
- Baseline adaptive model (no external ML dependencies)
- Shannon entropy analysis for encrypted traffic
- Z-score anomaly detection
- Key rotation anomaly monitoring
- Honeypot simulation on TLS ports
- Zero external dependencies
"""

import time
import json
import math
import random
import logging
from collections import deque
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger("core.icarus_v2")

# ==========================
# CONFIG
# ==========================
WINDOW_SIZE = 50
ANOMALY_THRESHOLD = 2.5
HONEYPOT_PORTS = [4433, 8443, 9443]


# ==========================
# UTILS
# ==========================
def shannon_entropy(data: bytes) -> float:
    """Calculate Shannon entropy of byte data."""
    if not data:
        return 0
    freq = {}
    for b in data:
        freq[b] = freq.get(b, 0) + 1
    entropy = 0
    for count in freq.values():
        p = count / len(data)
        entropy -= p * math.log2(p)
    return entropy


def z_score(value: float, mean: float, std: float) -> float:
    """Calculate z-score for anomaly detection."""
    if std == 0:
        return 0
    return (value - mean) / std


# ==========================
# BASELINE MODEL
# ==========================
class BaselineModel:
    """Adaptive baseline for traffic pattern analysis."""

    def __init__(self):
        self.packet_sizes = deque(maxlen=WINDOW_SIZE)
        self.entropies = deque(maxlen=WINDOW_SIZE)
        self.intervals = deque(maxlen=WINDOW_SIZE)
        self.last_time = None

    def update(self, packet: bytes):
        """Update baseline with new packet."""
        now = time.time()
        size = len(packet)
        entropy = shannon_entropy(packet)

        self.packet_sizes.append(size)
        self.entropies.append(entropy)

        if self.last_time:
            self.intervals.append(now - self.last_time)
        self.last_time = now

    def stats(self, data) -> Tuple[float, float]:
        """Calculate mean and standard deviation."""
        if not data:
            return (0, 0)
        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / len(data)
        return (mean, math.sqrt(variance))

    def detect_anomaly(self, packet: bytes) -> Tuple[bool, Dict]:
        """Detect anomaly using z-score against baseline."""
        size = len(packet)
        entropy = shannon_entropy(packet)

        size_mean, size_std = self.stats(self.packet_sizes)
        ent_mean, ent_std = self.stats(self.entropies)

        size_z = z_score(size, size_mean, size_std)
        ent_z = z_score(entropy, ent_mean, ent_std)

        if abs(size_z) > ANOMALY_THRESHOLD or abs(ent_z) > ANOMALY_THRESHOLD:
            return True, {
                "size_z": round(size_z, 3),
                "entropy_z": round(ent_z, 3),
                "packet_size": size,
                "entropy": round(entropy, 3),
            }
        return False, {}


# ==========================
# ENCRYPTION KEY ANOMALY
# ==========================
class KeyRotationMonitor:
    """Monitor key rotation patterns for anomalies."""

    def __init__(self):
        self.key_history = deque(maxlen=WINDOW_SIZE)

    def register_key(self, key_hash: str):
        """Register a key hash in history."""
        self.key_history.append(key_hash)

    def detect_anomaly(self, key_hash: str) -> bool:
        """Detect if key is suspiciously new (not in recent history)."""
        if key_hash not in self.key_history and len(self.key_history) > 10:
            return True
        return False


# ==========================
# HONEYPOT
# ==========================
class Honeypot:
    """Simulated honeypot for E2E encrypted channel analysis."""

    def __init__(self):
        self.traps: List[Dict] = []

    def simulate_connection(self) -> Tuple[int, bytes]:
        """Simulate a connection attempt on honeypot port."""
        port = random.choice(HONEYPOT_PORTS)
        fake_payload = bytes([random.randint(0, 255) for _ in range(128)])
        return port, fake_payload

    def log_intrusion(self, port: int, payload: bytes):
        """Log a detected intrusion attempt."""
        entry = {
            "timestamp": time.time(),
            "port": port,
            "entropy": round(shannon_entropy(payload), 3),
            "payload_size": len(payload),
        }
        self.traps.append(entry)
        logger.warning(f"HONEYPOT ALERT: {entry}")

    def get_traps(self) -> List[Dict]:
        """Get all logged intrusion attempts."""
        return self.traps


# ==========================
# ICARUS V2 CORE
# ==========================
class IcarusV2:
    """
    Proactive behavioral threat hunter with encryption awareness.

    Combines:
    - Adaptive baseline traffic analysis
    - Key rotation anomaly detection
    - Honeypot-based intrusion detection
    - Shannon entropy analysis for encrypted traffic
    """

    def __init__(self):
        self.baseline = BaselineModel()
        self.key_monitor = KeyRotationMonitor()
        self.honeypot = Honeypot()
        self.alerts: List[Dict] = []
        self.packets_processed = 0

    def process_packet(self, packet: bytes, key_hash: str) -> Dict:
        """
        Process a packet through full analysis pipeline.
        Returns alert dict if anomaly detected, empty dict otherwise.
        """
        self.packets_processed += 1
        self.baseline.update(packet)

        anomaly, details = self.baseline.detect_anomaly(packet)
        key_anomaly = self.key_monitor.detect_anomaly(key_hash)

        self.key_monitor.register_key(key_hash)

        alert = {}
        if anomaly:
            alert["traffic_anomaly"] = details
            logger.warning(f"TRAFFIC ANOMALY: {details}")

        if key_anomaly:
            alert["key_anomaly"] = {"suspicious_key": key_hash}
            logger.warning(f"KEY ANOMALY: suspicious rotation to {key_hash}")

        if alert:
            alert["timestamp"] = time.time()
            alert["packet_number"] = self.packets_processed
            self.alerts.append(alert)

        return alert

    def run_honeypot_cycle(self) -> Optional[Dict]:
        """Run one honeypot simulation cycle."""
        port, payload = self.honeypot.simulate_connection()
        if shannon_entropy(payload) > 7.5:
            self.honeypot.log_intrusion(port, payload)
            return {"port": port, "entropy": shannon_entropy(payload)}
        return None

    def get_status(self) -> Dict:
        """Get Icarus V2 status."""
        return {
            "packets_processed": self.packets_processed,
            "alerts_total": len(self.alerts),
            "honeypot_traps": len(self.honeypot.traps),
            "baseline_window": len(self.baseline.packet_sizes),
            "keys_tracked": len(self.key_monitor.key_history),
        }


# ==========================
# CLI
# ==========================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    icarus = IcarusV2()

    print("Icarus V2 — Behavioral Threat Hunter")
    print("Running simulation (100 packets)...")

    for i in range(100):
        packet = bytes([random.randint(0, 255) for _ in range(random.randint(50, 1500))])
        key_hash = random.choice(["keyA", "keyB", "keyC", "keyX"])

        alert = icarus.process_packet(packet, key_hash)
        if alert:
            print(f"  [{i}] ALERT: {alert}")

        if random.random() < 0.1:
            icarus.run_honeypot_cycle()

    status = icarus.get_status()
    print(f"\nStatus: {json.dumps(status, indent=2)}")
