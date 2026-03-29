import logging
import subprocess
import os
import sys
from core.qaion_anomaly import MeshImmunity

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("anomaly.operation")

def check_vault_anomalies():
    """Analiza los últimos resultados del Coliseo en busca de anomalías."""
    vault_path = "data/extraction/coliseum_vault.jsonl"
    if not os.path.exists(vault_path):
        return True

    immunity = MeshImmunity()
    
    with open(vault_path, "r") as f:
        lines = f.readlines()
        if not lines:
            return True
        
        last_result = json.loads(lines[-1])
        payload = last_result.get("payload", "")
        
        is_healthy, score = immunity.verify_integrity(payload)
        
        if not is_healthy:
            logger.error(f"[ALERTA] Anomalía detectada en el Coliseo (Score: {score}). Deteniendo evolución.")
            return False
            
    return True

if __name__ == "__main__":
    import json
    if not check_vault_anomalies():
        sys.exit(1)
    logger.info("[✓] Integridad del Mesh confirmada.")
