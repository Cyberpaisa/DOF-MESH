import socket
import threading
import time
import json
from typing import Optional


class FederationManager:
    def __init__(self, my_id: str, port: int):
        self.my_id = my_id
        self.port = port
        self.peers = {}
        self.running = False
        self.server_thread: Optional[threading.Thread] = None
        
    def mock_udp_discovery(self):
        """Mock UDP broadcast discovery"""
        print(f"[{self.my_id}] Broadcasting discovery...")
        time.sleep(0.5)
        # Mock discovering node-beta on port 7893
        if self.my_id == "node-alpha":
            self.peers["node-beta"] = ("localhost", 7893)
            print(f"[{self.my_id}] Discovered node-beta at localhost:7893")
        
    def start_server(self):
        """Start TCP server for receiving messages"""
        self.running = True
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("localhost", self.port))
        sock.listen(5)
        
        while self.running:
            try:
                sock.settimeout(1)
                conn, addr = sock.accept()
                data = conn.recv(1024).decode('utf-8')
                if data:
                    msg = json.loads(data)
                    print(f"[{self.my_id}] Received from {msg.get('from')}: {msg.get('content')}")
                conn.close()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[{self.my_id}] Server error: {e}")
        sock.close()
        print(f"[{self.my_id}] Server stopped")
        
    def send_message(self, peer_id: str, content: str):
        """Send message to a peer"""
        if peer_id not in self.peers:
            print(f"[{self.my_id}] Unknown peer: {peer_id}")
            return
            
        host, port = self.peers[peer_id]
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            msg = {
                "from": self.my_id,
                "to": peer_id,
                "content": content,
                "timestamp": time.time()
            }
            sock.send(json.dumps(msg).encode('utf-8'))
            sock.close()
            print(f"[{self.my_id}] Sent to {peer_id}: {content}")
        except Exception as e:
            print(f"[{self.my_id}] Send failed to {peer_id}: {e}")
    
    def start(self):
        """Start federation manager"""
        print(f"[{self.my_id}] Starting on port {self.port}...")
        self.server_thread = threading.Thread(target=self.start_server, daemon=True)
        self.server_thread.start()
        time.sleep(0.2)  # Allow server to bind
        
    def stop(self):
        """Stop federation manager"""
        self.running = False
        if self.server_thread:
            self.server_thread.join(timeout=2)
        print(f"[{self.my_id}] Stopped")


def run_demo():
    """Main demo function"""
    print("DOF Federation Demo Starting...\n")
    
    # Create two nodes
    node_a = FederationManager("node-alpha", 7892)
    node_b = FederationManager("node-beta", 7893)
    
    # Start both nodes
    node_a.start()
    node_b.start()
    
    time.sleep(1)  # Allow servers to start
    
    # Mock discovery
    node_a.mock_udp_discovery()
    time.sleep(0.5)
    
    # Send message from A to B
    print()
    node_a.send_message("node-beta", "Hello from node-alpha!")
    
    # Let message be delivered
    time.sleep(1)
    
    # Clean shutdown
    print("\nShutting down...")
    node_a.stop()
    node_b.stop()
    
    print("\nDemo completed successfully!")


if __name__ == "__main__":
    run_demo()
