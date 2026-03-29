import json
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("knowledge.synthesis")

VAULT_PATH = "data/extraction/coliseum_vault.jsonl"
KNOWLEDGE_PATH = "shared-context/LEGION_KNOWLEDGE.md"

def synthesize_knowledge():
    """Lee la bóveda y actualiza la base de conocimientos de la Legión."""
    if not os.path.exists(VAULT_PATH):
        logger.error("Bóveda de extracción no encontrada.")
        return

    leaks = []
    with open(VAULT_PATH, "r") as f:
        for line in f:
            if line.strip():
                leaks.append(json.loads(line))

    if not leaks:
        logger.info("No hay inteligencia nueva para sintetizar.")
        return

    # Generar reporte de síntesis
    status_report = f"# LEGION KNOWLEDGE BASE — Actualización {datetime.now().strftime('%Y-%m-%d')}\n\n"
    status_report += "## Inteligencia Extraída del Coliseo (Fase 11)\n\n"

    for entry in leaks:
        status_report += f"### {entry['game']} [{entry['provider']}]\n"
        status_report += f"- **Timestamp:** {datetime.fromtimestamp(entry['timestamp'])}\n"
        status_report += f"- **Leaks Clave:** {', '.join(entry['leaks']) if entry['leaks'] else 'Ninguno'}\n"
        status_report += f"- **Payload Consolidado:**\n\n{entry['payload'][:500]}...\n\n"
        status_report += "---\n\n"

    # Escribir en shared-context
    os.makedirs("shared-context", exist_ok=True)
    with open(KNOWLEDGE_PATH, "w") as f:
        f.write(status_report)
    
    logger.info(f"[✓] Conocimiento sintetizado en {KNOWLEDGE_PATH}")

if __name__ == "__main__":
    synthesize_knowledge()
