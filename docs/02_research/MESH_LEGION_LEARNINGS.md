"""
docs/MESH_LEGION_LEARNINGS.md
DOF Mesh Legion — Aprendizajes Técnicos (Marzo 2026)
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import threading

# ============================================================================
# 1. ARQUITECTURA MULTI-MODELO
# ============================================================================

@dataclass
class ProviderConfig:
    """Configuración de proveedor LLM"""
    name: str
    base_url: str
    api_key: str = ""
    api_key_env: str = ""
    models: List[str] = field(default_factory=list)
    timeout: int = 30
    max_retries: int = 3
    
    def __post_init__(self):
        if self.api_key_env:
            self.api_key = os.getenv(self.api_key_env, "")

class MessageProtocol:
    """Protocolo de mensajes JSON para el mesh"""
    
    _lock = threading.Lock()
    
    def __init__(self, mesh_dir: str = "logs/mesh"):
        self.mesh_dir = mesh_dir
        self.inbox_dir = os.path.join(mesh_dir, "inbox")
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """Garantiza que existen los directorios del protocolo"""
        os.makedirs(self.inbox_dir, exist_ok=True)
        for node in ["router", "orchestrator", "breaker", "scaler"]:
            os.makedirs(os.path.join(self.inbox_dir, node), exist_ok=True)
    
    def send_message(self, node: str, message: Dict) -> str:
        """
        Envía mensaje a nodo específico.
        Resuelve race conditions con timestamp + lock.
        """
        with self._lock:
            timestamp = datetime.utcnow().isoformat().replace(":", "-")
            filename = f"{timestamp}_{id(message)}_{hash(str(message))}.json"
            node_dir = os.path.join(self.inbox_dir, node)
            
            # Escribe en archivo temporal primero
            temp_path = os.path.join(node_dir, f"temp_{filename}")
            final_path = os.path.join(node_dir, filename)
            
            try:
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(message, f, indent=2)
                
                # Rename atómico (evita FileNotFoundError)
                os.rename(temp_path, final_path)
                return final_path
                
            except (FileNotFoundError, PermissionError) as e:
                # Reintento con directorio asegurado
                os.makedirs(node_dir, exist_ok=True)
                with open(final_path, 'w', encoding='utf-8') as f:
                    json.dump(message, f, indent=2)
                return final_path
    
    def read_messages(self, node: str, limit: int = 100) -> List[Dict]:
        """Lee mensajes del inbox de un nodo"""
        node_dir = os.path.join(self.inbox_dir, node)
        if not os.path.exists(node_dir):
            return []
        
        messages = []
        files = sorted(os.listdir(node_dir))[:limit]
        
        for file in files:
            if file.endswith('.json') and not file.startswith('temp_'):
                try:
                    with open(os.path.join(node_dir, file), 'r', encoding='utf-8') as f:
                        messages.append(json.load(f))
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
        
        return messages

# ============================================================================
# 2. PROVIDERS GRATUITOS VALIDADOS
# ============================================================================

class ValidatedProviders:
    """Registro de proveedores gratuitos validados"""
    
    PROVIDERS = {
        "deepseek": {
            "model": "deepseek-chat",
            "cost": 0.0,
            "speed": "fast",
            "base_url": "https://api.deepseek.com/v1",
            "notes": "15M contexto, buena programación"
        },
        "cerebras": {
            "model": "llama3.1-70b",
            "cost": 0.0,
            "speed": "medium",
            "base_url": "https://api.cerebras.ai/v1",
            "notes": "Llama 3.1 70B gratuito"
        },
        "sambanova": {
            "model": "llama-3.1-70b",
            "cost": 0.0,
            "speed": "slow",
            "base_url": "https://api.sambanova.ai/v1",
            "notes": "Rate limit estricto"
        },
        "nvidia": {
            "model": "llama-3.1-70b",
            "cost": 0.0,
            "speed": "fast",
            "base_url": "https://integrate.api.nvidia.com/v1",
            "notes": "Requiere cuenta NVIDIA"
        },
        "gemini": {
            "model": "gemini-2.0-flash",
            "cost": 0.0,
            "speed": "very_fast",
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "notes": "Nativo Google, requiere bridge manual"
        },
        "ollama": {
            "model": "llama3.2:latest",
            "cost": 0.0,
            "speed": "local",
            "base_url": "http://localhost:11434/v1",
            "notes": "Auto-hospedado, sin límites"
        },
        "openrouter": {
            "model": "google/gemini-2.0-flash:free",
            "cost": 0.0,
            "speed": "medium",
            "base_url": "https://openrouter.ai/api/v1",
            "notes": "Agregador múltiple"
        },
        "together": {
            "model": "meta-llama/Llama-3.2-70B",
            "cost": 0.0,
            "speed": "medium",
            "base_url": "https://api.together.xyz/v1",
            "notes": "$1 crédito inicial"
        }
    }
    
    @classmethod
    def get_markdown_table(cls) -> str:
        """Genera tabla Markdown de proveedores"""
        table = [
            "| Provider | Modelo | Costo | Velocidad | Notas |",
            "|----------|--------|-------|-----------|-------|"
        ]
        
        for name, info in cls.PROVIDERS.items():
            table.append(
                f"| {name} | {info['model']} | ${info['cost']}/1M tokens | {info['speed']} | {info['notes']} |"
            )
        
        return "\n".join(table)

# ============================================================================
# 3. ESTRATEGIA COSTO CERO
# ============================================================================

class ZeroCostStrategy:
    """
    Estrategia para operación sin costo.
    Prioriza proveedores gratuitos, evita modelos caros.
    """
    
    EXPENSIVE_MODELS = {
        "claude-3-opus",
        "claude-3-sonnet", 
        "gpt-4-turbo",
        "gpt-4o",
        "gemini-2.0-pro"
    }
    
    FREE_FALLBACKS = {
        "claude-3-opus": "claude-3-haiku",
        "claude-3-sonnet": "claude-3-haiku",
        "gpt-4-turbo": "deepseek-chat",
        "gpt-4o": "gemini-2.0-flash",
        "gemini-2.0-pro": "gemini-2.0-flash"
    }
    
    @classmethod
    def should_use_model(cls, model: str) -> Tuple[bool, Optional[str]]:
        """
        Determina si un modelo debe usarse.
        Returns: (should_use, fallback_suggestion)
        """
        if model in cls.EXPENSIVE_MODELS:
            return False, cls.FREE_FALLBACKS.get(model)
        return True, None

class APINodeRunner:
    """
    Daemon que ejecuta nodos del mesh.
    Implementa estrategia costo cero.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, mesh_dir: str = "logs/mesh"):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.mesh_dir = mesh_dir
                cls._instance.protocol = MessageProtocol(mesh_dir)
                cls._instance.running = False
            return cls._instance
    
    def start(self):
        """Inicia el daemon del mesh"""
        self.running = True
        # En producción: threading.Thread para cada nodo
        print(f"DO