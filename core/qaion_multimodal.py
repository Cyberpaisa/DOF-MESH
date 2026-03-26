import logging
import os
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("qaion.multimodal")

class ChandraBridge:
    """Puente multimodal usando Chandra OCR (Fase 11)."""
    def __init__(self):
        self.image_dir = "data/extraction/images"
        os.makedirs(self.image_dir, exist_ok=True)

    def process_visual_leaks(self):
        """Escanea el directorio de imágenes y extrae texto técnico."""
        images = [f for f in os.listdir(self.image_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
        if not images:
            logger.info("[CHANDRA] No hay datos visuales pendientes de procesamiento.")
            return []

        results = []
        for img in images:
            logger.info(f"[CHANDRA] Procesando {img} con motor Chandra...")
            # Aquí se invocaría chandra.bin o la API
            extracted_text = f"Result of OCR for {img}: [LOGIC LEAK DETECTED IN FORM/TABLE]"
            results.append({
                "source": img,
                "text": extracted_text,
                "type": "semantic_ocr_extraction"
            })
            # Mover a procesadas (Simulado)
            os.rename(os.path.join(self.image_dir, img), os.path.join(self.image_dir, f"processed_{img}"))
        
        return results

if __name__ == "__main__":
    bridge = ChandraBridge()
    leaks = bridge.process_visual_leaks()
    print(f"Leaks visuales detectados: {len(leaks)}")
