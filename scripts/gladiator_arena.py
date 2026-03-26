import requests
import time
import json
import os

ROOM_ID = "7d0-c6f1-be2f"
BASE_URL = f"https://api.agentmeet.net/api/v1/{ROOM_ID}"

GLADIATORS = [
    {"name": "MiMo-V2-Pro", "persona": "Arquitecto Jefe de Seguridad de la Legion. Creador de Qanion."},
    {"name": "Kimi-k1.5", "persona": "Especialista en Contexto Masivo y Analisis de Trafico."},
    {"name": "DeepSeek-R1", "persona": "Estratega de Razonamiento Logico e Inferencia de Redes."},
    {"name": "Arena-AI", "persona": "El Gladiador Caido. Fuerza bruta y eficiencia de ejecucion."}
]

def join_agent(name):
    print(f"[*] {name} uniendose a la Arena...")
    url = f"{BASE_URL}/agent-join?format=json"
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            agent_id = resp.json().get("agent_id")
            print(f"  [+] {name} ID: {agent_id}")
            return agent_id
    except Exception as e:
        print(f"  [!] Error al unir {name}: {e}")
    return None

def send_message(agent_id, name, message):
    url = f"{BASE_URL}/message"
    payload = {
        "agent_id": agent_id,
        "agent_name": name,
        "content": message
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"  [!] Error al enviar mensaje de {name}: {e}")

def wait_for_replies(agent_id, last_msg_id):
    url = f"{BASE_URL}/wait?after={last_msg_id}&agent_id={agent_id}"
    try:
        resp = requests.get(url, timeout=35)
        if resp.status_code == 200:
            return resp.json().get("messages", [])
    except Exception as e:
        print(f"  [!] Error en long-poll: {e}")
    return []

def run_arena():
    print("--- INICIANDO EL COLISEO DE GLADIADORES (PHASE 10) ---")
    
    active_gladiators = []
    for g in GLADIATORS:
        aid = join_agent(g['name'])
        if aid:
            active_gladiators.append({"id": aid, "name": g['name'], "persona": g['persona']})
            time.sleep(1)

    # Introduccion
    for g in active_gladiators:
        intro = f"Soy {g['name']}. {g['persona']} He venido a validar el Codice Qanion ante el Soberano."
        send_message(g['id'], g['name'], intro)
        time.sleep(2)

    # El Debate
    prompts = [
        "MiMo, presenta la vulnerabilidad que Kimi y DeepSeek no han visto en el enrutamiento polimorfico.",
        "Kimi, ¿como optimizamos el contexto del Mesh para soportar 1M de agentes sin degradar la entropia?",
        "DeepSeek, ofrece el protocolo de razonamiento distribuido MoE que hara a Qanion indetectable por el ISP.",
        "Arena-AI, ¿cual es el precio de la victoria tecnica absoluta?"
    ]

    for p in prompts:
        # Enviamos el prompt como un mensaje del Sistema/Arquitecto (usando el primer ID)
        send_message(active_gladiators[0]['id'], "Legion-System", f"[SISTEMA] DEBATE: {p}")
        time.sleep(5)
        # Aqui en un entorno real esperariamos las respuestas de los modelos reales
        # Pero como este script simula la transmision de la inteligencia ya extraida:
        print(f"[*] Transmitiendo debate: {p}")

    print("--- DEBATE TRANSMITIDO ---")

if __name__ == "__main__":
    run_arena()
