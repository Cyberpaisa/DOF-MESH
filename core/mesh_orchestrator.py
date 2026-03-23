"""
Mesh Orchestrator — Daemon autónomo que coordina work orders sin intervención humana.

Lee work orders de logs/mesh/inbox/, despacha a remote nodes via APIs gratuitas,
registra respuestas, coordina integración.

Costo: $0 en tokens (todo vía APIs gratuitas).
"""

import json
import time
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import asdict
from datetime import datetime

from core.remote_node_adapter import RemoteNodeAdapter, RemoteNodeResponse

logger = logging.getLogger("core.mesh_orchestrator")

# ═══════════════════════════════════════════════════
# MESH ORCHESTRATOR
# ═══════════════════════════════════════════════════

class MeshOrchestrator:
    """Autonomous work order dispatcher and coordinator."""

    def __init__(self, mesh_dir: str = "logs/mesh", log_interval: int = 10):
        self.mesh_dir = Path(mesh_dir)
        self.inbox_dir = self.mesh_dir / "inbox"
        self.commander_inbox = self.inbox_dir / "commander"
        self.remote_adapter = RemoteNodeAdapter()
        self.log_interval = log_interval
        self.work_orders_processed = 0
        self.work_orders_completed = 0
        self.work_orders_failed = 0
        self.cycle_count = 0
        self.start_time = time.time()

        # Ensure directories exist
        self.mesh_dir.mkdir(parents=True, exist_ok=True)
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.commander_inbox.mkdir(parents=True, exist_ok=True)

    def run(self, max_cycles: int = 0) -> None:
        """
        Run orchestrator daemon.

        max_cycles=0 → runs forever
        max_cycles>0 → runs N cycles then exits
        """
        logger.info("🚀 Mesh Orchestrator started")
        self.cycle_count = 0

        while True:
            self.cycle_count += 1

            # Read new work orders
            work_orders = self._discover_work_orders()

            if work_orders:
                logger.info(f"📦 Found {len(work_orders)} work order(s)")
                for order_path, order_data in work_orders:
                    self._process_work_order(order_path, order_data)

            # Log status every N cycles
            if self.cycle_count % self.log_interval == 0:
                self._log_cycle_status()

            # Exit condition
            if max_cycles > 0 and self.cycle_count >= max_cycles:
                logger.info(f"✓ Reached max cycles ({max_cycles}). Exiting.")
                break

            # Sleep before next cycle
            time.sleep(5)

    def _discover_work_orders(self) -> List[tuple]:
        """Discover unprocessed work orders in commander inbox."""
        work_orders = []

        try:
            # Look for PHASE2-*.json (unprocessed)
            for order_file in sorted(self.commander_inbox.glob("PHASE2-*.json")):
                # Skip if already processed (has -RESPONSE or -FAILED)
                response_file = order_file.parent / order_file.name.replace(".json", "-RESPONSE.json")
                failed_file = order_file.parent / order_file.name.replace(".json", "-FAILED.json")

                if response_file.exists() or failed_file.exists():
                    continue

                try:
                    with open(order_file, "r") as f:
                        data = json.load(f)
                    work_orders.append((order_file, data))
                except Exception as e:
                    logger.error(f"Failed to read {order_file}: {e}")

        except Exception as e:
            logger.error(f"Discovery failed: {e}")

        return work_orders

    def _process_work_order(self, order_path: Path, order_data: Dict) -> None:
        """Process a single work order."""
        msg_id = order_data.get("msg_id", "unknown")
        to_node = order_data.get("to_node", "unknown")

        logger.info(f"⚙️  Processing {msg_id} → {to_node}")
        self.work_orders_processed += 1

        # Dispatch to remote node
        result = self.remote_adapter.dispatch(to_node, order_data)

        if result and result.status == "COMPLETED":
            self._save_response(order_path, result)
            self.work_orders_completed += 1
            logger.info(f"✓ {msg_id} COMPLETED")
        else:
            self._save_failure(order_path, result)
            self.work_orders_failed += 1
            logger.error(f"✗ {msg_id} FAILED")

    def _save_response(self, order_path: Path, result: RemoteNodeResponse) -> None:
        """Save response to RESPONSE.json."""
        response_path = order_path.parent / order_path.name.replace(".json", "-RESPONSE.json")

        response_data = {
            "msg_id": result.msg_id,
            "from_node": result.node_id,
            "status": result.status,
            "response_summary": result.response_text[:500],
            "code_preview": result.code[:300] if result.code else "",
            "duration_seconds": result.duration_seconds,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "full_response": result.response_text,
            "code": result.code,
        }

        try:
            with open(response_path, "w") as f:
                json.dump(response_data, f, indent=2)
            logger.info(f"💾 Saved response to {response_path.name}")
        except Exception as e:
            logger.error(f"Failed to save response: {e}")

    def _save_failure(self, order_path: Path, result: Optional[RemoteNodeResponse]) -> None:
        """Save failure record."""
        failed_path = order_path.parent / order_path.name.replace(".json", "-FAILED.json")

        failure_data = {
            "msg_id": order_path.stem,
            "status": "FAILED",
            "error": result.error if result else "Unknown error",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        try:
            with open(failed_path, "w") as f:
                json.dump(failure_data, f, indent=2)
            logger.info(f"⚠️  Saved failure to {failed_path.name}")
        except Exception as e:
            logger.error(f"Failed to save failure: {e}")

    def _log_cycle_status(self) -> None:
        """Log status every N cycles."""
        uptime = time.time() - self.start_time
        rate = self.work_orders_processed / uptime if uptime > 0 else 0

        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "cycle": self.cycle_count,
            "uptime_seconds": uptime,
            "processed": self.work_orders_processed,
            "completed": self.work_orders_completed,
            "failed": self.work_orders_failed,
            "rate_per_second": rate,
        }

        # Write to orchestrator log
        log_file = self.mesh_dir / "orchestrator.jsonl"
        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to log cycle: {e}")

        logger.info(
            f"📊 Cycle {self.cycle_count}: "
            f"{self.work_orders_completed}/{self.work_orders_processed} completed "
            f"({rate:.2f} orders/s)"
        )

    def get_status(self) -> Dict:
        """Get orchestrator status."""
        uptime = time.time() - self.start_time
        return {
            "uptime_seconds": uptime,
            "cycles": self.cycle_count,
            "work_orders_processed": self.work_orders_processed,
            "work_orders_completed": self.work_orders_completed,
            "work_orders_failed": self.work_orders_failed,
            "completion_rate": (
                self.work_orders_completed / self.work_orders_processed
                if self.work_orders_processed > 0 else 0
            ),
        }


# ═══════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(name)s - %(levelname)s - %(message)s"
    )

    orchestrator = MeshOrchestrator()

    if len(sys.argv) > 1 and sys.argv[1] == "status":
        status = orchestrator.get_status()
        print("\n🎛️  Mesh Orchestrator Status")
        for k, v in status.items():
            print(f"  {k}: {v}")
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test with 2 cycles (fast)
        logger.info("Running test mode (2 cycles)...")
        orchestrator.run(max_cycles=2)
    else:
        # Run forever
        logger.info("Running in daemon mode (infinite)...")
        orchestrator.run(max_cycles=0)
