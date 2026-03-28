"""
Versioned Z3 Cache — Cache con versionado por epoch y expiración.

Upgrade del cache simple de z3_gate.py. Cada verificación cacheada incluye:
- constraint_hash: hash del constraint
- epoch: epoch de Constitution cuando se verificó
- result: resultado de la verificación
- expires_at_epoch: epoch máximo de validez

Si el epoch actual > expires_at_epoch → cache miss (invalidación automática).
Si Constitution cambia (nuevo epoch) → entries viejas se invalidan progresivamente.
"""
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("core.versioned_cache")


@dataclass(frozen=True)
class CacheEntry:
    constraint_hash: str
    result: Any
    created_epoch: int
    expires_at_epoch: int
    timestamp: datetime


class VersionedCache:
    """
    Cache con versionado por epoch.

    Uso:
        cache = VersionedCache(ttl_epochs=10)
        cache.put("hash123", result_obj, current_epoch=5)

        # Epoch 5-15: cache hit
        result = cache.get("hash123", current_epoch=7)  # → result_obj

        # Epoch 16+: cache miss (expirado)
        result = cache.get("hash123", current_epoch=16)  # → None
    """

    def __init__(self, ttl_epochs: int = 10):
        self.ttl_epochs = ttl_epochs
        self._entries: dict[str, CacheEntry] = {}
        self._hits: int = 0
        self._misses: int = 0

    def put(self, key: str, result: Any, current_epoch: int) -> None:
        """Almacena resultado en cache con epoch actual y TTL."""
        entry = CacheEntry(
            constraint_hash=key,
            result=result,
            created_epoch=current_epoch,
            expires_at_epoch=current_epoch + self.ttl_epochs,
            timestamp=datetime.now(timezone.utc),
        )
        self._entries[key] = entry

    def get(self, key: str, current_epoch: int) -> Optional[Any]:
        """Retorna resultado cacheado si existe y no ha expirado. None si miss."""
        entry = self._entries.get(key)
        if entry is None:
            self._misses += 1
            return None
        if current_epoch > entry.expires_at_epoch:
            # Expirado por epoch
            del self._entries[key]
            self._misses += 1
            return None
        self._hits += 1
        return entry.result

    def invalidate_before_epoch(self, epoch: int) -> int:
        """Invalida todas las entries creadas antes del epoch dado. Retorna count."""
        to_remove = [k for k, e in self._entries.items() if e.created_epoch < epoch]
        for k in to_remove:
            del self._entries[k]
        if to_remove:
            logger.info(f"[VersionedCache] Invalidadas {len(to_remove)} entries antes de epoch {epoch}")
        return len(to_remove)

    def clear(self) -> int:
        """Limpia todo el cache. Retorna count."""
        count = len(self._entries)
        self._entries.clear()
        return count

    @property
    def size(self) -> int:
        return len(self._entries)

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses
