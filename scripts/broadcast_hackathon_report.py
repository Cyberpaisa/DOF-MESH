#!/usr/bin/env python3
import os
import sys
import json
import logging

# Ensure core is in path
sys.path.insert(0, os.getcwd())

from core.node_mesh import NodeMesh

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("broadcast_report")

REPORT_PATH = "reports/LEGION_HACKATHON_FINAL_REPORT.md"

async def main():
    if not os.path.exists(REPORT_PATH):
        logger.error(f"Report not found at {REPORT_PATH}")
        sys.exit(1)

    with open(REPORT_PATH, "r") as f:
        report_content = f.read()

    logger.info("Initializing NodeMesh...")
    # Initialize mesh. Path defaults to logs/mesh
    mesh = NodeMesh()

    logger.info(f"Broadcasting report to all nodes in the legion mesh...")
    
    # Send as an ALERT/SYNC message from the 'orchestrator'
    msg = mesh.broadcast(
        from_node="orchestrator",
        content=f"### [HACKATHON SYNCHRONIZATION REPORT]\n\n{report_content}",
        msg_type="sync"
    )

    logger.info(f"Broadcast complete. Message ID: {msg.msg_id}")
    print(f"SUCCESS: Report broadcasted via Mesh. ID: {msg.msg_id}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
