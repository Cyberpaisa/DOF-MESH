import time
import json
import logging
import subprocess
import os
import random

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(message)s',
    filename="logs/night_ops.log",
    filemode="a"
)
logger = logging.getLogger("night.orchestrator")

def run_extraction_cycle():
    """Ejecuta un ciclo completo de extracción y síntesis."""
    try:
        logger.info("--- Iniciando Ciclo de Extracción Nocturna ---")
        
        # 0. Investigación Viva (Last 30 Days)
        logger.info("Ejecutando Live Researcher...")
        subprocess.run(["python3", "scripts/phase11_live_researcher.py"], env=os.environ, check=True)
        
        # 1. Ejecutar Coliseo V2
        logger.info("Ejecutando Coliseo V2...")
        subprocess.run(["python3", "scripts/phase11_extraction_colosseum_v2.py"], env=os.environ, check=True)
        
        # 1.5 Detección de Anomalías (Mesh Immunity)
        logger.info("Verificando integridad técnica (Detección de Anomalías)...")
        result = subprocess.run(["python3", "scripts/phase11_anomaly_check.py"], env=os.environ)
        
        if result.returncode != 0:
            logger.warning("Anomalía detectada. Activando protocolo de Autocuración...")
            # Si falló MiMo, forzar reintento con DeepSeek antes de rendirse
            logger.info("[SELF-HEALING] Reintentando ciclo de extracción con DeepSeek prioritario...")
            os.environ["FORCE_PROVIDER"] = "DeepSeek"
            subprocess.run(["python3", "scripts/phase11_extraction_colosseum_v2.py"], env=os.environ, check=True)
            # Volver a verificar integridad con el nuevo dato
            result = subprocess.run(["python3", "scripts/phase11_anomaly_check.py"], env=os.environ)
            
            if result.returncode != 0:
                logger.error("[CRÍTICO] Autocuración fallida. Saltando ciclo para proteger ADN.")
                return False
            else:
                logger.info("[✓] Autocuración exitosa. Continuando evolución.")

        # 1.7 Extracción Multimodal (Chandra OCR)
        logger.info("Procesando inteligencia visual con Chandra OCR...")
        subprocess.run(["python3", "core/qaion_multimodal.py"], env=os.environ, check=True)

        # 1.8 Extracción Auditiva (Insanely Fast Whisper)
        logger.info("Procesando inteligencia auditiva con Insanely Fast Whisper...")
        subprocess.run(["python3", "core/qaion_audio.py"], env=os.environ, check=True)

        # 2. Sintetizar Inteligencia
        logger.info("Sintetizando inteligencia extraída...")
        subprocess.run(["python3", "scripts/phase11_knowledge_synthesis.py"], env=os.environ, check=True)
        
        # 2.2 Validación MVP (Minimalist Entrepreneur)
        logger.info("Priorizando MVP con lógica Minimalist...")
        subprocess.run(["python3", "core/qaion_minimalist.py"], env=os.environ, check=True)

        # 2.5 Meta-Análisis y Auditoría (Feynman Researcher)
        logger.info("Ejecutando Meta-Análisis Feynman...")
        subprocess.run(["python3", "core/qaion_research_feynman.py"], env=os.environ, check=True)

        # 3. Evolución Autónoma del Código
        logger.info("Iniciando auto-evolución de la lógica soberana...")
        subprocess.run(["python3", "scripts/phase11_autonomous_evolution.py"], env=os.environ, check=True)
        
        # 4. Auditoría Semántica (Muse-style)
        logger.info("Ejecutando Auditoría Semántica...")
        subprocess.run(["python3", "scripts/phase11_semantic_audit.py"], env=os.environ, check=True)
        
        logger.info("--- Ciclo Completado con Éxito ---")
        return True
    except Exception as e:
        logger.error(f"Error en el ciclo nocturno: {str(e)}")
        return False

def main():
    os.makedirs("logs", exist_ok=True)
    logger.info("=== LEGIÓN EN MODO EVOLUCIÓN PERMANENTE (INFINITO) ACTIVADO ===")
    
    cycle_count = 0
    while True:
        cycle_count += 1
        logger.info(f"--- Iniciando Ciclo de Evolución {cycle_count} ---")
        run_extraction_cycle()
        
        # Pausa dinámica para enfriamiento y límites de API
        wait_time = random.randint(600, 1200) # 10-20 minutos
        logger.info(f"Ciclo {cycle_count} completado. Esperando {wait_time}s para la próxima evolución...")
        time.sleep(wait_time)

    logger.info("=== OPERACIÓN NOCTURNA FINALIZADA. REPORTE LISTO PARA EL AMANECER. ===")

if __name__ == "__main__":
    main()
