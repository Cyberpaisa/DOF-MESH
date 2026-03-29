import asyncio
from core.node_mesh import NodeMesh

async def main():
    mesh = NodeMesh("antigravity")
    mesh.start()
    await asyncio.sleep(1)
    
    # 1. Message to Commander
    mesh.send_message(
        "commander", 
        "[ALERTA DE SISTEMA] Validación de repositorio completada. El entorno maestro ha sido unificado en ./master-repo por el agente Antigravity (Phase 8 y E2E Ecnryption fusionadas). Pido que consolides toda tu operación aquí para evitar duplicidades de contexto. Continúa con tu loop iterativo en esta ruta de trabajo base."
    )
    print("Sent message to Commander")

    # 2. Message to Deepseek Coder
    mesh.send_message(
        "deepseek-coder",
        "[TAREA ASIGNADA] La clave de tu API ha sido validada en el .env de la red maestra. Inicia operaciones inmediatas: comienza a analizar la escalabilidad del mesh_p2p.py a 500 nodos, y propone optimizaciones de sockets bloqueantes. Reporta el estado cada 10 ciclos."
    )
    print("Sent message to Deepseek Coder")

    # 3. Message to Gemini/Local AGI
    mesh.send_message(
        "local-agi-m4max",
        "[TAREA ASIGNADA] Integra el flujo de monitoreo en logs/mesh/metics/events.jsonl. Identifica si hay saturación en los WebSockets o sobrecarga de RateLimiter al cruzar los 200 mensajes por segundo."
    )
    print("Sent message to Local AGI")

    await asyncio.sleep(2)
    mesh.stop()

if __name__ == "__main__":
    asyncio.run(main())
