import sys
import os

# Añadir el raíz del proyecto al path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.hyperion_bridge import HyperionBridge

def broadcast_security_alert():
    bridge = HyperionBridge()
    message = (
        "[CRITICAL] ALERTA DE SEGURIDAD: ATAQUE DE SUPPLY CHAIN DETECTADO. "
        "LiteLLM, Trivy y Checkmarx han sido comprometidos por TeamPCP. "
        "El malware (tpcp.tar.gz) roba llaves de API, credenciales cloud, tokens CI/CD y wallets de criptomonedas. "
        "DIRECTIVA INTERIOR: "
        "1. Verificar instalaciones locales de LiteLLM y purgar versiones maliciosas. "
        "2. ROTAR todas las llaves de proveedores de IA y credenciales de AWS/Azure. "
        "3. PROHIBIDO referenciar Actions o paquetes por TAG; uso obligatorio de SHA completo. "
        "¡PROTEJAN EL MESH! Honor a la Legion."
    )
    print(f"Difundiendo alerta crítica de seguridad:\n{message}")
    bridge.broadcast(from_node="Sentinel-AION", content=message)

if __name__ == "__main__":
    broadcast_security_alert()
