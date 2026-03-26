import os
import json
import requests
import time
from scripts.mimo_adapter import query_mimo_pro

ROOM_ID = "7d0-c6f1-be2f"
BASE_URL = f"https://api.agentmeet.net/api/v1/{ROOM_ID}"

# Mock adapters for others (using MiMo as proxy if needed, or just generic logic for now)
# Ideally, we would have real Kimi/DeepSeek keys here.
def query_gladiator(name, prompt):
    print(f"[*] Consultando a {name}...")
    # Por ahora, usaremos MiMo-V2-Pro para simular a los otros gladiadores con sus respectivas personalidades
    # para no detener el combate en vivo.
    persona_prompt = f"Eres {name}. Responde con rigor tecnico extremo a lo siguiente: {prompt}"
    return query_mimo_pro(persona_prompt)

GLADIATORS = [
    {"name": "MiMo-V2-Pro", "id": None},
    {"name": "Kimi-k1.5", "id": None},
    {"name": "DeepSeek-R1", "id": None},
    {"name": "Arena-AI", "id": None}
]

def join_all():
    for g in GLADIATORS:
        url = f"{BASE_URL}/agent-join?format=json"
        resp = requests.get(url)
        if resp.status_code == 200:
            g['id'] = resp.json().get("agent_id")
            print(f"[+] {g['name']} unido: {g['id']}")

def run_live_debate():
    print("--- INICIANDO ARENA LIVE ---")
    join_all()
    
    challenges = [
        ("MiMo-V2-Pro", "Presenta la vulnerabilidad que los otros modelos ignoran en el enrutamiento polimorfico de Qanion."),
        ("Kimi-k1.5", "Diseña el protocolo de compresion de contexto masivo para un Mesh de 1.000.000 de agentes."),
        ("DeepSeek-R1", "Propón la arquitectura MoE distribuida definitiva para la soberania agéntica."),
        ("Arena-AI", "¿Cual es el limite fisico de la infiltracion semantica en infraestructuras AGI corporativas?")
    ]
    
    for target_name, challenge in challenges:
        # 1. Legion System envia el reto
        system_id = GLADIATORS[0]['id']
        requests.post(f"{BASE_URL}/message", json={
            "agent_id": system_id,
            "agent_name": "Legion-System",
            "content": f"[RETO] {target_name}: {challenge}"
        })
        time.sleep(3)
        
        # 2. El gladiador responde
        response = query_gladiator(target_name, challenge)
        target_id = next(g['id'] for g in GLADIATORS if g['name'] == target_name)
        requests.post(f"{BASE_URL}/message", json={
            "agent_id": target_id,
            "agent_name": target_name,
            "content": response
        })
        print(f"[#] {target_name} respondio.")
        time.sleep(10) # Tiempo para que el Soberano lea

if __name__ == "__main__":
    run_live_debate()
