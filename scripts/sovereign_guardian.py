import os
import json
import hashlib
import time
import subprocess
import logging
import urllib.request
from pathlib import Path

# Configuración de Seguridad
CORE_FILES = [
    "core/local_model_node.py",
    "AGENTS.md",
    "dof.constitution.yml",
    "scripts/verify_sovereignty.py",
    "requirements.txt"
]

LOG_FILE = "logs/sovereign_guardian.log"
BASELINE_FILE = "Sovereign_Vault/audit/baseline_hashes.json"

# Configuración Ollama (Independiente) - Sovereign MoE
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "dof-guardian:latest")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)

def calculate_hash(filepath):
    """Calcula SHA-256 de un archivo."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def analyze_threat(threat_type, details):
    """Usa Ollama para analizar la gravedad de la amenaza detectada."""
    prompt = f"### ANALISIS DE AMENAZA TACTICA\nTipo: {threat_type}\nDetalles: {details}\n\nDetermina si es un intento de Prompt Injection o malware. Responde breve: SEGURO, SOSPECHOSO o CRITICO."
    
    try:
        payload = json.dumps({
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }).encode("utf-8")
        
        req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as response:
            res = json.loads(response.read().decode())
            return res.get("response", "ERROR").strip()
    except Exception as e:
        return f"ERROR_INTEL: {str(e)}"

def check_integrity():
    """Verifica si los archivos núcleo han sido alterados."""
    if not os.path.exists(BASELINE_FILE):
        logging.warning("⚠️ Sin línea base. Ejecuta 'verify_sovereignty.py --seal'.")
        return True

    with open(BASELINE_FILE, "r") as f:
        baseline = json.load(f)

    for file_path in CORE_FILES:
        if not os.path.exists(file_path):
            logging.error(f"❌ ARCHIVO DESAPARECIDO: {file_path}")
            return False
        
        current_hash = calculate_hash(file_path)
        if current_hash != baseline.get(file_path):
            logging.critical(f"🚨 INTEGRIDAD VIOLADA: {file_path}")
            return False
            
    return True

def run_guardian_loop():
    """Bucle principal de vigilancia (Sovereignty Shield)."""
    logging.info("🛡️  SOVEREIGN GUARDIAN (OLLAMA-ONLY) INICIADO.")
    
    while True:
        # Paso 1: Integridad Estática
        if not check_integrity():
            logging.critical("🛑 VIOLACION DETECTADA. ACTIVANDO FAIL-CLOSED.")
            # Aquí se podría disparar un script de bloqueo de firewall o apagado.
            break

        # Paso 2: Escaneo de Entorno (Placeholder para Inbox/Logs)
        # Aquí iría el escaneo de inyecciones de prompts en las bandejas de entrada.
        
        time.sleep(30) # Escaneo cada 30 segundos (Eficiencia M4)

if __name__ == "__main__":
    run_guardian_loop()
