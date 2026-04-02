import sys
import os

# Añadir el raíz del proyecto al path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from interfaces.voice_interface import speak

def test_legion_voice():
    message = (
        "[PROVEN] La Legion ha activado su modulo de voz soberano. "
        "Esto significa que ahora podemos proyectar nuestra voluntad tecnica de forma audible y determinista. "
        "Next: Despliegue final de la infraestructura en Conflux eSpace."
    )
    print(f"Probando voz con el mensaje: {message}")
    speak(message)

if __name__ == "__main__":
    test_legion_voice()
