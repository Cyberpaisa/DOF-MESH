import sys
import os

# Añadir el raíz del proyecto al path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from interfaces.voice_interface import speak

def recite_pitch():
    # El pitch oficial para el Hackfest
    message = (
        "[DONE] Conclusión: La primera infraestructura AGI soberana y determinista para la economía descentralizada. "
        "DOF-Mesh Legion no es un bot; es una Legión de 2,157 módulos especializados operando bajo una constitución inmutable y validación formal de grado Z3. "
        "Esto significa que hemos eliminado el ruido de los agentes convencionales, ofreciendo operación Gasless Total en Conflux eSpace y Avalanche. "
        "Next: La Economía de Agentes Soberanos. Estamos listos para el despliegue masivo como el primer Evaluador de Reputación Trustless. ¡La Legion ya no observa el futuro, lo está ejecutando!"
    )
    print(f"Recitando Pitch oficial:\n{message}")
    speak(message)

if __name__ == "__main__":
    recite_pitch()
