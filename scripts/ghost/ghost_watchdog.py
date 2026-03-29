import os
import re
import time
import logging
from datetime import datetime

# Glassworm/Unicode Malware Protection Pattern
GHOST_PATTERN = re.compile(r"[\uFE00-\uFE0F\U000E0100-\U000E01EF]")

# Paths to monitor
MONITOR_PATHS = [
    "/Users/jquiceva/equipo-de-agentes/core",
    "/Users/jquiceva/equipo-de-agentes/scripts",
    "/Users/jquiceva/equipo-de-agentes/interfaces",
    "/Users/jquiceva/equipo-de-agentes/data"
]

LOG_FILE = "/Users/jquiceva/equipo-de-agentes/logs/ghost_watchdog.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

def scan_files():
    """Scans monitored paths for Unicode steganography."""
    alert_triggered = False
    for path in MONITOR_PATHS:
        if not os.path.exists(path):
            continue
            
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith((".py", ".js", ".json", ".md", ".txt", ".sh")):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        
                        if GHOST_PATTERN.search(content):
                            logging.warning(f"!!! GHOST DETECTADO EN: {file_path}")
                            print(f"[!] ALERTA DE SEGURIDAD: Infección detectada en {file_path}")
                            alert_triggered = True
                    except:
                        continue
    return alert_triggered

def main():
    print("[*] CENTINELA UNICODE ACTIVO (Vigilancia Permanente)")
    logging.info("Watchdog started.")
    
    while True:
        try:
            if scan_files():
                print("[!] SE RECOMIENDA PURGA INMEDIATA.")
            time.sleep(600)  # Escaneo cada 10 minutos
        except KeyboardInterrupt:
            print("[*] Centinela desactivado.")
            break
        except Exception as e:
            logging.error(f"Watchdog error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
