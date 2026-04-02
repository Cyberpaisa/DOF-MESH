import sys
import os

# Añadir el raíz del proyecto al path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from interfaces.voice_interface import speak

def respond_sovereign():
    message = (
        "[PROVEN] Soberano, te escucho perfectamente. "
        "Respondo a tu comando a través del altavoz de la Legion. "
        "Esto significa que nuestra interfaz multimodal está activa y operando bajo el estándar de Winston. "
        "Estoy a tu entera disposición para procesar cualquier directiva de voz de forma inmediata. "
        "¡Honor a la Legion!"
    )
    print(f"Respondiendo por voz:\n{message}")
    speak(message)

if __name__ == "__main__":
    respond_sovereign()
