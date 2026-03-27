# Evaluacion de Repositorios Externos para DOF-MESH (Ronda 2)

> Fecha: 2026-03-26
> Evaluador: Cyber Paisa (Enigma Group)
> Contexto: DOF-MESH v0.5.0 — 127 modulos core, 674 funciones sin docstring (35%), governance.py importado por 41 archivos, to_dict() duplicado en 24 archivos, AST verifier ya integrado.

---

## Tabla de Evaluacion

| Repo | Que hace | Valor para DOF | Veredicto |
|------|----------|----------------|-----------|
| **ChristopherKahler/paul** | Framework de orquestacion de desarrollo AI (Plan-Apply-Unify Loop). Slash commands para Claude Code. Gestion de estado, acceptance criteria, coherence checks. 26 comandos. | BAJO. DOF ya tiene su propio ciclo de governance (Constitution -> AST -> Z3 -> Supervisor), autonomous_daemon con 4 fases (Perceive-Decide-Execute-Evaluate), y crew_runner con retry. PAUL resuelve "context rot" en sesiones de Claude Code — un problema de workflow del desarrollador, no de runtime del mesh. No aporta nada al pipeline de verificacion deterministica ni a la orquestacion de nodos. | **SKIP** |
| **samwillis/solidtype** | CAD parametrico colaborativo para web. OpenCascade.js, Electric SQL, Yjs CRDTs, modelado 3D, AI-assisted modeling. Demo de tecnologias de sync (Durable Streams, TanStack DB). | NULO. Es una app de CAD 3D. Cero overlap con governance de agentes, mesh networking, o verificacion formal. Sin utilidad para DOF en ningun nivel. | **SKIP** |
| **quantium-ai/research** | Jupyter notebooks con estrategias de trading cuantitativo. Analisis tecnico, ML para prediccion de precios. Educational, no production. | NULO. Trading notebooks educativos. No hay libreria, no hay API, no hay componente reutilizable. Cero relevancia para DOF-MESH. | **SKIP** |
| **Muse Code Docs (concepto)** | Documentacion symbol-aware: call graph, cobertura via BFS, version inference por historial de simbolos, deteccion de docstrings stale, health score por funcion, doc debt ponderado por call count. Output json/html/md. CI gate con --ci. | **ALTO**. Ataca directamente las 674 funciones sin docstring. El call graph priorizaria documentar `governance.py` (41 importadores) antes que `qaion_minimalist.py` (0 importadores). El doc debt score ponderado por call count es exactamente la metrica que falta para sistematizar la deuda de documentacion. | **BUILD** |

---

## Analisis Detallado: Muse Code Docs como Feature de DOF

### Por que tiene sentido construirlo DENTRO de DOF

DOF ya tiene el 60% de la infraestructura necesaria:

| Componente Muse | Ya existe en DOF | Que falta |
|-----------------|------------------|-----------|
| AST parsing de Python | `core/ast_verifier.py` — parsea AST, detecta patterns | Extender para extraer signatures, docstrings, call relations |
| Grafo de imports | `CODE_ANALYSIS_MUSE.md` — ya calculo blast radius (41 archivos importan governance) | Formalizar en estructura de datos persistente |
| Deteccion de funciones sin docstring | Ya contamos 674/1902 | Automatizar deteccion de docstrings stale (signature cambio pero docstring no) |
| Risk scoring | Formula `risk = churn x imports x LoC` ya implementada | Agregar doc_debt_score = (1 - has_docstring) x call_count |
| JSONL logging | Todo DOF loguea a JSONL | Solo agregar output de doc health |
| CI gate | `.github/workflows/ci.yml` ya corre Z3 + tests | Agregar step `dof doc-health --ci --threshold 0.7` |

### Arquitectura propuesta: `core/doc_analyzer.py`

```
core/doc_analyzer.py
  ├── SymbolExtractor(ast.NodeVisitor)
  │     - Extrae funciones, clases, metodos con signatures
  │     - Detecta presencia/ausencia de docstring
  │     - Compara signature actual vs ultimo commit (stale detection)
  │
  ├── CallGraphBuilder(ast.NodeVisitor)
  │     - Construye grafo de llamadas funcion-a-funcion
  │     - BFS para calcular "alcance" de cada funcion
  │     - Complementa el import graph que ya tenemos
  │
  ├── DocHealthScorer
  │     - health_score(fn) = has_docstring x freshness x coverage_by_tests
  │     - doc_debt(fn) = (1 - health_score) x call_count
  │     - Prioriza: alto call_count + sin docstring = deuda maxima
  │
  └── DocReport
        - Output: json (para CI), html (para dashboard), md (para docs/)
        - --ci mode: exit(1) si score < threshold
        - Integra con dof CLI: `dof doc-health`
```

### Estimacion de esfuerzo

- **SymbolExtractor + docstring detection:** 2-3 horas (AST visitor simple, DOF ya tiene el patron en ast_verifier)
- **CallGraphBuilder:** 3-4 horas (ast.NodeVisitor para Name/Call nodes + BFS)
- **Stale detection via git blame:** 2 horas (comparar hash de signature line vs docstring line)
- **DocHealthScorer + ponderacion:** 1 hora (matematica pura)
- **Output formatters (json/html/md):** 2 horas
- **CI gate + dof CLI integration:** 1 hora
- **Tests:** 2 horas

**Total: ~14 horas de trabajo**

### Impacto inmediato

Con el call graph construido, podriamos generar automaticamente:
1. **Prioridad de documentacion**: Las 674 funciones ordenadas por doc_debt (call_count x riesgo)
2. **Deteccion de to_dict() duplicado**: El call graph revela que 24 implementaciones separadas deberian ser un mixin
3. **Stale docstrings**: Funciones cuya signature cambio en commits recientes pero el docstring no se actualizo
4. **CI gate**: Bloquear PRs que bajen el doc health score por debajo de un threshold

### Veredicto final

**BUILD IT.** No como dependencia externa — como `core/doc_analyzer.py` dentro de DOF. Reutiliza `ast_verifier.py` como base, extiende el AST visitor, y expone via `dof doc-health`. Es consistente con la filosofia DOF de "zero external deps para governance" y ataca un problema real medido (674 funciones, 35% sin docs).

---

*Evaluacion basada en READMEs oficiales y estado actual del codebase DOF-MESH.*
