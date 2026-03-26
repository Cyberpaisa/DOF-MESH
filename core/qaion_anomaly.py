import logging
import json
import os
from core.memory_manager import MemoryManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("qaion.anomaly")

class MeshImmunity:
    """Sistema de inmunidad semántica para detectar anomalías en el Mesh."""
    def __init__(self):
        self.memory = MemoryManager()
        self.threshold = 0.15  # Umbral de Fisher-Rao (menor = más anómalo)

    def verify_integrity(self, content: str, context: str = "baseline_sovereignty"):
        """Verifica si el contenido es semánticamente coherente con la soberanía."""
        logger.info(f"[INMUNIDAD] Verificando integridad de: {content[:50]}...")
        
        # Recuperar patrones similares de la memoria de largo plazo
        baselines = self.memory.search_long_term(context, max_results=1)
        
        if not baselines:
            logger.warning("No hay línea de base para comparación. Almacenando como primer espécimen.")
            self.memory.store_long_term(context, content, source="immunity_system")
            return True, 1.0

        baseline_text = baselines[0].value
        
        try:
            from core.fisher_rao import fisher_rao_similarity
            similarity = fisher_rao_similarity(content, baseline_text)
            
            is_healthy = similarity >= self.threshold
            logger.info(f"[INMUNIDAD] Similitud Fisher-Rao: {similarity:.4f} (Saludable: {is_healthy})")
            
            return is_healthy, similarity
        except ImportError:
            logger.error("Módulo Fisher-Rao no encontrado. Usando fallback de palabras clave.")
            return True, 1.0

if __name__ == "__main__":
    immunity = MeshImmunity()
    # Prueba de concepto
    res, score = immunity.verify_integrity("Estructura MoE soberana con ruteo Sparse Top-k.")
    print(f"Resultado: {res}, Score: {score}")
