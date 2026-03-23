"""
Remote Node Adapter — Integración con APIs gratuitas para mesh remoto autónomo.

Mapea web models (Gemini, GPT, Kimi, Qwen, MiniMax) a providers gratuitos:
- Gemini → Cerebras (Qwen 3.5) o NVIDIA (Qwen 3.3 70B)
- GPT → Groq (Llama 3.3 70B)
- Kimi → Zo (Claude equivalent)
- Qwen → Together AI (Qwen models)
- MiniMax → MiniMax API directo

Costo: $0 en tokens (todas apis gratuitas).
"""

import json
import os
import re
import time
import logging
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger("core.remote_node_adapter")

# ═══════════════════════════════════════════════════
# PROVIDER MAPPING
# ═══════════════════════════════════════════════════

class RemoteProvider(Enum):
    GROQ = "groq"           # Llama 3.3 70B
    CEREBRAS = "cerebras"   # Qwen 3.5
    ZO = "zo"               # Claude equivalent
    TOGETHER = "together"   # Qwen models
    MINIMAX = "minimax"     # Direct API
    NVIDIA = "nvidia"       # NIM — Qwen 3.3 70B

REMOTE_NODE_MAPPING = {
    "gpt-legion": RemoteProvider.NVIDIA,      # GPT → NVIDIA NIM (Groq key expired)
    "gemini-web": RemoteProvider.CEREBRAS,    # Gemini → Cerebras (Qwen 3 235B)
    "kimi-web": RemoteProvider.NVIDIA,        # Kimi → NVIDIA NIM
    "qwen-coder-480b": RemoteProvider.CEREBRAS,  # Qwen → Cerebras (Qwen 3 235B)
    "minimax": RemoteProvider.MINIMAX,        # MiniMax → direct API
}

# ═══════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════

@dataclass
class RemoteNodeRequest:
    """Request to send to remote node."""
    node_id: str
    msg_id: str
    task_title: str
    task_description: str
    deadline: str
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

@dataclass
class RemoteNodeResponse:
    """Response from remote node."""
    node_id: str
    msg_id: str
    status: str  # ACCEPTED, COMPLETED, FAILED
    response_text: str
    deliverable_preview: str = ""
    code: str = ""
    duration_seconds: float = 0.0
    timestamp: float = None
    error: str = ""

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

# ═══════════════════════════════════════════════════
# REMOTE NODE ADAPTER
# ═══════════════════════════════════════════════════

class RemoteNodeAdapter:
    """Sends work orders to remote models via free APIs."""

    def __init__(self):
        self.provider_clients = self._init_providers()
        self.request_history = []

    def _init_providers(self) -> Dict[RemoteProvider, Any]:
        """Initialize free API clients from .env keys."""
        # Load .env
        from dotenv import load_dotenv
        load_dotenv()

        clients = {}

        try:
            # Groq (GROQ_API_KEY)
            groq_key = os.environ.get("GROQ_API_KEY")
            if groq_key:
                from groq import Groq
                clients[RemoteProvider.GROQ] = Groq(api_key=groq_key)
                logger.info("✓ Groq initialized")
            else:
                logger.warning("GROQ_API_KEY not set")
        except Exception as e:
            logger.warning(f"Groq init failed: {e}")

        try:
            # Cerebras (CEREBRAS_API_KEY)
            cerebras_key = os.environ.get("CEREBRAS_API_KEY")
            if cerebras_key:
                import openai
                cerebras_client = openai.OpenAI(
                    api_key=cerebras_key,
                    base_url="https://api.cerebras.ai/v1"
                )
                clients[RemoteProvider.CEREBRAS] = cerebras_client
                logger.info("✓ Cerebras initialized")
            else:
                logger.warning("CEREBRAS_API_KEY not set")
        except Exception as e:
            logger.warning(f"Cerebras init failed: {e}")

        try:
            # MiniMax (MINIMAX_API_KEY)
            minimax_key = os.environ.get("MINIMAX_API_KEY")
            if minimax_key:
                import requests
                clients[RemoteProvider.MINIMAX] = requests
                logger.info("✓ MiniMax initialized")
            else:
                logger.warning("MINIMAX_API_KEY not set")
        except Exception as e:
            logger.warning(f"MiniMax init failed: {e}")

        try:
            # NVIDIA NIM (NVIDIA_API_KEY)
            nvidia_key = os.environ.get("NVIDIA_API_KEY")
            if nvidia_key:
                import openai
                nvidia_client = openai.OpenAI(
                    api_key=nvidia_key,
                    base_url="https://integrate.api.nvidia.com/v1"
                )
                clients[RemoteProvider.NVIDIA] = nvidia_client
                logger.info("✓ NVIDIA NIM initialized")
            else:
                logger.warning("NVIDIA_API_KEY not set")
        except Exception as e:
            logger.warning(f"NVIDIA NIM init failed: {e}")

        return clients

    def dispatch(self, node_id: str, work_order: Dict) -> Optional[RemoteNodeResponse]:
        """
        Send work order to remote node via appropriate free API.

        Returns RemoteNodeResponse with status and deliverable.
        """
        provider = REMOTE_NODE_MAPPING.get(node_id)
        if not provider:
            logger.error(f"No provider mapping for {node_id}")
            return None

        client = self.provider_clients.get(provider)
        if not client:
            logger.error(f"Provider {provider} not initialized")
            return None

        # Build prompt from work order
        prompt = self._build_prompt(node_id, work_order)

        start = time.time()
        try:
            if provider == RemoteProvider.GROQ:
                response = self._call_groq(client, prompt)
            elif provider == RemoteProvider.CEREBRAS:
                response = self._call_cerebras(client, prompt)
            elif provider == RemoteProvider.MINIMAX:
                response = self._call_minimax(client, prompt)
            elif provider == RemoteProvider.NVIDIA:
                response = self._call_nvidia(client, prompt)
            else:
                response = None

            duration = time.time() - start

            if response:
                node_response = RemoteNodeResponse(
                    node_id=node_id,
                    msg_id=work_order.get("msg_id", "unknown"),
                    status="COMPLETED",
                    response_text=response.get("text", ""),
                    deliverable_preview=response.get("preview", ""),
                    code=response.get("code", ""),
                    duration_seconds=duration,
                )
                self.request_history.append(asdict(node_response))
                return node_response
            else:
                return RemoteNodeResponse(
                    node_id=node_id,
                    msg_id=work_order.get("msg_id"),
                    status="FAILED",
                    response_text="",
                    error="Provider call failed",
                    duration_seconds=duration,
                )

        except Exception as e:
            logger.error(f"Dispatch to {node_id} failed: {e}")
            return RemoteNodeResponse(
                node_id=node_id,
                msg_id=work_order.get("msg_id"),
                status="FAILED",
                response_text="",
                error=str(e),
                duration_seconds=time.time() - start,
            )

    # ─────────────────────────────────────────────────
    # PROVIDER-SPECIFIC CALLERS
    # ─────────────────────────────────────────────────

    def _call_groq(self, client, prompt: str) -> Optional[Dict]:
        """Call Groq (Llama 3.3 70B)."""
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000,
            )
            text = response.choices[0].message.content
            return {
                "text": text,
                "preview": text[:200],
                "code": self._extract_code_block(text)
            }
        except Exception as e:
            logger.error(f"Groq call failed: {e}")
            return None

    def _call_cerebras(self, client, prompt: str) -> Optional[Dict]:
        """Call Cerebras (Llama 3.3 70B)."""
        try:
            response = client.chat.completions.create(
                model="qwen-3-235b-a22b-instruct-2507",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000,
            )
            text = response.choices[0].message.content
            return {
                "text": text,
                "preview": text[:200],
                "code": self._extract_code_block(text)
            }
        except Exception as e:
            logger.error(f"Cerebras call failed: {e}")
            return None

    def _call_zo(self, client, prompt: str) -> Optional[Dict]:
        """Call Zo (Claude equivalent)."""
        try:
            response = client.messages.create(
                model="claude-3-haiku",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
            )
            text = response.content[0].text
            return {
                "text": text,
                "preview": text[:200],
                "code": self._extract_code_block(text)
            }
        except Exception as e:
            logger.error(f"Zo call failed: {e}")
            return None

    def _call_together(self, client, prompt: str) -> Optional[Dict]:
        """Call Together AI (Qwen models)."""
        try:
            response = client.chat.completions.create(
                model="meta-llama/Llama-3-70b-chat-hf",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000,
            )
            text = response.choices[0].message.content
            return {
                "text": text,
                "preview": text[:200],
                "code": self._extract_code_block(text)
            }
        except Exception as e:
            logger.error(f"Together AI call failed: {e}")
            return None

    def _call_minimax(self, client, prompt: str) -> Optional[Dict]:
        """Call MiniMax API."""
        try:
            import os
            url = "https://api.minimax.chat/v1/text/chatcompletion"
            headers = {
                "Authorization": f"Bearer {os.getenv('MINIMAX_API_KEY')}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "MiniMax-M2.1",
                "messages": [{"sender_type": "USER", "text": prompt}],
                "stream": False,
                "reply_constraints": {"sender_type": "BOT"}
            }
            response = client.post(url, json=payload, headers=headers, timeout=30)
            data = response.json()
            text = data.get("reply", "")
            return {
                "text": text,
                "preview": text[:200],
                "code": self._extract_code_block(text)
            }
        except Exception as e:
            logger.error(f"MiniMax call failed: {e}")
            return None

    def _call_nvidia(self, client, prompt: str) -> Optional[Dict]:
        """Call NVIDIA NIM (Qwen 3.3 70B)."""
        try:
            response = client.chat.completions.create(
                model="meta/llama-3.3-70b-instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000,
            )
            text = response.choices[0].message.content
            return {
                "text": text,
                "preview": text[:200],
                "code": self._extract_code_block(text)
            }
        except Exception as e:
            logger.error(f"NVIDIA NIM call failed: {e}")
            return None

    # ─────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────

    def _build_prompt(self, node_id: str, work_order: Dict) -> str:
        """Build prompt from work order."""
        task = work_order.get("task", {})
        return f"""You are a mesh node (ID: {node_id}) in the DOF autonomous system.

Process this work order:
- Title: {task.get('title', 'Unknown')}
- Description: {task.get('description', 'No description')}
- Deadline: {task.get('timeline', 'ASAP')}

Your response MUST be valid JSON:
{{
  "msg_id": "{work_order.get('msg_id')}",
  "from_node": "{node_id}",
  "status": "ACCEPTED|COMPLETED",
  "response_summary": "...",
  "code": "... complete implementation ...",
  "notes": "..."
}}

Respond ONLY with the JSON object, no markdown, no explanation."""

    def _extract_code_block(self, text: str) -> str:
        """Extract Python code from response."""
        match = re.search(r'```(?:python)?\n(.*?)```', text, re.DOTALL)
        return match.group(1) if match else ""

    def get_history(self) -> list:
        """Get request history."""
        return self.request_history

# ═══════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    adapter = RemoteNodeAdapter()

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test all providers
        test_order = {
            "msg_id": "TEST-001",
            "task": {
                "title": "Test Task",
                "description": "Simple test to verify provider integration",
                "timeline": "Now"
            }
        }
        for node_id in ["gpt-legion", "gemini-web", "kimi-web"]:
            print(f"\n🚀 Testing {node_id}...")
            result = adapter.dispatch(node_id, test_order)
            if result:
                print(f"  Status: {result.status}")
                print(f"  Duration: {result.duration_seconds:.2f}s")
            else:
                print(f"  FAILED")
    else:
        print("Usage: python3 core/remote_node_adapter.py test")
