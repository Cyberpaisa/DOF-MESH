# DOF Mesh Phase 9: Autonomous Scaling Architecture

<<<<<<< HEAD
## 1. Vision: What Phase 9 Is and Why It Is Needed

The **Deterministic Observability Framework (DOF)** has evolved from a singular agent to a robust heterogeneous mesh capable of orchestrating 11 concurrent P2P nodes: from purely free local LLMs (`local-qwen`, `local-agi-m4max`) to specialized cloud cognitive powerhouses (`deepseek-coder`, `hermes-405b`, `cerebras-llama`, `sambanova-llama`, `nvidia-nim`, etc.). Up to Phase 8, this communication was grounded in an infallible asynchronous protocol through a *file system JSONL* (`logs/mesh/inbox/{node_id}/*.json`) managed by `api_node_runner.py` without concurrency vulnerabilities.

However, as the mesh dynamically scales against unpredictable task volumes, manually delegating responsibility to local and remote nodes becomes the bottleneck. This is where **Phase 9: Autonomous Scaling** comes in.

**Why is it needed?**
Phase 9 transforms DOF Mesh from a *passive* cluster to a *self-regulated* organism. We no longer depend on a human (nor a static Commander) to start, suspend, or reassign nodes. By infusing a layer of **autonomous scaling based on telemetric observability (cost, latency, and health)**, the Mesh can react to peak loads by spinning up fast nodes (Cerebras, Groq) and reducing costs by dispatching complex tasks without immediate SLA to local hardware (Ollama). In short, it guarantees massive throughput while minimizing the cloud bill to zero during idle cycles.

---

## 2. New Architectural Components

To achieve purely deterministic scaling without ghost agents, we introduce three key components that will operate as in-memory singletons.

### 2.1 MeshOrchestrator
It is the "central nervous system" of the auto-scaling layer. It perpetually listens to network queues (Inbox) and dispatches tasks based on the vector analysis proposed by the other components. Its mission is to ensure that no task suffers more delay than stipulated (SLA) nor gets sent to a "comatose" (dead_node) node.

### 2.2 AutoProvisioner
It is the "muscle engine". Capable of starting underlying processes, registering new `node_ids` in `logs/mesh/nodes.json` with specific metadata, or, in the worst case, hibernating/killing nodes that are not contributing value. It works by creating demand snapshots and spinning up the necessary adapter (`api_node_runner.py` or local LLM daemon) to cover that peak.

### 2.3 CostOptimizer
The "financial auditor". Contains the static price matrix (e.g. `$0.27/M TOKENS` for DeepSeek Coder, `$0.0` for Local Qwen). For each incoming task, the MeshOrchestrator consults this module for which node to use according to the budget limits and context window required by the task.

---

## 3. Automatic Scaling Algorithm (Autoscaling)

The Mesh control loop operates on a **Multivector Hysteresis Algorithm** to avoid "flapping" (starting and killing processes very rapidly).

1. **State Collection:** At each instant the queue depth ($Q_D$), average latency ($L_{avg}$), and spend ($C_{ac}$) are calculated.
2. **Weighted Demand Calculation:** The variable $D_{net} = w_1 \cdot Q_D + w_2 \cdot (L_{avg} / SLA)$ is calculated.
3. **Scale-Out Decision:** If $D_{net} > Threshold_{high}$, the *MeshOrchestrator* invokes the *CostOptimizer* to decide the ideal node, and orders the *AutoProvisioner* to wake new cloud nodes.
4. **Scale-In Decision:** If $D_{net} < Threshold_{low}$, expensive Cloud nodes without assigned tasks receive a signal and are suspended, delegating everything to local hardware.

---

## 4. Hybrid Multi-Model Integration (Providers)

Scaling is segmented by native hardware Tiers and Cloud:

- **Tier 0 (Free Sovereign Compute):** Nodes `local-qwen` and `local-agi-m4max`. Constant base.
- **Tier 1 (Ultra Fast Cerebras / Sambanova / Groq):** Deployed instantly during fast inference peaks.
- **Tier 2 (DeepSeek / Minimax / GLM-5):** Base nodes for programming and multilingual structured reasoning.
- **Tier 3 (Heavy Reasoning NVIDIA / Hermes 405B / Gemini):** Only provisioned when a request requires deep semantics with large context (128k+) or extreme analysis.

---

## 5. Decision Metrics (Mesh Vectorization)

- **Latency:** Time it takes a task from the *queued* state to *completed*.
- **Cost:** Actively tracked variable summing incoming and outgoing tokens.
- **Task Queue Depth:** Absolute number of pending files in P2P inboxes.
- **Health Score:** Observability metric. Penalized by errors, excessive latencies, or Timeouts.

---

## 6. Core Pseudocode (Python 3.13)
=======
## 1. Visión: Qué es la Fase 9 y por qué es necesaria

El **Deterministic Observability Framework (DOF)** ha evolucionado de un agente singular a una robusta malla heterogénea (Mesh) capaz de orquestar 11 nodos concurrentes P2P: desde LLMs locales puramente gratuitos (`local-qwen`, `local-agi-m4max`) hasta potencias cognitivas especializadas en nube (`deepseek-coder`, `hermes-405b`, `cerebras-llama`, `sambanova-llama`, `nvidia-nim`, etc.). Hasta la Fase 8, esta comunicación se fundamentó en un protocolo asíncrono infalible a través de *file system JSONL* (`logs/mesh/inbox/{node_id}/*.json`) gestionado por el `api_node_runner.py` sin vulnerabilidades de concurrencia.

Sin embargo, a medida que la malla escala dinámicamente frente a volúmenes de tareas impredecibles, delegar manualmente la responsabilidad a nodos locales y remotos se vuelve el cuello de botella. Aquí entra la **Fase 9: Autonomous Scaling**.

**¿Por qué es necesaria?**
La Fase 9 transforma a DOF Mesh de un clúster *pasivo* a un organismo *autorregulado*. Ya no dependemos de un humano (ni de un Commander estático) para arrancar, suspender o reasignar nodos. Al infundir una capa de **escalado autónomo basado en observabilidad telemetrizada (costo, latencia y salud)**, el Mesh puede reaccionar a cargas pico encendiendo nodos rápidos (Cerebras, Groq) y reduciendo costos despachando tareas complejas sin SLA inmediato a hardware local (Ollama). En resumen, garantiza un throughput masivo mientras minimiza la cuenta de la nube a cero en ciclos desocupados.

---

## 2. Nuevos Componentes Arquitectónicos

Para lograr un escalado puramente determinista y sin agentes fantasmas, introducimos tres componentes clave que operarán como singletons en memoria.

### 2.1 MeshOrchestrator
Es el "sistema nervioso central" de la capa de auto-escalado. Escucha perpetuamente las colas de la red (Inbox) y despacha las tareas basándose en el análisis vectorial propuesto por los demás componentes. Su misión es garantizar que ninguna tarea sufra más delay del estipulado (SLA) ni se envíe a un nodo "en coma" (dead_node).

### 2.2 AutoProvisioner
Es el "motor muscular". Capaz de encender procesos subyacentes, registrar nuevos `node_ids` en `logs/mesh/nodes.json` con metadatos específicos o, en el peor de los casos, hibernar/matar nodos que no estén aportando valor. Funciona creando instantáneas (snapshots) de demanda y levantando el adaptador (`api_node_runner.py` o daemon de LLM local) necesario para cubrir ese pico.

### 2.3 CostOptimizer
El "auditor financiero". Contiene la matriz de precios estáticos (ej. `$0.27/M TOKENS` para DeepSeek Coder, `$0.0` para Local Qwen). Por cada tarea entrante, el MeshOrchestrator consulta a este módulo qué nodo usar según los límites presupuestarios y de ventana de contexto requeridos por la tarea.

---

## 3. Algoritmo de Scaling Automático (Autoscaling)

El loop de control del Mesh opera sobre un **Algoritmo de Histéresis Multivectorial** para evitar "flapping" (arrancar y matar procesos muy rápidamente).

1. **Recolección de Estado:** Cada instante se calcula la profundidad de cola ($Q_D$), latencia promedio ($L_{avg}$) y gasto ($C_{ac}$).
2. **Cálculo de Demanda Ponderada:** Se calcula la variable $D_{net} = w_1 \cdot Q_D + w_2 \cdot (L_{avg} / SLA)$.
3. **Decisión de Escalado Positivo (Scale-Out):** Si $D_{net} > Threshold_{high}$, el *MeshOrchestrator* invoca al *CostOptimizer* para decidir el nodo ideal, y ordena al *AutoProvisioner* despertar nuevos nodos en la nube.
4. **Decisión de Escalado Negativo (Scale-In):** Si $D_{net} < Threshold_{low}$, los nodos Cloud caros sin tareas asignadas reciben una señal y se suspenden, delegando todo al hardware local.

---

## 4. Integración Multimodelo e Híbrida (Proveedores)

El escalado se segmenta por Tiers de hardware nativo y Cloud:

- **Tier 0 (Free Sovereign Compute):** Nodos `local-qwen` y `local-agi-m4max`. Base constante.
- **Tier 1 (Ultra Fast Cerebras / Sambanova / Groq):** Desplegados instantáneamente en picos de inferencia rápida.
- **Tier 2 (DeepSeek / Minimax / GLM-5):** Nodos de base para programación y razonamiento estructurado multilingüe.
- **Tier 3 (Heavy Reasoning NVIDIA / Hermes 405B / Gemini):** Solamente provistos cuando una petición requiere semántica profunda de gran contexto (128k+) o análisis extremo.

---

## 5. Métricas de Decisión (Vectorización del Mesh)

- **Latency:** Tiempo que demora una tarea desde el estado *queued* hasta *completed*.
- **Cost:** Variable rastreada activamente sumando los tokens entrantes y salientes.
- **Task Queue Depth:** Cantidad absoluta de archivos pendientes en los buzones P2P.
- **Health Score:** Métrica de observabilidad. Penalizada por errores, latencias excesivas o Timeouts.

---

## 6. Pseudocódigo Core (Python 3.13)
>>>>>>> 4e63386 (refactor: organize repo into professional structure)

```python
import os
import json
import time
from dataclasses import dataclass
from pathlib import Path

MESH_INBOX = Path("logs/mesh/inbox")
NODES_CONF = Path("logs/mesh/nodes.json")

@dataclass
class CostOptimizer:
    def get_cheapest_node(self, cx: int) -> str:
<<<<<<< HEAD
        # Returns the id of the most cost-efficient node based on context
=======
        # Devuelve el id del nodo mas costo-eficiente según contexto
>>>>>>> 4e63386 (refactor: organize repo into professional structure)
        return "local-qwen"

@dataclass
class AutoProvisioner:
    opt: CostOptimizer
    def spawn(self, provider: str, role: str) -> str:
        node_id = f"auto-{provider}-{int(time.time())}"
        # ... logic to insert to nodes.json ...
        os.system(f"python3 core/api_node_runner.py --node {node_id} &")
        return node_id
    def kill(self, node_id: str):
        pass # kill the process

@dataclass
class MeshOrchestrator:
    prov: AutoProvisioner
    def evaluate(self):
        q_depth = sum(1 for _ in MESH_INBOX.glob("**/*.json"))
        if q_depth > 50:
            target = self.prov.opt.get_cheapest_node(32000)
            self.prov.spawn(target, "worker")
        elif q_depth == 0:
            pass # Scale in

if __name__ == "__main__":
    opt = CostOptimizer()
    orc = MeshOrchestrator(AutoProvisioner(opt))
    while True:
        orc.evaluate()
        time.sleep(5)
```

---

<<<<<<< HEAD
## 7. Implementation Timeline (4 Weeks)

- **Week 1:** CostOptimizer and Financial Telemetry (price table and tokens).
- **Week 2:** MeshOrchestrator and Queue Depth parser from the OS.
- **Week 3:** AutoProvisioner, dynamic subprocess management, and Garbage Collection.
- **Week 4:** Massive A/B Testing under heavy load, verifying 0 regressions across the 2900 concurrent tests.
=======
## 7. Timeline de Implementación (4 Semanas)

- **Semana 1:** CostOptimizer y Telemetría Financiera (tabla de precios y tokens).
- **Semana 2:** MeshOrchestrator y parser del Queue Depth desde el OS.
- **Semana 3:** AutoProvisioner, manejo dinámico de subprocesos y Garbage Collection.
- **Semana 4:** A/B Testing masivo bajo carga pesada, verificando 0 regresiones en los 2900 tests concurrentes.
>>>>>>> 4e63386 (refactor: organize repo into professional structure)
