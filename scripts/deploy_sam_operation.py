#!/usr/bin/env python3
"""
Orquestador de Operaciones SAM (Sovereign Arbitrage Multidimensional)
Versión Mesh-Polling (Phase 4 Sovereign Hardening)

Este script:
1.  Escanea señales geopolíticas (Global Arbitrageur).
2.  Escanea spreads de DeFi en Avalanche (Phase 12 Arbitrageur).
3.  Envía una "Work Order" al Mesh Inbox de local-agi-m4max.
4.  Espera la respuesta estratégica (YES/NO) firmada por el cerebro local.
5.  Registra la operación en el Sovereign Vault.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path

# Configuración de Rutas
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from scripts.q_aion.q_aion_global_arbitrageur import QAionGlobalArbitrageur
from scripts.phase11.phase12_real_arbitrageur import Phase12RealArbitrageur

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("SAM.MeshOrchestrator")

MESH_INBOX_DIR = os.path.join(BASE_DIR, "logs/mesh/inbox")
OPERATIONS_LOG = os.path.join(BASE_DIR, "logs/operations/sam_history.jsonl")

class SAMMeshOrchestrator:
    def __init__(self):
        self.global_scanner = QAionGlobalArbitrageur()
        self.dex_scanner = Phase12RealArbitrageur(require_key=False)
        
        # Inboxes
        self.node_id = "local-agi-m4max"
        self.node_inbox = Path(MESH_INBOX_DIR) / self.node_id
        self.commander_inbox = Path(MESH_INBOX_DIR) / "commander"
        
        self.node_inbox.mkdir(parents=True, exist_ok=True)
        self.commander_inbox.mkdir(parents=True, exist_ok=True)

    def _send_to_mesh(self, content: str) -> str:
        """Escribe una tarea en el buzón del nodo y espera la respuesta."""
        msg_id = f"SAM-OP-{int(time.time()*1000)}"
        task = {
            "msg_id": msg_id,
            "from_node": "sam-orchestrator",
            "to_node": self.node_id,
            "content": content,
            "msg_type": "task",
            "timestamp": time.time(),
            "read": False
        }
        
        task_file = self.node_inbox / f"{msg_id}.json"
        with open(task_file, "w") as f:
            json.dump(task, f, indent=2)
        
        logger.info(f"  [📡] Tarea enviada al Nodo {self.node_id}: {msg_id}")
        
        # Polling para respuesta
        logger.info(f"  [⏳] Esperando decisión estratégica (60s timeout)...")
        for _ in range(60):
            for resp_file in self.commander_inbox.glob("*.json"):
                try:
                    with open(resp_file, "r") as f:
                        resp = json.load(f)
                    if resp.get("reply_to") == msg_id or (resp.get("msg_id") == msg_id and resp.get("msg_type") == "reply"):
                        logger.info(f"  [🛡] Decisión recibida: {resp.get('content')}")
                        # Limpiar buzón (opcional en vault, pero Mesh lo requiere)
                        # os.remove(resp_file) 
                        return resp.get("content", "NO_REPLY")
                except Exception as e:
                    logger.debug(f"Error leyendo respuesta: {e}")
            time.sleep(1)
        
        return "TIMEOUT"

    def run_operation(self):
        logger.info("💠 INICIANDO CICLO SAM: Orquestación Mesh Phase 4")
        
        # 1. Escaneo Geopolítico
        geo_opps = self.global_scanner.scan_opportunities()
        geo_context = f"Geopolitical Alpha: {json.dumps(geo_opps)}"
        
        # 2. Escaneo DeFi (Dry Run)
        dex_data = self.dex_scanner.scan_all_prices(amount_usdc=10.0)
        dex_context = f"DeFi Spreads: {json.dumps(dex_data['spreads'])}"
        
        # 3. Consolidar Alpha
        context = f"""
        Actúa como el Estratega SAM de la Legión.
        Señales Detectadas:
        1. {geo_context}
        2. {dex_context}
        
        ¿Autorizas ejecución de arbitraje? Responde solo con SI o NO y una razón corta.
        """
        
        # 4. Inferencia Mesh (oMLX/MLX/Ollama via daemon)
        decision = self._send_to_mesh(context)
        
        # 5. Registro en Sovereign Vault
        status = "APPROVED" if "SI" in decision.upper() else "REJECTED"
        if decision == "TIMEOUT":
            status = "TIMEOUT"
            
        operation_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "decision_raw": decision,
            "alpha": {
                "geopolitical": geo_opps,
                "dex_spreads": dex_data['spreads']
            }
        }
        
        os.makedirs(os.path.dirname(OPERATIONS_LOG), exist_ok=True)
        with open(OPERATIONS_LOG, "a") as f:
            f.write(json.dumps(operation_record) + "\n")
            
        logger.info(f"✅ Operación SAM concluida. Estado: {status}")
        return operation_record

if __name__ == "__main__":
    orch = SAMMeshOrchestrator()
    orch.run_operation()
