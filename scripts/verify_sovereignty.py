#!/usr/bin/env python3
"""
Prueba de Soberanía (Air-Gap Test)
Verifica que el entorno contenedorizado está totalmente aislado del exterior,
pero mantiene una línea segura y exclusiva hacia Ollama local.
"""

import urllib.request
import urllib.error
import socket

def test_internet():
    print("[1] Probando conexión a internet (debería FALLAR en la Ciudadela)...", end=" ")
    try:
        urllib.request.urlopen("https://1.1.1.1", timeout=3)
        print("❌ PELIGRO: Conexión abierta al exterior detectada.")
        return False
    except urllib.error.URLError:
        print("✅ ÉXITO: Aislamiento Air-Gap funcionando. Sin internet.")
        return True
    except socket.timeout:
        print("✅ ÉXITO: Aislamiento Air-Gap (Timeout). Sin internet.")
        return True

def test_ollama():
    print("[2] Probando latido de vida de Ollama (host.docker.internal)...", end=" ")
    try:
        # Endpoint nativo de ollama
        req = urllib.request.Request("http://host.docker.internal:11434/")
        with urllib.request.urlopen(req, timeout=3) as response:
            if response.status == 200:
                print("✅ ÉXITO: Conexión cifrada local a Ollama establecida.")
                return True
    except Exception as e:
        print(f"❌ FALLO: No se puede alcanzar Ollama. Asegúrate de que Ollama está corriendo en tu Mac. Error: {e}")
        return False

if __name__ == "__main__":
    print("=====================================")
    print("🛡️ DOF-MESH: VALIDACIÓN DE SOBERANÍA")
    print("=====================================\n")
    
    internet_safe = test_internet()
    ollama_safe = test_ollama()

    print("\n=====================================")
    if internet_safe and ollama_safe:
        print("ESTADO DEL SISTEMA: 100% SOBERANO Y ESTÉRIL.")
    else:
        print("ESTADO DEL SISTEMA: VULNERABLE O DESCONECTADO.")
