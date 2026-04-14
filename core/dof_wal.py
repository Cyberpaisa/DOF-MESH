from __future__ import annotations
"""
dof_wal.py — Write-Ahead Log para crash recovery en DOF Mesh Hyperion.

Garantiza que ninguna tarea se pierda en caso de crash.
Formato: una línea JSON por entrada. Thread-safe.

Uso:
    wal = WriteAheadLog("logs/wal/node-a")
    seq = wal.append("enqueue", "task-42", {"prompt": "..."})
    # ... procesar tarea ...
    wal.confirm(seq)
    wal.compact()  # limpia entradas confirmadas
"""
import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("core.dof_wal")


@dataclass
class WALEntry:
    seq: int
    timestamp: float
    operation: str     # "enqueue" | "dequeue" | "complete" | "fail"
    key: str
    data: dict
    checksum: str
    confirmed: bool = False

    def to_dict(self) -> dict:
        return {
            "seq": self.seq,
            "timestamp": self.timestamp,
            "operation": self.operation,
            "key": self.key,
            "data": self.data,
            "checksum": self.checksum,
            "confirmed": self.confirmed,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WALEntry":
        return cls(
            seq=d["seq"],
            timestamp=d["timestamp"],
            operation=d["operation"],
            key=d["key"],
            data=d.get("data", {}),
            checksum=d["checksum"],
            confirmed=d.get("confirmed", False),
        )

    @staticmethod
    def compute_checksum(seq: int, operation: str, key: str, data: dict) -> str:
        raw = f"{seq}:{operation}:{key}:{json.dumps(data, sort_keys=True)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def is_valid(self) -> bool:
        expected = self.compute_checksum(self.seq, self.operation, self.key, self.data)
        return self.checksum == expected


class WriteAheadLog:
    """
    Write-Ahead Log append-only con confirmación y compactación.

    - append() → escribe entrada y retorna seq
    - confirm(seq) → marca como procesada
    - recover() → retorna entradas no confirmadas (tras crash)
    - compact() → elimina entradas confirmadas del archivo
    """

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._path.mkdir(parents=True, exist_ok=True)
        self._file = self._path / "wal.jsonl"
        self._lock = threading.Lock()
        self._seq = self._load_max_seq()
        logger.info("WAL ready at %s (seq=%d)", self._file, self._seq)

    # ── Public API ────────────────────────────────────────────────────────────

    def append(self, operation: str, key: str, data: dict) -> int:
        """Escribir entrada. Retorna número de secuencia."""
        with self._lock:
            self._seq += 1
            seq = self._seq
            checksum = WALEntry.compute_checksum(seq, operation, key, data)
            entry = WALEntry(
                seq=seq,
                timestamp=time.time(),
                operation=operation,
                key=key,
                data=data,
                checksum=checksum,
            )
            with open(self._file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
            return seq

    def confirm(self, seq: int) -> None:
        """Marcar entrada como procesada (rewrite en memoria, flush a disco)."""
        with self._lock:
            entries = self._read_all()
            updated = False
            for e in entries:
                if e.seq == seq and not e.confirmed:
                    e.confirmed = True
                    updated = True
                    break
            if updated:
                self._write_all(entries)

    def recover(self) -> list[WALEntry]:
        """Retorna entradas no confirmadas con checksum válido."""
        with self._lock:
            entries = self._read_all()
        return [e for e in entries if not e.confirmed and e.is_valid()]

    def compact(self) -> int:
        """Elimina entradas confirmadas. Retorna cantidad eliminada."""
        with self._lock:
            entries = self._read_all()
            before = len(entries)
            pending = [e for e in entries if not e.confirmed]
            self._write_all(pending)
            removed = before - len(pending)
        if removed:
            logger.info("WAL compacted: removed %d confirmed entries", removed)
        return removed

    def close(self) -> None:
        pass  # archivo se cierra en cada escritura (append mode)

    def size(self) -> int:
        """Número total de entradas en el WAL."""
        with self._lock:
            return len(self._read_all())

    # ── Internal ──────────────────────────────────────────────────────────────

    def _load_max_seq(self) -> int:
        if not self._file.exists():
            return 0
        max_seq = 0
        try:
            with open(self._file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            d = json.loads(line)
                            max_seq = max(max_seq, d.get("seq", 0))
                        except json.JSONDecodeError:
                            pass
        except OSError:
            pass
        return max_seq

    def _read_all(self) -> list[WALEntry]:
        if not self._file.exists():
            return []
        entries = []
        with open(self._file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(WALEntry.from_dict(json.loads(line)))
                    except (json.JSONDecodeError, KeyError):
                        pass
        return entries

    def _write_all(self, entries: list[WALEntry]) -> None:
        tmp = self._file.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e.to_dict(), ensure_ascii=False) + "\n")
        tmp.replace(self._file)
