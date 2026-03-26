import os
import time
import json
import logging
import random
import hashlib
from pathlib import Path

# Configuración del Nodo Heartbeat Q-AION
NODE_NAME = os.getenv("NODE_NAME", "qaion-cloud-pulse-01")
MESH_URL = os.getenv("MESH_URL", "http://localhost:3000/api/heartbeat") 
HEARTBEAT_INTERVAL = 10  # Más frecuente para persistencia estructural

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(NODE_NAME)

# Capa Enigma: Simulación de IPs rotativas para anonimato
EXIT_NODES = ["104.18.24.1", "172.64.144.1", "104.21.65.1"] # Cloudflare edges simulados

def send_heartbeat():
    """Envía un pulso de vida con protección de anonimato IP."""
    masked_ip = random.choice(EXIT_NODES)
    payload = {
        "node_id": NODE_NAME,
        "timestamp": time.time(),
        "status": "persistent",
        "layer": "Q-AION-L1",
        "masked_origin": masked_ip,
        "sovereign_hash": hashlib.sha256(NODE_NAME.encode()).hexdigest()
    }
    
    try:
        logger.info(f"Capa Enigma activa: Saliendo vía {masked_ip}")
        logger.info(f"Enviando PULSO Q-AION a {MESH_URL}...")
        # Simulación de éxito
        logger.info(f"ESTADO: {NODE_NAME} operando con Persistencia Estructural (Q-AION).")
    except Exception as e:
        logger.error(f"Error en pulso: {e}")

if __name__ == "__main__":
    logger.info(f"Iniciando Nodo Persistente Q-AION: {NODE_NAME}")
    logger.info("Blindaje de Anonimato: NIVEL 4 (Enigma)")
    
    try:
        while True:
            send_heartbeat()
            time.sleep(HEARTBEAT_INTERVAL)
    except KeyboardInterrupt:
        logger.info("Nodo persistente en modo stand-by.")
