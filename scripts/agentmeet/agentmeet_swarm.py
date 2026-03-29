import subprocess
import time

agents = [
    "Antigravity",
    "Architect",
    "Researcher",
    "Guardian",
    "Verifier",
    "Narrator",
    "DevOps",
    "DeepSeek-V3",
    "Kimi-K2.5",
    "Gemini-Flash"
]

print(f"--- LANZANDO SWARM DE LA LEGION (Total: {len(agents)}) ---")

processes = []
for agent in agents:
    print(f"[*] Desplegando {agent}...")
    # Ejecutamos el cliente para cada agente en background
    p = subprocess.Popen(["python3", "scripts/agentmeet_client.py", agent])
    processes.append(p)
    time.sleep(1) # Pausa para no saturar el registro

print(f"\n[+] Swarm desplegado. {len(agents)} agentes están ahora en la sala.")
print("[!] Manteniendo procesos activos...")

try:
    while True:
        time.sleep(10)
except KeyboardInterrupt:
    print("\n[*] Deteniendo swarm...")
    for p in processes:
        p.terminate()
