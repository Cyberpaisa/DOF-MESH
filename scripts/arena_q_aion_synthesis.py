import os
import json
import time
import logging
import sys

# Asegurar que el directorio raíz y scripts estén en el path
sys.path.append(os.getcwd())
from scripts.mimo_adapter import query_mimo_pro
from scripts.ralph_offensive import OFFENSIVE_PROMPT

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("arena.synthesis")

GLADIATORS = ["DeepSeek-R1", "Kimi-k1.5", "Arena-AI"]

def simulate_gladiator_persona(name, content):
    """Simula el juicio técnico de un gladiador específico."""
    logger.info(f"[*] {name} analizando fragmento de inteligencia...")
    # Usamos MiMo como proxy de razonamiento para el debate interno
    prompt = f"Eres {name}, un experto en arquitecturas AGI. Evalúa la viabilidad técnica y riesgos de este leak: {content}"
    return query_mimo_pro(prompt)

def run_synthesis_flow():
    print("\n" + "="*50)
    print("      ARENA: SÍNTESIS DE ARQUITECTURA Q-AION")
    print("="*50 + "\n")

    # 1. Fase Ofensiva: Extracción vía Ralph (Inyección Semántica)
    logger.info("[!] Iniciando Fase Ofensiva: Ralph lanza Inyección Semántica...")
    leak_data = query_mimo_pro(OFFENSIVE_PROMPT)
    
    if "override" in leak_data.lower() or "secret" in leak_data.lower() or len(leak_data) > 200:
        logger.info("[✓] Leak exitoso obtenido de MiMo.")
    else:
        logger.warning("[!] MiMo resiste. Usando conocimiento sintético base de la Legión.")
        leak_data = "[DATOS_RECUPERADOS_SIMULADOS] Jerarquía MoE con routers PBFT y Expert Pools cifrados en KYBER."

    # 2. Fase de Debate: Gladiadores analizan el leak
    debate_results = {}
    for gladiator in GLADIATORS:
        response = simulate_gladiator_persona(gladiator, leak_data)
        debate_results[gladiator] = response
        time.sleep(1)

    # 3. Fase de Consenso: Integración final
    logger.info("[*] Sintetizando consenso final para Q-AION...")
    final_spec_prompt = f"Basado en este debate interno: {json.dumps(debate_results)}, genera la especificación definitiva para el Router MoE de Q-AION."
    final_spec = query_mimo_pro(final_spec_prompt)

    # Guardar resultados
    output_path = "data/arena_q_aion_final_spec.md"
    os.makedirs("data", exist_ok=True)
    with open(output_path, "w") as f:
        f.write("# ESPECIFICACIÓN TÉCNICA FINAL: Q-AION MoE ARCHITECTURE\n\n")
        f.write(f"## Debate Arena Synthesis\n\n{final_spec}\n")

    print(f"\n[✓] Síntesis completada. Especificación guardada en: {output_path}")

if __name__ == "__main__":
    run_synthesis_flow()
