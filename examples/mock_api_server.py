"""
Mock API Server — Minimal deterministic REST API for testing the observability framework.

stdlib only (http.server), no Flask.
Endpoints:
  GET  /health          → {"status": "ok"}
  GET  /analyze          → Analysis with optional latency/failure
  POST /analyze          → Analysis from POST body with optional latency/failure

Query params:
  ?latency_ms=N   Add artificial latency (milliseconds)
  ?fail=true      Force a 503 error response

Usage:
    python examples/mock_api_server.py
    python examples/mock_api_server.py --port 8765
"""

import json
import time
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


ANALYSIS_RESPONSE = {
    "titulo": "Analisis de mercado ERC-8004",
    "resumen": (
        "El ecosistema de agentes autonomos en Avalanche muestra crecimiento sostenido. "
        "Se identificaron 47 agentes activos con Trust Score promedio de 72.3. "
        "Los principales proveedores de infraestructura mantienen SLAs superiores al 99.5%. "
        "Recomendacion: incrementar cobertura de monitoreo en agentes con score inferior a 60."
    ),
    "metricas": {
        "agentes_activos": 47,
        "trust_score_promedio": 72.3,
        "sla_infraestructura": 99.5,
        "transacciones_24h": 1283,
    },
    "fuentes": [
        "https://8004scan.io/agents",
        "https://snowtrace.io/stats",
    ],
    "estado": "completado",
    "confianza": 0.87,
}


class MockAPIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/health":
            self._respond(200, {"status": "ok"})
            return

        if parsed.path == "/analyze":
            self._handle_analyze(params)
            return

        self._respond(404, {"error": "not_found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/analyze":
            # Read body but response is deterministic regardless
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                self.rfile.read(content_length)
            self._handle_analyze(params)
            return

        self._respond(404, {"error": "not_found"})

    def _handle_analyze(self, params: dict):
        # Configurable failure
        if "fail" in params and params["fail"][0].lower() == "true":
            self._respond(503, {"error": "service_unavailable", "message": "Simulated failure"})
            return

        # Configurable latency
        latency_ms = int(params.get("latency_ms", ["0"])[0])
        if latency_ms > 0:
            time.sleep(latency_ms / 1000.0)

        self._respond(200, ANALYSIS_RESPONSE)

    def _respond(self, status: int, body: dict):
        response = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        # Suppress default request logging for clean experiment output
        pass


def run_server(host: str = "127.0.0.1", port: int = 8765):
    server = HTTPServer((host, port), MockAPIHandler)
    print(f"Mock API server running at http://{host}:{port}")
    print("Endpoints: GET /health, GET|POST /analyze")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mock API Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    run_server(args.host, args.port)
