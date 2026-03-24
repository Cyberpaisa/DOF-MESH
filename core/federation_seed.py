import argparse
import json
import socket
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib import request, parse
from typing import Dict, Tuple, List, Optional


class SeedHTTPHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.seed_server = kwargs.pop('seed_server')
        super().__init__(*args, **kwargs)

    def do_POST(self):
        if self.path == '/register':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                node_id = data.get('node_id')
                host = data.get('host')
                port = data.get('port')
                if node_id and host and port:
                    self.seed_server.register(node_id, host, port)
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'OK')
                else:
                    self.send_error(400, 'Missing fields')
            except Exception:
                self.send_error(400, 'Invalid JSON')
        else:
            self.send_error(404)

    def do_GET(self):
        if self.path == '/peers':
            peers = self.seed_server.get_peers()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(peers).encode('utf-8'))
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass


class SeedServer:
    def __init__(self, host='0.0.0.0', port=7893):
        self.host = host
        self.port = port
        self.peers: Dict[str, Tuple[str, int, float]] = {}
        self.lock = threading.Lock()
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        self.server = HTTPServer((self.host, self.port), lambda *args, **kwargs: SeedHTTPHandler(*args, seed_server=self, **kwargs))

    def register(self, node_id: str, host: str, port: int):
        with self.lock:
            self.peers[node_id] = (host, port, time.time())

    def get_peers(self) -> List[Dict[str, str]]:
        with self.lock:
            now = time.time()
            active = []
            for node_id, (host, port, timestamp) in list(self.peers.items()):
                if now - timestamp > 300:
                    del self.peers[node_id]
                else:
                    active.append({'node_id': node_id, 'host': host, 'port': str(port)})
            return active

    def _cleanup_loop(self):
        while True:
            time.sleep(60)
            self.get_peers()

    def serve_forever(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


class SeedClient:
    def __init__(self, seed_host: str, seed_port: int):
        self.base_url = f'http://{seed_host}:{seed_port}'

    def register(self, node_id: str, host: str, port: int) -> bool:
        data = json.dumps({'node_id': node_id, 'host': host, 'port': port}).encode('utf-8')
        req = request.Request(f'{self.base_url}/register', data=data, method='POST', headers={'Content-Type': 'application/json'})
        try:
            with request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def get_peers(self) -> List[Dict[str, str]]:
        try:
            with request.urlopen(f'{self.base_url}/peers', timeout=5) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception:
            return []


_seed_client_instance: Optional[SeedClient] = None
_seed_client_lock = threading.Lock()


def get_seed_client(host: str = 'localhost', port: int = 7893) -> SeedClient:
    global _seed_client_instance
    with _seed_client_lock:
        if _seed_client_instance is None:
            _seed_client_instance = SeedClient(host, port)
        return _seed_client_instance


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='DOF Federation Seed')
    parser.add_argument('--serve', action='store_true', help='Start seed server')
    parser.add_argument('--peers', action='store_true', help='Query peers from seed')
    parser.add_argument('--host', default='localhost', help='Seed server host')
    parser.add_argument('--port', type=int, default=7893, help='Seed server port')
    args = parser.parse_args()

    if args.serve:
        server = SeedServer(args.host, args.port)
        print(f'Seed server starting on {args.host}:{args.port}')
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.shutdown()
            print('\nSeed server stopped')
    elif args.peers:
        client = get_seed_client(args.host, args.port)
        peers = client.get_peers()
        print(json.dumps(peers, indent=2))
    else:
        parser.print_help()
