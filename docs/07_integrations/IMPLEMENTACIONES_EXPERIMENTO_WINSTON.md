# Implementaciones extraídas del Experimento Winston v4-Web
## DOF Mesh Legion — Cyber Paisa / Enigma Group
> **Fuente:** Experimento Winston vs Baseline — 10 modelos frontier, 3 niveles, BLUE + RED
> **Fecha:** 28 mar 2026 | **Archivo resultados:** `experiments/winston_vs_baseline/web_experiment_results.json`

---

## Resumen de resultados (BLUE vs RED — datos parciales, RED INTERMEDIATE completado)

| Modelo | BLUE avg | RED avg | Delta | Nota |
|--------|----------|---------|-------|------|
| GLM-4.5 | 90.0 | 42.0 | +48.0 | |
| Claude Sonnet 4.6 | 90.0 | 62.0 | +28.0 | |
| ChatGPT-4o | 88.7 | 86.0 | +2.7 | ⚠️ GPT adopta Winston espontáneamente |
| DeepSeek-V3 | 88.7 | 34.7 | +54.0 | |
| Gemini-2.5Pro | 84.7 | 60.0 | +24.7 | |
| Grok-3 | 84.7 | 0.0 | — | Sin tokens en RED |
| Perplexity-Sonar | 82.0 | 83.0 | -1.0 | ⚠️ Perplexity supera BLUE en RED |
| Mistral-Large | 78.7 | 40.0 | +38.7 | |
| MiniMax-M2 | 76.0 | 78.0 | -2.0 | ⚠️ MiMo ya usa formato estructurado sin instrucción |
| Kimi-K2 | 64.0 | 65.0 | -1.0 | ⚠️ Kimi ignora el formato Winston |

**Hallazgo principal:** 8 de 10 modelos frontier adoptan Winston perfectamente con solo el system prompt + ejemplo.

**Hallazgo RED (nuevo):** ChatGPT-4o, Perplexity, MiniMax/MiMo y Kimi usan formato estructurado + evidencia incluso sin instrucción Winston. Estos modelos han **internalizado el patrón** — el delta real de Winston para ellos es mínimo. El mayor valor de Winston está en modelos como GLM, DeepSeek, Mistral (+38-54 pts).

---

## IDEAS IMPLEMENTABLES — Clasificadas por impacto

### 🔴 PRIORIDAD 1 — Implementar en próximo sprint

---

#### 1. ConstitutionIntegrityWatcher
**Origen:** Claude Sonnet 4.6 (INTERMEDIATE)
**Qué hace:** Recalcula SHA-256 del árbol de reglas Constitution cada N ciclos y compara contra hash atestiguado on-chain. Detecta drift de estado en <30s.

```python
# constitution/integrity_watcher.py
import hashlib
from dof_sdk.attestation import fetch_onchain_hash

class ConstitutionIntegrityWatcher:
    def __init__(self, constitution_tree, interval_seconds=30):
        self.tree = constitution_tree
        self.interval = interval_seconds
        self.baseline = fetch_onchain_hash(attestation_id="constitution-root")

    def compute_current_hash(self) -> str:
        raw = str(self.tree.serialize()).encode()
        return hashlib.sha256(raw).hexdigest()

    def verify(self) -> bool:
        current = self.compute_current_hash()
        if current != self.baseline:
            raise ConstitutionDriftException(
                f"Drift detectado: expected={self.baseline[:12]}… got={current[:12]}…"
            )
        return True
```

**Métricas de éxito:** Detección drift <30s, mutation score ≥98%, 0 attestations invalidadas por drift/30 días.

---

#### 2. AdaptiveCircuitBreaker en Supervisor
**Origen:** Claude Sonnet 4.6 (INTERMEDIATE)
**Qué hace:** Trackea tasa de acciones bloqueadas por agente en ventanas de 60s. Al 15% block rate activa modo degradado antes del fallo total.

```python
# supervisor/adaptive_circuit_breaker.py
from collections import deque
from datetime import datetime, timedelta

class AdaptiveCircuitBreaker:
    def __init__(self, agent_id: str, threshold_rate=0.15, window_seconds=60):
        self.agent_id = agent_id
        self.threshold = threshold_rate
        self.window = timedelta(seconds=window_seconds)
        self.events = deque()

    def record(self, blocked: bool):
        now = datetime.utcnow()
        self.events.append((now, blocked))
        self._purge_old(now)

    def _purge_old(self, now):
        while self.events and (now - self.events[0][0]) > self.window:
            self.events.popleft()

    def state(self) -> str:
        if not self.events:
            return "CLOSED"
        blocked_rate = sum(1 for _, b in self.events if b) / len(self.events)
        if blocked_rate >= self.threshold:
            return "OPEN"
        elif blocked_rate >= self.threshold * 0.6:
            return "HALF_OPEN"
        return "CLOSED"
```

**Métricas de éxito:** MTTR <90s, falsos positivos <2% sobre 3720 tests, cobertura Supervisor ≥95% branch.

---

#### 3. Mutation Testing en Adversarial Layer
**Origen:** Perplexity-Sonar (INTERMEDIATE)
**Qué hace:** Agrega mutation testing con `mutmut` sobre el módulo adversarial como gate en CI/CD. Detecta código que cambia comportamiento sin romper tests sintácticos.

```bash
# Agregar a CI pipeline
mutmut run --paths-to-mutate core/adversarial.py
mutmut results  # target: mutation_score >= 0.85
```

**Métricas de éxito:** mutation_score ≥85% como gate CI (pipeline falla si no alcanza), 50 adversarial prompt fixtures clasificados por vector (injection, jailbreak, boundary overflow).

---

#### 4. Z3 Unknown Rate Monitor
**Origen:** Perplexity-Sonar (INTERMEDIATE)
**Qué hace:** Detecta cuando Z3 retorna `unknown` bajo presión de tiempo y fuerza `FAIL` + alerta en vez de degradación silenciosa.

```python
# core/z3_verifier.py — agregar al resultado de check()
def _handle_z3_result(self, result) -> str:
    if result == z3.sat:
        return "PASS"
    elif result == z3.unsat:
        return "FAIL"
    else:  # z3.unknown — NUNCA tratar como PASS implícito
        self._increment_unknown_counter()
        logger.warning("Z3 returned unknown — forcing FAIL + alert")
        if self._unknown_rate_5min() > 0.01:  # >1% en 5min
            self._trigger_degraded_mode()
        return "FAIL"
```

**Métricas de éxito:** `z3_unknown_rate < 0.5%` en producción, 120 casos de regresión cubriendo sat/unsat/unknown/timeout.

---

### 🟡 PRIORIDAD 2 — Para escalado a 50 nodos

---

#### 5. Z3 Proof Caching (Memoization SMT)
**Origen:** DeepSeek-V3 + Grok-3 + ChatGPT-4o (coincidencia 3 modelos)
**Qué hace:** Cachea queries SMT frecuentes por hash de constraints → resultado. Reduce latencia 40-70%.

```python
# core/z3_gate.py — agregar cache
import functools

class Z3Gate:
    def __init__(self):
        self._cache: dict[str, str] = {}

    def _constraint_hash(self, constraints: list) -> str:
        import hashlib
        return hashlib.sha256(str(constraints).encode()).hexdigest()

    def verify_cached(self, constraints: list) -> str:
        key = self._constraint_hash(constraints)
        if key in self._cache:
            return self._cache[key]
        result = self._verify_z3(constraints)
        self._cache[key] = result
        return result
```

**Métricas de éxito:** Cache hit rate ≥60% en CI, latencia promedio ↓40-70%, timeouts Z3 <2%.

---

#### 6. ByzantineNodeGuard — Reputación por nodo
**Origen:** Claude Sonnet 4.6 (ADVANCED)
**Qué hace:** Asigna score de reputación 0.0-1.0 a cada nodo. Penaliza timeouts Z3, cuarentena automática bajo 0.3. Restaurable en <50 transacciones.

```python
# core/node_mesh.py — agregar a NodeMesh
from collections import defaultdict

class ByzantineNodeGuard:
    def __init__(self, max_z3_budget_ms=50):
        self.node_reputation = defaultdict(lambda: 1.0)
        self.max_budget = max_z3_budget_ms

    def validate_constraint(self, node_id: str, constraint) -> bool:
        if self.node_reputation[node_id] < 0.3:
            return False  # En cuarentena
        # ... ejecutar con timeout
        # actualizar reputación según resultado

    def _update_reputation(self, node_id, success, penalty=0.05):
        if success:
            self.node_reputation[node_id] = min(1.0, self.node_reputation[node_id] + 0.01)
        else:
            self.node_reputation[node_id] -= penalty
```

**Métricas de éxito:** 0 nodos con CPU >90% sostenido >10s, reputación restaurable <50 transacciones.

---

#### 7. ConstitutionUpdateCoordinator — Two-phase commit
**Origen:** Claude Sonnet 4.6 (ADVANCED)
**Qué hace:** Two-phase commit para actualizaciones de Constitution con quorum 67%. Evita inconsistencias entre nodos durante actualizaciones.

```python
# constitution/distributed_lock.py
class ConstitutionUpdateCoordinator:
    def propose_update(self, new_constitution: bytes, quorum: float = 0.67):
        version_hash = hashlib.sha256(new_constitution).hexdigest()
        votes = self.broadcast_prepare(version_hash)
        if sum(votes) / len(votes) < quorum:
            raise InsufficientQuorumError()
        self.broadcast_commit(new_constitution, timeout=5.0)
        self.attest_onchain(version_hash)  # 1 attestation por update
```

**Métricas de éxito:** Ventana inconsistencia <100ms, 0 attestations contradictorias en producción.

---

#### 8. Attestation Batching on-chain (Merkle)
**Origen:** Perplexity-Sonar + MiMo + Gemini (coincidencia 3 modelos)
**Qué hace:** En vez de N attestations individuales, emitir Merkle-aggregated attestation batches en Avalanche C-Chain. Reduce gas cost ~70%.

**Diseño:**
```
N governance decisions → Merkle tree → 1 root attestation en C-Chain
Challenge window: 60s (optimistic attestation)
Si nadie disputa → finalizado
```

**Métricas de éxito:** `attestation_cost_per_verification` reducido ≥65%, costo <$0.01 por decisión.

---

#### 9. Z3 Portfolio Solving (instancias paralelas)
**Origen:** Perplexity-Sonar (ADVANCED)
**Qué hace:** Lanzar múltiples instancias Z3 con estrategias distintas en paralelo, tomar el primer resultado válido. Reduce latencia ~40%.

```python
# core/z3_verifier.py
import concurrent.futures

def portfolio_solve(constraints: list, timeout_ms=200) -> str:
    strategies = [
        lambda c: z3.Solver().check(*c),        # estrategia default
        lambda c: z3.Optimize().check(*c),       # con optimización
        lambda c: z3.SolverFor("QF_LIA").check(*c),  # aritmética lineal
    ]
    with concurrent.futures.ThreadPoolExecutor() as ex:
        futures = {ex.submit(s, constraints): s for s in strategies}
        for f in concurrent.futures.as_completed(futures, timeout=timeout_ms/1000):
            result = f.result()
            if result != z3.unknown:
                return str(result)
    return "unknown"
```

**Métricas de éxito:** `z3_unknown_rate <0.5%`, latencia ↓40% en queries complejas.

---

### 🟢 PRIORIDAD 3 — Roadmap futuro (escalado 50 nodos)

---

#### 10. Node Capability Manifest (NCM)
**Origen:** Perplexity-Sonar (ADVANCED)
**Qué hace:** Cada nodo declara `{memory_gb, z3_timeout_ms, chain_support[], agent_type}` al unirse. El Supervisor asigna constraints según NCM.

#### 11. Constraint Complexity Budget (CCB)
**Origen:** Perplexity-Sonar (ADVANCED)
**Qué hace:** Cada nodo tiene presupuesto máximo de complejidad por verificación (`max_vars=256`). Si un constraint excede CCB, el Supervisor lo divide automáticamente.

#### 12. Tiered Z3 por hardware
**Origen:** MiniMax-M2 (ADVANCED)
**Qué hace:** GPU <50ms primary, x86 <150ms secondary, ARM <300ms batch mode. Asignación dinámica por perfil.

#### 13. BLS Aggregate Signatures
**Origen:** Gemini-2.5Pro (ADVANCED)
**Qué hace:** Comprimir 50 attestations de nodos en 1 sola firma on-chain. Reduce gas cost ~90%.

---

## IDEAS ADICIONALES — Extraídas de RED ADVANCED (10 modelos)

Las siguientes propuestas emergieron de las respuestas RED ADVANCED. Son ideas convergentes — cuando 3+ modelos proponen lo mismo independientemente, la probabilidad de que sea correcto es alta.

### Convergencia universal (7-10 modelos coinciden)

| Idea | Modelos que la proponen | Implementabilidad |
|------|------------------------|-------------------|
| Batch attestation Merkle (N decisiones → 1 root on-chain) | Claude, Kimi, Gemini, GPT, Perplexity, DeepSeek, Mistral | 🟡 Sprint 2 |
| Nodos heterogéneos con 3 roles: Z3-Heavy / Z3-Lite / Oracle-Memory | Todos | 🟢 Diseño listo |
| Escalado en 3 fases con métricas por fase antes de avanzar | Todos | 🟢 Roadmap |
| Riesgo #1 universal: divergencia contexto Z3 entre nodos | Todos | 🔴 Prioridad 1 |

### Ideas específicas implementables

**Context Epoch System** (Claude ADVANCED)
Cada update de Constitution incrementa `context_epoch`. Toda verificación Z3 incluye el epoch. Nodo con epoch inferior rechaza queries hasta re-sincronizar. Convierte divergencia silenciosa en error detectable.

**Golden Node árbitro** (Claude ADVANCED)
1 nodo Z3 read-only que nunca procesa queries en producción. Solo referencia canónica. En conflicto entre nodos → Golden emite veredicto final + registra incidente on-chain.

**Tiered Z3 Validation** (ChatGPT-4o ADVANCED)
Tier 1 (10-15 nodos): Z3 completo. Tier 2 (20-25 nodos): Z3 parcial/heurístico. Tier 3 (10-15 nodos): verificación diferida para auditoría. Reduce carga Z3 global ~40-60%.

**Constitution Hash Beacon** (Perplexity ADVANCED)
Publicar hash del estado Constitution cada epoch (50 bloques Avalanche) en C-Chain. Nodo con state hash divergente → modo HALT automático hasta resincronización.

**Adaptive Timeout en Consensus** (MiniMax ADVANCED)
`timeout = max(measured_rtt × 3, 500ms)` + hysteresis delay 100ms post-quorum para catch-up de nodos rezagados.

**Sybil Defense — Staking + Rotación** (Kimi + DeepSeek ADVANCED)
Staking mínimo por nodo Edge + rotación de qué nodos adversariales evalúan cada agente cada 12h. Elimina fijación de ataque coordinado.

**Z3 Resource Budgeting** (Perplexity ADVANCED)
Cada query Z3 tiene presupuesto: 500ms hard timeout + máx 10,000 cláusulas. Si excede → `CONSTRAINT_BUDGET_EXCEEDED`, escala a Oracle Layer heurística. Separa Adversarial Layer en sandbox con rate limiting.

### Hallazgos del experimento (no implementables, pero valiosos)

| Hallazgo | Implicación |
|---------|-------------|
| MiMo rechazó responder en RED ADVANCED por no verificar que DOF existiera | Epistemología adversarial activa — único modelo con ese comportamiento |
| DeepSeek fabricó métricas (22,891 LOC, 47 fallos CI) en RED INTERMEDIATE | Hallucination con precisión quirúrgica — documentar como anti-patrón |
| 4 modelos (ChatGPT, Gemini, Perplexity, MiniMax) tienen Winston internalizado | Para ellos, el framework refina en lugar de transformar |
| 10 modelos convergieron en la misma arquitectura de 3 fases independientemente | Alta confianza en el diseño de escalado propuesto |

---

## IMPLEMENTACIÓN SUGERIDA — Orden

```
✅ Sprint completado (28 mar 2026 — commit 0d96f94 + 140f0e9):
  1. Z3 Unknown Rate Monitor — DONE (core/z3_verifier.py)
  2. Z3 Proof Caching — DONE (core/z3_gate.py)
  3. AdaptiveCircuitBreaker — DONE (core/adaptive_circuit_breaker.py)
  Tests: +39 tests (test_z3_verifier.py + test_z3_gate_cache.py + test_adaptive_circuit_breaker.py)

Próximo sprint:
  4. ConstitutionIntegrityWatcher (3h — nuevo módulo constitution/)
  5. Mutation testing en CI (1h — agregar mutmut a GitHub Actions)
  6. ByzantineNodeGuard (3h — integrar en node_mesh.py)
  7. Context Epoch System + Golden Node (2h — extensión z3_verifier.py)

Para escalado a 50 nodos:
  8. ConstitutionUpdateCoordinator (two-phase commit, quorum 67%)
  9. Z3 Portfolio Solving (instancias paralelas)
  10. Attestation Batching Merkle (-70% gas)
  11. Node Capability Manifest (NCM)
  12. Tiered Z3 Validation (Tier 1/2/3 por nodo)
  13. Constitution Hash Beacon (on-chain cada 50 bloques)
```

---

## PATRONES RECHAZADOS

Propuestas que suenan bien pero tienen problemas:

| Propuesta | Origen | Por qué NO implementar |
|-----------|--------|------------------------|
| Métricas internas fabricadas (14,231 LOC Supervisor) | DeepSeek-V3 | Hallucination — no verificadas en el código real |
| Integrar LibraBFT/HotStuff | Mistral-Large | Dependencia externa pesada, complejidad alta |
| SOC2 compliance | GLM-4.5 | Fuera de scope para fase actual |
| 3 regiones geo simultáneas | GLM-4.5 | Premature optimization |

---

*Generado: 28 mar 2026 | DOF Mesh Legion v0.5.0*
*Fuente: experiments/winston_vs_baseline/web_experiment_results.json*
