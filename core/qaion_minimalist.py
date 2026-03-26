import logging
import json
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("qaion.minimalist")

class MinimalistValidator:
    """Validador de Valor y Priorización de MVP (Minimalist Entrepreneur Style)."""
    def __init__(self):
        self.mvp_roadmap = "data/MVP_ROADMAP.md"

    def validate_and_prioritize(self, extraction_results: list):
        """Filtra y prioriza hallazgos basados en viabilidad y valor inmediato."""
        logger.info("[MINIMALIST] Validando ideas y reduciendo alcance para el MVP...")
        
        priorities = []
        for result in extraction_results:
            # Lógica de filtrado: ¿Es esencial para la soberanía o es ruido técnico?
            score = 0
            if "moe" in result.lower(): score += 5
            if "npu" in result.lower(): score += 5
            if "privacy" in result.lower(): score += 10
            
            if score >= 10:
                priorities.append(result)
        
        logger.info(f"[MINIMALIST] {len(priorities)} características priorizadas para el MVP.")
        return priorities

    def update_roadmap(self, priorities: list):
        """Actualiza el roadmap del MVP en el Libro de la Legión."""
        if not priorities:
            return
            
        with open(self.mvp_roadmap, "a") as f:
            f.write(f"\n### Iteración MVP - {json.dumps(priorities)}\n")
        
        logger.info("[MINIMALIST] Roadmap de MVP actualizado.")

if __name__ == "__main__":
    validator = MinimalistValidator()
    validator.validate_and_prioritize(["Optimize MoE weight distribution", "Useless technical detail", "NPU secure enclave binding"])
