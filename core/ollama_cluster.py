"""
ollama_cluster.py — Round-robin load balancer for a local Ollama cluster.

Manages 3 Ollama instances on ports 11434 / 11435 / 11436 and distributes
inference calls across healthy nodes using a thread-safe round-robin strategy.
"""

from __future__ import annotations

import threading
from typing import Optional

import requests


class OllamaCluster:
    """Round-robin client for multiple local Ollama instances.

    Attributes
    ----------
    ports : list[int]
        Ordered list of ports to include in rotation.
    _index : int
        Current round-robin cursor (advances on every call to ``next_port``).
    _lock : threading.Lock
        Protects ``_index`` for concurrent access.
    """

    def __init__(self, ports: Optional[list[int]] = None) -> None:
        self.ports: list[int] = ports if ports is not None else [11434, 11435, 11436]
        self._index: int = 0
        self._lock = threading.Lock()

    # ── Health ────────────────────────────────────────────────────────────

    def is_alive(self, port: int) -> bool:
        """Return True if the Ollama instance on *port* responds within 2 s."""
        try:
            resp = requests.get(
                f"http://localhost:{port}/api/tags",
                timeout=2,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def active_ports(self) -> list[int]:
        """Return the subset of ``self.ports`` that are currently alive."""
        return [p for p in self.ports if self.is_alive(p)]

    # ── Routing ───────────────────────────────────────────────────────────

    def next_port(self) -> int:
        """Return the next healthy port in round-robin order.

        Iterates through all ports (starting from the current cursor) until it
        finds one that is alive.  Advances the cursor regardless of health so
        that a dead node does not monopolise the cursor position.

        Raises
        ------
        RuntimeError
            If no ports are alive at the time of the call.
        """
        with self._lock:
            n = len(self.ports)
            for _ in range(n):
                port = self.ports[self._index % n]
                self._index = (self._index + 1) % n
                if self.is_alive(port):
                    return port
        raise RuntimeError(
            f"No Ollama instances are alive on ports {self.ports}"
        )

    # ── Inference ─────────────────────────────────────────────────────────

    def call(
        self,
        messages: list[dict],
        model: str = "llama3",
        port: Optional[int] = None,
    ) -> str:
        """Send a chat completion request and return the full response text.

        Parameters
        ----------
        messages:
            OpenAI-style message list, e.g.
            ``[{"role": "user", "content": "Hello"}]``.
        model:
            Ollama model tag to use (must be pulled on the target instance).
        port:
            If provided, use this specific port; otherwise pick via
            ``next_port()``.

        Returns
        -------
        str
            Concatenated content from all streamed response chunks.

        Raises
        ------
        requests.HTTPError
            If the HTTP response status is not 2xx.
        RuntimeError
            If no healthy port is available (when *port* is None).
        """
        chosen_port = port if port is not None else self.next_port()
        url = f"http://localhost:{chosen_port}/api/chat"

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
        }

        response = requests.post(url, json=payload, stream=True, timeout=120)
        response.raise_for_status()

        chunks: list[str] = []
        for line in response.iter_lines():
            if not line:
                continue
            import json as _json
            try:
                data = _json.loads(line)
            except _json.JSONDecodeError:
                continue
            content = (
                data.get("message", {}).get("content", "")
                or data.get("response", "")
            )
            if content:
                chunks.append(content)

        return "".join(chunks)
