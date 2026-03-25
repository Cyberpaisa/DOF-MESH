"""
tests/test_ollama_cluster.py — Unit tests for core.ollama_cluster.OllamaCluster

All HTTP calls are mocked with unittest.mock so no real Ollama process is needed.
"""

import json
import threading
import unittest
from unittest.mock import MagicMock, patch

from core.ollama_cluster import OllamaCluster


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_tags_response(status_code: int = 200) -> MagicMock:
    """Return a mock requests.Response for /api/tags."""
    resp = MagicMock()
    resp.status_code = status_code
    return resp


def _make_stream_lines(*contents: str) -> list[bytes]:
    """Build encoded JSON lines that mimic Ollama streaming output."""
    lines = []
    for c in contents:
        lines.append(json.dumps({"message": {"content": c}}).encode())
    # Final done message with empty content
    lines.append(json.dumps({"message": {"content": ""}, "done": True}).encode())
    return lines


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestIsAlive(unittest.TestCase):

    @patch("core.ollama_cluster.requests.get")
    def test_is_alive_returns_true_on_200(self, mock_get):
        mock_get.return_value = _mock_tags_response(200)
        cluster = OllamaCluster()
        self.assertTrue(cluster.is_alive(11434))

    @patch("core.ollama_cluster.requests.get")
    def test_is_alive_returns_false_on_500(self, mock_get):
        mock_get.return_value = _mock_tags_response(500)
        cluster = OllamaCluster()
        self.assertFalse(cluster.is_alive(11435))

    @patch("core.ollama_cluster.requests.get", side_effect=Exception("connection refused"))
    def test_is_alive_returns_false_on_exception(self, _mock_get):
        cluster = OllamaCluster()
        self.assertFalse(cluster.is_alive(11436))

    @patch("core.ollama_cluster.requests.get")
    def test_is_alive_uses_correct_url(self, mock_get):
        mock_get.return_value = _mock_tags_response(200)
        cluster = OllamaCluster()
        cluster.is_alive(11434)
        mock_get.assert_called_once_with(
            "http://localhost:11434/api/tags", timeout=2
        )


class TestActivePorts(unittest.TestCase):

    @patch("core.ollama_cluster.requests.get")
    def test_active_ports_all_alive(self, mock_get):
        mock_get.return_value = _mock_tags_response(200)
        cluster = OllamaCluster()
        self.assertEqual(cluster.active_ports(), [11434, 11435, 11436])

    @patch("core.ollama_cluster.requests.get")
    def test_active_ports_none_alive(self, mock_get):
        mock_get.return_value = _mock_tags_response(503)
        cluster = OllamaCluster()
        self.assertEqual(cluster.active_ports(), [])

    @patch("core.ollama_cluster.requests.get")
    def test_active_ports_partial(self, mock_get):
        # Only the first call (port 11434) returns 200; the rest return 503
        mock_get.side_effect = [
            _mock_tags_response(200),
            _mock_tags_response(503),
            _mock_tags_response(503),
        ]
        cluster = OllamaCluster()
        self.assertEqual(cluster.active_ports(), [11434])


class TestNextPort(unittest.TestCase):

    @patch("core.ollama_cluster.requests.get")
    def test_next_port_round_robin_order(self, mock_get):
        mock_get.return_value = _mock_tags_response(200)
        cluster = OllamaCluster()
        ports = [cluster.next_port() for _ in range(6)]
        self.assertEqual(ports, [11434, 11435, 11436, 11434, 11435, 11436])

    @patch("core.ollama_cluster.requests.get")
    def test_next_port_skips_dead_node(self, mock_get):
        # 11434 dead, 11435 alive, 11436 alive
        mock_get.side_effect = [
            _mock_tags_response(503),  # 11434 dead
            _mock_tags_response(200),  # 11435 alive → returned
        ] * 10
        cluster = OllamaCluster()
        port = cluster.next_port()
        self.assertEqual(port, 11435)

    @patch(
        "core.ollama_cluster.requests.get",
        side_effect=Exception("all down"),
    )
    def test_next_port_raises_when_all_dead(self, _mock_get):
        cluster = OllamaCluster()
        with self.assertRaises(RuntimeError):
            cluster.next_port()

    @patch("core.ollama_cluster.requests.get")
    def test_next_port_thread_safe(self, mock_get):
        """Concurrent calls must not produce duplicate indices or race conditions."""
        mock_get.return_value = _mock_tags_response(200)
        cluster = OllamaCluster()
        results: list[int] = []
        lock = threading.Lock()

        def worker():
            p = cluster.next_port()
            with lock:
                results.append(p)

        threads = [threading.Thread(target=worker) for _ in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(results), 30)
        # Every returned port must be in the cluster's port list
        for p in results:
            self.assertIn(p, cluster.ports)


class TestCall(unittest.TestCase):

    @patch("core.ollama_cluster.requests.post")
    @patch("core.ollama_cluster.requests.get")
    def test_call_returns_joined_content(self, mock_get, mock_post):
        mock_get.return_value = _mock_tags_response(200)

        stream_lines = _make_stream_lines("Hello", ", ", "world")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_lines.return_value = stream_lines
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        cluster = OllamaCluster()
        result = cluster.call([{"role": "user", "content": "Hi"}], model="llama3")
        self.assertEqual(result, "Hello, world")

    @patch("core.ollama_cluster.requests.post")
    @patch("core.ollama_cluster.requests.get")
    def test_call_uses_explicit_port(self, mock_get, mock_post):
        mock_get.return_value = _mock_tags_response(200)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_lines.return_value = _make_stream_lines("ok")
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        cluster = OllamaCluster()
        cluster.call([{"role": "user", "content": "test"}], model="phi3", port=11436)

        call_url = mock_post.call_args[0][0]
        self.assertIn("11436", call_url)

    @patch("core.ollama_cluster.requests.post")
    @patch("core.ollama_cluster.requests.get")
    def test_call_sends_stream_true(self, mock_get, mock_post):
        mock_get.return_value = _mock_tags_response(200)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_lines.return_value = _make_stream_lines("data")
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        cluster = OllamaCluster()
        cluster.call([{"role": "user", "content": "x"}])

        payload = mock_post.call_args[1]["json"]
        self.assertTrue(payload["stream"])

    @patch("core.ollama_cluster.requests.post")
    @patch("core.ollama_cluster.requests.get")
    def test_call_raises_on_http_error(self, mock_get, mock_post):
        mock_get.return_value = _mock_tags_response(200)

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("500 Server Error")
        mock_post.return_value = mock_resp

        cluster = OllamaCluster()
        with self.assertRaises(Exception):
            cluster.call([{"role": "user", "content": "x"}])

    @patch("core.ollama_cluster.requests.post")
    @patch("core.ollama_cluster.requests.get")
    def test_call_uses_response_fallback_field(self, mock_get, mock_post):
        """Handles the /api/generate-style response field 'response'."""
        mock_get.return_value = _mock_tags_response(200)

        lines = [json.dumps({"response": "chunk"}).encode()]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_lines.return_value = lines
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        cluster = OllamaCluster()
        result = cluster.call([{"role": "user", "content": "y"}], port=11434)
        self.assertEqual(result, "chunk")


class TestCustomPorts(unittest.TestCase):

    @patch("core.ollama_cluster.requests.get")
    def test_custom_port_list(self, mock_get):
        mock_get.return_value = _mock_tags_response(200)
        cluster = OllamaCluster(ports=[12000, 12001])
        self.assertEqual(cluster.active_ports(), [12000, 12001])

    def test_default_ports(self):
        cluster = OllamaCluster()
        self.assertEqual(cluster.ports, [11434, 11435, 11436])


if __name__ == "__main__":
    unittest.main()
