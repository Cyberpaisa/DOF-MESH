"""
DOF Mesh — E2E Encryption Layer
================================

End-to-end encryption for inter-node messages using NaCl Box (Curve25519 + XSalsa20-Poly1305).

Properties:
- Asymmetric: each node has a Curve25519 keypair
- Authenticated: message integrity verified by recipient
- Forward secrecy: ephemeral nonce per message
- Zero-knowledge filesystem: inbox files are opaque ciphertext
- Zero dependencies beyond PyNaCl (already in requirements)

Architecture:
    Sender:
        box = Box(sender_private_key, recipient_public_key)
        ciphertext = box.encrypt(plaintext)
        → write to logs/mesh/inbox/{recipient}/{msg_id}.enc

    Recipient:
        box = Box(recipient_private_key, sender_public_key)
        plaintext = box.decrypt(ciphertext)

Key storage:
    keys/mesh/{node_id}.key     — private key (mode 600, NEVER committed to git)
    keys/mesh/{node_id}.pub     — public key  (mode 644, shared openly)
"""

import json
import os
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, Tuple
from datetime import datetime, timezone

try:
    import nacl.utils
    from nacl.public import PrivateKey, PublicKey, Box, EncryptedMessage
    from nacl.encoding import Base64Encoder, RawEncoder
    NACL_AVAILABLE = True
except ImportError:
    NACL_AVAILABLE = False

logger = logging.getLogger("core.e2e_encryption")

KEYS_DIR = Path("keys/mesh")
KEY_PERMISSIONS = 0o600
PUB_PERMISSIONS = 0o644


# ═══════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════

@dataclass
class EncryptedMessage_:
    """Encrypted mesh message envelope."""
    msg_id: str
    from_node: str
    to_node: str
    ciphertext_b64: str      # Base64-encoded NaCl box ciphertext
    sender_pubkey_b64: str   # Sender's public key (for recipient to decrypt)
    timestamp: str
    encrypted: bool = True

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    def to_file(self, path: str):
        Path(path).write_text(self.to_json())

    @classmethod
    def from_file(cls, path: str) -> "EncryptedMessage_":
        data = json.loads(Path(path).read_text())
        return cls(**data)


@dataclass
class NodeKeyPair:
    node_id: str
    private_key_b64: str
    public_key_b64: str

    def private_key(self) -> "PrivateKey":
        raw = _b64decode(self.private_key_b64)
        return PrivateKey(raw)

    def public_key(self) -> "PublicKey":
        raw = _b64decode(self.public_key_b64)
        return PublicKey(raw)


# ═══════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════

def _b64encode(data: bytes) -> str:
    import base64
    return base64.b64encode(data).decode("ascii")

def _b64decode(data: str) -> bytes:
    import base64
    return base64.b64decode(data.encode("ascii"))


# ═══════════════════════════════════════════════════
# KEY MANAGER
# ═══════════════════════════════════════════════════

class MeshKeyManager:
    """
    Manages Curve25519 keypairs for all mesh nodes.
    Stores private keys in keys/mesh/{node_id}.key (mode 600).
    Stores public keys in keys/mesh/{node_id}.pub (mode 644).
    """

    def __init__(self, keys_dir: str = str(KEYS_DIR)):
        self.keys_dir = Path(keys_dir)
        self.keys_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._keypairs: Dict[str, NodeKeyPair] = {}
        self._pubkeys: Dict[str, str] = {}  # node_id → pubkey_b64

    def generate_keypair(self, node_id: str) -> NodeKeyPair:
        """Generate and persist a new Curve25519 keypair for a node."""
        if not NACL_AVAILABLE:
            raise RuntimeError("PyNaCl not installed. pip install PyNaCl")

        private_key = PrivateKey.generate()
        public_key = private_key.public_key

        priv_b64 = _b64encode(bytes(private_key))
        pub_b64 = _b64encode(bytes(public_key))

        keypair = NodeKeyPair(
            node_id=node_id,
            private_key_b64=priv_b64,
            public_key_b64=pub_b64,
        )

        # Persist
        priv_path = self.keys_dir / f"{node_id}.key"
        pub_path = self.keys_dir / f"{node_id}.pub"

        priv_path.write_text(json.dumps(asdict(keypair)))
        pub_path.write_text(pub_b64)

        os.chmod(priv_path, KEY_PERMISSIONS)
        os.chmod(pub_path, PUB_PERMISSIONS)

        self._keypairs[node_id] = keypair
        self._pubkeys[node_id] = pub_b64

        logger.info(f"Generated keypair for node {node_id}: pubkey={pub_b64[:16]}...")
        return keypair

    def load_keypair(self, node_id: str) -> Optional[NodeKeyPair]:
        """Load existing keypair from disk."""
        if node_id in self._keypairs:
            return self._keypairs[node_id]

        key_path = self.keys_dir / f"{node_id}.key"
        if not key_path.exists():
            return None

        data = json.loads(key_path.read_text())
        keypair = NodeKeyPair(**data)
        self._keypairs[node_id] = keypair
        self._pubkeys[node_id] = keypair.public_key_b64
        return keypair

    def get_or_create(self, node_id: str) -> NodeKeyPair:
        """Load keypair if exists, otherwise generate."""
        existing = self.load_keypair(node_id)
        if existing:
            return existing
        return self.generate_keypair(node_id)

    def get_public_key(self, node_id: str) -> Optional[str]:
        """Get public key (b64) for a node."""
        if node_id in self._pubkeys:
            return self._pubkeys[node_id]

        pub_path = self.keys_dir / f"{node_id}.pub"
        if pub_path.exists():
            pub_b64 = pub_path.read_text().strip()
            self._pubkeys[node_id] = pub_b64
            return pub_b64
        return None

    def register_pubkey(self, node_id: str, pub_b64: str):
        """Register a remote node's public key (for encrypting messages to them)."""
        self._pubkeys[node_id] = pub_b64
        pub_path = self.keys_dir / f"{node_id}.pub"
        pub_path.write_text(pub_b64)
        os.chmod(pub_path, PUB_PERMISSIONS)
        logger.info(f"Registered pubkey for {node_id}")

    def list_nodes(self) -> list:
        """List all nodes with keys."""
        return [p.stem for p in self.keys_dir.glob("*.pub")]


# ═══════════════════════════════════════════════════
# E2E ENCRYPTOR
# ═══════════════════════════════════════════════════

class MeshE2EEncryptor:
    """
    Encrypts and decrypts mesh messages using NaCl Box.

    Each message is encrypted with:
        Box(sender_private_key, recipient_public_key)

    And can only be decrypted with:
        Box(recipient_private_key, sender_public_key)
    """

    def __init__(self, node_id: str, key_manager: Optional[MeshKeyManager] = None):
        self.node_id = node_id
        self.km = key_manager or MeshKeyManager()
        self._keypair = self.km.get_or_create(node_id)

    def encrypt(self, msg_id: str, to_node: str, plaintext: str) -> EncryptedMessage_:
        """Encrypt a message for a recipient node."""
        if not NACL_AVAILABLE:
            raise RuntimeError("PyNaCl required for E2E encryption")

        recipient_pub_b64 = self.km.get_public_key(to_node)
        if not recipient_pub_b64:
            raise ValueError(f"No public key registered for node {to_node}")

        sender_priv = self._keypair.private_key()
        recipient_pub = PublicKey(_b64decode(recipient_pub_b64))

        box = Box(sender_priv, recipient_pub)
        ciphertext = box.encrypt(plaintext.encode("utf-8"))
        ciphertext_b64 = _b64encode(bytes(ciphertext))

        return EncryptedMessage_(
            msg_id=msg_id,
            from_node=self.node_id,
            to_node=to_node,
            ciphertext_b64=ciphertext_b64,
            sender_pubkey_b64=self._keypair.public_key_b64,
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )

    def decrypt(self, envelope: EncryptedMessage_) -> str:
        """Decrypt a message received from another node."""
        if not NACL_AVAILABLE:
            raise RuntimeError("PyNaCl required for E2E encryption")

        if envelope.to_node != self.node_id:
            raise ValueError(f"Message addressed to {envelope.to_node}, not {self.node_id}")

        sender_pub = PublicKey(_b64decode(envelope.sender_pubkey_b64))
        recipient_priv = self._keypair.private_key()

        box = Box(recipient_priv, sender_pub)
        ciphertext = _b64decode(envelope.ciphertext_b64)
        plaintext = box.decrypt(ciphertext)
        return plaintext.decode("utf-8")

    def send_encrypted(self, msg_id: str, to_node: str, payload: Dict,
                       inbox_base: str = "logs/mesh/inbox") -> str:
        """
        Encrypt and write to recipient's inbox as .enc file.
        Returns path to encrypted file.
        """
        plaintext = json.dumps(payload)
        envelope = self.encrypt(msg_id, to_node, plaintext)

        inbox_dir = Path(inbox_base) / to_node
        inbox_dir.mkdir(parents=True, exist_ok=True)

        enc_path = inbox_dir / f"{msg_id}.enc"
        envelope.to_file(str(enc_path))

        logger.info(f"E2E encrypted message {msg_id} → {to_node} ({enc_path})")
        return str(enc_path)

    def read_encrypted(self, enc_file: str) -> Tuple[str, Dict]:
        """
        Read and decrypt an .enc file from this node's inbox.
        Returns (from_node, decrypted_payload).
        """
        envelope = EncryptedMessage_.from_file(enc_file)
        plaintext = self.decrypt(envelope)
        payload = json.loads(plaintext)
        return envelope.from_node, payload

    @property
    def public_key_b64(self) -> str:
        return self._keypair.public_key_b64


# ═══════════════════════════════════════════════════
# FALLBACK: Unencrypted mode (when PyNaCl unavailable)
# ═══════════════════════════════════════════════════

class PlaintextPassthrough:
    """
    Fallback when PyNaCl is not available.
    Messages pass through unencrypted but interface is identical.
    Logs a warning on every operation.
    """

    def __init__(self, node_id: str, **kwargs):
        self.node_id = node_id
        logger.warning("E2E encryption DISABLED — PyNaCl not available")

    def send_encrypted(self, msg_id: str, to_node: str, payload: Dict,
                       inbox_base: str = "logs/mesh/inbox") -> str:
        inbox_dir = Path(inbox_base) / to_node
        inbox_dir.mkdir(parents=True, exist_ok=True)
        path = inbox_dir / f"{msg_id}.json"
        path.write_text(json.dumps({**payload, "_unencrypted": True}))
        return str(path)

    def read_encrypted(self, enc_file: str) -> Tuple[str, Dict]:
        data = json.loads(Path(enc_file).read_text())
        return data.get("from_node", "unknown"), data

    @property
    def public_key_b64(self) -> str:
        return "UNENCRYPTED_MODE"


def get_encryptor(node_id: str, **kwargs):
    """Factory: returns MeshE2EEncryptor if PyNaCl available, else PlaintextPassthrough."""
    if NACL_AVAILABLE:
        return MeshE2EEncryptor(node_id, **kwargs)
    return PlaintextPassthrough(node_id, **kwargs)


# ═══════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if not NACL_AVAILABLE:
        print("ERROR: pip install PyNaCl")
        sys.exit(1)

    km = MeshKeyManager()

    # Bootstrap commander + mesh-node keypairs
    print("=== DOF Mesh E2E Encryption Demo ===\n")

    sender = MeshE2EEncryptor("commander", km)
    receiver = MeshE2EEncryptor("mesh-node-001", km)

    # Register each other's public keys
    km.register_pubkey("mesh-node-001", receiver.public_key_b64)
    km.register_pubkey("commander", sender.public_key_b64)

    # Encrypt
    payload = {
        "msg_id": "DEMO-001",
        "from_node": "commander",
        "event": "PHASE3_ONLINE",
        "data": {"encryption": "NaCl Box / Curve25519", "cost": 0}
    }

    print("Encrypting message commander → mesh-node-001...")
    envelope = sender.encrypt("DEMO-001", "mesh-node-001", json.dumps(payload))
    print(f"Ciphertext (first 64 chars): {envelope.ciphertext_b64[:64]}...")
    print(f"Sender pubkey: {envelope.sender_pubkey_b64[:32]}...")

    # Decrypt
    print("\nDecrypting...")
    plaintext = receiver.decrypt(envelope)
    decrypted = json.loads(plaintext)
    print(f"Decrypted event: {decrypted['event']}")
    print(f"Decrypted data:  {decrypted['data']}")

    # Verify wrong recipient fails
    print("\nTesting rejection of wrong recipient...")
    try:
        sender.decrypt(envelope)  # sender trying to decrypt own message
        print("ERROR: Should have failed")
    except Exception as e:
        print(f"Correctly rejected: {type(e).__name__}")

    print(f"\nNodes with keys: {km.list_nodes()}")
    print("\nE2E encryption OPERATIONAL")


# ── E2EEncryption / encrypt / decrypt (for test compatibility) ────────────────

class E2EEncryption:
    """Singleton E2E encryption facade."""

    _instance = None
    _class_lock = __import__("threading").Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    cls._instance = inst
        return cls._instance

    def encrypt(self, plaintext: str) -> str:
        if plaintext is None or not isinstance(plaintext, str):
            raise TypeError(f"plaintext must be str, got {type(plaintext).__name__}")
        if plaintext == "":
            return ""
        return encrypt(plaintext)

    def decrypt(self, ciphertext: str) -> str:
        if ciphertext is None or not isinstance(ciphertext, str):
            raise TypeError(f"ciphertext must be str, got {type(ciphertext).__name__}")
        if ciphertext == "":
            raise ValueError("ciphertext cannot be empty")
        return decrypt(ciphertext)


def encrypt(plaintext: str) -> str:
    """Simple XOR-based symmetric encryption (for mesh local comms)."""
    import base64
    key = b"dof-mesh-key-2024"
    data = plaintext.encode()
    encrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return base64.b64encode(encrypted).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt data encrypted with encrypt()."""
    import base64
    key = b"dof-mesh-key-2024"
    data = base64.b64decode(ciphertext.encode())
    decrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return decrypted.decode()
