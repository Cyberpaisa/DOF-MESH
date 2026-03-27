#!/usr/bin/env python3
"""
"""

import asyncio
import copy
import heapq
import math
import os
import queue
import random
import sys
import json
import time
import struct
import hashlib
import hmac
import logging
import secrets
import threading
import traceback
import uuid
from enum import Enum, IntEnum, auto
from typing import (
    Any, Callable, Coroutine, Deque, Dict, FrozenSet, List,
    Optional, Set, Tuple, Union,
    ByteString, NamedTuple, Final
)
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, deque
from io import BytesIO
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor

import numpy as np

try:
    import mmh3
    HAS_MMH3 = True
except ImportError:
    HAS_MMH3 = False

try:
    from sortedcontainers import SortedDict
    HAS_SORTEDCONTAINERS = True
except ImportError:
    HAS_SORTEDCONTAINERS = False

# CRYPTOGRAPHIC BACKENDS

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

try:
    import oqs
    HAS_OQS = True
except ImportError:
    HAS_OQS = False

try:
    import nacl.secret
    import nacl.utils
    import nacl.signing
    import nacl.encoding
    HAS_NACL = True
except ImportError:
    HAS_NACL = False


# QANION CONSTANTS

class QanionConstants:
    """Constantes fundamentales del protocolo QANION."""
    
    PROTOCOL_NAME: Final[str] = "QANION"
    PROTOCOL_VERSION: Final[Tuple[int, int, int]] = (1, 0, 0)
    MAGIC_BYTES: Final[bytes] = b'\x51\x41\x4E\x49'  # "QANI"
    
    # Tamaños de paquete
    MAX_PACKET_SIZE: Final[int] = 65535
    MIN_PACKET_SIZE: Final[int] = 64
    HEADER_SIZE: Final[int] = 48
    FOOTER_SIZE: Final[int] = 16
    MAX_PAYLOAD_SIZE: Final[int] = MAX_PACKET_SIZE - HEADER_SIZE - FOOTER_SIZE
    
    # Criptografía
    AES_KEY_SIZE: Final[int] = 32  # AES-256
    AES_NONCE_SIZE: Final[int] = 12
    AES_TAG_SIZE: Final[int] = 16
    CHACHA_KEY_SIZE: Final[int] = 32
    CHACHA_NONCE_SIZE: Final[int] = 12
    
    # Kyber
    KYBER_512_PK: Final[int] = 800
    KYBER_512_SK: Final[int] = 1632
    KYBER_512_CT: Final[int] = 768
    KYBER_768_PK: Final[int] = 1184
    KYBER_768_SK: Final[int] = 2400
    KYBER_768_CT: Final[int] = 1088
    KYBER_1024_PK: Final[int] = 1568
    KYBER_1024_SK: Final[int] = 3168
    KYBER_1024_CT: Final[int] = 1568
    
    # Falcon
    FALCON_512_PK: Final[int] = 897
    FALCON_512_SK: Final[int] = 1281
    FALCON_512_SIG: Final[int] = 666
    FALCON_1024_PK: Final[int] = 1793
    FALCON_1024_SK: Final[int] = 2305
    FALCON_1024_SIG: Final[int] = 1280
    
    # Key Rotation
    DEFAULT_KEY_ROTATION_INTERVAL: Final[int] = 3600  # 1 hora
    DEFAULT_KEY_ROTATION_COUNT: Final[int] = 1000
    MAX_KEY_AGE: Final[int] = 86400  # 24 horas
    
    # Timeouts
    DEFAULT_TIMEOUT: Final[float] = 30.0
    HANDSHAKE_TIMEOUT: Final[float] = 10.0
    RETRY_INTERVAL: Final[float] = 1.0
    MAX_RETRIES: Final[int] = 3
    
    # Buffer
    DEFAULT_BUFFER_SIZE: Final[int] = 4096
    MAX_BUFFER_SIZE: Final[int] = 1048576  # 1MB
    
    # Logging
    LOG_MAX_SIZE: Final[int] = 10485760  # 10MB
    LOG_BACKUP_COUNT: Final[int] = 5


# QANION ENUMERATIONS

class QanionPacketType(IntEnum):
    """Tipos de paquetes QANION."""
    HANDSHAKE_INIT = 0x01
    HANDSHAKE_RESPONSE = 0x02
    HANDSHAKE_COMPLETE = 0x03
    DATA = 0x10
    DATA_ACK = 0x11
    DATA_RETRANSMIT = 0x12
    KEY_EXCHANGE = 0x20
    KEY_ROTATION = 0x21
    KEY_CONFIRMATION = 0x22
    HEARTBEAT = 0x30
    HEARTBEAT_ACK = 0x31
    DISCONNECT = 0x40
    DISCONNECT_ACK = 0x41
    ERROR = 0x50
    PING = 0x60
    PONG = 0x61
    FRAGMENT_START = 0x70
    FRAGMENT_CONTINUE = 0x71
    FRAGMENT_END = 0x72
    ENCRYPTED = 0x80
    SIGNED = 0x81
    COMPRESSED = 0x82
    METADATA = 0x90
    CONTROL = 0xA0
    CUSTOM = 0xF0


class QanionEncryptionMode(IntEnum):
    """Modos de encriptación."""
    NONE = 0
    AES_256_GCM = 1
    AES_256_CTR = 2
    CHACHA20_POLY1305 = 3
    KYBER_AES_HYBRID = 4
    KYBER_CHACHA_HYBRID = 5
    DOUBLE_LAYER = 6


class QanionSignatureMode(IntEnum):
    """Modos de firma digital."""
    NONE = 0
    FALCON_512 = 1
    FALCON_1024 = 2
    ED25519 = 3
    HMAC_SHA256 = 4
    HMAC_SHA512 = 5


class QanionCompressionMode(IntEnum):
    """Modos de compresión."""
    NONE = 0
    ZLIB = 1
    LZ4 = 2
    ZSTD = 3
    SNAPPY = 4


class QanionKeyState(IntEnum):
    """Estados de las claves."""
    INITIALIZING = 0
    ACTIVE = 1
    ROTATING = 2
    EXPIRING = 3
    EXPIRED = 4
    REVOKED = 5
    COMPROMISED = 6


class QanionLogLevel(IntEnum):
    """Niveles de log."""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    SECURITY = 60


class QanionConnectionState(IntEnum):
    """Estados de conexión."""
    DISCONNECTED = 0
    CONNECTING = 1
    HANDSHAKING = 2
    AUTHENTICATING = 3
    ESTABLISHED = 4
    SUSPENDED = 5
    REKEYING = 6
    DISCONNECTING = 7
    ERROR = 8


class QanionPriority(IntEnum):
    """Prioridades de paquete."""
    LOWEST = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3
    HIGHEST = 4
    CRITICAL = 5
    EMERGENCY = 6


# QANION CONFIG

@dataclass
class QanionCryptoConfig:
    """Configuración criptográfica."""
    encryption_mode: QanionEncryptionMode = QanionEncryptionMode.AES_256_GCM
    signature_mode: QanionSignatureMode = QanionSignatureMode.FALCON_512
    compression_mode: QanionCompressionMode = QanionCompressionMode.NONE
    kyber_level: int = 768  # 512, 768, 1024
    falcon_level: int = 512  # 512, 1024
    enable_pfs: bool = True  # Perfect Forward Secrecy
    enable_key_pinning: bool = True
    min_key_length: int = 256
    hash_algorithm: str = "SHA3-256"
    kdf_algorithm: str = "HKDF-SHA256"
    enable_double_ratchet: bool = False
    enable_quantum_resistance: bool = True


@dataclass
class QanionKeyRotationConfig:
    """Configuración de rotación de claves."""
    enabled: bool = True
    rotation_interval: float = QanionConstants.DEFAULT_KEY_ROTATION_INTERVAL
    max_key_age: float = QanionConstants.MAX_KEY_AGE
    max_operations: int = QanionConstants.DEFAULT_KEY_ROTATION_COUNT
    pre_generate_keys: bool = True
    pre_generate_count: int = 3
    notify_before_expiry: float = 300.0  # 5 minutos
    force_rotation_on_compromise: bool = True
    key_history_size: int = 10
    rotation_strategy: str = "time_based"  # time_based, count_based, hybrid


@dataclass
class QanionNetworkConfig:
    """Configuración de red."""
    host: str = "0.0.0.0"
    port: int = 8443
    bind_address: Optional[str] = None
    multicast_group: Optional[str] = None
    multicast_port: int = 8444
    max_connections: int = 1000
    max_packet_size: int = QanionConstants.MAX_PACKET_SIZE
    buffer_size: int = QanionConstants.DEFAULT_BUFFER_SIZE
    timeout: float = QanionConstants.DEFAULT_TIMEOUT
    handshake_timeout: float = QanionConstants.HANDSHAKE_TIMEOUT
    keepalive_interval: float = 30.0
    keepalive_probes: int = 3
    tcp_no_delay: bool = True
    reuse_address: bool = True
    reuse_port: bool = False
    enable_ipv6: bool = True
    enable_multicast: bool = False
    enable_broadcast: bool = False
    mtu: int = 1500
    enable_fragmentation: bool = True
    fragment_size: int = 1400
    max_fragments: int = 100
    enable_compression: bool = False
    compression_threshold: int = 1024


@dataclass
class QanionSecurityConfig:
    """Configuración de seguridad."""
    enable_authentication: bool = True
    enable_authorization: bool = True
    enable_rate_limiting: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: float = 60.0
    enable_ip_whitelist: bool = False
    ip_whitelist: List[str] = field(default_factory=list)
    enable_ip_blacklist: bool = True
    ip_blacklist: List[str] = field(default_factory=list)
    max_failed_attempts: int = 5
    lockout_duration: float = 300.0
    enable_replay_protection: bool = True
    replay_window_size: int = 1024
    replay_window_time: float = 60.0
    enable_certificate_pinning: bool = False
    trusted_certificates: List[str] = field(default_factory=list)
    require_client_cert: bool = False
    min_tls_version: str = "TLSv1.3"
    enable_hsm: bool = False
    hsm_config: Optional[Dict[str, Any]] = None


@dataclass
class QanionLoggingConfig:
    """Configuración de logging."""
    log_level: QanionLogLevel = QanionLogLevel.INFO
    log_to_file: bool = True
    log_to_console: bool = True
    log_to_syslog: bool = False
    log_file_path: str = "./logs/qanion.log"
    log_max_size: int = QanionConstants.LOG_MAX_SIZE
    log_backup_count: int = QanionConstants.LOG_BACKUP_COUNT
    log_format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    log_date_format: str = "%Y-%m-%d %H:%M:%S.%f"
    enable_json_logging: bool = False
    enable_security_audit: bool = True
    security_log_path: str = "./logs/qanion_security.log"
    enable_performance_logging: bool = False
    performance_log_path: str = "./logs/qanion_perf.log"
    log_sensitive_data: bool = False
    mask_patterns: List[str] = field(default_factory=lambda: [
        r'key[=:]\s*\S+',
        r'password[=:]\s*\S+',
        r'token[=:]\s*\S+',
        r'secret[=:]\s*\S+',
    ])


@dataclass
class QanionPerformanceConfig:
    """Configuración de rendimiento."""
    enable_connection_pooling: bool = True
    connection_pool_size: int = 100
    enable_async_io: bool = True
    worker_threads: int = 4
    io_threads: int = 2
    enable_batching: bool = True
    batch_size: int = 100
    batch_timeout: float = 0.1
    enable_caching: bool = True
    cache_size: int = 10000
    cache_ttl: float = 300.0
    enable_metrics: bool = True
    metrics_interval: float = 60.0
    enable_profiling: bool = False
    max_queue_size: int = 10000
    queue_overflow_strategy: str = "drop_oldest"  # drop_oldest, drop_newest, block


@dataclass
class QanionNodeConfig:
    """Configuración del nodo."""
    node_id: str = field(default_factory=lambda: secrets.token_hex(16))
    node_name: str = "qanion-node"
    node_role: str = "peer"  # peer, relay, gateway, bootstrap
    capabilities: List[str] = field(default_factory=lambda: ["data", "relay"])
    metadata: Dict[str, Any] = field(default_factory=dict)
    enable_discovery: bool = True
    discovery_interval: float = 60.0
    bootstrap_nodes: List[str] = field(default_factory=list)
    enable_nat_traversal: bool = True
    stun_servers: List[str] = field(default_factory=lambda: [
        "stun.l.google.com:19302",
        "stun1.l.google.com:19302"
    ])


@dataclass
class QanionConfig:
    """Configuración principal de QANION."""
    
    # Identidad
    node: QanionNodeConfig = field(default_factory=QanionNodeConfig)
    
    # Sub-configuraciones
    crypto: QanionCryptoConfig = field(default_factory=QanionCryptoConfig)
    key_rotation: QanionKeyRotationConfig = field(default_factory=QanionKeyRotationConfig)
    network: QanionNetworkConfig = field(default_factory=QanionNetworkConfig)
    security: QanionSecurityConfig = field(default_factory=QanionSecurityConfig)
    logging: QanionLoggingConfig = field(default_factory=QanionLoggingConfig)
    performance: QanionPerformanceConfig = field(default_factory=QanionPerformanceConfig)
    
    # Metadatos
    config_version: str = "1.0.0"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    # Personalización
    custom_options: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Valida la configuración completa."""
        errors = []
        
        # Validar red
        if not 1 <= self.network.port <= 65535:
            errors.append(f"Puerto inválido: {self.network.port}")
        if self.network.max_connections < 1:
            errors.append("max_connections debe ser >= 1")
        if self.network.max_packet_size < QanionConstants.MIN_PACKET_SIZE:
            errors.append("max_packet_size demasiado pequeño")
        if self.network.mtu < 576:
            errors.append("MTU mínimo recomendado: 576")
        
        # Validar crypto
        if self.crypto.kyber_level not in (512, 768, 1024):
            errors.append(f"Nivel Kyber inválido: {self.crypto.kyber_level}")
        if self.crypto.falcon_level not in (512, 1024):
            errors.append(f"Nivel Falcon inválido: {self.crypto.falcon_level}")
        
        # Validar key rotation
        if self.key_rotation.rotation_interval < 60:
            errors.append("Intervalo de rotación mínimo: 60s")
        if self.key_rotation.max_key_age < self.key_rotation.rotation_interval:
            errors.append("max_key_age debe ser >= rotation_interval")
        
        # Validar seguridad
        if self.security.rate_limit_requests < 1:
            errors.append("rate_limit_requests debe ser >= 1")
        
        # Validar logging
        if self.logging.log_to_file:
            log_dir = Path(self.logging.log_file_path).parent
            if not log_dir.exists():
                try:
                    log_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    errors.append(f"No se puede crear directorio de logs: {e}")
        
        return len(errors) == 0, errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la configuración a diccionario."""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Convierte la configuración a JSON."""
        def _serialize(obj):
            if isinstance(obj, IntEnum):
                return obj.value
            if isinstance(obj, bytes):
                return obj.hex()
            return obj
        
        return json.dumps(self.to_dict(), default=_serialize, indent=indent)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QanionConfig':
        """Crea configuración desde diccionario."""
        config = cls()
        
        if 'node' in data:
            config.node = QanionNodeConfig(**data['node'])
        if 'crypto' in data:
            config.crypto = QanionCryptoConfig(**data['crypto'])
        if 'key_rotation' in data:
            config.key_rotation = QanionKeyRotationConfig(**data['key_rotation'])
        if 'network' in data:
            config.network = QanionNetworkConfig(**data['network'])
        if 'security' in data:
            config.security = QanionSecurityConfig(**data['security'])
        if 'logging' in data:
            config.logging = QanionLoggingConfig(**data['logging'])
        if 'performance' in data:
            config.performance = QanionPerformanceConfig(**data['performance'])
        
        for key in ('config_version', 'created_at', 'updated_at', 'custom_options'):
            if key in data:
                setattr(config, key, data[key])
        
        return config
    
    @classmethod
    def from_json(cls, json_str: str) -> 'QanionConfig':
        """Crea configuración desde JSON."""
        return cls.from_dict(json.loads(json_str))
    
    @classmethod
    def from_file(cls, filepath: Union[str, Path]) -> 'QanionConfig':
        """Carga configuración desde archivo."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Archivo de configuración no encontrado: {filepath}")
        
        with open(path, 'r') as f:
            if path.suffix == '.json':
                return cls.from_json(f.read())
            elif path.suffix in ('.yaml', '.yml'):
                import yaml
                return cls.from_dict(yaml.safe_load(f.read()))
            else:
                raise ValueError(f"Formato no soportado: {path.suffix}")
    
    def save(self, filepath: Union[str, Path]) -> None:
        """Guarda configuración a archivo."""
        self.updated_at = time.time()
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            if path.suffix == '.json':
                f.write(self.to_json())
            elif path.suffix in ('.yaml', '.yml'):
                import yaml
                yaml.dump(self.to_dict(), f, default_flow_style=False)
            else:
                raise ValueError(f"Formato no soportado: {path.suffix}")
    
    def merge(self, other: 'QanionConfig') -> 'QanionConfig':
        """Fusiona otra configuración."""
        merged = copy.deepcopy(self)
        other_dict = other.to_dict()
        
        def _deep_merge(base: dict, override: dict) -> dict:
            result = base.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = _deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        merged_dict = _deep_merge(merged.to_dict(), other_dict)
        return self.from_dict(merged_dict)
    
    def get_encryption_key_size(self) -> int:
        """Obtiene tamaño de clave de encriptación según modo."""
        sizes = {
            QanionEncryptionMode.AES_256_GCM: 32,
            QanionEncryptionMode.AES_256_CTR: 32,
            QanionEncryptionMode.CHACHA20_POLY1305: 32,
            QanionEncryptionMode.KYBER_AES_HYBRID: 32,
            QanionEncryptionMode.KYBER_CHACHA_HYBRID: 32,
            QanionEncryptionMode.DOUBLE_LAYER: 64,
        }
        return sizes.get(self.crypto.encryption_mode, 32)
    
    def get_kyber_params(self) -> Dict[str, int]:
        """Obtiene parámetros Kyber según nivel."""
        params = {
            512: {
                'pk': QanionConstants.KYBER_512_PK,
                'sk': QanionConstants.KYBER_512_SK,
                'ct': QanionConstants.KYBER_512_CT,
                'ss': 32
            },
            768: {
                'pk': QanionConstants.KYBER_768_PK,
                'sk': QanionConstants.KYBER_768_SK,
                'ct': QanionConstants.KYBER_768_CT,
                'ss': 32
            },
            1024: {
                'pk': QanionConstants.KYBER_1024_PK,
                'sk': QanionConstants.KYBER_1024_SK,
                'ct': QanionConstants.KYBER_1024_CT,
                'ss': 32
            }
        }
        return params[self.crypto.kyber_level]
    
    def get_falcon_params(self) -> Dict[str, int]:
        """Obtiene parámetros Falcon según nivel."""
        params = {
            512: {
                'pk': QanionConstants.FALCON_512_PK,
                'sk': QanionConstants.FALCON_512_SK,
                'sig': QanionConstants.FALCON_512_SIG
            },
            1024: {
                'pk': QanionConstants.FALCON_1024_PK,
                'sk': QanionConstants.FALCON_1024_SK,
                'sig': QanionConstants.FALCON_1024_SIG
            }
        }
        return params[self.crypto.falcon_level]


# QANION LOGGER

class QanionSecurityFilter(logging.Filter):
    """Filtro para enmascarar datos sensibles en logs."""
    
    def __init__(self, patterns: List[str]):
        super().__init__()
        import re
        self.patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
    
    def filter(self, record: logging.LogRecord) -> bool:
        if hasattr(record, 'msg'):
            msg = str(record.msg)
            for pattern in self.patterns:
                msg = pattern.sub(lambda m: m.group().split('=')[0].split(':')[0] + '=***MASKED***', msg)
            record.msg = msg
        return True


class QanionJSONFormatter(logging.Formatter):
    """Formateador JSON para logs estructurados."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'thread_name': record.threadName,
            'process': record.process,
        }
        
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        if hasattr(record, 'extra_data'):
            log_entry['extra'] = record.extra_data
        
        return json.dumps(log_entry, default=str)


class QanionSecurityFormatter(logging.Formatter):
    """Formateador para logs de seguridad."""
    
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        level = record.levelname
        event_type = getattr(record, 'event_type', 'UNKNOWN')
        source = getattr(record, 'source', record.name)
        message = record.getMessage()
        
        return f"[{timestamp}] [{level}] [{event_type}] [{source}] {message}"


class QanionLogBuffer:
    """Buffer circular para logs recientes."""
    
    def __init__(self, max_size: int = 1000):
        self._buffer: deque = deque(maxlen=max_size)
        self._lock = threading.RLock()
    
    def add(self, record: logging.LogRecord) -> None:
        with self._lock:
            self._buffer.append({
                'timestamp': record.created,
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno,
            })
    
    def get_recent(self, count: int = 100, level: Optional[str] = None) -> List[Dict]:
        with self._lock:
            entries = list(self._buffer)
            if level:
                entries = [e for e in entries if e['level'] == level]
            return entries[-count:]
    
    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()
    
    def size(self) -> int:
        with self._lock:
            return len(self._buffer)


class QanionBufferHandler(logging.Handler):
    """Handler que almacena logs en buffer circular."""
    
    def __init__(self, buffer: QanionLogBuffer):
        super().__init__()
        self.buffer = buffer
    
    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.buffer.add(record)
        except Exception:
            self.handleError(record)


class QanionMetricsCollector:
    """Recolector de métricas de logging."""
    
    def __init__(self):
        self._lock = threading.RLock()
        self._counters: Dict[str, int] = {
            'TRACE': 0, 'DEBUG': 0, 'INFO': 0,
            'WARNING': 0, 'ERROR': 0, 'CRITICAL': 0, 'SECURITY': 0
        }
        self._rate_windows: Dict[str, deque] = {
            level: deque(maxlen=1000) for level in self._counters
        }
        self._start_time = time.time()
    
    def record(self, level: str) -> None:
        with self._lock:
            if level in self._counters:
                self._counters[level] += 1
                self._rate_windows[level].append(time.time())
    
    def get_counts(self) -> Dict[str, int]:
        with self._lock:
            return self._counters.copy()
    
    def get_rate(self, level: str, window: float = 60.0) -> float:
        with self._lock:
            if level not in self._rate_windows:
                return 0.0
            now = time.time()
            cutoff = now - window
            count = sum(1 for t in self._rate_windows[level] if t > cutoff)
            return count / window
    
    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            total = sum(self._counters.values())
            uptime = time.time() - self._start_time
            return {
                'total_logs': total,
                'counts': self._counters.copy(),
                'uptime_seconds': uptime,
                'logs_per_second': total / uptime if uptime > 0 else 0,
                'error_rate': (
                    (self._counters['ERROR'] + self._counters['CRITICAL']) / total 
                    if total > 0 else 0
                )
            }
    
    def reset(self) -> None:
        with self._lock:
            for key in self._counters:
                self._counters[key] = 0
                self._rate_windows[key].clear()
            self._start_time = time.time()


class QanionMetricsHandler(logging.Handler):
    """Handler que recolecta métricas."""
    
    def __init__(self, collector: QanionMetricsCollector):
        super().__init__()
        self.collector = collector
    
    def emit(self, record: logging.LogRecord) -> None:
        self.collector.record(record.levelname)


class QanionLogger:
    """
    Sistema de logging avanzado para QANION.
    
    Características:
    - Múltiples destinos (archivo, consola, syslog)
    - Formato JSON estructurado
    - Buffer circular para logs recientes
    - Métricas de logging
    - Filtros de seguridad para datos sensibles
    - Logs de auditoría de seguridad
    - Logs de rendimiento
    - Rotación automática de archivos
    """
    
    _instances: Dict[str, 'QanionLogger'] = {}
    _lock = threading.RLock()
    _SECURITY_LEVEL = 60
    
    def __new__(cls, name: str = "qanion", config: Optional[QanionLoggingConfig] = None):
        with cls._lock:
            if name not in cls._instances:
                instance = super().__new__(cls)
                instance._initialized = False
                cls._instances[name] = instance
            return cls._instances[name]
    
    def __init__(self, name: str = "qanion", config: Optional[QanionLoggingConfig] = None):
        if self._initialized:
            return
        
        self._name = name
        self._config = config or QanionLoggingConfig()
        self._lock = threading.RLock()
        
        # Registrar nivel SECURITY
        logging.addLevelName(self._SECURITY_LEVEL, "SECURITY")
        
        # Logger principal
        self._logger = logging.getLogger(name)
        self._logger.setLevel(self._config.log_level.value)
        
        # Logger de seguridad
        self._security_logger = logging.getLogger(f"{name}.security")
        self._security_logger.setLevel(logging.DEBUG)
        
        # Logger de rendimiento
        self._perf_logger = logging.getLogger(f"{name}.performance")
        self._perf_logger.setLevel(logging.DEBUG)
        
        # Buffer circular
        self._buffer = QanionLogBuffer(max_size=10000)
        
        # Métricas
        self._metrics = QanionMetricsCollector()
        
        # Configurar handlers
        self._setup_handlers()
        
        # Filtro de seguridad
        if not self._config.log_sensitive_data:
            self._security_filter = QanionSecurityFilter(self._config.mask_patterns)
            self._logger.addFilter(self._security_filter)
        
        self._initialized = True
    
    def _setup_handlers(self) -> None:
        """Configura handlers de logging."""
        # Buffer handler
        buffer_handler = QanionBufferHandler(self._buffer)
        self._logger.addHandler(buffer_handler)

        # Metrics handler
        metrics_handler = QanionMetricsHandler(self._metrics)
        self._logger.addHandler(metrics_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(QanionJSONFormatter())
        self._logger.addHandler(console_handler)


# ============================================
# 1. QanionRouting COMPLETA
# ============================================

class QuantumState(Enum):
    SUPERPOSITION = auto()
    COLLAPSED = auto()
    ENTANGLED = auto()
    DECOHERENT = auto()

@dataclass
class QuantumPath:
    path_id: str
    nodes: List[str]
    probability_amplitude: complex
    phase: float = 0.0
    entangled_with: Optional[str] = None
    last_measurement: float = 0.0
    coherence_time: float = 1.0
    
    def measure(self) -> float:
        """Colapsa la superposición a un valor clásico"""
        probability = abs(self.probability_amplitude) ** 2
        self.probability_amplitude = complex(probability, 0)
        self.last_measurement = time.time()
        return probability
    
    def apply_decoherence(self, delta_t: float):
        """Aplica decoherencia cuántica"""
        decoherence_factor = np.exp(-delta_t / self.coherence_time)
        self.probability_amplitude *= decoherence_factor
        if abs(self.probability_amplitude) < 0.01:
            self.probability_amplitude = complex(0, 0)

class QuantumRouter:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.path_registry: Dict[str, QuantumPath] = {}
        self.entanglement_pairs: Dict[str, Tuple[str, str]] = {}
        self.superposition_cache: Dict[str, List[QuantumPath]] = {}
        self.routing_table: Dict[str, List[Tuple[str, float]]] = {}
        self.measurement_history: deque = deque(maxlen=1000)
        self.executor = ThreadPoolExecutor(max_workers=8)
        
    def create_superposition_paths(self, destination: str, num_paths: int = 3) -> List[QuantumPath]:
        """Crea múltiples caminos en superposición"""
        paths = []
        for i in range(num_paths):
            path_id = f"{self.node_id}->{destination}_path_{i}_{hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]}"
            
            # Generar amplitud de probabilidad compleja
            amplitude = complex(
                random.gauss(0.7, 0.2),
                random.gauss(0.0, 0.1)
            )
            # Normalizar
            norm = abs(amplitude)
            if norm > 0:
                amplitude /= norm
            
            path = QuantumPath(
                path_id=path_id,
                nodes=[self.node_id, f"relay_{i}", destination],
                probability_amplitude=amplitude,
                phase=random.uniform(0, 2 * np.pi),
                coherence_time=random.uniform(0.5, 2.0)
            )
            paths.append(path)
            self.path_registry[path_id] = path
        
        self.superposition_cache[destination] = paths
        return paths
    
    def create_entanglement(self, path1_id: str, path2_id: str):
        """Crea entrelazamiento cuántico entre dos caminos"""
        if path1_id in self.path_registry and path2_id in self.path_registry:
            entanglement_id = hashlib.sha256(f"{path1_id}:{path2_id}".encode()).hexdigest()[:16]
            self.entanglement_pairs[entanglement_id] = (path1_id, path2_id)
            
            # Establecer relación de entrelazamiento
            self.path_registry[path1_id].entangled_with = entanglement_id
            self.path_registry[path2_id].entangled_with = entanglement_id
            
            # Correlacionar amplitudes
            p1 = self.path_registry[path1_id]
            p2 = self.path_registry[path2_id]
            
            # Aplicar transformación de entrelazamiento
            combined_amplitude = (p1.probability_amplitude + p2.probability_amplitude) / np.sqrt(2)
            p1.probability_amplitude = combined_amplitude
            p2.probability_amplitude = combined_amplitude.conjugate()
    
    def quantum_routing_decision(self, destination: str, packet_hash: str) -> QuantumPath:
        """Toma decisión de routing usando interferencia cuántica"""
        if destination not in self.superposition_cache:
            self.create_superposition_paths(destination)
        
        paths = self.superposition_cache[destination]
        
        # Aplicar interferencia basada en hash del paquete
        interference_factors = []
        for i, path in enumerate(paths):
            # Factor de interferencia determinístico pero pseudo-aleatorio
            seed = int(packet_hash[:8], 16) + i
            random.seed(seed)
            interference = complex(
                np.cos(random.uniform(0, 2 * np.pi)),
                np.sin(random.uniform(0, 2 * np.pi))
            )
            interference_factors.append(interference)
        
        # Calcular amplitudes resultantes después de interferencia
        final_amplitudes = []
        for i, path in enumerate(paths):
            interfered = path.probability_amplitude * interference_factors[i]
            final_amplitudes.append(interfered)
        
        # Normalizar probabilidades
        probabilities = [abs(amp) ** 2 for amp in final_amplitudes]
        total_prob = sum(probabilities)
        
        if total_prob > 0:
            probabilities = [p / total_prob for p in probabilities]
        else:
            # Fallback: distribución uniforme
            probabilities = [1.0 / len(paths)] * len(paths)
        
        # Selección probabilística
        selected_idx = random.choices(range(len(paths)), weights=probabilities)[0]
        selected_path = paths[selected_idx]
        
        # Registrar medición
        self.measurement_history.append({
            'timestamp': time.time(),
            'destination': destination,
            'packet_hash': packet_hash,
            'selected_path': selected_path.path_id,
            'probabilities': probabilities,
            'interference_factors': [abs(f) for f in interference_factors]
        })
        
        # Aplicar decoherencia a los caminos no seleccionados
        for i, path in enumerate(paths):
            if i != selected_idx:
                path.apply_decoherence(0.1)
        
        return selected_path
    
    def quantum_walk_routing(self, current_node: str, target_node: str, steps: int = 10) -> List[str]:
        """Implementa un quantum walk para routing adaptativo"""
        path = [current_node]
        current = current_node
        
        for step in range(steps):
            if current == target_node:
                break
            
            # Obtener vecinos (simulado)
            neighbors = self._get_neighbors(current)
            if not neighbors:
                break
            
            # Crear superposición de estados de vecinos
            amplitudes = []
            for neighbor in neighbors:
                # Amplitud basada en distancia heurística
                distance = self._heuristic_distance(neighbor, target_node)
                amplitude = complex(1.0 / (distance + 1), 0)
                amplitudes.append(amplitude)
            
            # Normalizar
            norm = np.sqrt(sum(abs(a) ** 2 for a in amplitudes))
            if norm > 0:
                amplitudes = [a / norm for a in amplitudes]
            
            # Medir (colapsar) al siguiente nodo
            probabilities = [abs(a) ** 2 for a in amplitudes]
            next_node = random.choices(neighbors, weights=probabilities)[0]
            
            path.append(next_node)
            current = next_node
        
        return path
    
    def _get_neighbors(self, node: str) -> List[str]:
        """Obtiene nodos vecinos (implementación simulada)"""
        # En implementación real, esto consultaría la topología de red
        return [f"node_{i}" for i in range(random.randint(1, 5))]
    
    def _heuristic_distance(self, node1: str, node2: str) -> float:
        """Heurística de distancia (simulada)"""
        # En implementación real, usaría métricas de red reales
        return random.uniform(1, 10)

class QanionRouting:
    """Sistema completo de routing cuántico-inspirado"""
    
    def __init__(self, network_topology: Dict[str, List[str]]):
        self.topology = network_topology
        self.routers: Dict[str, QuantumRouter] = {}
        self.global_entanglement_graph: Dict[str, List[str]] = {}
        self.path_optimization_history: List[Dict] = []
        self.executor = ThreadPoolExecutor(max_workers=16)
        
        # Inicializar routers para cada nodo
        for node in network_topology.keys():
            self.routers[node] = QuantumRouter(node)
    
    def establish_entanglement_network(self, entanglement_density: float = 0.3):
        """Establece una red de entrelazamiento cuántico"""
        nodes = list(self.routers.keys())
        
        for i, node1 in enumerate(nodes):
            for j, node2 in enumerate(nodes[i+1:], i+1):
                if random.random() < entanglement_density:
                    # Crear entrelazamiento entre routers
                    path1_id = f"{node1}_to_{node2}_ent"
                    path2_id = f"{node2}_to_{node1}_ent"
                    
                    # Registrar en grafo global
                    if node1 not in self.global_entanglement_graph:
                        self.global_entanglement_graph[node1] = []
                    if node2 not in self.global_entanglement_graph:
                        self.global_entanglement_graph[node2] = []
                    
                    self.global_entanglement_graph[node1].append(node2)
                    self.global_entanglement_graph[node2].append(node1)
    
    def route_packet(self, source: str, destination: str, packet_data: bytes) -> Dict[str, Any]:
        """Enruta un paquete usando el sistema QANION"""
        packet_hash = hashlib.sha256(packet_data).hexdigest()
        
        # Obtener router de origen
        if source not in self.routers:
            raise ValueError(f"Nodo fuente {source} no encontrado")
        
        router = self.routers[source]
        
        # Decisión de routing cuántico
        selected_path = router.quantum_routing_decision(destination, packet_hash)
        
        # Verificar si hay entrelazamiento que afecte la decisión
        if selected_path.entangled_with:
            entanglement_id = selected_path.entangled_with
            if entanglement_id in router.entanglement_pairs:
                path1_id, path2_id = router.entanglement_pairs[entanglement_id]
                
                # Efecto de entrelazamiento: correlacionar decisiones
                if path1_id == selected_path.path_id:
                    correlated_path = router.path_registry.get(path2_id)
                else:
                    correlated_path = router.path_registry.get(path1_id)
                
                if correlated_path:
                    # Aplicar efecto de entrelazamiento
                    correlated_path.probability_amplitude = selected_path.probability_amplitude.conjugate()
        
        # Preparar resultado
        routing_result = {
            'source': source,
            'destination': destination,
            'selected_path': selected_path.path_id,
            'route_nodes': selected_path.nodes,
            'probability_amplitude': {
                'real': selected_path.probability_amplitude.real,
                'imag': selected_path.probability_amplitude.imag
            },
            'phase': selected_path.phase,
            'packet_hash': packet_hash,
            'timestamp': time.time(),
            'quantum_state': 'SUPERPOSITION' if abs(selected_path.probability_amplitude) < 1.0 else 'COLLAPSED'
        }
        
        # Registrar para optimización
        self.path_optimization_history.append(routing_result)
        
        return routing_result
    
    def adaptive_path_optimization(self, performance_metrics: Dict[str, float]):
        """Optimiza rutas basado en métricas de rendimiento"""
        for node, router in self.routers.items():
            for path_id, path in router.path_registry.items():
                # Ajustar amplitudes basado en rendimiento
                if path_id in performance_metrics:
                    latency = performance_metrics[path_id]
                    # Factor de ajuste: menor latencia = mayor amplitude
                    adjustment_factor = 1.0 / (latency + 0.1)
                    
                    # Aplicar ajuste manteniendo fase
                    current_amplitude = path.probability_amplitude
                    magnitude = abs(current_amplitude) * adjustment_factor
                    phase = np.angle(current_amplitude)
                    
                    # Reconstruir amplitud compleja
                    new_amplitude = complex(
                        magnitude * np.cos(phase),
                        magnitude * np.sin(phase)
                    )
                    
                    # Normalizar
                    norm = abs(new_amplitude)
                    if norm > 0:
                        path.probability_amplitude = new_amplitude / norm
    
    def get_routing_analytics(self) -> Dict[str, Any]:
        """Obtiene analíticas del sistema de routing"""
        analytics = {
            'total_routers': len(self.routers),
            'total_paths': sum(len(router.path_registry) for router in self.routers.values()),
            'entanglement_pairs': sum(len(router.entanglement_pairs) for router in self.routers.values()),
            'measurement_count': sum(len(router.measurement_history) for router in self.routers.values()),
            'global_entanglement_nodes': len(self.global_entanglement_graph),
            'recent_measurements': []
        }
        
        # Agregar mediciones recientes
        for router in self.routers.values():
            if router.measurement_history:
                analytics['recent_measurements'].extend(list(router.measurement_history)[-5:])
        
        return analytics

# ============================================
# 2. PolymorphicObfuscation
# ============================================

class ObfuscationTechnique(Enum):
    DECOY_TRAFFIC = auto()
    TIMING_JITTER = auto()
    PACKET_PADDING = auto()
    HEADER_MORPHING = auto()
    PROTOCOL_SWITCHING = auto()
    BURST_INJECTION = auto()

@dataclass
class DecoyProfile:
    profile_id: str
    traffic_pattern: str  # 'constant', 'bursty', 'random', 'mimicry'
    packet_size_range: Tuple[int, int]
    interval_range: Tuple[float, float]
    protocol_mimicry: Optional[str] = None
    priority: int = 1
    active: bool = True
    created_at: float = field(default_factory=time.time)
    
    def generate_decoy_packet(self) -> Dict[str, Any]:
        """Genera un paquete señuelo basado en el perfil"""
        packet_size = random.randint(*self.packet_size_range)
        
        # Generar datos aleatorios que parezcan tráfico real
        if self.protocol_mimicry == "HTTP":
            payload = self._generate_http_like_payload(packet_size)
        elif self.protocol_mimicry == "DNS":
            payload = self._generate_dns_like_payload(packet_size)
        else:
            payload = self._generate_random_payload(packet_size)
        
        return {
            'type': 'decoy',
            'profile_id': self.profile_id,
            'size': packet_size,
            'payload': payload,
            'timestamp': time.time(),
            'protocol_mimicry': self.protocol_mimicry
        }
    
    def _generate_http_like_payload(self, size: int) -> bytes:
        """Genera payload similar a HTTP"""
        methods = ['GET', 'POST', 'PUT', 'DELETE']
        paths = ['/api/v1/data', '/index.html', '/images/logo.png', '/css/style.css']
        
        http_template = f"{random.choice(methods)} {random.choice(paths)} HTTP/1.1\r\n"
        http_template += f"Host: example{random.randint(1, 100)}.com\r\n"
        http_template += f"User-Agent: Mozilla/5.0 (Obfuscated)\r\n"
        http_template += f"Content-Length: {max(0, size - len(http_template))}\r\n\r\n"
        
        # Rellenar hasta el tamaño deseado
        padding_needed = size - len(http_template)
        if padding_needed > 0:
            http_template += ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=padding_needed))
        
        return http_template.encode()[:size]
    
    def _generate_dns_like_payload(self, size: int) -> bytes:
        """Genera payload similar a DNS"""
        # Simplificado para ejemplo
        domains = ['example.com', 'test.org', 'sample.net', 'demo.io']
        query_types = ['A', 'AAAA', 'MX', 'TXT', 'CNAME']
        
        dns_data = {
            'transaction_id': random.randint(0, 65535),
            'domain': random.choice(domains),
            'type': random.choice(query_types),
            'padding': ''.join(random.choices('0123456789abcdef', k=size-50))
        }
        
        return json.dumps(dns_data).encode()[:size]
    
    def _generate_random_payload(self, size: int) -> bytes:
        """Genera payload aleatorio"""
        return bytes(random.getrandbits(8) for _ in range(size))

class JitterController:
    """Controlador de jitter aleatorio para timing obfuscation"""
    
    def __init__(self, base_interval: float = 0.1, jitter_range: float = 0.05):
        self.base_interval = base_interval
        self.jitter_range = jitter_range
        self.jitter_distribution = 'gaussian'  # 'gaussian', 'uniform', 'exponential'
        self.last_packet_time = 0.0
        self.jitter_history: deque = deque(maxlen=1000)
        
    def calculate_next_send_time(self) -> float:
        """Calcula el próximo tiempo de envío con jitter"""
        current_time = time.time()
        
        # Calcular jitter según distribución
        if self.jitter_distribution == 'gaussian':
            jitter = random.gauss(0, self.jitter_range)
        elif self.jitter_distribution == 'uniform':
            jitter = random.uniform(-self.jitter_range, self.jitter_range)
        elif self.jitter_distribution == 'exponential':
            jitter = random.expovariate(1.0 / self.jitter_range)
        else:
            jitter = 0.0
        
        # Aplicar jitter al intervalo base
        interval = self.base_interval + jitter
        
        # Asegurar intervalo mínimo
        interval = max(0.001, interval)
        
        # Calcular próximo tiempo
        next_time = current_time + interval
        
        # Registrar para análisis
        self.jitter_history.append({
            'timestamp': current_time,
            'interval': interval,
            'jitter': jitter,
            'distribution': self.jitter_distribution
        })
        
        self.last_packet_time = next_time
        return next_time
    
    def adaptive_jitter(self, network_conditions: Dict[str, float]):
        """Ajusta jitter basado en condiciones de red"""
        latency = network_conditions.get('latency', 0.1)
        packet_loss = network_conditions.get('packet_loss', 0.0)
        
        # Aumentar jitter en condiciones de red malas
        if latency > 0.5 or packet_loss > 0.1:
            self.jitter_range *= 1.5
            self.jitter_distribution = 'exponential'
        else:
            self.jitter_range *= 0.9
            self.jitter_distribution = 'gaussian'
        
        # Limitar rango de jitter
        self.jitter_range = max(0.01, min(1.0, self.jitter_range))

class PolymorphicObfuscation:
    """Sistema completo de obfuscation polimórfica"""
    
    def __init__(self):
        self.decoy_profiles: Dict[str, DecoyProfile] = {}
        self.active_techniques: List[ObfuscationTechnique] = []
        self.jitter_controller = JitterController()
        self.obfuscation_rules: List[Dict] = []
        self.traffic_morphing_engine = TrafficMorphingEngine()
        self.obfuscation_stats: Dict[str, int] = {
            'decoys_sent': 0,
            'packets_jittered': 0,
            'headers_morphed': 0,
            'protocols_switched': 0
        }
        
        # Inicializar perfiles de señuelo por defecto
        self._initialize_default_profiles()
    
    def _initialize_default_profiles(self):
        """Inicializa perfiles de señuelo por defecto"""
        default_profiles = [
            DecoyProfile(
                profile_id="http_burst",
                traffic_pattern="bursty",
                packet_size_range=(500, 1500),
                interval_range=(0.1, 0.5),
                protocol_mimicry="HTTP",
                priority=2
            ),
            DecoyProfile(
                profile_id="dns_constant",
                traffic_pattern="constant",
                packet_size_range=(50, 200),
                interval_range=(1.0, 5.0),
                protocol_mimicry="DNS",
                priority=1
            ),
            DecoyProfile(
                profile_id="random_noise",
                traffic_pattern="random",
                packet_size_range=(100, 1000),
                interval_range=(0.05, 0.3),
                protocol_mimicry=None,
                priority=3
            )
        ]
        
        for profile in default_profiles:
            self.decoy_profiles[profile.profile_id] = profile
    
    def enable_technique(self, technique: ObfuscationTechnique):
        """Habilita una técnica de obfuscation"""
        if technique not in self.active_techniques:
            self.active_techniques.append(technique)
    
    def disable_technique(self, technique: ObfuscationTechnique):
        """Deshabilita una técnica de obfuscation"""
        if technique in self.active_techniques:
            self.active_techniques.remove(technique)
    
    def generate_decoy_traffic(self, intensity: float = 0.3) -> List[Dict]:
        """Genera tráfico señuelo"""
        decoy_packets = []
        
        for profile in self.decoy_profiles.values():
            if not profile.active:
                continue
            
            # Determinar cuántos paquetes generar basado en intensidad y prioridad
            num_packets = int(intensity * profile.priority * random.uniform(0.5, 1.5))
            
            for _ in range(num_packets):
                decoy = profile.generate_decoy_packet()
                decoy['obfuscation_technique'] = 'DECOY_TRAFFIC'
                decoy_packets.append(decoy)
                self.obfuscation_stats['decoys_sent'] += 1
        
        return decoy_packets
    
    def apply_timing_jitter(self, packet_schedule: List[float]) -> List[float]:
        """Aplica jitter aleatorio a un calendario de paquetes"""
        jittered_schedule = []
        
        for original_time in packet_schedule:
            # Calcular tiempo con jitter
            jittered_time = self.jitter_controller.calculate_next_send_time()
            jittered_schedule.append(jittered_time)
            self.obfuscation_stats['packets_jittered'] += 1
        
        return jittered_schedule
    
    def morph_packet_headers(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        """Morfología los headers del paquete"""
        morphed_packet = packet.copy()
        
        # Técnicas de morphing de headers
        if 'headers' in morphed_packet:
            headers = morphed_packet['headers']
            
            # 1. Reordenar headers
            if random.random() < 0.3:
                header_items = list(headers.items())
                random.shuffle(header_items)
                headers = dict(header_items)
            
            # 2. Agregar headers dummy
            if random.random() < 0.4:
                dummy_headers = {
                    f'X-Dummy-{i}': hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
                    for i in range(random.randint(1, 3))
                }
                headers.update(dummy_headers)
            
            # 3. Modificar valores de headers existentes
            for key in list(headers.keys()):
                if random.random() < 0.2:
                    if isinstance(headers[key], str):
                        # Agregar padding aleatorio
                        headers[key] += f"; padding={random.randint(0, 999)}"
            
            morphed_packet['headers'] = headers
        
        self.obfuscation_stats['headers_morphed'] += 1
        return morphed_packet
    
    def protocol_switching(self, packet: Dict[str, Any], target_protocol: str) -> Dict[str, Any]:
        """Cambia el protocolo del paquete"""
        switched_packet = packet.copy()
        
        # Simular cambio de protocolo
        original_protocol = switched_packet.get('protocol', 'TCP')
        switched_packet['original_protocol'] = original_protocol
        switched_packet['protocol'] = target_protocol
        switched_packet['protocol_switch_marker'] = hashlib.sha256(
            f"{original_protocol}:{target_protocol}".encode()
        ).hexdigest()[:16]
        
        self.obfuscation_stats['protocols_switched'] += 1
        return switched_packet
    
    def burst_injection(self, base_traffic: List[Dict], burst_size: int = 5) -> List[Dict]:
        """Inyecta ráfagas de tráfico"""
        injected_traffic = base_traffic.copy()
        
        # Determinar puntos de inyección aleatorios
        if len(injected_traffic) > 0:
            injection_points = sorted(random.sample(
                range(len(injected_traffic)),
                min(burst_size, len(injected_traffic))
            ))
            
            for point in reversed(injection_points):
                # Crear ráfaga de paquetes señuelo
                burst_packets = self.generate_decoy_traffic(intensity=0.8)
                injected_traffic[point:point] = burst_packets
        
        return injected_traffic
    
    def adaptive_obfuscation(self, network_conditions: Dict[str, Any], threat_level: float):
        """Ajusta técnicas de obfuscation basado en condiciones"""
        # Ajustar jitter
        self.jitter_controller.adaptive_jitter(network_conditions)
        
        # Ajustar perfiles de señuelo basado en nivel de amenaza
        for profile in self.decoy_profiles.values():
            if threat_level > 0.7:
                # Alta amenaza: más tráfico señuelo
                profile.active = True
                profile.priority = min(5, profile.priority + 1)
            elif threat_level < 0.3:
                # Baja amenaza: menos tráfico señuelo
                if profile.priority > 1:
                    profile.priority -= 1
        
        # Habilitar técnicas basado en amenaza
        if threat_level > 0.5:
            self.enable_technique(ObfuscationTechnique.BURST_INJECTION)
            self.enable_technique(ObfuscationTechnique.PROTOCOL_SWITCHING)
        else:
            self.disable_technique(ObfuscationTechnique.BURST_INJECTION)
    
    def get_obfuscation_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de obfuscation"""
        return {
            'stats': self.obfuscation_stats.copy(),
            'active_techniques': [t.name for t in self.active_techniques],
            'active_decoy_profiles': len([p for p in self.decoy_profiles.values() if p.active]),
            'jitter_distribution': self.jitter_controller.jitter_distribution,
            'jitter_range': self.jitter_controller.jitter_range
        }

class TrafficMorphingEngine:
    """Motor de morphing de tráfico para obfuscation avanzada"""
    
    def __init__(self):
        self.morphing_patterns: Dict[str, Callable] = {}
        self.traffic_templates: Dict[str, Dict] = {}
        self._initialize_patterns()
    
    def _initialize_patterns(self):
        """Inicializa patrones de morphing"""
        self.morphing_patterns = {
            'size_normalization': self._normalize_packet_sizes,
            'timing_smoothing': self._smooth_timing_patterns,
            'protocol_masquerading': self._masquerade_protocol,
            'entropy_manipulation': self._manipulate_entropy
        }
    
    def _normalize_packet_sizes(self, packets: List[Dict]) -> List[Dict]:
        """Normaliza tamaños de paquetes"""
        if not packets:
            return packets
        
        # Calcular tamaño objetivo (media móvil)
        sizes = [p.get('size', 0) for p in packets]
        target_size = int(np.mean(sizes[-10:])) if len(sizes) >= 10 else int(np.mean(sizes))
        
        normalized = []
        for packet in packets:
            p = packet.copy()
            current_size = p.get('size', 0)
            
            if current_size < target_size:
                # Agregar padding
                padding_size = target_size - current_size
                if 'payload' in p:
                    p['payload'] += bytes(padding_size)
                p['size'] = target_size
                p['padding_added'] = padding_size
            elif current_size > target_size:
                # Fragmentar (simplificado)
                p['size'] = target_size
                p['fragmented'] = True
            
            normalized.append(p)
        
        return normalized
    
    def _smooth_timing_patterns(self, packets: List[Dict]) -> List[Dict]:
        """Suaviza patrones temporales"""
        if len(packets) < 2:
            return packets
        
        smoothed = []
        for i, packet in enumerate(packets):
            p = packet.copy()
            
            if i > 0:
                # Ajustar timestamp para suavizar
                prev_time = packets[i-1].get('timestamp', time.time())
                current_time = p.get('timestamp', time.time())
                
                # Aplicar suavizado exponencial
                alpha = 0.3
                smoothed_time = alpha * current_time + (1 - alpha) * prev_time
                p['timestamp'] = smoothed_time
                p['timing_smoothed'] = True
            
            smoothed.append(p)
        
        return smoothed
    
    def _masquerade_protocol(self, packet: Dict, target_protocol: str) -> Dict:
        """Enmascara el protocolo del paquete"""
        masqueraded = packet.copy()
        
        # Cambiar indicadores de protocolo
        masqueraded['apparent_protocol'] = target_protocol
        masqueraded['protocol_masqueraded'] = True
        
        # Agregar características del protocolo objetivo
        if target_protocol == 'HTTP':
            masqueraded['http_like'] = True
        elif target_protocol == 'DNS':
            masqueraded['dns_like'] = True
        
        return masqueraded
    
    def _manipulate_entropy(self, payload: bytes, target_entropy: float) -> bytes:
        """Manipula la entropía del payload"""
        if not payload:
            return payload
        
        # Calcular entropía actual
        byte_counts = [0] * 256
        for byte in payload:
            byte_counts[byte] += 1
        
        probabilities = [count / len(payload) for count in byte_counts if count > 0]
        current_entropy = -sum(p * np.log2(p) for p in probabilities)
        
        # Ajustar entropía
        if current_entropy < target_entropy:
            # Aumentar entropía agregando ruido
            noise_size = int(len(payload) * 0.1)
            noise = bytes(random.getrandbits(8) for _ in range(noise_size))
            return payload + noise
        else:
            # Reducir entropía (simplificado)
            return payload

# ============================================
# 3. TrafficProfile
# ============================================

class TrafficPatternType(Enum):
    CONSTANT = auto()
    BURSTY = auto()
    PERIODIC = auto()
    RANDOM = auto()
    MIMICRY = auto()
    ADAPTIVE = auto()

@dataclass
class TrafficSample:
    timestamp: float
    packet_size: int
    direction: str  # 'inbound', 'outbound'
    protocol: str
    source_port: int
    dest_port: int
    flags: List[str] = field(default_factory=list)
    latency: float = 0.0
    jitter: float = 0.0
    packet_loss: float = 0.0
    
    def to_feature_vector(self) -> List[float]:
        """Convierte la muestra a vector de características"""
        return [
            self.timestamp,
            self.packet_size,
            1.0 if self.direction == 'outbound' else 0.0,
            self.source_port / 65535.0,  # Normalizado
            self.dest_port / 65535.0,    # Normalizado
            self.latency,
            self.jitter,
            self.packet_loss,
            len(self.flags) / 10.0  # Normalizado
        ]

@dataclass
class TrafficProfile:
    profile_id: str
    pattern_type: TrafficPatternType
    samples: List[TrafficSample] = field(default_factory=list)
    statistics: Dict[str, float] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    confidence_score: float = 0.0
    anomaly_score: float = 0.0
    
    def add_sample(self, sample: TrafficSample):
        """Añade una muestra de tráfico al perfil"""
        self.samples.append(sample)
        self.last_updated = time.time()
        self._update_statistics()
    
    def _update_statistics(self):
        """Actualiza estadísticas del perfil"""
        if not self.samples:
            return
        
        # Calcular estadísticas básicas
        sizes = [s.packet_size for s in self.samples]
        intervals = []
        
        for i in range(1, len(self.samples)):
            interval = self.samples[i].timestamp - self.samples[i-1].timestamp
            intervals.append(interval)
        
        self.statistics = {
            'mean_packet_size': np.mean(sizes),
            'std_packet_size': np.std(sizes),
            'mean_interval': np.mean(intervals) if intervals else 0.0,
            'std_interval': np.std(intervals) if intervals else 0.0,
            'packet_count': len(self.samples),
            'bytes_total': sum(sizes),
            'duration': self.samples[-1].timestamp - self.samples[0].timestamp if len(self.samples) > 1 else 0.0,
            'inbound_ratio': sum(1 for s in self.samples if s.direction == 'inbound') / len(self.samples),
            'avg_latency': np.mean([s.latency for s in self.samples]),
            'avg_jitter': np.mean([s.jitter for s in self.samples])
        }
        
        # Calcular score de confianza basado en consistencia
        if len(self.samples) > 10:
            size_consistency = 1.0 - min(1.0, self.statistics['std_packet_size'] / self.statistics['mean_packet_size'])
            interval_consistency = 1.0 - min(1.0, self.statistics['std_interval'] / max(0.001, self.statistics['mean_interval']))
            self.confidence_score = (size_consistency + interval_consistency) / 2
    
    def detect_pattern_type(self) -> TrafficPatternType:
        """Detecta automáticamente el tipo de patrón"""
        if len(self.samples) < 5:
            return TrafficPatternType.RANDOM
        
        # Analizar intervalos
        intervals = []
        for i in range(1, len(self.samples)):
            intervals.append(self.samples[i].timestamp - self.samples[i-1].timestamp)
        
        if not intervals:
            return TrafficPatternType.CONSTANT
        
        # Calcular métricas
        interval_cv = np.std(intervals) / np.mean(intervals) if np.mean(intervals) > 0 else float('inf')

        if interval_cv < 0.1:
            return TrafficPatternType.CONSTANT
        elif interval_cv < 0.5:
            return TrafficPatternType.PERIODIC
        elif interval_cv < 1.0:
            return TrafficPatternType.BURSTY
        else:
            return TrafficPatternType.RANDOM


# SECTION 1: TRAPDETECTION ENGINE

class ThreatLevel(Enum):
    """Niveles de amenaza cuantificados."""
    CLEAN = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    QUANTUM_BREACH = 5


class DetectionMode(Enum):
    """Modos de detección disponibles."""
    SHANNON_ONLY = auto()
    SAMPLE_ONLY = auto()
    HYBRID = auto()
    ADAPTIVE = auto()
    QUANTUM_AWARE = auto()


@dataclass
class EntropyProfile:
    """Perfil de entropía para un segmento de datos."""
    shannon_entropy: float = 0.0
    sample_entropy: float = 0.0
    permutation_entropy: float = 0.0
    spectral_entropy: float = 0.0
    approximate_entropy: float = 0.0
    composite_score: float = 0.0
    anomaly_confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)
    window_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


@dataclass
class SigmaCalibration:
    """Estado de calibración sigma dinámica."""
    mean: float = 0.0
    std_dev: float = 1.0
    variance: float = 1.0
    sample_count: int = 0
    running_sum: float = 0.0
    running_sum_sq: float = 0.0
    sigma_1_threshold: float = 1.0
    sigma_2_threshold: float = 2.0
    sigma_3_threshold: float = 3.0
    ewma_alpha: float = 0.1
    ewma_mean: float = 0.0
    ewma_variance: float = 1.0
    min_samples: int = 100
    confidence_level: float = 0.95
    adaptive_factor: float = 1.0


@dataclass
class TrapSignature:
    """Firma de trampa detectada."""
    trap_id: str = field(default_factory=lambda: f"TRAP-{uuid.uuid4().hex[:12].upper()}")
    trap_type: str = "UNKNOWN"
    severity: ThreatLevel = ThreatLevel.LOW
    entropy_profile: Optional[EntropyProfile] = None
    source_hash: str = ""
    detection_vector: List[float] = field(default_factory=list)
    false_positive_probability: float = 0.0
    mitigation_action: str = "MONITOR"
    detected_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ShannonEntropyCalculator:
    """
    Calculador de entropía de Shannon optimizado.
    H(X) = -Σ p(x) * log2(p(x))
    """
    
    def __init__(self, base: float = 2.0, normalization: bool = True):
        self.base = base
        self.normalization = normalization
        self._log_cache: Dict[int, float] = {}
        self._byte_frequency: np.ndarray = np.zeros(256, dtype=np.float64)
    
    def _cached_log(self, value: int) -> float:
        if value not in self._log_cache:
            if value > 0:
                self._log_cache[value] = math.log(value, self.base)
            else:
                self._log_cache[value] = 0.0
        return self._log_cache[value]
    
    def calculate(self, data: Union[bytes, np.ndarray, List[int]]) -> float:
        """Calcula entropía de Shannon sobre los datos."""
        if isinstance(data, bytes):
            data_array = np.frombuffer(data, dtype=np.uint8)
        elif isinstance(data, list):
            data_array = np.array(data, dtype=np.uint8)
        else:
            data_array = data.astype(np.uint8)
        
        if len(data_array) == 0:
            return 0.0
        
        self._byte_frequency.fill(0)
        np.add.at(self._byte_frequency, data_array, 1.0)
        
        total = len(data_array)
        probabilities = self._byte_frequency[self._byte_frequency > 0] / total
        
        if len(probabilities) == 0:
            return 0.0
        
        entropy = -np.sum(probabilities * np.log2(probabilities))
        
        if self.normalization:
            max_entropy = math.log2(256)
            entropy = entropy / max_entropy if max_entropy > 0 else 0.0
        
        return float(entropy)
    
    def calculate_windowed(
        self, 
        data: Union[bytes, np.ndarray], 
        window_size: int = 256, 
        overlap: float = 0.5
    ) -> List[Tuple[int, float]]:
        """Calcula entropía en ventanas deslizantes."""
        if isinstance(data, bytes):
            data_array = np.frombuffer(data, dtype=np.uint8)
        else:
            data_array = data
        
        step = int(window_size * (1 - overlap))
        if step < 1:
            step = 1
        
        results = []
        for start in range(0, len(data_array) - window_size + 1, step):
            window = data_array[start:start + window_size]
            entropy = self.calculate(window)
            results.append((start, entropy))
        
        return results
    
    def calculate_block_entropy(
        self, 
        data: Union[bytes, np.ndarray], 
        block_size: int = 8
    ) -> float:
        """Calcula entropía por bloques de bits."""
        if isinstance(data, bytes):
            bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8))
        else:
            bits = np.unpackbits(data.astype(np.uint8))
        
        num_blocks = len(bits) // block_size
        if num_blocks == 0:
            return 0.0
        
        blocks = bits[:num_blocks * block_size].reshape(-1, block_size)
        block_values = np.packbits(blocks, axis=1).flatten()
        
        return self.calculate(block_values)
    
    def conditional_entropy(
        self, 
        data_x: Union[bytes, np.ndarray], 
        data_y: Union[bytes, np.ndarray]
    ) -> float:
        """Calcula entropía condicional H(Y|X)."""
        if isinstance(data_x, bytes):
            x = np.frombuffer(data_x, dtype=np.uint8)
        else:
            x = data_x.astype(np.uint8)
        
        if isinstance(data_y, bytes):
            y = np.frombuffer(data_y, dtype=np.uint8)
        else:
            y = data_y.astype(np.uint8)
        
        min_len = min(len(x), len(y))
        x, y = x[:min_len], y[:min_len]
        
        joint_counts = defaultdict(int)
        x_counts = defaultdict(int)
        
        for xi, yi in zip(x, y):
            joint_counts[(xi, yi)] += 1
            x_counts[xi] += 1
        
        total = min_len
        h_joint = 0.0
        for count in joint_counts.values():
            p = count / total
            if p > 0:
                h_joint -= p * math.log2(p)
        
        h_x = 0.0
        for count in x_counts.values():
            p = count / total
            if p > 0:
                h_x -= p * math.log2(p)
        
        return h_joint - h_x


class SampleEntropyCalculator:
    """
    Calculador de Sample Entropy (Richman & Moorman 2000).
    SampEn(m,r,N) = -ln(A/B)
    donde A = pares similares de longitud m+1
         B = pares similares de longitud m
    """
    
    def __init__(
        self, 
        m: int = 2, 
        r: Optional[float] = None,
        normalize: bool = True,
        use_chebyshev: bool = True
    ):
        self.m = m
        self.r = r
        self.normalize = normalize
        self.use_chebyshev = use_chebyshev
        self._tolerance_cache: Dict[float, float] = {}
    
    def _create_templates(
        self, 
        data: np.ndarray, 
        m: int
    ) -> np.ndarray:
        """Crea vectores template de dimensión m."""
        n = len(data)
        templates = np.zeros((n - m + 1, m), dtype=np.float64)
        for i in range(n - m + 1):
            templates[i] = data[i:i + m]
        return templates
    
    def _count_similar(
        self, 
        templates: np.ndarray, 
        tolerance: float
    ) -> int:
        """Cuenta pares de templates similares."""
        count = 0
        n = len(templates)
        
        if self.use_chebyshev:
            for i in range(n):
                for j in range(i + 1, n):
                    if np.max(np.abs(templates[i] - templates[j])) <= tolerance:
                        count += 1
        else:
            for i in range(n):
                for j in range(i + 1, n):
                    dist = np.sqrt(np.sum((templates[i] - templates[j]) ** 2))
                    if dist <= tolerance:
                        count += 1
        
        return count
    
    def _count_similar_vectorized(
        self, 
        templates: np.ndarray, 
        tolerance: float
    ) -> int:
        """Versión vectorizada del conteo de similitudes."""
        n = len(templates)
        count = 0
        
        batch_size = min(1000, n)
        for i in range(0, n, batch_size):
            end_i = min(i + batch_size, n)
            batch_i = templates[i:end_i]
            
            for j in range(i + 1, n, batch_size):
                end_j = min(j + batch_size, n)
                batch_j = templates[j:end_j]
                
                if self.use_chebyshev:
                    diffs = np.max(
                        np.abs(batch_i[:, np.newaxis, :] - batch_j[np.newaxis, :, :]),
                        axis=2
                    )
                else:
                    diffs = np.sqrt(
                        np.sum(
                            (batch_i[:, np.newaxis, :] - batch_j[np.newaxis, :, :]) ** 2,
                            axis=2
                        )
                    )
                
                mask = diffs <= tolerance
                if i == j:
                    np.fill_diagonal(mask, False)
                count += np.sum(mask)
        
        return count // 2
    
    def calculate(
        self, 
        data: Union[bytes, np.ndarray, List[float]],
        use_vectorized: bool = True
    ) -> float:
        """Calcula Sample Entropy."""
        if isinstance(data, bytes):
            data_array = np.frombuffer(data, dtype=np.uint8).astype(np.float64)
        elif isinstance(data, list):
            data_array = np.array(data, dtype=np.float64)
        else:
            data_array = data.astype(np.float64)
        
        if self.normalize:
            std = np.std(data_array)
            if std > 0:
                data_array = (data_array - np.mean(data_array)) / std
        
        if self.r is None:
            tolerance = 0.2 * np.std(data_array)
        else:
            tolerance = self.r * np.std(data_array)
        
        if tolerance == 0:
            tolerance = 0.001
        
        n = len(data_array)
        if n <= self.m + 1:
            return 0.0
        
        templates_m = self._create_templates(data_array, self.m)
        templates_m1 = self._create_templates(data_array, self.m + 1)
        
        if use_vectorized and n < 5000:
            B = self._count_similar_vectorized(templates_m, tolerance)
            A = self._count_similar_vectorized(templates_m1, tolerance)
        else:
            B = self._count_similar(templates_m, tolerance)
            A = self._count_similar(templates_m1, tolerance)
        
        if B == 0 or A == 0:
            return float('inf')
        
        sample_entropy = -math.log(A / B)
        return sample_entropy
    
    def calculate_multiscale(
        self, 
        data: Union[bytes, np.ndarray], 
        max_scale: int = 10
    ) -> List[Tuple[int, float]]:
        """Calcula Sample Entropy multi-escala."""
        if isinstance(data, bytes):
            data_array = np.frombuffer(data, dtype=np.uint8).astype(np.float64)
        else:
            data_array = data.astype(np.float64)
        
        results = []
        for scale in range(1, max_scale + 1):
            if scale > 1:
                n = len(data_array) // scale
                coarse = np.array([
                    np.mean(data_array[i*scale:(i+1)*scale]) 
                    for i in range(n)
                ])
            else:
                coarse = data_array
            
            if len(coarse) > self.m + 1:
                entropy = self.calculate(coarse, use_vectorized=False)
                results.append((scale, entropy))
        
        return results
    
    def fuzzy_sample_entropy(
        self, 
        data: Union[bytes, np.ndarray],
        r: float = 0.2,
        n_factor: float = 2.0
    ) -> float:
        """Sample Entropy difusa con función de similitud gaussiana."""
        if isinstance(data, bytes):
            data_array = np.frombuffer(data, dtype=np.uint8).astype(np.float64)
        else:
            data_array = data.astype(np.float64)
        
        std = np.std(data_array)
        if std == 0:
            return 0.0
        
        data_array = (data_array - np.mean(data_array)) / std
        tolerance = r * std
        
        templates_m = self._create_templates(data_array, self.m)
        templates_m1 = self._create_templates(data_array, self.m + 1)
        
        def fuzzy_count(templates: np.ndarray, tol: float) -> float:
            n = len(templates)
            total = 0.0
            for i in range(n):
                for j in range(i + 1, n):
                    dist = np.max(np.abs(templates[i] - templates[j]))
                    similarity = math.exp(-(dist ** 2) / (2 * tol ** 2))
                    total += similarity
            return total
        
        B = fuzzy_count(templates_m, tolerance)
        A = fuzzy_count(templates_m1, tolerance)
        
        if B == 0 or A == 0:
            return float('inf')
        
        return -math.log(A / B)


class SigmaCalibrator:
    """
    Calibrador sigma dinámico con EWMA y detección adaptativa.
    Implementa control estadístico de procesos (SPC).
    """
    
    def __init__(
        self,
        initial_mean: float = 0.5,
        initial_std: float = 0.1,
        ewma_alpha: float = 0.1,
        min_samples: int = 100,
        confidence_level: float = 0.95,
        use_robust: bool = True
    ):
        self.state = SigmaCalibration(
            mean=initial_mean,
            std_dev=initial_std,
            variance=initial_std ** 2,
            ewma_alpha=ewma_alpha,
            ewma_mean=initial_mean,
            ewma_variance=initial_std ** 2,
            min_samples=min_samples,
            confidence_level=confidence_level
        )
        self.use_robust = use_robust
        self._history: Deque[float] = deque(maxlen=10000)
        self._median_buffer: Deque[float] = deque(maxlen=1000)
        self._mad_buffer: Deque[float] = deque(maxlen=1000)
        self._cusum_positive: float = 0.0
        self._cusum_negative: float = 0.0
        self._cusum_threshold: float = 5.0
        self._cusum_slack: float = 0.5
    
    def update(self, value: float) -> SigmaCalibration:
        """Actualiza calibración con nuevo valor."""
        self._history.append(value)
        self.state.sample_count += 1
        self.state.running_sum += value
        self.state.running_sum_sq += value ** 2
        
        self._median_buffer.append(value)
        
        if self.state.sample_count >= 2:
            self.state.mean = self.state.running_sum / self.state.sample_count
            variance = (
                self.state.running_sum_sq / self.state.sample_count 
                - self.state.mean ** 2
            )
            self.state.variance = max(variance, 1e-10)
            self.state.std_dev = math.sqrt(self.state.variance)
        
        self.state.ewma_mean = (
            self.state.ewma_alpha * value 
            + (1 - self.state.ewma_alpha) * self.state.ewma_mean
        )
        
        deviation = (value - self.state.ewma_mean) ** 2
        self.state.ewma_variance = (
            self.state.ewma_alpha * deviation 
            + (1 - self.state.ewma_alpha) * self.state.ewma_variance
        )
        
        self._update_cusum(value)
        
        if self.state.sample_count >= self.state.min_samples:
            self._update_thresholds()
        
        return self.state
    
    def _update_cusum(self, value: float):
        """Actualiza estadístico CUSUM para detección de cambios."""
        if self.state.std_dev > 0:
            standardized = (value - self.state.mean) / self.state.std_dev
        else:
            standardized = 0.0
        
        self._cusum_positive = max(
            0, 
            self._cusum_positive + standardized - self._cusum_slack
        )
        self._cusum_negative = max(
            0, 
            self._cusum_negative - standardized - self._cusum_slack
        )
    
    def _update_thresholds(self):
        """Actualiza umbrales sigma basado en distribución observada."""
        if self.use_robust and len(self._median_buffer) >= 10:
            median = np.median(list(self._median_buffer))
            mad = np.median([abs(x - median) for x in self._median_buffer])
            robust_std = mad * 1.4826
            
            blend_factor = min(1.0, self.state.sample_count / 1000)
            effective_std = (
                blend_factor * self.state.std_dev 
                + (1 - blend_factor) * robust_std
            )
        else:
            effective_std = self.state.std_dev
        
        z_score = self._get_z_score(self.state.confidence_level)
        
        self.state.sigma_1_threshold = effective_std
        self.state.sigma_2_threshold = 2 * effective_std
        self.state.sigma_3_threshold = 3 * effective_std
        
        self.state.adaptive_factor = self._calculate_adaptive_factor()
    
    def _get_z_score(self, confidence: float) -> float:
        """Obtiene z-score para nivel de confianza dado."""
        z_scores = {
            0.90: 1.645, 0.95: 1.96, 0.99: 2.576, 0.999: 3.291
        }
        return z_scores.get(confidence, 1.96)
    
    def _calculate_adaptive_factor(self) -> float:
        """Calcula factor adaptativo basado en estabilidad del proceso."""
        if len(self._history) < 50:
            return 1.0
        
        recent = list(self._history)[-50:]
        recent_std = np.std(recent)
        
        if self.state.std_dev > 0:
            stability_ratio = recent_std / self.state.std_dev
        else:
            stability_ratio = 1.0
        
        if stability_ratio < 0.5:
            return 0.8
        elif stability_ratio > 2.0:
            return 1.5
        else:
            return 1.0
    
    def classify_sigma_level(self, value: float) -> Tuple[int, float]:
        """Clasifica valor según nivel sigma."""
        if self.state.std_dev == 0:
            return 0, 0.0
        
        deviation = abs(value - self.state.ewma_mean)
        sigma_units = deviation / (self.state.std_dev * self.state.adaptive_factor)
        
        if sigma_units <= 1:
            return 1, sigma_units
        elif sigma_units <= 2:
            return 2, sigma_units
        elif sigma_units <= 3:
            return 3, sigma_units
        else:
            return min(int(sigma_units), 6), sigma_units
    
    def detect_change_point(self) -> bool:
        """Detecta si hubo un cambio significativo en el proceso."""
        return (
            self._cusum_positive > self._cusum_threshold 
            or self._cusum_negative > self._cusum_threshold
        )
    
    def get_confidence_interval(self) -> Tuple[float, float]:
        """Retorna intervalo de confianza actual."""
        z = self._get_z_score(self.state.confidence_level)
        margin = z * self.state.std_dev / math.sqrt(max(1, self.state.sample_count))
        return (self.state.mean - margin, self.state.mean + margin)
    
    def reset(self):
        """Reinicia calibración."""
        self.state = SigmaCalibration()
        self._history.clear()
        self._median_buffer.clear()
        self._cusum_positive = 0.0
        self._cusum_negative = 0.0


class TrapPatternLibrary:
    """Biblioteca de patrones de trampa conocidos."""
    
    KNOWN_PATTERNS = {
        "REPLAY_ATTACK": {
            "shannon_range": (0.0, 0.1),
            "sample_range": (0.0, 0.05),
            "description": "Datos repetidos indican ataque de replay"
        },
        "ENTROPY_INJECTION": {
            "shannon_range": (0.99, 1.01),
            "sample_range": (0.8, 1.0),
            "description": "Entropía máxima indica inyección de ruido"
        },
        "PADDING_ORACLE": {
            "shannon_range": (0.7, 0.85),
            "sample_range": (0.3, 0.5),
            "description": "Patrón consistente con oracle de padding"
        },
        "SIDE_CHANNEL": {
            "shannon_range": (0.4, 0.6),
            "sample_range": (0.6, 0.8),
            "description": "Variaciones temporales sugieren canal lateral"
        },
        "QUANTUM_DECOHERENCE": {
            "shannon_range": (0.5, 0.7),
            "sample_range": (0.1, 0.3),
            "description": "Pérdida de coherencia cuántica detectada"
        },
        "MAN_IN_THE_MIDDLE": {
            "shannon_range": (0.3, 0.5),
            "sample_range": (0.4, 0.6),
            "description": "Intercepción activa detectada"
        },
        "TIMING_ATTACK": {
            "shannon_range": (0.2, 0.4),
            "sample_range": (0.7, 0.9),
            "description": "Variaciones temporales anómalas"
        },
        "BYTE_DISTRIBUTION_ANOMALY": {
            "shannon_range": (0.15, 0.35),
            "sample_range": (0.2, 0.4),
            "description": "Distribución de bytes no uniforme"
        }
    }
    
    @classmethod
    def match_pattern(
        cls, 
        shannon: float, 
        sample: float,
        tolerance: float = 0.1
    ) -> List[Tuple[str, float, str]]:
        """Encuentra patrones que coinciden con los valores dados."""
        matches = []
        
        for name, pattern in cls.KNOWN_PATTERNS.items():
            shannon_min, shannon_max = pattern["shannon_range"]
            sample_min, sample_max = pattern["sample_range"]
            
            shannon_dist = 0.0
            if shannon < shannon_min - tolerance:
                shannon_dist = shannon_min - tolerance - shannon
            elif shannon > shannon_max + tolerance:
                shannon_dist = shannon - shannon_max - tolerance
            
            sample_dist = 0.0
            if sample < sample_min - tolerance:
                sample_dist = sample_min - tolerance - sample
            elif sample > sample_max + tolerance:
                sample_dist = sample - sample_max - tolerance
            
            total_dist = math.sqrt(shannon_dist ** 2 + sample_dist ** 2)
            
            if total_dist == 0:
                confidence = 1.0
            elif total_dist < tolerance * 2:
                confidence = 1.0 - (total_dist / (tolerance * 2))
            else:
                confidence = 0.0
            
            if confidence > 0.3:
                matches.append((name, confidence, pattern["description"]))
        
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches


class TrapDetectionEngine:
    """
    Motor principal de detección de trampas.
    Combina Shannon entropy, Sample entropy y calibración sigma.
    """
    
    def __init__(
        self,
        mode: DetectionMode = DetectionMode.HYBRID,
        window_size: int = 256,
        shannon_base: float = 2.0,
        sample_m: int = 2,
        sample_r: float = 0.2,
        ewma_alpha: float = 0.1,
        min_samples: int = 100,
        confidence_threshold: float = 0.7,
        enable_pattern_matching: bool = True,
        enable_cusum: bool = True,
        max_history: int = 10000
    ):
        self.mode = mode
        self.window_size = window_size
        self.confidence_threshold = confidence_threshold
        self.enable_pattern_matching = enable_pattern_matching
        self.enable_cusum = enable_cusum
        
        self.shannon_calc = ShannonEntropyCalculator(
            base=shannon_base, 
            normalization=True
        )
        self.sample_calc = SampleEntropyCalculator(
            m=sample_m, 
            r=sample_r, 
            normalize=True
        )
        self.sigma_calibrator = SigmaCalibrator(
            ewma_alpha=ewma_alpha,
            min_samples=min_samples
        )
        
        self._detection_history: Deque[TrapSignature] = deque(maxlen=max_history)
        self._entropy_history: Deque[EntropyProfile] = deque(maxlen=max_history)
        self._threat_callbacks: Dict[ThreatLevel, List[Callable]] = defaultdict(list)
        self._baseline_profiles: Dict[str, EntropyProfile] = {}
        self._anomaly_buffer: Deque[float] = deque(maxlen=100)
        self._false_positive_tracker: Dict[str, int] = defaultdict(int)
        
        self._stats = {
            "total_scans": 0,
            "traps_detected": 0,
            "false_positives": 0,
            "avg_scan_time_ms": 0.0,
            "last_calibration": 0.0
        }
    
    async def analyze(
        self, 
        data: Union[bytes, np.ndarray],
        context: Optional[Dict[str, Any]] = None,
        source_id: str = "unknown"
    ) -> Tuple[EntropyProfile, Optional[TrapSignature]]:
        """Analiza datos para detectar trampas."""
        start_time = time.time()
        self._stats["total_scans"] += 1
        
        profile = await self._compute_entropy_profile(data)
        self._entropy_history.append(profile)
        
        self.sigma_calibrator.update(profile.composite_score)
        
        trap = await self._evaluate_threat(
            profile, context, source_id
        )
        
        if trap:
            self._detection_history.append(trap)
            self._stats["traps_detected"] += 1
            await self._fire_threat_callbacks(trap)
        
        scan_time = (time.time() - start_time) * 1000
        self._stats["avg_scan_time_ms"] = (
            self._stats["avg_scan_time_ms"] * 0.9 + scan_time * 0.1
        )
        
        return profile, trap
    
    async def _compute_entropy_profile(
        self, 
        data: Union[bytes, np.ndarray]
    ) -> EntropyProfile:
        """Calcula perfil completo de entropía."""
        profile = EntropyProfile()
        
        if self.mode == DetectionMode.SHANNON_ONLY:
            profile.shannon_entropy = self.shannon_calc.calculate(data)
            profile.composite_score = profile.shannon_entropy
        
        elif self.mode == DetectionMode.SAMPLE_ONLY:
            profile.sample_entropy = self.sample_calc.calculate(data)
            profile.composite_score = self._normalize_sample(profile.sample_entropy)
        
        elif self.mode in (DetectionMode.HYBRID, DetectionMode.ADAPTIVE, DetectionMode.QUANTUM_AWARE):
            profile.shannon_entropy = self.shannon_calc.calculate(data)
            profile.sample_entropy = self.sample_calc.calculate(data)
            
            profile.permutation_entropy = self._calculate_permutation_entropy(data)
            profile.spectral_entropy = self._calculate_spectral_entropy(data)
            profile.approximate_entropy = self._calculate_approximate_entropy(data)
            
            if self.mode == DetectionMode.ADAPTIVE:
                weights = self._compute_adaptive_weights()
            elif self.mode == DetectionMode.QUANTUM_AWARE:
                weights = (0.25, 0.25, 0.2, 0.15, 0.15)
            else:
                weights = (0.35, 0.35, 0.15, 0.10, 0.05)
            
            normalized_sample = self._normalize_sample(profile.sample_entropy)
            normalized_perm = profile.permutation_entropy
            normalized_spectral = profile.spectral_entropy
            normalized_approx = self._normalize_sample(profile.approximate_entropy)
            
            profile.composite_score = (
                weights[0] * profile.shannon_entropy +
                weights[1] * normalized_sample +
                weights[2] * normalized_perm +
                weights[3] * normalized_spectral +
                weights[4] * normalized_approx
            )
        
        sigma_level, sigma_units = self.sigma_calibrator.classify_sigma_level(
            profile.composite_score
        )
        profile.anomaly_confidence = min(1.0, sigma_units / 3.0)
        
        return profile
    
    def _normalize_sample(self, value: float) -> float:
        """Normaliza Sample Entropy a rango [0, 1]."""
        if value == float('inf') or value > 10:
            return 1.0
        return min(1.0, max(0.0, value / 5.0))
    
    def _calculate_permutation_entropy(
        self, 
        data: Union[bytes, np.ndarray], 
        order: int = 3, 
        delay: int = 1
    ) -> float:
        """Calcula entropía de permutación."""
        if isinstance(data, bytes):
            x = np.frombuffer(data, dtype=np.uint8).astype(np.float64)
        else:
            x = data.astype(np.float64)
        
        n = len(x)
        if n < order:
            return 0.0
        
        permutations = defaultdict(int)
        for i in range(n - (order - 1) * delay):
            window = x[i:i + order * delay:delay]
            perm = tuple(np.argsort(window))
            permutations[perm] += 1
        
        total = sum(permutations.values())
        if total == 0:
            return 0.0
        
        entropy = 0.0
        for count in permutations.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)
        
        max_entropy = math.log2(math.factorial(order))
        return entropy / max_entropy if max_entropy > 0 else 0.0
    
    def _calculate_spectral_entropy(
        self, 
        data: Union[bytes, np.ndarray]
    ) -> float:
        """Calcula entropía espectral usando FFT."""
        if isinstance(data, bytes):
            x = np.frombuffer(data, dtype=np.uint8).astype(np.float64)
        else:
            x = data.astype(np.float64)
        
        if len(x) < 4:
            return 0.0
        
        x = x - np.mean(x)
        
        fft = np.fft.rfft(x)
        power_spectrum = np.abs(fft) ** 2
        
        total_power = np.sum(power_spectrum)
        if total_power == 0:
            return 0.0
        
        probabilities = power_spectrum / total_power
        probabilities = probabilities[probabilities > 0]
        
        entropy = -np.sum(probabilities * np.log2(probabilities))
        max_entropy = math.log2(len(probabilities))
        
        return entropy / max_entropy if max_entropy > 0 else 0.0
    
    def _calculate_approximate_entropy(
        self, 
        data: Union[bytes, np.ndarray],
        m: int = 2,
        r: float = 0.2
    ) -> float:
        """Calcula Approximate Entropy (Pincus 1991)."""
        if isinstance(data, bytes):
            x = np.frombuffer(data, dtype=np.uint8).astype(np.float64)
        else:
            x = data.astype(np.float64)
        
        n = len(x)
        if n < m + 1:
            return 0.0
        
        std = np.std(x)
        if std == 0:
            return 0.0
        
        tolerance = r * std
        
        def phi(m_val: int) -> float:
            templates = np.array([x[i:i + m_val] for i in range(n - m_val + 1)])
            counts = np.zeros(len(templates))
            
            for i in range(len(templates)):
                for j in range(len(templates)):
                    if np.max(np.abs(templates[i] - templates[j])) <= tolerance:
                        counts[i] += 1
            
            counts = counts / (n - m_val + 1)
            return np.mean(np.log(counts + 1e-10))
        
        return phi(m) - phi(m + 1)
    
    def _compute_adaptive_weights(self) -> Tuple[float, ...]:
        """Calcula pesos adaptativos basados en historial."""
        if len(self._entropy_history) < 10:
            return (0.35, 0.35, 0.15, 0.15)
        
        weights = [0.4, 0.3, 0.2, 0.1]
        return tuple(weights)

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas actuales del motor."""
        return self._stats

if __name__ == "__main__":
    print("[*] Qanion Mimo Layer - Estatus: OPERATIVO (Phase 10)")
