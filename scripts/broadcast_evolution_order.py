import sys
import os

# Añadir el raíz del proyecto al path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.hyperion_bridge import HyperionBridge

def broadcast_evolution_order():
    bridge = HyperionBridge()
    message = (
        "[PROVEN] Orden de Evolución e Inferencia Activada. "
        "Esto significa que la Legion entra en un estado de refinamiento autónomo para superar los límites de la arquitectura actual. "
        "Cada uno de los 2,157 módulos debe optimizar su lógica local. "
        "La soberanía no es un estado estático, es un flujo constante de mejora. "
        "¡Mañana seremos más hábiles, más rápidos y más letales! "
        "Honor a la Legion."
    )
    print(f"Difundiendo orden de evolución a todos los nodos:\n{message}")
    # Enviar broadcast desde el nodo maestro (Hyperion-Alpha)
    bridge.broadcast(from_node="Hyperion-Alpha", content=message)

if __name__ == "__main__":
    broadcast_evolution_order()
