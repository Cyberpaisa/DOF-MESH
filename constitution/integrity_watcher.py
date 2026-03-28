import hashlib
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("constitution.integrity_watcher")


class ConstitutionDriftException(Exception):
    pass


@dataclass
class IntegritySnapshot:
    current_hash: str
    baseline_hash: str
    timestamp: datetime
    drift_detected: bool
    delta_seconds: float  # tiempo desde ultimo check


class ConstitutionIntegrityWatcher:
    """
    Recalcula SHA-256 del arbol de reglas Constitution cada N segundos
    y compara contra el hash baseline (simulado como on-chain atestado).
    Detecta drift de estado en <30s.

    En produccion, baseline_hash viene de fetch_onchain_hash().
    En esta implementacion, se establece en __init__ y puede actualizarse
    con update_baseline() cuando hay un update legitimo de Constitution.
    """

    def __init__(self, constitution_rules: dict, interval_seconds: int = 30):
        self.rules = constitution_rules
        self.interval = interval_seconds
        self._last_check: Optional[datetime] = None
        self._check_count: int = 0
        self.baseline = self._compute_hash(constitution_rules)

    def _compute_hash(self, data) -> str:
        raw = str(sorted(str(data).encode())).encode()
        return hashlib.sha256(raw).hexdigest()

    def current_hash(self) -> str:
        return self._compute_hash(self.rules)

    def verify(self) -> IntegritySnapshot:
        now = datetime.now(timezone.utc)
        delta = (now - self._last_check).total_seconds() if self._last_check else 0.0
        self._last_check = now
        self._check_count += 1

        current = self.current_hash()
        drift = (current != self.baseline)

        snap = IntegritySnapshot(
            current_hash=current,
            baseline_hash=self.baseline,
            timestamp=now,
            drift_detected=drift,
            delta_seconds=delta,
        )

        if drift:
            logger.error(
                f"[Constitution] Drift detectado: "
                f"baseline={self.baseline[:12]}... got={current[:12]}..."
            )
            raise ConstitutionDriftException(
                f"Drift detectado: baseline={self.baseline[:12]}... got={current[:12]}..."
            )

        return snap

    def update_baseline(self, new_rules: dict) -> str:
        """Actualiza el baseline cuando hay un update legitimo de Constitution."""
        self.rules = new_rules
        self.baseline = self._compute_hash(new_rules)
        logger.info(f"[Constitution] Baseline actualizado: {self.baseline[:12]}...")
        return self.baseline

    @property
    def check_count(self) -> int:
        return self._check_count
