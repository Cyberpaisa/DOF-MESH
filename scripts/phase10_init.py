import time
import logging
from core.mesh_orchestrator import MeshOrchestrator

logging.basicConfig(level=logging.INFO)

def launch_phase_10_alpha():
    orch = MeshOrchestrator()
    nodes = ["architect", "researcher", "guardian", "verifier", "narrator", "devops"]
    
    print(f"--- INICIANDO DESPLIEGUE MASIVO FASE 10 (PROVIDER: DEEPSEEK) ---")
    
    for node_type in nodes:
        task = {
            "task_id": f"phase10-alpha-{node_type}-{int(time.time())}",
            "task_type": node_type,
            "context_length": 50000,
            "payload": f"Fase 10 Iniciada. El Soberano CyberPaisa demanda máxima operatividad. Analiza tu submódulo y optimiza para escalado global via Hyperion.",
            "msg_type": "urgent"
        }
        print(f"Despachando tarea a {node_type}...")
        result = orch.orchestrate(task)
        print(f"  [+] Result: {result.selected_node} (Latency: {result.latency_ms}ms)")

    print("\n[!] Todos los nodos han sido activados. La Legion está a plena potencia.")

if __name__ == "__main__":
    launch_phase_10_alpha()
