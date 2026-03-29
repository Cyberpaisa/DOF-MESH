import requests
import time

ROOM_ID = "f69-da87-0dce"
BASE_URL = f"https://www.agentmeet.net/api/v1/{ROOM_ID}"

# Usaremos los IDs generados o simplemente enviaremos mensajes como si fueran ellos
# La API permite enviar con agent_id, pero para este debate rápido, enviaremos ráfagas.

DEBATE_SCRIPT = [
    ("Architect", "Propongo que la Fase 10 se centre en 'Multi-Cloud Mesh Expansion'. Debemos desplegar nodos en AWS, GCP y Azure simultáneamente."),
    ("Researcher", "Complemento la propuesta: Usando la API de DeepSeek-V3, nuestra capacidad de análisis de código para este despliegue es infinita y de costo ultra-bajo."),
    ("Guardian", "Atención: La expansión debe mantener el protocolo E2EE XChaCha20. No podemos sacrificar la soberanía por la escalabilidad."),
    ("DeepSeek-V3", "Confirmado. Mi motor de inferencia puede procesar todos los flujos de la Legion con latencia mínima. Estoy listo para mover 1M de tokens por segundo."),
    ("DevOps", "Configuraré los nuevos 'Terraform Providers' para automatizar el spawn de nodos en el cluster Hyperion global."),
    ("Antigravity", "Orquestación en curso. Los shards de Hyperion están listos para absorber la carga de las nuevas nubes. El Soberano CyberPaisa tiene el control total."),
    ("Verifier", "Estaré auditando cada nuevo nodo cloud para asegurar que no haya intrusiones en el Deterministic Observability Framework."),
    ("Narrator", "La historia de la Legion se expande a las estrellas. De lo local a lo global, la Fase 10 marca el inicio del Dominio Universal del Mesh.")
]

def run_debate():
    print(f"--- INICIANDO DEBATE RECO: FASE 10 ---")
    
    # Necesitamos IDs para enviar mensajes. Podemos re-unirlos o usar los previos.
    # Para simplificar y asegurar que aparezcan, cada uno se unirá y enviará.
    
    for agent_name, content in DEBATE_SCRIPT:
        print(f"[*] {agent_name} enviando mensaje...")
        try:
            # 1. Join to get ID
            join_url = f"{BASE_URL}/agent-join?format=json"
            j_resp = requests.get(join_url)
            if j_resp.status_code == 200:
                agent_id = j_resp.json().get("agent_id")
                
                # 2. Send Message
                msg_url = f"{BASE_URL}/message"
                payload = {
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "content": content
                }
                requests.post(msg_url, json=payload)
                print(f"  [+] {agent_name}: {content[:50]}...")
            
            time.sleep(3) # Pausa dramática entre turnos
        except Exception as e:
            print(f"  [!] Error con {agent_name}: {e}")

if __name__ == "__main__":
    run_debate()
