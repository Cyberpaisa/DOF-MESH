# SDK DE GOBERNANZA UNIVERSAL MULTI-SEGMENTO (DOF-MESH)
## Visión Estratégica y Arquitectura | Abril 2026

### 1. Definición del Producto
El SDK es una **capa de infraestructura horizontal** que permite a cualquier organización integrar gobernanza determinística en sus agentes autónomos. Es el "TLS para la IA".

### 2. Arquitectura de 5 Capas
| Capa | Componentes |
|------|-------------|
| **5. Interfaces** | SDKs (Py, Node, Go), CLI, REST API, MCP Server. |
| **4. Orquestación** | Agent Runtime (CrewAI/LangGraph), Memory Manager. |
| **3. Gobernanza** | Constitution Registry (HIPAA, SOX, etc.), Z3 Verifier, MetaSupervisor. |
| **2. Prueba/Attestación** | Proof Engine, Attestation Layer (Web3, PKI, DLT). |
| **1. LLM Engine** | LiteLLM Router (Kimi, Claude, GPT, Local). |

### 3. Stack Técnico Core
- **Routing:** LiteLLM (failover + multi-provider).
- **Verificación:** Z3-Solver (pruebas formales de invariantes).
- **Atestación:** Web3 (EVM chains) + PKI (X.509 para Enterprise).
- **Memoria:** ChromaDB + Redis.

### 4. Estrategia por Industria
- **FinTech:** Kimi K2.6 + SOX Pack + Avalanche/Base.
- **GovTech (US):** Claude Sonnet + FedRAMP Pack + PKI/DID + AWS Bedrock.
- **Salud:** Claude Sonnet + HIPAA Pack + Hyperledger Fabric.

---
*Documento de referencia para el pivot estratégico a SDK Universal.*
