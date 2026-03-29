"""
hyperion_http.py — HTTP Bridge para DOF Mesh Hyperion.

Expone DistributedMeshQueue via REST. Permite que nodos en máquinas
distintas se comuniquen sin filesystem compartido.

Endpoints:
  POST /enqueue          — encolar tarea
  GET  /dequeue/{shard}  — desencolar del shard
  GET  /status           — estado del sistema
  GET  /health           — healthcheck
  POST /broadcast        — enviar a todos los agentes

Uso:
  # Servidor (en cada máquina)
  python3 core/hyperion_http.py --host 0.0.0.0 --port 8765

  # Cliente (desde otra máquina)
  curl -X POST http://machine-a:8765/enqueue \
       -H 'Content-Type: application/json' \
       -d '{"task_id":"t1","shard_key":"agent-5","prompt":"analiza"}'
"""
import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger("core.hyperion_http")

# ── HTTP Handler (stdlib, sin dependencias externas) ──────────────────────────

from http.server import BaseHTTPRequestHandler, HTTPServer
from core.dof_sharding import DOFShardManager
from core.dof_distributed_queue import DistributedMeshQueue, DistributedTask

REPO_ROOT = Path(__file__).parent.parent
DEFAULT_MACHINES = ["machine-a", "machine-b", "machine-c", "machine-d", "machine-e"]


class HyperionHTTPServer:
    """
    Servidor HTTP ligero para el Hyperion Bridge.
    Usa solo stdlib — sin FastAPI ni uvicorn.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        machines: list[str] = None,
        shard_count: int = 10,
    ):
        self.host = host
        self.port = port
        machines = machines or DEFAULT_MACHINES
        self._sm = DOFShardManager(machines, shard_count=shard_count, replication_factor=3)
        self._queue = DistributedMeshQueue(
            node_id=f"http-bridge-{host}:{port}",
            shard_manager=self._sm,
            wal_path=str(REPO_ROOT / "logs" / "wal" / "http-bridge"),
        )
        self._requests = 0
        self._start_time = time.time()
        logger.info("HyperionHTTP ready: %s:%d | %d machines | %d shards",
                    host, port, len(machines), shard_count)

    def run(self):
        server = self
        queue  = self._queue
        sm     = self._sm

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                logger.debug(fmt, *args)

            def _json(self, code: int, data: dict):
                body = json.dumps(data, ensure_ascii=False).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _read_body(self) -> dict:
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length) if length else b"{}"
                return json.loads(raw)

            def do_GET(self):
                server._requests += 1
                path = self.path.split("?")[0]

                if path == "/health":
                    self._json(200, {"status": "ok", "uptime_s": round(time.time() - server._start_time)})

                elif path == "/status":
                    self._json(200, {
                        "status": "ok",
                        "queue": queue.status(),
                        "requests_total": server._requests,
                        "uptime_s": round(time.time() - server._start_time),
                    })

                elif path.startswith("/dequeue/"):
                    try:
                        shard_id = int(path.split("/dequeue/")[1])
                        task = queue.dequeue(shard_id, timeout=0.5)
                        if task:
                            self._json(200, task.to_dict())
                        else:
                            self._json(204, {"message": "queue empty"})
                    except (ValueError, IndexError):
                        self._json(400, {"error": "invalid shard_id"})

                elif path == "/dequeue":
                    task = queue.dequeue_any(timeout=0.5)
                    if task:
                        self._json(200, task.to_dict())
                    else:
                        self._json(204, {"message": "all queues empty"})

                else:
                    self._json(404, {"error": "not found"})

            def do_POST(self):
                server._requests += 1
                path = self.path.split("?")[0]

                if path == "/enqueue":
                    try:
                        data = self._read_body()
                        task = DistributedTask.from_dict(data)
                        if not task.task_id:
                            task.task_id = f"http-{int(time.time_ns())}"
                        queue.enqueue(task)
                        shard = sm.get_shard_for_key(task.shard_key or task.task_id)
                        self._json(201, {
                            "task_id": task.task_id,
                            "shard": shard.id,
                            "primary": shard.primary_node,
                        })
                    except Exception as e:
                        self._json(400, {"error": str(e)})

                elif path == "/broadcast":
                    try:
                        data = self._read_body()
                        prompt = data.get("prompt", "")
                        agents = data.get("agents", ["architect","researcher","guardian",
                                                      "verifier","narrator","devops"])
                        ids = []
                        for agent in agents:
                            task = DistributedTask(
                                task_id=f"{agent}-{int(time.time_ns())}",
                                shard_key=agent,
                                prompt=prompt,
                                metadata=data,
                            )
                            queue.enqueue(task)
                            ids.append(task.task_id)
                        self._json(201, {"enqueued": len(ids), "task_ids": ids})
                    except Exception as e:
                        self._json(400, {"error": str(e)})

                elif path == "/task_done":
                    try:
                        data = self._read_body()
                        task = DistributedTask.from_dict(data)
                        queue.task_done(task)
                        self._json(200, {"confirmed": task.task_id})
                    except Exception as e:
                        self._json(400, {"error": str(e)})

                else:
                    self._json(404, {"error": "not found"})

        class _ReuseHTTPServer(HTTPServer):
            allow_reuse_address = True

            def server_bind(self):
                import socket as _socket
                self.socket.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
                if hasattr(_socket, "SO_REUSEPORT"):
                    self.socket.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEPORT, 1)
                super().server_bind()

        httpd = _ReuseHTTPServer((self.host, self.port), Handler)
        logger.info("Hyperion HTTP listening on %s:%d", self.host, self.port)
        print(f"✅ Hyperion HTTP Bridge → http://{self.host}:{self.port}")
        print(f"   /health  /status  /enqueue  /dequeue  /dequeue/{{shard}}  /broadcast")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Hyperion HTTP stopped")
        finally:
            httpd.server_close()


# ── Cliente HTTP ligero ───────────────────────────────────────────────────────

class HyperionClient:
    """
    Cliente HTTP para comunicarse con HyperionHTTPServer desde otra máquina.

    Ejemplo:
        client = HyperionClient("http://machine-a:8765")
        client.enqueue("t1", "agent-5", "analiza el mesh")
        task = client.dequeue()
    """

    def __init__(self, base_url: str = "http://localhost:8765"):
        self.base_url = base_url.rstrip("/")

    def enqueue(self, task_id: str, shard_key: str, prompt: str,
                priority: int = 1, metadata: dict = None) -> dict:
        import urllib.request
        data = json.dumps({
            "task_id": task_id, "shard_key": shard_key,
            "prompt": prompt, "priority": priority,
            **(metadata or {}),
        }).encode()
        req = urllib.request.Request(
            f"{self.base_url}/enqueue", data=data,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())

    def dequeue(self, shard_id: Optional[int] = None) -> Optional[dict]:
        import urllib.request
        url = f"{self.base_url}/dequeue/{shard_id}" if shard_id is not None else f"{self.base_url}/dequeue"
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                return json.loads(r.read()) if r.status == 200 else None
        except Exception:
            return None

    def status(self) -> dict:
        import urllib.request
        with urllib.request.urlopen(f"{self.base_url}/status", timeout=5) as r:
            return json.loads(r.read())

    def health(self) -> bool:
        import urllib.request
        try:
            with urllib.request.urlopen(f"{self.base_url}/health", timeout=3) as r:
                return r.status == 200
        except Exception:
            return False

    def broadcast(self, prompt: str, agents: list[str] = None) -> dict:
        import urllib.request
        data = json.dumps({"prompt": prompt, "agents": agents or []}).encode()
        req = urllib.request.Request(
            f"{self.base_url}/broadcast", data=data,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
                        datefmt="%H:%M:%S")
    parser = argparse.ArgumentParser(description="Hyperion HTTP Bridge")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--shards", type=int, default=10)
    args = parser.parse_args()

    srv = HyperionHTTPServer(host=args.host, port=args.port, shard_count=args.shards)
    srv.run()


if __name__ == "__main__":
    main()
