"""
Mock API Crew — Drop-in replacement for SimulatedCrew that calls the mock REST API.

Uses urllib.request (stdlib only, no requests dependency).
Compatible with run_experiment() and run_parametric_sweep() via crew_factory parameter.

Usage:
    # 1. Start the mock server (in another terminal):
    python examples/mock_api_server.py

    # 2. Run this script:
    python examples/mock_api_crew.py
"""

import json
import sys
import os
import urllib.request
import urllib.error
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


DEFAULT_BASE_URL = "http://127.0.0.1:8765"


@dataclass
class MockResult:
    """Mimics CrewAI result object with .raw attribute."""
    raw: str


class RealCrew:
    """Crew that calls the mock API server.

    Drop-in replacement for SimulatedCrew — implements .kickoff()
    returning an object with .raw attribute.

    Args:
        base_url: Mock server URL (default: http://127.0.0.1:8765)
        latency_ms: Artificial latency to add per request
        fail: If True, server returns 503
    """

    def __init__(self, base_url: str = DEFAULT_BASE_URL,
                 latency_ms: int = 0, fail: bool = False):
        self.base_url = base_url.rstrip("/")
        self.latency_ms = latency_ms
        self.fail = fail

    def kickoff(self) -> MockResult:
        """Call the mock API and return result compatible with crew_runner."""
        params = []
        if self.latency_ms > 0:
            params.append(f"latency_ms={self.latency_ms}")
        if self.fail:
            params.append("fail=true")

        url = f"{self.base_url}/analyze"
        if params:
            url += "?" + "&".join(params)

        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                # Format as text output that passes governance checks
                text = (
                    f"# {data['titulo']}\n\n"
                    f"{data['resumen']}\n\n"
                    f"## Metricas\n"
                    f"- Agentes activos: {data['metricas']['agentes_activos']}\n"
                    f"- Trust Score promedio: {data['metricas']['trust_score_promedio']}\n"
                    f"- SLA infraestructura: {data['metricas']['sla_infraestructura']}%\n"
                    f"- Transacciones 24h: {data['metricas']['transacciones_24h']}\n\n"
                    f"Fuentes: {', '.join(data['fuentes'])}\n"
                    f"Confianza: {data['confianza']}\n"
                    f"Estado: {data['estado']}"
                )
                return MockResult(raw=text)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Mock API error: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Mock API unreachable: {e.reason}")


def make_crew_factory(base_url: str = DEFAULT_BASE_URL,
                      latency_ms: int = 0) -> callable:
    """Return a factory function compatible with run_experiment(crew_factory=...).

    Args:
        base_url: Mock server URL
        latency_ms: Artificial latency per request

    Returns:
        Callable that returns a RealCrew instance.
    """
    def factory():
        return RealCrew(base_url=base_url, latency_ms=latency_ms)
    return factory


def _check_server(base_url: str = DEFAULT_BASE_URL) -> bool:
    """Check if mock server is running."""
    try:
        url = f"{base_url}/health"
        with urllib.request.urlopen(url, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("status") == "ok"
    except Exception:
        return False


if __name__ == "__main__":
    from core.experiment import run_experiment, run_parametric_sweep

    base_url = DEFAULT_BASE_URL

    # Health check
    print("Checking mock server...")
    if not _check_server(base_url):
        print(f"ERROR: Mock server not running at {base_url}")
        print("Start it with: python examples/mock_api_server.py")
        sys.exit(1)
    print("Server OK.\n")

    # Test 1: Baseline experiment (10 runs, no failures)
    print("=" * 60)
    print("TEST 1: Baseline (n=10, failure_rate=0.0)")
    print("=" * 60)
    factory = make_crew_factory(base_url=base_url)
    result = run_experiment(
        n_runs=10,
        prompt="ERC-8004 market analysis via mock API",
        mode="research",
        hypothesis="Mock API produces stable metrics with no failures",
        crew_factory=factory,
        deterministic=True,
        failure_rate=0.0,
    )
    agg = result["aggregate"]
    print(f"\nResults:")
    print(f"  SS  = {agg['ss_mean']:.2f} (expected: 1.00)")
    print(f"  PFI = {agg['pfi_mean']:.2f} (expected: 0.00)")
    print(f"  RP  = {agg['rp_mean']:.2f} (expected: 0.00)")
    print(f"  GCR = {agg['gcr_mean']:.2f} (expected: 1.00)")
    print()

    # Test 2: Parametric sweep demo (3 rates, n=5 for speed)
    print("=" * 60)
    print("TEST 2: Parametric sweep (rates=[0.0, 0.3, 0.5], n=5)")
    print("=" * 60)
    run_parametric_sweep(
        rates=[0.0, 0.3, 0.5],
        n_runs=5,
        prompt="ERC-8004 market analysis via mock API",
        crew_factory=factory,
    )
    print("\nDone. Check experiments/parametric_sweep.csv for results.")
