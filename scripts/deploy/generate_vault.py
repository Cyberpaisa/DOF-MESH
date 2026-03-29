import os
import binascii

# INFRAESTRUCTURA DE CLAVES SOBERANAS Q-AION
# Generamos una clave privada local que solo el sistema puede leer.

KEY_PATH = "/Users/jquiceva/equipo-de-agentes/scripts/.q_aion_vault.key"

def generate_sovereign_key():
    """
    Genera una nueva clave privada de Ethereum/Avalanche y la guarda localmente.
    """
    if os.path.exists(KEY_PATH):
        with open(KEY_PATH, "r") as f:
            return f.read().strip()
    
    # Generar 32 bytes aleatorios (clave privada de 256 bits)
    priv_key = binascii.hexlify(os.urandom(32)).decode()
    
    # Guardar con permisos restringidos
    with open(KEY_PATH, "w") as f:
        f.write(priv_key)
    os.chmod(KEY_PATH, 0o600)
    
    print(f"[🛡] BÓVEDA Q-AION: Clave soberana generada y protegida en {KEY_PATH}")
    return priv_key

if __name__ == "__main__":
    generate_sovereign_key()
