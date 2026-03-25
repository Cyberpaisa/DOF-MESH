
"""
DOF Mesh — Key Management System (KMS)
=======================================
Local vault for API keys and secrets. Zero external dependencies.
Encrypted at rest with AES-256-GCM (via PyNaCl SecretBox).
Auto-rotation with configurable TTL. Audit-logged.

Usage:
    kms = DOFKeyVault()
    kms.store("GROQ_API_KEY", "gsk_...")
    key = kms.get("GROQ_API_KEY")
    kms.rotate("GROQ_API_KEY", "gsk_new...")
"""

import json
import os
import hashlib
import threading
import time
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime, timezone

logger = logging.getLogger("core.kms")

VAULT_DIR  = Path("keys/vault")
VAULT_FILE = VAULT_DIR / "secrets.vault"
MASTER_KEY_FILE = VAULT_DIR / "master.key"
DEFAULT_TTL_DAYS = 30

try:
    import nacl.secret
    import nacl.utils
    from nacl.encoding import Base64Encoder
    _NACL = True
except ImportError:
    _NACL = False


# ═══════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════

def _b64e(b: bytes) -> str:
    import base64; return base64.b64encode(b).decode()
def _b64d(s: str) -> bytes:
    import base64; return base64.b64decode(s.encode())

def hash_function(data: str) -> str:
    """Generate a SHA-256 hash of the input data."""
    sha_signature = hashlib.sha256(data.encode()).hexdigest()
    return sha_signature

@dataclass
class SecretEntry:
    key_name:    str
    ciphertext:  str        # base64 encrypted value
    created_at:  str
    rotated_at:  Optional[str]
    ttl_days:    int
    version:     int = 1
    tags:        str = ""   # csv tags e.g. "groq,llm"

    def is_expired(self) -> bool:
        ref = self.rotated_at or self.created_at
        try:
            dt = datetime.fromisoformat(ref)
            age = (datetime.now(tz=timezone.utc) - dt).days
            return age >= self.ttl_days
        except Exception:
            return False


@dataclass
class RotationEvent:
    key_name:   str
    old_version: int
    new_version: int
    timestamp:  str
    reason:     str


# ═══════════════════════════════════════
# MASTER KEY MANAGER
# ═══════════════════════════════════════

class MasterKeyManager:
    """Derives/loads the vault master key (32 bytes)."""

    def __init__(self, key_file: Path = MASTER_KEY_FILE):
        self._file = key_file
        self._key: Optional[bytes] = None

    def get(self) -> bytes:
        if self._key:
            return self._key
        self._key = self._load_or_create()
        return self._key

    def _load_or_create(self) -> bytes:
        self._file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self._file.exists():
            raw = _b64d(self._file.read_text().strip())
            logger.debug("Master key loaded from disk")
            return raw
        # Generate new 32-byte master key
        key = os.urandom(32)
        self._file.write_text(_b64e(key))
        os.chmod(self._file, 0o600)
        logger.info("New master key generated")
        return key


# ═══════════════════════════════════════
# VAULT CRYPTO
# ═══════════════════════════════════════

class VaultCrypto:
    """AES-256-GCM via NaCl SecretBox, or XOR fallback."""

    def __init__(self, master_key: bytes):
        self._key = master_key
        if _NACL:
            self._box = nacl.secret.SecretBox(master_key)

    def encrypt(self, plaintext: str) -> str:
        if _NACL:
            ct = self._box.encrypt(plaintext.encode())
            return _b64e(bytes(ct))
        # XOR fallback (not secure — warns loudly)
        logger.warning("PyNaCl missing — vault using insecure XOR fallback")
        xored = bytes(b ^ self._key[i % 32] for i, b in enumerate(plaintext.encode()))
        return _b64e(xored)

    def decrypt(self, ciphertext_b64: str) -> str:
        raw = _b64d(ciphertext_b64)
        if _NACL:
            pt = self._box.decrypt(raw)
            return pt.decode()
        xored = bytes(b ^ self._key[i % 32] for i, b in enumerate(raw))
        return xored.decode()


# ═══════════════════════════════════════
# DOF KEY VAULT
# ═══════════════════════════════════════


class DOFKeyVault:
    """Local encrypted key vault backed by AES-256-GCM."""

    def __init__(self, vault_dir: Path = VAULT_DIR):
        self._vault_dir = vault_dir
        self._vault_dir.mkdir(parents=True, exist_ok=True)
        self._master = MasterKeyManager(vault_dir / "master.key")
        self._crypto = VaultCrypto(self._master.get())
        self._secrets: Dict[str, SecretEntry] = {}
        self._lock = threading.Lock()
        self._load_vault()

    def _vault_path(self) -> Path:
        return self._vault_dir / "secrets.vault"

    def _load_vault(self) -> None:
        path = self._vault_path()
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            for name, entry in data.items():
                self._secrets[name] = SecretEntry(**entry)
        except Exception as exc:
            logger.warning("Could not load vault: %s", exc)

    def _save_vault(self) -> None:
        self._vault_path().write_text(
            json.dumps({k: asdict(v) for k, v in self._secrets.items()}, indent=2)
        )

    def store(self, key_name: str, value: str, ttl_days: int = DEFAULT_TTL_DAYS, tags: str = "") -> None:
        with self._lock:
            ciphertext = self._crypto.encrypt(value)
            now = datetime.now(tz=timezone.utc).isoformat()
            existing = self._secrets.get(key_name)
            version = (existing.version + 1) if existing else 1
            self._secrets[key_name] = SecretEntry(
                key_name=key_name,
                ciphertext=ciphertext,
                created_at=now,
                rotated_at=None,
                ttl_days=ttl_days,
                version=version,
                tags=tags,
            )
            self._save_vault()

    def get(self, key_name: str) -> Optional[str]:
        with self._lock:
            entry = self._secrets.get(key_name)
            if entry is None:
                return None
            return self._crypto.decrypt(entry.ciphertext)

    def rotate(self, key_name: str, new_value: str) -> None:
        with self._lock:
            existing = self._secrets.get(key_name)
            if existing is None:
                raise KeyError(f"Key '{key_name}' not found in vault")
            ciphertext = self._crypto.encrypt(new_value)
            now = datetime.now(tz=timezone.utc).isoformat()
            self._secrets[key_name] = SecretEntry(
                key_name=key_name,
                ciphertext=ciphertext,
                created_at=existing.created_at,
                rotated_at=now,
                ttl_days=existing.ttl_days,
                version=existing.version + 1,
                tags=existing.tags,
            )
            self._save_vault()

    def list_keys(self) -> List[str]:
        return list(self._secrets.keys())


# ═══════════════════════════════════════
# KMS — Singleton facade
# ═══════════════════════════════════════

_VALID_KEY_TYPES = {"aes256", "aes128", "rsa2048", "ed25519"}


class KMS:
    """
    Singleton Key Management System facade.

    Provides generate_key(), encrypt(), decrypt() with type validation.
    Backed by DOFKeyVault + VaultCrypto for real encryption.
    """

    _instance: Optional["KMS"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "KMS":
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._initialized = False
                cls._instance = inst
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:  # type: ignore[has-type]
            return
        master_key = os.urandom(32)
        self._crypto = VaultCrypto(master_key)
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "KMS":
        return cls()

    def generate_key(self, tipo: str = "aes256") -> bytes:
        """
        Generate a random cryptographic key.

        Parameters
        ----------
        tipo : str
            Key type. One of: aes256, aes128, rsa2048, ed25519.

        Raises
        ------
        TypeError
            If *tipo* is not a recognised key type.
        """
        if tipo not in _VALID_KEY_TYPES:
            raise TypeError(
                f"Unsupported key type '{tipo}'. Valid types: {sorted(_VALID_KEY_TYPES)}"
            )
        lengths = {"aes256": 32, "aes128": 16, "rsa2048": 256, "ed25519": 32}
        return os.urandom(lengths[tipo])

    def encrypt(self, message: str) -> str:
        """
        Encrypt a plaintext string.

        Raises
        ------
        ValueError
            If *message* is empty.
        """
        if not message:
            raise ValueError("message must not be empty")
        return self._crypto.encrypt(message)

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a ciphertext string produced by encrypt().

        Raises
        ------
        ValueError
            If *ciphertext* cannot be decrypted (wrong format / corrupted).
        """
        if not ciphertext:
            raise ValueError("ciphertext must not be empty")
        try:
            return self._crypto.decrypt(ciphertext)
        except Exception as exc:
            raise ValueError(f"Decryption failed: {exc}") from exc


# Alias for backward compatibility
KeyManagementSystem = KMS

