import time
import logging
from concurrent.futures import ThreadPoolExecutor
from core.mesh_orchestrator import MeshOrchestrator

logging.basicConfig(level=logging.INFO)

def send_task(orch, i):
    task = {
        "task_id": f"stress-test-{i}-{int(time.time())}",
        "task_type": "researcher",
        "context_length": 1000,
        "payload": f"STRESS TEST {i}: Validate sub-module {i % 10} for global scaling.",
        "msg_type": "urgent"
    }
    try:
        start = time.time()
        result = orch.orchestrate(task)
        latency = (time.time() - start) * 1000
        return f"Task {i}: {result.selected_node} ({latency:.1f}ms)"
    except Exception as e:
        return f"Task {i}: FAILED ({e})"

def run_big_stress_test(num_tasks=100):
    orch = MeshOrchestrator()
    print(f"--- INICIANDO PRUEBA DE ESTRÉS MASIVA: {num_tasks} TAREAS ---")
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(lambda i: send_task(orch, i), range(num_tasks)))

    for r in results:
        print(r)

    print("\n[!] Prueba de Estrés Finalizada.")

if __name__ == "__main__":
    run_big_stress_test()
