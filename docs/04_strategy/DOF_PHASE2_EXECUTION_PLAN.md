# DOF PHASE 2 — EXECUTION PLAN
## Memory Governance + OAGS Bridge + Oracle Bridge ERC-8004

**Author:** Juan Carlos Quiceno Vasquez
**Project:** `/Users/jquiceva/equipo de agentes/`
**Prerequisites:** Phase 1 complete (149 tests, CI verde, 8 modules)

---

## OVERVIEW

| Session | Module | Depends On | Time Est. | Tests Expected |
|---------|--------|------------|-----------|----------------|
| 9  | Memory Governance — GovernedMemoryStore | governance.py, constitution.yml | 45 min | ~25 new |
| 10 | Memory Governance — TemporalGraph | Session 9 | 30 min | ~15 new |
| 11 | Memory Governance — Classifier + Decay | Session 10 | 30 min | ~15 new |
| 12 | Memory Governance — Integration + Constitution | Sessions 9-11 | 30 min | ~10 new |
| 13 | OAGS Bridge — Identity + Policy | governance.py, constitution.yml | 45 min | ~20 new |
| 14 | Oracle Bridge — ERC-8004 Attestation | Sessions 9-13 | 45 min | ~20 new |
| 15 | Full Integration + README + Paper Update | Sessions 9-14 | 30 min | validation |
| **Total** | **7 sessions** | | **~4.5 hours** | **~105 new tests** |

After Phase 2: ~254 total tests, 25+ modules, 3 new systems fully integrated.

---

## WHY THIS ORDER

1. **Memory Governance first** (Sessions 9-12): Creates the governed memory store that OAGS Bridge needs for identity persistence and Oracle Bridge needs for attestation history.

2. **OAGS Bridge second** (Session 13): Uses memory governance to persist agent identities. Exports constitution.yml to sekuire.yml format. Needs to exist before Oracle Bridge because on-chain attestation requires OAGS-compatible identity.

3. **Oracle Bridge last** (Session 14): Takes governance metrics + OAGS identity and publishes to Avalanche ERC-8004. This is the capstone — it connects everything to the blockchain.

4. **Integration last** (Session 15): Wire everything together, update README, paper, and push.

---

## SESSION 9: GovernedMemoryStore (Core)

**What it creates:** The core governed memory store — add/update/delete with ConstitutionEnforcer validation on every operation. Zero external dependencies.

**Paste this in Claude Code:**

```
Lee estos archivos primero para entender los patrones existentes:
- core/memory_manager.py (el sistema de memoria actual con ChromaDB)
- core/governance.py (el ConstitutionEnforcer con HARD_RULES, SOFT_RULES, AST)
- core/observability.py (RunTrace, StepTrace, causal attribution)
- dof.constitution.yml (las reglas constitucionales)

Crea core/memory_governance.py con el componente principal: GovernedMemoryStore.

1. Dataclass MemoryEntry:
   - id: str (UUID4)
   - content: str
   - category: str (knowledge, preferences, context, decisions, errors)
   - metadata: dict
   - valid_from: datetime
   - valid_to: Optional[datetime] (None = vigente)
   - recorded_at: datetime
   - relevance_score: float (1.0 inicial)
   - governance_status: str ("approved", "warning", "rejected")
   - version: int (incrementa con cada update)
   - parent_id: Optional[str] (apunta a la versión anterior)

2. Clase GovernedMemoryStore:
   - __init__(constitution_path="dof.constitution.yml"):
     * Carga las reglas de governance
     * Inicializa lista de memorias vacía
     * Si existe memory/governed_store.jsonl, carga estado previo

   - Método add(content: str, category: str, metadata: dict = None) -> MemoryEntry:
     * ANTES de guardar, pasa el content por ConstitutionEnforcer
     * Si viola HARD_RULE → rechaza la memoria, loggea el rechazo, retorna entry con status "rejected"
     * Si viola SOFT_RULE → guarda con governance_status="warning"
     * Si pasa todo → guarda con governance_status="approved"
     * Verifica contra memorias existentes por similitud simple (keyword overlap > 70%)
     * Si ya existe memoria similar → llama update() en vez de crear nueva
     * Asigna memory_id único (UUID4), version=1, valid_from=now, relevance_score=1.0
     * Persiste a memory/governed_store.jsonl
     * Loggea operación a logs/memory_governance.jsonl
     * Retorna MemoryEntry

   - Método update(memory_id: str, new_content: str) -> MemoryEntry:
     * Misma governance que add()
     * NO sobrescribe: crea nueva versión con version+1 y parent_id=memory_id
     * Marca versión anterior con valid_to=now
     * Retorna nueva MemoryEntry

   - Método delete(memory_id: str, reason: str) -> bool:
     * Marca valid_to=now, NO borra físicamente
     * Loggea motivo del borrado
     * Retorna True si encontró y marcó

   - Método query(query: str, category: str = None, as_of: datetime = None) -> list[MemoryEntry]:
     * Filtra memorias activas (valid_to is None)
     * Si as_of: retorna memorias válidas EN ESA FECHA (valid_from <= as_of AND (valid_to is None OR valid_to > as_of))
     * Si category: filtra por categoría
     * Ordena por relevance_score descendente
     * Búsqueda por keyword matching simple (sin vector store externo)

   - Método get_history(memory_id: str) -> list[MemoryEntry]:
     * Sigue la cadena parent_id para encontrar todas las versiones
     * Retorna en orden cronológico

   - Método get_stats() -> dict:
     * total_memories, active_memories, by_category, by_status, avg_relevance

3. Persistencia:
   - Guardar en memory/governed_store.jsonl (una línea JSON por memory entry)
   - Cada operación append a logs/memory_governance.jsonl con: timestamp, operation, memory_id, status, reason

4. Tests en tests/test_memory_governance.py:
   - Test add con governance aprobada → status "approved"
   - Test add con HARD_RULE violada → status "rejected", no se guarda como activa
   - Test add con SOFT_RULE violada → status "warning", sí se guarda
   - Test update crea nueva versión sin sobrescribir
   - Test update mantiene cadena de parent_id
   - Test delete marca valid_to sin borrar físicamente
   - Test query filtra por categoría
   - Test query temporal (as_of) retorna estado histórico correcto
   - Test get_history retorna cadena completa de versiones
   - Test persistencia: guardar, crear nueva instancia, verificar que cargó todo
   - Test detección de memoria similar en add → llama update
   - Ejecuta TODOS los tests

IMPORTANTE:
- CERO dependencias externas nuevas
- CERO uso de LLM. Todo determinístico
- TODA operación loggeada a JSONL
- El ConstitutionEnforcer tiene la última palabra

NO hagas commit todavía. Solo crea el archivo y corre los tests.
```

**Expected output:** core/memory_governance.py created, ~25 tests passing.

---

## SESSION 10: TemporalGraph

**What it creates:** Bi-temporal versioning layer over the memory store. "What did the agent know last Tuesday at 3pm?"

**Paste this in Claude Code:**

```
Lee core/memory_governance.py que acabas de crear.

Agrega la clase TemporalGraph al mismo archivo core/memory_governance.py.

1. Clase TemporalGraph:
   - __init__(store: GovernedMemoryStore):
     * Referencia al store para acceder a las memorias

   - Método snapshot(as_of: datetime) -> list[MemoryEntry]:
     * Retorna el estado COMPLETO de la memoria en un punto del tiempo
     * Incluye solo memorias donde: valid_from <= as_of AND (valid_to is None OR valid_to > as_of)
     * Para memorias con múltiples versiones, retorna solo la versión vigente en as_of
     * "¿Qué sabía el agente el martes pasado a las 3pm?"

   - Método timeline(category: str = None) -> list[dict]:
     * Retorna línea de tiempo de TODOS los cambios
     * Cada entrada: {memory_id, action: "ADD"|"UPDATE"|"DELETE", timestamp, category, content_summary (primeros 100 chars)}
     * Si category: filtra solo esa categoría
     * Ordenado cronológicamente

   - Método diff(from_date: datetime, to_date: datetime) -> dict:
     * Compara estado de memoria entre dos fechas
     * Retorna: {added: [...], updated: [...], deleted: [...], unchanged: int}
     * "¿Qué cambió entre lunes y viernes?"

   - Método memory_age_distribution() -> dict:
     * Retorna distribución de edades de memorias activas
     * Buckets: <1h, 1h-24h, 1d-7d, 7d-30d, >30d
     * Útil para dashboards

2. Tests en tests/test_memory_governance.py (agregar a los existentes):
   - Test snapshot retorna estado correcto en un punto del tiempo
   - Test snapshot con memoria actualizada retorna versión correcta para la fecha
   - Test timeline retorna eventos en orden cronológico
   - Test timeline filtrado por categoría
   - Test diff entre dos fechas muestra cambios correctos
   - Test memory_age_distribution retorna buckets correctos
   - Ejecuta TODOS los tests (viejos + nuevos)

NO hagas commit todavía.
```

**Expected output:** TemporalGraph added, ~15 new tests passing, total growing.

---

## SESSION 11: MemoryClassifier + ConstitutionalDecay

**What it creates:** Deterministic category assignment and governed memory decay.

**Paste this in Claude Code:**

```
Lee core/memory_governance.py con GovernedMemoryStore y TemporalGraph.

Agrega dos clases más al mismo archivo core/memory_governance.py.

1. Clase MemoryClassifier:
   - Categorías predefinidas:
     * "knowledge" — hechos, datos técnicos, resultados de research
     * "preferences" — configuración, preferencias del usuario o sistema
     * "context" — contexto de sesión, tareas en progreso, estado temporal
     * "decisions" — decisiones tomadas y su justificación
     * "errors" — errores pasados, lecciones aprendidas, fallos documentados

   - Método classify(content: str) -> str:
     * Clasificación por keyword matching determinístico:
       - Si contiene "error", "fail", "exception", "bug", "crash" → "errors"
       - Si contiene "decidido", "decided", "elegimos", "optamos", "chose" → "decisions"
       - Si contiene "prefer", "config", "setting", "option" → "preferences"
       - Si contiene "task", "pending", "current", "session", "working on" → "context"
       - Default → "knowledge"
     * Sin LLM — puro pattern matching
     * Retorna la categoría como string

   - Método classify_with_confidence(content: str) -> tuple[str, float]:
     * Retorna (category, confidence) donde confidence = keywords_matched / total_keywords_checked
     * Si confidence < 0.3 → retorna ("uncategorized", confidence)

2. Clase ConstitutionalDecay:
   - __init__(store: GovernedMemoryStore, decay_lambda: float = 0.99, threshold: float = 0.1):
     * decay_lambda: factor de decaimiento por hora
     * threshold: debajo de este valor, memoria se archiva
     * protected_categories: ["decisions", "errors"] — NUNCA decaen

   - Método decay_cycle() -> dict:
     * Recorre TODAS las memorias activas
     * Para cada una:
       - Calcula horas desde última actualización
       - Aplica: relevance_score *= decay_lambda ^ hours
       - Si relevance_score < threshold Y categoría NO es protegida → marca como archived (valid_to=now)
       - Si categoría ES protegida → NO aplica decay, mantiene score
     * Loggea ciclo completo a logs/memory_decay.jsonl
     * Retorna: {processed: int, decayed: int, archived: int, protected: int}

   - Método reinforce(memory_id: str, boost: float = 0.1) -> float:
     * Cuando una memoria se consulta, refuerza: score = min(1.0, score + boost)
     * Memorias usadas frecuentemente sobreviven al decay
     * Retorna nuevo score

   - Método get_decay_status() -> list[dict]:
     * Retorna lista de memorias con su relevance_score actual
     * Ordenado por score ascendente (las que van a decaer primero)

3. Integrar MemoryClassifier en GovernedMemoryStore.add():
   - Si el usuario no provee category, usar MemoryClassifier.classify() automáticamente

4. Integrar ConstitutionalDecay con GovernedMemoryStore:
   - GovernedMemoryStore.query() llama reinforce() en cada memoria retornada

5. Tests en tests/test_memory_governance.py (agregar):
   - Test classify "error in provider" → "errors"
   - Test classify "we decided to use Z3" → "decisions"
   - Test classify "API key configuration" → "preferences"
   - Test classify "working on research task" → "context"
   - Test classify "the framework uses 5 metrics" → "knowledge"
   - Test classify_with_confidence baja confianza → "uncategorized"
   - Test decay reduce relevance_score con el tiempo
   - Test memorias protegidas (decisions, errors) NO decaen
   - Test reinforce incrementa score
   - Test archived cuando score < threshold
   - Test auto-classify cuando add() no recibe category
   - Test query refuerza memorias consultadas
   - Ejecuta TODOS los tests

NO hagas commit todavía.
```

**Expected output:** Classifier + Decay added, ~15 new tests, all passing.

---

## SESSION 12: Integration + Constitution Update + Commit

**What it creates:** Wires memory governance into the full system and commits everything.

**Paste this in Claude Code:**

```
Lee todo core/memory_governance.py (ya tiene GovernedMemoryStore, TemporalGraph, MemoryClassifier, ConstitutionalDecay).

Ahora integra el memory governance system con el resto del DOF:

1. Actualizar dof.constitution.yml — agregar sección de memoria:
   memory:
     categories:
       - knowledge
       - preferences
       - context
       - decisions
       - errors
     decay:
       lambda: 0.99
       threshold: 0.1
       protected_categories:
         - decisions
         - errors
     limits:
       max_memories: 10000
       max_content_length: 50000
     governance:
       enforce_on_add: true
       enforce_on_update: true
       log_queries: true

2. Actualizar GovernedMemoryStore.__init__() para cargar config de memoria desde dof.constitution.yml

3. Integrar con core/crew_runner.py:
   - Después de cada ejecución exitosa (ACCEPT), guardar resultado como memoria tipo "knowledge":
     memory_store.add(content=result_summary, category="knowledge", metadata={"task": task_name, "score": supervisor_score})
   - Después de cada fallo terminal, guardar como memoria tipo "errors":
     memory_store.add(content=error_summary, category="errors", metadata={"task": task_name, "error_class": error_class})
   - Esto es OPCIONAL (flag governed_memory=True/False en run_crew)

4. Integrar con core/adversarial.py:
   - Después de evaluación adversarial, guardar issues no resueltos como memoria tipo "errors"

5. Actualizar dof/__init__.py para exponer:
   from dof import GovernedMemoryStore, TemporalGraph, MemoryClassifier, ConstitutionalDecay

6. Agregar a main.py como opción 18: "Memory Governance Dashboard"
   - Muestra: stats del store, top memorias por relevance, distribución por categoría, memorias próximas a decaer

7. Tests de integración en tests/test_memory_governance.py (agregar):
   - Test que constitution.yml carga config de memoria correctamente
   - Test que crew_runner guarda memoria en éxito
   - Test que crew_runner guarda error en fallo
   - Test que el dashboard retorna datos válidos
   - Ejecuta TODOS los tests del proyecto completo

Después de que TODOS los tests pasen:
git add -A
git commit --author="Juan Carlos Quiceno Vasquez <jquiceva@gmail.com>" -m "feat: constitutional memory governance — governed store, temporal graph, classifier, decay engine

- core/memory_governance.py: first memory system with constitutional governance
- GovernedMemoryStore: add/update/delete with ConstitutionEnforcer validation
- TemporalGraph: bi-temporal versioning with snapshot/diff/timeline
- MemoryClassifier: deterministic category assignment (zero LLM)
- ConstitutionalDecay: relevance decay with protected categories (decisions, errors)
- dof.constitution.yml: memory governance configuration
- Integration with crew_runner.py and adversarial.py
- Full JSONL audit trail for all memory operations
- Zero external dependencies, zero LLM involvement"
git push origin main

Solo Juan Carlos Quiceno Vasquez como autor. NO co-authored-by.
```

**Expected output:** Full memory governance integrated, ~65 new tests total for memory system, commit + push.

---

## SESSION 13: OAGS Bridge

**What it creates:** Compatibility with Open Agent Governance Specification. BLAKE3 identity, sekuire.yml export, OAGS Level 2 conformance.

**Paste this in Claude Code:**

```
Primero instala: pip install blake3

Lee estos archivos:
- core/governance.py (ConstitutionEnforcer)
- core/memory_governance.py (GovernedMemoryStore)
- dof.constitution.yml (la constitución)
- core/observability.py (métricas)

Investiga el estándar OAGS (Open Agent Governance Specification) de Sekuire. El concepto clave es:
- Cada agente tiene una identidad determinística basada en hash de sus componentes
- Las políticas se expresan en formato sekuire.yml
- Hay niveles de conformance: Level 1 (declarativo), Level 2 (runtime enforcement), Level 3 (attestation)

Crea core/oags_bridge.py:

1. Clase OAGSIdentity:
   - Método compute_identity(model: str, constitution_hash: str, tools: list[str]) -> str:
     * Calcula BLAKE3 hash de: model + constitution_hash + sorted(tools)
     * Este es el identificador determinístico del agente según OAGS
     * El mismo agente con la misma configuración SIEMPRE produce el mismo identity hash

   - Método compute_constitution_hash(constitution_path: str) -> str:
     * Lee dof.constitution.yml
     * Calcula BLAKE3 hash del contenido
     * Si la constitución cambia, el identity cambia

   - Método get_agent_card() -> dict:
     * Retorna: {identity_hash, model, constitution_hash, tools, created_at, framework: "DOF", version: "0.1.0"}
     * Formato compatible con OAGS Agent Card

2. Clase OAGSPolicyBridge:
   - Método export_sekuire(constitution_path: str, output_path: str) -> str:
     * Lee dof.constitution.yml
     * Convierte a formato sekuire.yml:
       - HARD_RULES → OAGS "block" policies
       - SOFT_RULES → OAGS "warn" policies
       - AST_RULES → OAGS "code_analysis" policies
       - Métricas → OAGS "observability" section
     * Escribe el archivo sekuire.yml
     * Retorna el path

   - Método import_sekuire(sekuire_path: str) -> dict:
     * Lee un archivo sekuire.yml
     * Convierte reglas al formato de dof.constitution.yml
     * Retorna dict con las reglas convertidas (NO modifica constitution.yml automáticamente)

   - Método validate_conformance(level: int = 2) -> dict:
     * Level 1: Verifica que existe constitution.yml con reglas declaradas → check policies
     * Level 2: Verifica que ConstitutionEnforcer está activo en runtime → check enforcement
     * Level 2: Verifica que métricas se calculan en runtime → check observability
     * Level 3: Verifica que existe attestation mechanism (Oracle Bridge) → check si core/oracle_bridge.py existe
     * Retorna: {level_1: {passed: bool, checks: [...]}, level_2: {...}, level_3: {...}, max_level_passed: int}

3. Clase OAGSAuditBridge:
   - Método export_audit_events(logs_path: str = "logs/") -> list[dict]:
     * Lee los JSONL de DOF (execution_log, memory_governance, adversarial, etc.)
     * Convierte cada evento al formato de OAGS audit events:
       {event_id, agent_identity, timestamp, event_type, payload, governance_decision}
     * Retorna lista de eventos OAGS-compatible

   - Método generate_audit_report(events: list[dict]) -> dict:
     * Resume: total_events, by_type, governance_decisions, compliance_rate
     * Formato compatible con OAGS audit requirements

4. Integración:
   - Agregar a dof/__init__.py: from dof import OAGSIdentity, OAGSPolicyBridge, OAGSAuditBridge
   - Agregar a main.py como opción 19: "OAGS Compliance Check"
     * Muestra: agent identity hash, conformance level, policy count, audit summary

5. Persistencia:
   - Agent card guardado en memory/oags_identity.json
   - Audit events exportados a logs/oags_audit.jsonl

6. Tests en tests/test_oags_bridge.py:
   - Test compute_identity es determinístico (mismo input = mismo hash)
   - Test compute_identity cambia si modelo cambia
   - Test compute_identity cambia si constitución cambia
   - Test compute_constitution_hash es determinístico
   - Test export_sekuire genera YAML válido
   - Test import_sekuire lee formato sekuire
   - Test export → import roundtrip preserva reglas
   - Test validate_conformance Level 1 pasa (tenemos constitution.yml)
   - Test validate_conformance Level 2 pasa (tenemos ConstitutionEnforcer activo)
   - Test validate_conformance Level 3 falla (aún no tenemos Oracle Bridge)
   - Test export_audit_events genera formato OAGS válido
   - Test agent card tiene todos los campos requeridos
   - Ejecuta TODOS los tests

Después de que TODOS los tests pasen:
git add -A
git commit --author="Juan Carlos Quiceno Vasquez <jquiceva@gmail.com>" -m "feat: OAGS Bridge — BLAKE3 identity, sekuire.yml export/import, Level 2 conformance

- core/oags_bridge.py: Open Agent Governance Specification compatibility
- OAGSIdentity: deterministic BLAKE3 agent identity hash
- OAGSPolicyBridge: constitution.yml <-> sekuire.yml bidirectional conversion
- OAGSAuditBridge: JSONL traces to OAGS audit event format
- Conformance validation: Level 1 (declarative) + Level 2 (runtime enforcement)
- Zero LLM, fully deterministic identity and policy management"
git push origin main

Solo Juan Carlos Quiceno Vasquez como autor. NO co-authored-by.
```

**Expected output:** core/oags_bridge.py, ~20 tests, OAGS Level 2 conformance passing.

---

## SESSION 14: Oracle Bridge ERC-8004

**What it creates:** On-chain attestation of governance metrics via ERC-8004 Validation Registry on Avalanche C-Chain.

**Paste this in Claude Code:**

```
Lee estos archivos:
- core/oags_bridge.py (OAGS identity — compute_identity, agent card)
- core/observability.py (métricas SS, GCR, PFI, RP, SSR)
- core/z3_verifier.py (pruebas formales verificadas)
- core/memory_governance.py (GovernedMemoryStore)

Crea core/oracle_bridge.py — el puente entre DOF off-chain governance y ERC-8004 on-chain attestation en Avalanche.

NOTA: Este módulo NO requiere conexión a blockchain para funcionar en tests. Genera las attestation structures off-chain y las firma. La publicación on-chain real se hace cuando hay conexión a Avalanche.

1. Dataclass AttestationCertificate:
   - agent_identity: str (BLAKE3 hash from OAGS)
   - task_id: str
   - timestamp: datetime
   - metrics: dict (SS, GCR, PFI, RP, SSR values)
   - governance_status: str ("COMPLIANT" si GCR==1.0, "NON_COMPLIANT" si GCR<1.0)
   - z3_verified: bool (True si invariantes Z3 están verificados)
   - signature: str (Ed25519 signature of the certificate)
   - certificate_hash: str (BLAKE3 hash del certificado completo)

2. Clase Ed25519Signer:
   - __init__(): genera par de claves Ed25519 (o carga de keys/oracle_key.pem si existe)
   - Método sign(data: bytes) -> str: firma con clave privada, retorna hex
   - Método verify(data: bytes, signature: str) -> bool: verifica con clave pública
   - Método get_public_key() -> str: retorna clave pública como hex
   - Persistencia: guarda claves en keys/ directory (crear si no existe)
   - Usa la librería estándar de Python (cryptography o nacl — verificar cuál está disponible, si ninguna usar hashlib como fallback simple)

3. Clase OracleBridge:
   - __init__(signer: Ed25519Signer, oags: OAGSIdentity):
     * Inicializa con el signer y la identidad OAGS

   - Método create_attestation(task_id: str, metrics: dict, z3_results: dict = None) -> AttestationCertificate:
     * Toma las métricas de una ejecución
     * Determina governance_status: "COMPLIANT" si metrics["GCR"] == 1.0, else "NON_COMPLIANT"
     * Determina z3_verified: True si z3_results y todos los teoremas VERIFIED
     * Serializa todo a bytes
     * Firma con Ed25519Signer
     * Calcula certificate_hash con BLAKE3
     * Retorna AttestationCertificate

   - Método should_publish(cert: AttestationCertificate) -> bool:
     * Solo publica si governance_status == "COMPLIANT"
     * Si GCR < 1.0 → NO se publica on-chain (governance failure = no attestation)
     * Si SS < 0.5 → se publica con flag warning=True
     * Retorna bool

   - Método prepare_transaction(cert: AttestationCertificate) -> dict:
     * Genera la estructura de transacción ERC-8004 compatible:
       {
         "to": "0x... (Validation Registry address placeholder)",
         "data": {
           "agent_id": cert.agent_identity,
           "validation_signal": cert.governance_status,
           "metrics_hash": cert.certificate_hash,
           "timestamp": cert.timestamp.isoformat(),
           "signature": cert.signature
         },
         "chain": "avalanche-c-chain",
         "gas_estimate": None  # placeholder for real deployment
       }
     * NO envía la transacción — solo la prepara
     * El envío real se implementará cuando se conecte a Avalanche

   - Método batch_attestations(certs: list[AttestationCertificate]) -> dict:
     * Agrupa múltiples attestations en una sola transacción batch
     * Gas optimization: un solo tx para N attestations
     * Retorna: {batch_id, certificates: N, estimated_gas, transaction_data}

   - Método verify_attestation(cert: AttestationCertificate) -> bool:
     * Cualquier tercero puede verificar: recalcula hash, verifica firma
     * Retorna True si todo es consistente

4. Clase AttestationRegistry (off-chain local):
   - Guarda todas las attestations en logs/attestations.jsonl
   - Método get_attestation(certificate_hash: str) -> AttestationCertificate
   - Método get_agent_history(agent_identity: str) -> list[AttestationCertificate]
   - Método get_compliance_rate() -> float (attestations compliant / total)
   - Método export_for_chain() -> list[dict] (attestations pendientes de publicar on-chain)

5. Integración:
   - En core/crew_runner.py: después de ACCEPT, si oracle_mode=True:
     * Crear attestation con métricas del run
     * Si should_publish() → guardar en registry
     * Loggear a logs/oracle_bridge.jsonl
   - Agregar a dof/__init__.py: from dof import OracleBridge, AttestationCertificate
   - Agregar a main.py como opción 20: "ERC-8004 Attestation Dashboard"
     * Muestra: total attestations, compliance rate, pending for on-chain, last attestation details

6. Actualizar OAGS conformance:
   - En core/oags_bridge.py: validate_conformance Level 3 ahora pasa (Oracle Bridge existe)

7. Tests en tests/test_oracle_bridge.py:
   - Test create_attestation con métricas compliant → governance_status "COMPLIANT"
   - Test create_attestation con GCR < 1.0 → governance_status "NON_COMPLIANT"
   - Test should_publish con COMPLIANT → True
   - Test should_publish con NON_COMPLIANT → False
   - Test should_publish con SS < 0.5 pero COMPLIANT → True con warning
   - Test signature es verificable
   - Test verify_attestation con certificado válido → True
   - Test verify_attestation con certificado modificado → False
   - Test certificate_hash es determinístico
   - Test batch_attestations agrupa correctamente
   - Test AttestationRegistry persiste y recupera
   - Test get_agent_history retorna historial correcto
   - Test get_compliance_rate calcula correctamente
   - Test prepare_transaction genera estructura ERC-8004 válida
   - Test OAGS Level 3 conformance ahora pasa
   - Ejecuta TODOS los tests del proyecto completo

Después de que TODOS los tests pasen:
git add -A
git commit --author="Juan Carlos Quiceno Vasquez <jquiceva@gmail.com>" -m "feat: ERC-8004 Oracle Bridge — on-chain attestation of governance metrics

- core/oracle_bridge.py: bridge between DOF off-chain governance and ERC-8004 on-chain attestation
- AttestationCertificate: signed governance metrics with BLAKE3 hash
- Ed25519Signer: deterministic signature generation and verification
- OracleBridge: attestation creation, publishing rules, transaction preparation
- AttestationRegistry: off-chain local registry with JSONL persistence
- Batch attestation support for gas optimization
- OAGS Level 3 conformance now passing
- Only COMPLIANT (GCR=1.0) attestations published on-chain
- Zero blockchain dependency for testing — transaction preparation only"
git push origin main

Solo Juan Carlos Quiceno Vasquez como autor. NO co-authored-by.
```

**Expected output:** core/oracle_bridge.py, ~20 tests, OAGS Level 3 passing.

---

## SESSION 15: Full Integration + README + Paper

**What it creates:** Final wiring, updated README and paper, clean commit.

**Paste this in Claude Code:**

```
Ejecuta todos los tests del proyecto completo:
python -m unittest discover tests/ -v

Muéstrame el conteo total de tests.

Luego actualiza README.md (mantén tono académico formal, mantén Cyber Paisa / Enigma Group como autor):

1. Actualiza header stats con nuevo conteo de tests y módulos

2. Agrega a Key Contributions:
   - Constitutional Memory Governance — first memory system with formal governance. GovernedMemoryStore validates every add/update/delete against ConstitutionEnforcer. TemporalGraph provides bi-temporal versioning with point-in-time snapshots. ConstitutionalDecay applies configurable relevance decay with protected categories (decisions and errors never decay). Zero external dependencies, zero LLM involvement.
   - OAGS Bridge — compatibility with the Open Agent Governance Specification. Deterministic BLAKE3 agent identity hash, bidirectional policy conversion between dof.constitution.yml and sekuire.yml format, OAGS audit event export, and conformance validation up to Level 3.
   - ERC-8004 Oracle Bridge — on-chain attestation of governance metrics via Avalanche C-Chain. Ed25519-signed attestation certificates, BLAKE3 certificate hashing, compliance-gated publishing (only GCR=1.0 attestations published), batch transaction support for gas optimization. Connects DOF off-chain governance with ERC-8004 Validation Registry.

3. Agrega nuevas secciones formales para Memory Governance, OAGS Bridge, y Oracle Bridge (mismo estilo que las secciones de Z3 y Adversarial)

4. Actualiza Project Structure con nuevos archivos

5. Actualiza Citation

Luego actualiza paper/PAPER_OBSERVABILITY_LAB.md:
1. Agrega sección "Constitutional Memory Governance" con descripción formal
2. Agrega sección "OAGS Conformance" con tabla de niveles
3. Agrega sección "On-Chain Attestation via ERC-8004" con descripción del mecanismo
4. Actualiza conteos

Después:
git add -A
git commit --author="Juan Carlos Quiceno Vasquez <jquiceva@gmail.com>" -m "docs: update README and paper with Memory Governance, OAGS Bridge, Oracle Bridge — Phase 2 complete"
git push origin main

Solo Juan Carlos Quiceno Vasquez como autor. NO co-authored-by.
```

**Expected output:** README + Paper updated, all tests passing, pushed.

---

## EXECUTION CHECKLIST

| # | Session | Status | Tests | Commit |
|---|---------|--------|-------|--------|
| 9  | GovernedMemoryStore | ⬜ | ~25 | (no commit yet) |
| 10 | TemporalGraph | ⬜ | ~15 | (no commit yet) |
| 11 | Classifier + Decay | ⬜ | ~15 | (no commit yet) |
| 12 | Integration + Commit | ⬜ | ~10 | ✅ commit + push |
| 13 | OAGS Bridge | ⬜ | ~20 | ✅ commit + push |
| 14 | Oracle Bridge ERC-8004 | ⬜ | ~20 | ✅ commit + push |
| 15 | README + Paper | ⬜ | validation | ✅ commit + push |

**Total new: ~105 tests | 3 commits | 3 new systems**
**Grand total after Phase 2: ~254 tests | 25+ modules | CI green**

---

## RULES

1. **One prompt per session.** Don't combine sessions.
2. **Sessions 9-11 NO commit.** They build incrementally in the same file. Session 12 commits all memory governance together as one clean commit.
3. **Session 13 commits independently.** OAGS Bridge is its own module.
4. **Session 14 commits independently.** Oracle Bridge is its own module.
5. **All commits:** `--author="Juan Carlos Quiceno Vasquez <jquiceva@gmail.com>"` — NO co-authored-by, NEVER.
6. **If tests fail:** Fix before moving to next session. Every session depends on the previous one passing.
7. **If Claude Code asks for permission:** Select option 2 "Yes, allow all edits this session."
8. **If Claude Code session expires:** Re-authenticate, cd to project, paste the current session prompt again.
