"""
core/session_resume.py
──────────────────────
Persistencia de sesión entre reinicios del DaemonAutonomous.

Problema: cada reinicio del daemon resetea cycle_count y total_improvements a 0.
Solución: snapshot JSON atómico en logs/daemon/session_<type>.json.

Uso básico:
    from core.session_resume import SessionStore

    store = SessionStore(daemon_type="default")
    session = store.load()          # None si no hay sesión válida
    if session:
        self.cycle_count = session.cycle_count
        self.total_improvements = session.total_improvements

    # en cada ciclo:
    store.save(self.cycle_count, self.total_improvements)

    # en shutdown limpio:
    store.clear()

Sigue el patrón singleton DOF: tiene reset() para aislamiento entre tests.
"""

import json
import logging
import os
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger("dof.session_resume")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_DIR = os.path.join(BASE_DIR, "logs", "daemon")
MAX_SESSION_AGE_SECONDS = 86400  # 24 horas


# ─────────────────────────────────────────────────────────────────────────────
# DaemonSession — datos de una sesión persistida
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DaemonSession:
    """
    Snapshot de estado de un DaemonAutonomous en un momento dado.

    Campos:
        session_id:         UUID único por sesión (nuevo en cada primera escritura)
        daemon_type:        "default" | "builder" | "guardian" | "researcher"
        cycle_count:        Número de ciclos ejecutados en esta sesión
        total_improvements: Mejoras acumuladas en esta sesión
        started_at:         Timestamp UNIX de la primera escritura
        last_updated_at:    Timestamp UNIX de la última actualización
    """
    session_id: str
    daemon_type: str
    cycle_count: int
    total_improvements: int
    started_at: float
    last_updated_at: float

    # ── Métodos de utilidad ─────────────────────────────────────────────────

    def age_seconds(self) -> float:
        """Segundos transcurridos desde last_updated_at."""
        return time.time() - self.last_updated_at

    def is_expired(self, max_age: float = MAX_SESSION_AGE_SECONDS) -> bool:
        """True si la sesión no ha sido actualizada en max_age segundos."""
        return self.age_seconds() > max_age

    def to_dict(self) -> dict:
        """Serializa a dict JSON-compatible."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "DaemonSession":
        """
        Deserializa desde dict.

        Raises:
            KeyError: si faltan campos obligatorios.
            TypeError: si los tipos son incompatibles.
        """
        return cls(
            session_id=str(d["session_id"]),
            daemon_type=str(d["daemon_type"]),
            cycle_count=int(d["cycle_count"]),
            total_improvements=int(d["total_improvements"]),
            started_at=float(d["started_at"]),
            last_updated_at=float(d["last_updated_at"]),
        )

    def __repr__(self) -> str:
        return (
            f"DaemonSession(type={self.daemon_type!r}, "
            f"cycles={self.cycle_count}, "
            f"improvements={self.total_improvements}, "
            f"age={self.age_seconds():.0f}s)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# SessionStore — gestión de persistencia
# ─────────────────────────────────────────────────────────────────────────────

class SessionStore:
    """
    Persiste y recupera DaemonSession en disco mediante escritura atómica.

    Escritura atómica: escribe a <file>.tmp y luego rename para evitar
    corrupción en caso de crash durante la escritura.

    Thread-safe: las escrituras son operaciones atómicas a nivel de SO
    (rename es atómico en POSIX).

    Sigue el patrón singleton DOF: tiene reset() para aislamiento entre tests.
    """

    def __init__(
        self,
        daemon_type: str = "default",
        base_dir: str = BASE_DIR,
        max_age_seconds: float = MAX_SESSION_AGE_SECONDS,
    ) -> None:
        self._daemon_type = daemon_type
        self._max_age_seconds = max_age_seconds
        self._session_dir = os.path.join(base_dir, "logs", "daemon")
        self._session_file = os.path.join(
            self._session_dir, f"session_{daemon_type}.json"
        )
        self._current_session: Optional[DaemonSession] = None
        logger.debug(
            "SessionStore init: type=%s path=%s", daemon_type, self._session_file
        )

    # ── Interfaz pública ────────────────────────────────────────────────────

    def save(self, cycle_count: int, total_improvements: int) -> None:
        """
        Persiste el estado actual del daemon en disco.

        Si no existe sesión activa, crea una nueva con session_id nuevo.
        Si ya existe, actualiza cycle_count, total_improvements y last_updated_at.

        Usa escritura atómica (write tmp → rename) para evitar corrupción.

        Args:
            cycle_count:        Valor actual de DaemonAutonomous.cycle_count
            total_improvements: Valor actual de DaemonAutonomous.total_improvements
        """
        now = time.time()

        if self._current_session is None:
            self._current_session = DaemonSession(
                session_id=str(uuid.uuid4()),
                daemon_type=self._daemon_type,
                cycle_count=cycle_count,
                total_improvements=total_improvements,
                started_at=now,
                last_updated_at=now,
            )
        else:
            self._current_session.cycle_count = cycle_count
            self._current_session.total_improvements = total_improvements
            self._current_session.last_updated_at = now

        self._write_atomic(self._current_session.to_dict())
        logger.debug(
            "SessionStore.save: cycles=%d improvements=%d",
            cycle_count,
            total_improvements,
        )

    def load(self) -> Optional[DaemonSession]:
        """
        Lee la sesión persistida desde disco.

        Returns:
            DaemonSession si existe y no está expirada (< 24h sin actualizar).
            None si no existe, está corrupta, o está expirada.

        No lanza excepciones — loggea advertencia y retorna None en caso de error.
        """
        if not os.path.exists(self._session_file):
            logger.debug("SessionStore.load: no session file at %s", self._session_file)
            return None

        try:
            with open(self._session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            session = DaemonSession.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            logger.warning("SessionStore.load: corrupt session file — %s", exc)
            return None

        if session.is_expired(self._max_age_seconds):
            logger.info(
                "SessionStore.load: session expired (age=%.0fs > %.0fs) — ignoring",
                session.age_seconds(),
                self._max_age_seconds,
            )
            return None

        self._current_session = session
        logger.info(
            "SessionStore.load: resumed session %s — cycles=%d improvements=%d",
            session.session_id[:8],
            session.cycle_count,
            session.total_improvements,
        )
        return session

    def clear(self) -> None:
        """
        Elimina el archivo de sesión del disco.

        Llamar en shutdown limpio del daemon para no contaminar el próximo arranque.
        No lanza excepción si el archivo no existe.
        """
        self._current_session = None
        if os.path.exists(self._session_file):
            os.remove(self._session_file)
            logger.debug("SessionStore.clear: removed %s", self._session_file)
        else:
            logger.debug("SessionStore.clear: nothing to remove")

    def reset(self) -> None:
        """
        Resetea el estado en memoria SIN tocar disco.

        Requerido por el patrón singleton DOF para aislamiento entre tests.
        Para limpiar disco en tests, usar clear() o crear SessionStore con
        directorio temporal.
        """
        self._current_session = None
        logger.debug("SessionStore.reset: in-memory state cleared")

    @property
    def session_path(self) -> str:
        """Ruta absoluta al archivo de sesión."""
        return self._session_file

    @property
    def current_session(self) -> Optional[DaemonSession]:
        """Sesión actualmente en memoria (puede ser None si no se ha cargado)."""
        return self._current_session

    # ── Internos ────────────────────────────────────────────────────────────

    def _write_atomic(self, data: dict) -> None:
        """
        Escribe data como JSON a disco de forma atómica.

        Patrón: open(tmp) → write → flush → close → rename(tmp → final)
        rename es atómico en POSIX: nunca deja el archivo en estado parcial.
        """
        os.makedirs(self._session_dir, exist_ok=True)
        tmp_path = self._session_file + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.flush()
            os.replace(tmp_path, self._session_file)
        except OSError as exc:
            logger.error("SessionStore._write_atomic: failed — %s", exc)
            # Limpiar tmp si quedó
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            raise

    def __repr__(self) -> str:
        return (
            f"SessionStore(type={self._daemon_type!r}, "
            f"path={self._session_file!r}, "
            f"session={'yes' if self._current_session else 'none'})"
        )
