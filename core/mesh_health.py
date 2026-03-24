#!/usr/bin/env python3
"""
DOF Mesh Health Checker
Checks health of all mesh nodes: local Ollama, API providers, federation bridge, and local mesh files.
"""

import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import socket


class HealthStatus(Enum):
    """Health status of a mesh node."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"


@dataclass
class NodeHealth:
    """Health information for a single node."""
    node_id: str
    status: HealthStatus
    latency_ms: Optional[float] = None
    error_msg: Optional[str] = None

    def to_dict(self):
        d = asdict(self)
        d['status'] = self.status.value
        return d


class MeshHealth:
    """Singleton health checker for DOF mesh nodes."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
    
    def check_all(self) -> Dict[str, NodeHealth]:
        """Check health of all mesh components."""
        results = {}
        
        # Check local Ollama
        results["ollama"] = self._check_ollama()
        
        # Check API providers
        api_providers = [
            ("openai", "https://api.openai.com/v1/models"),
            ("anthropic", "https://api.anthropic.com/v1/messages"),
            ("google", "https://generativelanguage.googleapis.com/v1beta/models"),
            ("deepseek", "https://api.deepseek.com/v1/models"),
        ]
        for name, url in api_providers:
            results[name] = self._check_api_provider(name, url)
        
        # Check federation bridge
        results["federation_bridge"] = self._check_federation_bridge()
        
        # Check local mesh files
        results["local_mesh_files"] = self._check_local_mesh_files()
        
        return results
    
    def _check_ollama(self) -> NodeHealth:
        """Check local Ollama instance."""
        start = time.time()
        try:
            req = Request("http://localhost:11434/api/tags", method="GET")
            with urlopen(req, timeout=5) as response:
                if response.status == 200:
                    latency = (time.time() - start) * 1000
                    return NodeHealth(
                        node_id="ollama",
                        status=HealthStatus.HEALTHY,
                        latency_ms=round(latency, 2)
                    )
        except (URLError, HTTPError, socket.timeout) as e:
            latency = (time.time() - start) * 1000
            return NodeHealth(
                node_id="ollama",
                status=HealthStatus.OFFLINE,
                latency_ms=round(latency, 2),
                error_msg=str(e)
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return NodeHealth(
                node_id="ollama",
                status=HealthStatus.DEGRADED,
                latency_ms=round(latency, 2),
                error_msg=str(e)
            )
        
        latency = (time.time() - start) * 1000
        return NodeHealth(
            node_id="ollama",
            status=HealthStatus.DEGRADED,
            latency_ms=round(latency, 2),
            error_msg="Unexpected response"
        )
    
    def _check_api_provider(self, name: str, url: str) -> NodeHealth:
        """Check external API provider with HEAD request."""
        start = time.time()
        try:
            # Use HEAD request to avoid large responses
            req = Request(url, method="HEAD")
            req.add_header("User-Agent", "DOF-Mesh-Health-Checker/1.0")
            with urlopen(req, timeout=5) as response:
                latency = (time.time() - start) * 1000
                status = HealthStatus.HEALTHY if response.status < 500 else HealthStatus.DEGRADED
                return NodeHealth(
                    node_id=name,
                    status=status,
                    latency_ms=round(latency, 2)
                )
        except HTTPError as e:
            # 4xx errors mean API is reachable but request was bad
            latency = (time.time() - start) * 1000
            return NodeHealth(
                node_id=name,
                status=HealthStatus.HEALTHY if e.code < 500 else HealthStatus.DEGRADED,
                latency_ms=round(latency, 2),
                error_msg=f"HTTP {e.code}"
            )
        except (URLError, socket.timeout) as e:
            latency = (time.time() - start) * 1000
            return NodeHealth(
                node_id=name,
                status=HealthStatus.OFFLINE,
                latency_ms=round(latency, 2),
                error_msg=str(e)
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return NodeHealth(
                node_id=name,
                status=HealthStatus.DEGRADED,
                latency_ms=round(latency, 2),
                error_msg=str(e)
            )
    
    def _check_federation_bridge(self) -> NodeHealth:
        """Check federation bridge health endpoint."""
        start = time.time()
        try:
            req = Request("http://localhost:7892/health", method="GET")
            with urlopen(req, timeout=5) as response:
                latency = (time.time() - start) * 1000
                if response.status == 200:
                    return NodeHealth(
                        node_id="federation_bridge",
                        status=HealthStatus.HEALTHY,
                        latency_ms=round(latency, 2)
                    )
                else:
                    return NodeHealth(
                        node_id="federation_bridge",
                        status=HealthStatus.DEGRADED,
                        latency_ms=round(latency, 2),
                        error_msg=f"HTTP {response.status}"
                    )
        except (URLError, HTTPError, socket.timeout) as e:
            latency = (time.time() - start) * 1000
            return NodeHealth(
                node_id="federation_bridge",
                status=HealthStatus.OFFLINE,
                latency_ms=round(latency, 2),
                error_msg=str(e)
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return NodeHealth(
                node_id="federation_bridge",
                status=HealthStatus.DEGRADED,
                latency_ms=round(latency, 2),
                error_msg=str(e)
            )
    
    def _check_local_mesh_files(self) -> NodeHealth:
        """Check if essential local mesh files exist."""
        start = time.time()
        essential_files = [
            "mesh_config.json",
            "node_registry.json",
            os.path.join("core", "mesh_router.py"),
            os.path.join("core", "mesh_health.py"),
        ]
        
        missing_files = []
        for file in essential_files:
            if not os.path.exists(file):
                missing_files.append(file)
        
        latency = (time.time() - start) * 1000
        if not missing_files:
            return NodeHealth(
                node_id="local_mesh_files",
                status=HealthStatus.HEALTHY,
                latency_ms=round(latency, 2)
            )
        else:
            return NodeHealth(
                node_id="local_mesh_files",
                status=HealthStatus.DEGRADED,
                latency_ms=round(latency, 2),
                error_msg=f"Missing files: {', '.join(missing_files[:3])}"
            )


def get_mesh_health() -> MeshHealth:
    """Get singleton MeshHealth instance."""
    return MeshHealth()


def print_ascii_table(results: Dict[str, NodeHealth]):
    """Print ASCII table with colored status."""
    # ANSI color codes
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    print(f"{BOLD}DOF Mesh Health Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print("=" * 70)
    print(f"{BOLD}{'Node':<20} {'Status':<12} {'Latency (ms)':<12} {'Error/Message'}{RESET}")
    print("-" * 70)
    
    for node_id, health in results.items():
        status = health.status.value
        latency = f"{health.latency_ms:.2f}" if health.latency_ms else "N/A"
        error = health.error_msg or ""
        
        # Color coding
        if status == "HEALTHY":
            status_colored = f"{GREEN}{status}{RESET}"
        elif status == "DEGRADED":
            status_colored = f"{YELLOW}{status}{RESET}"
        else:
            status_colored = f"{RED}{status}{RESET}"
        
        print(f"{node_id:<20} {status_colored:<20} {latency:<12} {error}")
    
    print("=" * 70)
    
    # Summary
    healthy = sum(1 for h in results.values() if h.status == HealthStatus.HEALTHY)
    degraded = sum(1 for h in results.values() if h.status == HealthStatus.DEGRADED)
    offline = sum(1 for h in results.values() if h.status == HealthStatus.OFFLINE)
    
    print(f"{BOLD}Summary:{RESET} {GREEN}HEALTHY: {healthy}{RESET}, {YELLOW}DEGRADED: {degraded}{RESET}, {RED}OFFLINE: {offline}{RESET}")


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="DOF Mesh Health Checker")
    parser.add_argument("--check", action="store_true", help="Print ASCII table with colors")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    args = parser.parse_args()
    
    # Default to --check if no args provided
    if not args.check and not args.json:
        args.check = True
    
    health_checker = get_mesh_health()
    results = health_checker.check_all()
    
    if args.json:
        output = {
            "timestamp": datetime.now().isoformat(),
            "nodes": {node_id: health.to_dict() for node_id, health in results.items()}
        }
        print(json.dumps(output, indent=2))
    else:
        print_ascii_table(results)


if __name__ == "__main__":
    main()
