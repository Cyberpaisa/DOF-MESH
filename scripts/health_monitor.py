#!/usr/bin/env python3
"""
health_monitor.py — DOF Mesh System Health Monitor.

Runs every 60 seconds and checks:
  1. Active processes (mesh daemons, autonomous daemons, web bridge)
  2. API key validity (Groq, Cerebras, NVIDIA — HEAD-level probe)
  3. Wallet balance via Enigma on-chain (if configured)
  4. Mesh queue depth (HyperionBridge or inbox file count)

Alerts are written to logs/health/alerts.jsonl.
A rolling summary is kept at logs/health/status.json.

Usage:
    python3 scripts/health_monitor.py              # run forever
    python3 scripts/health_monitor.py --once       # single check
    python3 scripts/health_monitor.py --interval 30
"""
import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Allow imports from repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Load .env
_env = REPO_ROOT / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            k, _, v = _line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

LOG_DIR = REPO_ROOT / "logs" / "health"
LOG_DIR.mkdir(parents=True, exist_ok=True)
ALERTS_FILE = LOG_DIR / "alerts.jsonl"
STATUS_FILE = LOG_DIR / "status.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [HEALTH] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("health_monitor")


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class CheckResult:
    name: str
    ok: bool
    value: str       # human-readable current value
    threshold: str   # what we expect
    detail: str = ""
    ts: float = field(default_factory=time.time)


@dataclass
class HealthReport:
    timestamp: float = field(default_factory=time.time)
    iso: str = ""
    checks: list = field(default_factory=list)
    overall_ok: bool = True
    alerts: list = field(default_factory=list)

    def __post_init__(self):
        self.iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(self.timestamp))


# ── Check implementations ─────────────────────────────────────────────────────

def check_processes() -> list[CheckResult]:
    """Check that key daemon processes are running."""
    import subprocess
    results = []
    targets = [
        ("autonomous_daemon.py", "AutonomousDaemon"),
        ("web_bridge.py",        "WebBridge"),
        ("mesh_orchestrator.py", "MeshOrchestrator"),
        ("node_mesh.py",         "NodeMesh daemon"),
    ]
    try:
        ps = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=10
        )
        for script, label in targets:
            running = script in ps.stdout
            results.append(CheckResult(
                name=f"process:{label}",
                ok=running,
                value="running" if running else "NOT FOUND",
                threshold="running",
            ))
    except Exception as e:
        results.append(CheckResult(
            name="process:check",
            ok=False,
            value=f"error: {e}",
            threshold="no error",
        ))
    return results


def check_api_keys() -> list[CheckResult]:
    """Probe API endpoints to confirm keys are valid (non-expired)."""
    import urllib.request
    import urllib.error

    results = []

    providers = {
        "GROQ": {
            "env_key": "GROQ_API_KEY",
            "url": "https://api.groq.com/openai/v1/models",
            "header": "Authorization",
            "prefix": "Bearer ",
        },
        "CEREBRAS": {
            "env_key": "CEREBRAS_API_KEY",
            "url": "https://api.cerebras.ai/v1/models",
            "header": "Authorization",
            "prefix": "Bearer ",
        },
        "NVIDIA": {
            "env_key": "NVIDIA_API_KEY",
            "url": "https://integrate.api.nvidia.com/v1/models",
            "header": "Authorization",
            "prefix": "Bearer ",
        },
    }

    for name, cfg in providers.items():
        key = os.environ.get(cfg["env_key"], "")
        if not key:
            results.append(CheckResult(
                name=f"api:{name}",
                ok=False,
                value="KEY_MISSING",
                threshold="key present",
            ))
            continue

        try:
            req = urllib.request.Request(
                cfg["url"],
                headers={cfg["header"]: cfg["prefix"] + key, "User-Agent": "DOF-HealthMonitor/1.0"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                status = resp.status
            ok = status < 400
            results.append(CheckResult(
                name=f"api:{name}",
                ok=ok,
                value=f"HTTP {status}",
                threshold="HTTP 2xx",
            ))
        except urllib.error.HTTPError as e:
            expired = e.code in (401, 403)
            results.append(CheckResult(
                name=f"api:{name}",
                ok=False,
                value=f"HTTP {e.code} ({'EXPIRED' if expired else 'error'})",
                threshold="HTTP 2xx",
                detail=str(e.reason),
            ))
        except Exception as e:
            results.append(CheckResult(
                name=f"api:{name}",
                ok=False,
                value=f"error: {type(e).__name__}",
                threshold="HTTP 2xx",
                detail=str(e),
            ))

    return results


def check_wallet_balance() -> list[CheckResult]:
    """Check on-chain wallet balance if Enigma/web3 config is available."""
    results = []
    wallet = os.environ.get("ENIGMA_WALLET_ADDRESS", "")
    rpc = os.environ.get("AVALANCHE_RPC_URL", "https://api.avax.network/ext/bc/C/rpc")

    if not wallet:
        results.append(CheckResult(
            name="wallet:balance",
            ok=True,
            value="not configured",
            threshold="any",
            detail="Set ENIGMA_WALLET_ADDRESS in .env to enable",
        ))
        return results

    try:
        import urllib.request as _ur
        payload = json.dumps({
            "jsonrpc": "2.0", "method": "eth_getBalance",
            "params": [wallet, "latest"], "id": 1,
        }).encode()
        req = _ur.Request(rpc, data=payload, headers={"Content-Type": "application/json"})
        with _ur.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        hex_bal = data.get("result", "0x0")
        avax = int(hex_bal, 16) / 1e18
        low = avax < 0.01
        results.append(CheckResult(
            name="wallet:balance",
            ok=not low,
            value=f"{avax:.4f} AVAX",
            threshold=">0.01 AVAX",
            detail=wallet,
        ))
    except Exception as e:
        results.append(CheckResult(
            name="wallet:balance",
            ok=False,
            value=f"error: {e}",
            threshold=">0.01 AVAX",
        ))

    return results


def check_mesh_queue() -> list[CheckResult]:
    """Check mesh queue depth via inbox file count."""
    results = []
    inbox = REPO_ROOT / "logs" / "mesh" / "inbox"

    if not inbox.exists():
        results.append(CheckResult(
            name="mesh:queue_depth",
            ok=True,
            value="inbox not found",
            threshold="<100",
        ))
        return results

    try:
        pending = list(inbox.glob("**/*.json"))
        # Exclude response/done files
        pending = [
            f for f in pending
            if not f.stem.endswith("-RESPONSE")
            and not f.stem.endswith("-FAILED")
            and not f.suffix == ".processing"
            and not f.suffix == ".done"
        ]
        depth = len(pending)
        high = depth > 100
        results.append(CheckResult(
            name="mesh:queue_depth",
            ok=not high,
            value=str(depth),
            threshold="<100 pending tasks",
        ))
    except Exception as e:
        results.append(CheckResult(
            name="mesh:queue_depth",
            ok=False,
            value=f"error: {e}",
            threshold="<100",
        ))

    # Also check HyperionBridge queue if available
    try:
        from core.hyperion_bridge import HyperionBridge
        bridge = HyperionBridge()
        hq = bridge.queue_size()
        high_h = hq > 500
        results.append(CheckResult(
            name="mesh:hyperion_queue",
            ok=not high_h,
            value=str(hq),
            threshold="<500",
        ))
    except Exception:
        pass  # Hyperion not always running

    return results


def check_log_errors() -> list[CheckResult]:
    """Check for recent errors in daemon logs."""
    results = []
    log_files = [
        (REPO_ROOT / "logs" / "daemon" / "cycles.jsonl", "daemon"),
        (REPO_ROOT / "logs" / "mesh" / "orchestrator.jsonl", "orchestrator"),
    ]
    cutoff = time.time() - 3600  # last hour

    for log_file, label in log_files:
        if not log_file.exists():
            continue
        try:
            errors = 0
            with open(log_file) as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        ts = entry.get("timestamp", entry.get("ts", 0))
                        if ts > cutoff and entry.get("result_status") == "error":
                            errors += 1
                    except Exception:
                        pass
            high = errors >= 5
            results.append(CheckResult(
                name=f"logs:{label}_errors_1h",
                ok=not high,
                value=str(errors),
                threshold="<5 errors/h",
            ))
        except Exception as e:
            results.append(CheckResult(
                name=f"logs:{label}_errors_1h",
                ok=False,
                value=f"error: {e}",
                threshold="<5 errors/h",
            ))

    return results


# ── Alert writer ──────────────────────────────────────────────────────────────

def write_alert(check: CheckResult):
    """Append a failed check to the alerts JSONL file."""
    entry = asdict(check)
    entry["iso"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(check.ts))
    with open(ALERTS_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    logger.warning("ALERT [%s] value=%s (expected %s) %s",
                   check.name, check.value, check.threshold,
                   f"— {check.detail}" if check.detail else "")


def write_status(report: HealthReport):
    """Overwrite the rolling status file with the latest report."""
    data = {
        "timestamp": report.timestamp,
        "iso": report.iso,
        "overall_ok": report.overall_ok,
        "alerts": report.alerts,
        "checks": [asdict(c) for c in report.checks],
    }
    STATUS_FILE.write_text(json.dumps(data, indent=2))


# ── Main loop ─────────────────────────────────────────────────────────────────

def run_checks() -> HealthReport:
    """Run all checks and return a HealthReport."""
    report = HealthReport()
    all_checks: list[CheckResult] = []

    all_checks.extend(check_processes())
    all_checks.extend(check_api_keys())
    all_checks.extend(check_wallet_balance())
    all_checks.extend(check_mesh_queue())
    all_checks.extend(check_log_errors())

    report.checks = all_checks
    for c in all_checks:
        if not c.ok:
            report.overall_ok = False
            report.alerts.append(c.name)
            write_alert(c)

    return report


def main():
    parser = argparse.ArgumentParser(description="DOF Health Monitor")
    parser.add_argument("--interval", type=int, default=60, help="Check interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run one check and exit")
    args = parser.parse_args()

    logger.info("DOF Health Monitor starting (interval=%ds)", args.interval)

    while True:
        logger.info("─── Health check ───")
        report = run_checks()
        write_status(report)

        ok_count = sum(1 for c in report.checks if c.ok)
        total = len(report.checks)
        icon = "✅" if report.overall_ok else "❌"
        logger.info("%s %d/%d checks OK%s",
                    icon, ok_count, total,
                    f" | ALERTS: {report.alerts}" if report.alerts else "")

        if args.once:
            break

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
