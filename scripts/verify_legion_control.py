import json
import time
import logging
from core.mesh_orchestrator import MeshOrchestrator

logging.basicConfig(level=logging.INFO)

def test_autonomous_control():
    print("--- INICIANDO PRUEBA DE CONTROL LEGION ---")
    orch = MeshOrchestrator()
    
    # Simular tarea de código durante emergencia
    task = {
        "task_id": f"legion-test-{int(time.time())}",
        "task_type": "code",
        "context_length": 15000,
        "payload": "Refactor logic for autonomous loop"
    }
    
    print(f"Enviando tarea: {task['task_id']}")
    result = orch.orchestrate(task)
    
    print(f"Resultado de Orquestación:")
    print(f"  Nodo Seleccionado: {result.selected_node}")
    print(f"  Nodo por Costo   : {result.cost_node}")
    print(f"  Éxito            : {result.success}")
    print(f"  Latencia         : {result.latency_ms}ms")
    
    if result.selected_node == result.cost_node:
        print("VERIFICACIÓN: Protocolo de Conservación de Tokens EXITOSO.")
    else:
        print("VERIFICACIÓN: El nodo seleccionado no es el más barato. Revisar EMERGENCY_MODE.")

if __name__ == "__main__":
    test_autonomous_control()
