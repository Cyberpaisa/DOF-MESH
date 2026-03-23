"""
NATS TLS 1.3 + mTLS Configuration
Protocol: DOF_OCTANET_v1 | Security Level: HARDENED
Zero external dependencies (stdlib only)

Delivered by: kimi-web (PHASE2-001)
"""

import ssl
import socket
import json
import os
import time
import hashlib
import threading
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Callable
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger("octanet.nats_tls")


@dataclass
class TLSConfig:
    """Configuration for NATS TLS 1.3 + mTLS"""
    # Server certificates
    server_cert_path: str = "certs/server.crt"
    server_key_path: str = "certs/server.key"
    ca_cert_path: str = "certs/ca.crt"

    # mTLS settings
    mtls_enabled: bool = True
    verify_mode: int = ssl.CERT_REQUIRED  # FORCE mTLS
    verify_depth: int = 9

    # TLS 1.3 only
    min_version: int = ssl.TLSVersion.TLSv1_3
    max_version: int = ssl.TLSVersion.TLSv1_3

    # Cipher suites (TLS 1.3)
    ciphers: str = "TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_128_GCM_SHA256"

    # Certificate rotation
    rotation_days: int = 30
    warning_days: int = 7

    def to_dict(self) -> Dict:
        return asdict(self)


class NATSTLSContext:
    """
    Manages TLS 1.3 + mTLS context for NATS JetStream
    Thread-safe, supports hot-reloading
    """

    def __init__(self, config: Optional[TLSConfig] = None):
        self.config = config or TLSConfig()
        self._context: Optional[ssl.SSLContext] = None
        self._lock = threading.RLock()
        self._last_reload = 0.0
        self._cert_fingerprints: Dict[str, str] = {}

        # Initialize
        self._build_context()
        logger.info("NATS TLS Context initialized (TLS 1.3 + mTLS)")

    def _build_context(self) -> ssl.SSLContext:
        """Build TLS 1.3 context with mTLS"""
        with self._lock:
            # Create context with explicit TLS 1.3
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.minimum_version = self.config.min_version
            context.maximum_version = self.config.max_version

            # Load server certificate and private key
            context.load_cert_chain(
                certfile=self.config.server_cert_path,
                keyfile=self.config.server_key_path
            )

            # Load CA for client verification (mTLS)
            if self.config.mtls_enabled:
                context.load_verify_locations(self.config.ca_cert_path)
                context.verify_mode = self.config.verify_mode
                context.verify_flags = ssl.VERIFY_DEFAULT

            # TLS 1.3 cipher configuration
            context.set_ciphers(self.config.ciphers)

            # Additional security options
            context.options |= ssl.OP_NO_COMPRESSION  # CRIME attack prevention
            context.options |= ssl.OP_SINGLE_ECDH_USE  # Perfect forward secrecy
            context.options |= ssl.OP_CIPHER_SERVER_PREFERENCE

            # Certificate verification callback
            context.set_servername_callback(self._sni_callback)

            self._context = context
            self._last_reload = time.time()

            # Compute fingerprints for monitoring
            self._update_fingerprints()

            return context

    def _sni_callback(self, sock, hostname, context):
        """Server Name Indication callback for virtual hosting"""
        logger.debug(f"SNI callback: {hostname}")

    def _update_fingerprints(self):
        """Update certificate SHA-256 fingerprints"""
        paths = {
            "server": self.config.server_cert_path,
            "ca": self.config.ca_cert_path
        }
        for name, path in paths.items():
            if Path(path).exists():
                with open(path, "rb") as f:
                    self._cert_fingerprints[name] = hashlib.sha256(f.read()).hexdigest()[:16]

    def get_context(self) -> ssl.SSLContext:
        """Get current SSL context (thread-safe)"""
        with self._lock:
            return self._context

    def reload_if_needed(self) -> bool:
        """
        Hot-reload certificates if changed
        Returns True if reloaded
        """
        with self._lock:
            current_mtime = 0
            for path in [self.config.server_cert_path, self.config.ca_cert_path]:
                p = Path(path)
                if p.exists():
                    current_mtime = max(current_mtime, p.stat().st_mtime)

            if current_mtime > self._last_reload:
                logger.info("Certificate files changed, reloading...")
                self._build_context()
                return True
            return False

    def get_cert_info(self) -> Dict:
        """Get current certificate information"""
        with self._lock:
            return {
                "fingerprints": self._cert_fingerprints,
                "last_reload": datetime.fromtimestamp(
                    self._last_reload, tz=timezone.utc
                ).isoformat(),
                "mtls_enabled": self.config.mtls_enabled,
                "tls_version": "1.3",
                "verify_mode": "CERT_REQUIRED" if self.config.mtls_enabled else "NONE"
            }


class NATSClientTLS:
    """
    Client-side TLS configuration for NATS
    mTLS: Client presents certificate to server
    """

    def __init__(self, config: Optional[TLSConfig] = None):
        self.config = config or TLSConfig()
        self._context: Optional[ssl.SSLContext] = None
        self._build_context()

    def _build_context(self) -> ssl.SSLContext:
        """Build client TLS context with mTLS"""
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.minimum_version = self.config.min_version
        context.maximum_version = self.config.max_version

        # Load client certificate (for mTLS)
        context.load_cert_chain(
            certfile="certs/client.crt",
            keyfile="certs/client.key"
        )

        # Verify server certificate
        context.load_verify_locations(self.config.ca_cert_path)
        context.verify_mode = ssl.CERT_REQUIRED
        context.verify_flags = ssl.VERIFY_DEFAULT

        # TLS 1.3 ciphers
        context.set_ciphers(self.config.ciphers)

        context.options |= ssl.OP_NO_COMPRESSION

        self._context = context
        return context

    def wrap_socket(self, sock: socket.socket, server_hostname: str) -> ssl.SSLSocket:
        """Wrap a socket with TLS"""
        return self._context.wrap_socket(
            sock,
            server_hostname=server_hostname,
            do_handshake_on_connect=True
        )

    def get_context(self) -> ssl.SSLContext:
        """Get SSL context for async libraries"""
        return self._context


class NATSConnectionManager:
    """
    Manages NATS connections with TLS/mTLS
    Handles reconnection with exponential backoff
    """

    def __init__(self, tls_context: NATSTLSContext):
        self.tls = tls_context
        self._connections: Dict[str, ssl.SSLSocket] = {}
        self._lock = threading.RLock()
        self._max_retries = 5
        self._base_delay = 1.0

    def connect(self, host: str, port: int, timeout: float = 10.0) -> ssl.SSLSocket:
        """
        Establish TLS connection to NATS server
        With retry logic and exponential backoff
        """
        context = self.tls.get_context()

        for attempt in range(self._max_retries):
            try:
                sock = socket.create_connection((host, port), timeout=timeout)
                ssock = context.wrap_socket(sock, server_side=False)

                cipher = ssock.cipher()
                version = ssock.version()
                logger.info(f"TLS connected: {version} | {cipher[0]} | {host}:{port}")

                with self._lock:
                    self._connections[f"{host}:{port}"] = ssock

                return ssock

            except ssl.SSLError as e:
                logger.error(f"TLS handshake failed (attempt {attempt+1}): {e}")
                if attempt == self._max_retries - 1:
                    raise
                time.sleep(self._base_delay * (2 ** attempt))

            except Exception as e:
                logger.error(f"Connection failed (attempt {attempt+1}): {e}")
                if attempt == self._max_retries - 1:
                    raise
                time.sleep(self._base_delay * (2 ** attempt))

        raise ConnectionError(f"Failed to connect to {host}:{port} after {self._max_retries} attempts")

    def get_connection(self, host: str, port: int) -> Optional[ssl.SSLSocket]:
        """Get existing connection if alive"""
        key = f"{host}:{port}"
        with self._lock:
            conn = self._connections.get(key)
            if conn and not conn._closed:
                return conn
            return None

    def close_all(self):
        """Close all connections"""
        with self._lock:
            for key, conn in list(self._connections.items()):
                try:
                    conn.close()
                    logger.info(f"Closed connection: {key}")
                except Exception as e:
                    logger.warning(f"Error closing {key}: {e}")
            self._connections.clear()


class CertificateManager:
    """
    Manages certificate lifecycle: generation, rotation, validation
    Zero external dependencies (uses openssl via subprocess)
    """

    def __init__(self, cert_dir: str = "certs"):
        self.cert_dir = Path(cert_dir)
        self.cert_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._rotation_callbacks: List[Callable] = []

    def generate_ca(self,
                    common_name: str = "OCTANET-CA",
                    validity_days: int = 365,
                    key_size: int = 4096) -> Tuple[str, str]:
        """Generate Certificate Authority. Returns: (cert_path, key_path)"""
        import subprocess
        key_path = self.cert_dir / "ca.key"
        cert_path = self.cert_dir / "ca.crt"

        subprocess.run(
            ["openssl", "genrsa", "-out", str(key_path), str(key_size)],
            capture_output=True
        )

        subj = f"/C=CO/ST=Antioquia/L=Medellin/O=OCTANET/OU=Security/CN={common_name}"
        subprocess.run(
            ["openssl", "req", "-x509", "-new", "-nodes", "-key", str(key_path),
             "-sha384", "-days", str(validity_days), "-out", str(cert_path), "-subj", subj],
            capture_output=True
        )

        os.chmod(key_path, 0o600)
        os.chmod(cert_path, 0o644)

        logger.info(f"CA generated: {cert_path}")
        return str(cert_path), str(key_path)

    def generate_server_cert(self,
                             ca_cert: str,
                             ca_key: str,
                             common_name: str = "nats.octanet.local",
                             validity_days: int = 30,
                             alt_names: Optional[List[str]] = None) -> Tuple[str, str]:
        """Generate server certificate signed by CA"""
        import subprocess
        key_path = self.cert_dir / "server.key"
        cert_path = self.cert_dir / "server.crt"
        csr_path = self.cert_dir / "server.csr"
        ext_path = self.cert_dir / "server.ext"

        subprocess.run(
            ["openssl", "genrsa", "-out", str(key_path), "2048"],
            capture_output=True
        )

        subj = f"/C=CO/ST=Antioquia/L=Medellin/O=OCTANET/OU=NATS/CN={common_name}"
        subprocess.run(
            ["openssl", "req", "-new", "-key", str(key_path),
             "-out", str(csr_path), "-subj", subj],
            capture_output=True
        )

        alt_names = alt_names or ["localhost", "127.0.0.1", "*.nats.octanet.local"]
        with open(ext_path, "w") as f:
            f.write("authorityKeyIdentifier=keyid,issuer\n")
            f.write("basicConstraints=CA:FALSE\n")
            f.write("keyUsage = digitalSignature, keyEncipherment\n")
            f.write("extendedKeyUsage = serverAuth\n")
            f.write("subjectAltName = " + ",".join(f"DNS:{n}" for n in alt_names))

        subprocess.run(
            ["openssl", "x509", "-req", "-in", str(csr_path), "-CA", ca_cert,
             "-CAkey", ca_key, "-CAcreateserial", "-out", str(cert_path),
             "-days", str(validity_days), "-sha384", "-extfile", str(ext_path)],
            capture_output=True
        )

        csr_path.unlink(missing_ok=True)
        ext_path.unlink(missing_ok=True)
        os.chmod(key_path, 0o600)
        os.chmod(cert_path, 0o644)

        logger.info(f"Server cert generated: {cert_path} (valid {validity_days} days)")
        return str(cert_path), str(key_path)

    def generate_client_cert(self,
                             ca_cert: str,
                             ca_key: str,
                             client_id: str,
                             validity_days: int = 30) -> Tuple[str, str]:
        """Generate client certificate for mTLS"""
        import subprocess
        key_path = self.cert_dir / f"client_{client_id}.key"
        cert_path = self.cert_dir / f"client_{client_id}.crt"
        csr_path = self.cert_dir / f"client_{client_id}.csr"

        subprocess.run(
            ["openssl", "genrsa", "-out", str(key_path), "2048"],
            capture_output=True
        )

        subj = f"/C=CO/ST=Antioquia/L=Medellin/O=OCTANET/OU=Clients/CN={client_id}"
        subprocess.run(
            ["openssl", "req", "-new", "-key", str(key_path),
             "-out", str(csr_path), "-subj", subj],
            capture_output=True
        )

        subprocess.run(
            ["openssl", "x509", "-req", "-in", str(csr_path), "-CA", ca_cert,
             "-CAkey", ca_key, "-CAcreateserial", "-out", str(cert_path),
             "-days", str(validity_days), "-sha384"],
            capture_output=True
        )

        csr_path.unlink(missing_ok=True)
        os.chmod(key_path, 0o600)
        os.chmod(cert_path, 0o644)

        logger.info(f"Client cert generated: {cert_path} for {client_id}")
        return str(cert_path), str(key_path)

    def check_expiration(self, cert_path: str, warning_days: int = 7) -> Dict:
        """Check certificate expiration. Returns status and days remaining."""
        import subprocess

        try:
            result = subprocess.run(
                ["openssl", "x509", "-in", cert_path, "-noout", "-enddate"],
                capture_output=True, text=True
            )
            end_date_str = result.stdout.strip().split("=")[1]
            end_date = datetime.strptime(end_date_str, "%b %d %H:%M:%S %Y %Z")

            now = datetime.now()
            days_remaining = (end_date - now).days

            status = "valid"
            if days_remaining < 0:
                status = "expired"
            elif days_remaining <= warning_days:
                status = "warning"

            return {
                "path": cert_path,
                "status": status,
                "days_remaining": days_remaining,
                "expires": end_date.isoformat()
            }

        except Exception as e:
            return {"path": cert_path, "status": "error", "error": str(e)}

    def rotate_if_needed(self,
                         cert_path: str,
                         ca_cert: str,
                         ca_key: str,
                         warning_days: int = 7) -> bool:
        """Rotate certificate if nearing expiration. Returns True if rotated."""
        check = self.check_expiration(cert_path, warning_days)

        if check["status"] in ("warning", "expired"):
            logger.warning(f"Certificate {cert_path} needs rotation: {check}")

            if "server" in cert_path:
                self.generate_server_cert(ca_cert, ca_key)
            elif "client" in cert_path:
                client_id = Path(cert_path).stem.replace("client_", "")
                self.generate_client_cert(ca_cert, ca_key, client_id)

            for callback in self._rotation_callbacks:
                callback(cert_path, check)

            return True

        return False

    def on_rotation(self, callback: Callable):
        """Register callback for rotation events"""
        self._rotation_callbacks.append(callback)
