"""
docs/MESH_LEGION_LEARNINGS.md
DOF Mesh Legion — Technical Learnings (March 2026)
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import threading

# ============================================================================
# 1. MULTI-MODEL ARCHITECTURE
# ============================================================================

@dataclass
class ProviderConfig:
    """LLM provider configuration"""
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
    """JSON message protocol for the mesh"""

    _lock = threading.Lock()

    def __init__(self, mesh_dir: str = "logs/mesh"):
        self.mesh_dir = mesh_dir
        self.inbox_dir = os.path.join(mesh_dir, "inbox")
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Ensures protocol directories exist"""
        os.makedirs(self.inbox_dir, exist_ok=True)
        for node in ["router", "orchestrator", "breaker", "scaler"]:
            os.makedirs(os.path.join(self.inbox_dir, node), exist_ok=True)

    def send_message(self, node: str, message: Dict) -> str:
        """
        Sends message to specific node.
        Resolves race conditions with timestamp + lock.
        """
        with self._lock:
            timestamp = datetime.utcnow().isoformat().replace(":", "-")
            filename = f"{timestamp}_{id(message)}_{hash(str(message))}.json"
            node_dir = os.path.join(self.inbox_dir, node)

            # Write to temp file first
            temp_path = os.path.join(node_dir, f"temp_{filename}")
            final_path = os.path.join(node_dir, filename)

            try:
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(message, f, indent=2)

                # Atomic rename (avoids FileNotFoundError)
                os.rename(temp_path, final_path)
                return final_path

            except (FileNotFoundError, PermissionError) as e:
                # Retry with ensured directory
                os.makedirs(node_dir, exist_ok=True)
                with open(final_path, 'w', encoding='utf-8') as f:
                    json.dump(message, f, indent=2)
                return final_path

    def read_messages(self, node: str, limit: int = 100) -> List[Dict]:
        """Reads messages from a node's inbox"""
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
# 2. VALIDATED FREE PROVIDERS
# ============================================================================

class ValidatedProviders:
    """Registry of validated free providers"""

    PROVIDERS = {
        "deepseek": {
            "model": "deepseek-chat",
            "cost": 0.0,
            "speed": "fast",
            "base_url": "https://api.deepseek.com/v1",
            "notes": "15M context, good at coding"
        },
        "cerebras": {
            "model": "llama3.1-70b",
            "cost": 0.0,
            "speed": "medium",
            "base_url": "https://api.cerebras.ai/v1",
            "notes": "Free Llama 3.1 70B"
        },
        "sambanova": {
            "model": "llama-3.1-70b",
            "cost": 0.0,
            "speed": "slow",
            "base_url": "https://api.sambanova.ai/v1",
            "notes": "Strict rate limit"
        },
        "nvidia": {
            "model": "llama-3.1-70b",
            "cost": 0.0,
            "speed": "fast",
            "base_url": "https://integrate.api.nvidia.com/v1",
            "notes": "Requires NVIDIA account"
        },
        "gemini": {
            "model": "gemini-2.0-flash",
            "cost": 0.0,
            "speed": "very_fast",
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "notes": "Native Google, requires manual bridge"
        },
        "ollama": {
            "model": "llama3.2:latest",
            "cost": 0.0,
            "speed": "local",
            "base_url": "http://localhost:11434/v1",
            "notes": "Self-hosted, no limits"
        },
        "openrouter": {
            "model": "google/gemini-2.0-flash:free",
            "cost": 0.0,
            "speed": "medium",
            "base_url": "https://openrouter.ai/api/v1",
            "notes": "Multi-model aggregator"
        },
        "together": {
            "model": "meta-llama/Llama-3.2-70B",
            "cost": 0.0,
            "speed": "medium",
            "base_url": "https://api.together.xyz/v1",
            "notes": "$1 initial credit"
        }
    }

    @classmethod
    def get_markdown_table(cls) -> str:
        """Generates Markdown table of providers"""
        table = [
            "| Provider | Model | Cost | Speed | Notes |",
            "|----------|--------|-------|-----------|-------|"
        ]

        for name, info in cls.PROVIDERS.items():
            table.append(
                f"| {name} | {info['model']} | ${info['cost']}/1M tokens | {info['speed']} | {info['notes']} |"
            )

        return "\n".join(table)

# ============================================================================
# 3. ZERO-COST STRATEGY
# ============================================================================

class ZeroCostStrategy:
    """
    Strategy for zero-cost operation.
    Prioritizes free providers, avoids expensive models.
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
        Determines if a model should be used.
        Returns: (should_use, fallback_suggestion)
        """
        if model in cls.EXPENSIVE_MODELS:
            return False, cls.FREE_FALLBACKS.get(model)
        return True, None

class APINodeRunner:
    """
    Daemon that runs mesh nodes.
    Implements zero-cost strategy.
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
        """Starts the mesh daemon"""
        self.running = True
        # In production: threading.Thread for each node
        print(f"DO