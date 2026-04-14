from __future__ import annotations
"""
Self-Improvement Engine — Inspirado en MiniMax M2.7.

DOF se auto-audita, extrae lecciones de sus propias ejecuciones,
y genera mejoras automáticamente. Analiza logs de governance,
mesh orchestrator, y resultados de tests para producir
lecciones aprendidas accionables.

Storage: logs/improvement/cycles.jsonl + logs/improvement/lessons.jsonl
"""

import json
import os
import re
import uuid
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("core.self_improvement")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMPROVEMENT_DIR = os.path.join(BASE_DIR, "logs", "improvement")
CYCLES_FILE = os.path.join(IMPROVEMENT_DIR, "cycles.jsonl")
LESSONS_FILE = os.path.join(IMPROVEMENT_DIR, "lessons.jsonl")

# Default log paths
DEFAULT_GOVERNANCE_LOG = os.path.join(BASE_DIR, "logs", "proofs", "governance_proofs.jsonl")
DEFAULT_MESH_LOG = os.path.join(BASE_DIR, "logs", "mesh", "orchestrator.jsonl")


# ── Dataclasses ──

@dataclass
class GovernanceAnalysis:
    """Resultado del análisis de governance proofs."""
    total_decisions: int = 0
    pass_count: int = 0
    fail_count: int = 0
    pass_rate: float = 0.0
    fail_rate: float = 0.0
    top_failing_rules: list = field(default_factory=list)  # [(rule, count)]
    trend: str = "unknown"  # "improving", "worsening", "stable", "unknown"
    first_half_fail_rate: float = 0.0
    second_half_fail_rate: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MeshAnalysis:
    """Resultado del análisis de mesh orchestrator."""
    total_events: int = 0
    avg_latency_by_node: dict = field(default_factory=dict)  # {node: avg_ms}
    success_rate_by_node: dict = field(default_factory=dict)  # {node: rate}
    circuit_breaker_open_nodes: list = field(default_factory=list)
    most_efficient_node: str = ""
    overall_avg_latency: float = 0.0
    overall_success_rate: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TestAnalysis:
    """Resultado del análisis de output de unittest."""
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    failing_files: list = field(default_factory=list)  # [(file, count)]
    trend: str = "unknown"  # "improving", "worsening", "stable", "unknown"
    previous_passed: int = -1
    previous_failed: int = -1

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Lesson:
    """Una lección aprendida extraída del análisis."""
    id: str = ""
    category: str = ""  # governance, mesh, testing, performance
    finding: str = ""
    recommendation: str = ""
    severity: str = "low"  # high, medium, low
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DriftAnalysis:
    """Performance Drift Ratio (PDR) — del issue #1 (nanookclaw).

    PDR = 1 - (observed / baseline)
    PDR = 0: sin drift. PDR > 0: degradación. PDR < 0: mejora.
    Detecta degradación ANTES de que se viole un invariante Z3.
    """
    pdr: float = 0.0
    baseline: float = 0.0
    observed: float = 0.0
    trend: str = "stable"  # "degrading", "improving", "stable", "oscillating"
    window_size: int = 0
    near_misses: int = 0  # scores cercanos al threshold sin cruzarlo
    threshold: float = 0.8

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ImprovementCycle:
    """Resultado de un ciclo completo de auto-mejora."""
    cycle_id: str = ""
    timestamp: str = ""
    governance: Optional[dict] = None
    mesh: Optional[dict] = None
    tests: Optional[dict] = None
    drift: Optional[dict] = None
    lessons: list = field(default_factory=list)
    recommendations_count: int = 0

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# ── Motor de Auto-Mejora ──

class SelfImprover:
    """Motor de auto-mejora inspirado en MiniMax M2.7.

    Analiza logs de governance, mesh y tests para extraer
    lecciones aprendidas y generar recomendaciones.
    """

    def __init__(self, improvement_dir: str = IMPROVEMENT_DIR):
        self.improvement_dir = improvement_dir
        self.cycles_file = os.path.join(improvement_dir, "cycles.jsonl")
        self.lessons_file = os.path.join(improvement_dir, "lessons.jsonl")
        self._lesson_counter = 0

    def _next_lesson_id(self) -> str:
        """Genera un ID incremental para lecciones."""
        self._lesson_counter += 1
        return f"L-{self._lesson_counter:03d}"

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── a) Governance Analysis ──

    def analyze_governance_logs(self, log_path: str = DEFAULT_GOVERNANCE_LOG) -> GovernanceAnalysis:
        """Lee governance proofs y calcula métricas.

        Args:
            log_path: Ruta al archivo governance_proofs.jsonl

        Returns:
            GovernanceAnalysis con estadísticas de governance.
        """
        analysis = GovernanceAnalysis()

        if not os.path.exists(log_path):
            return analysis

        entries = []
        with open(log_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        if not entries:
            return analysis

        analysis.total_decisions = len(entries)

        # Contar PASS y FAIL
        rule_fail_counts: dict[str, int] = {}
        for entry in entries:
            verdict = entry.get("verdict", entry.get("status", "")).upper()
            if verdict in ("PASS", "PASSED", "OK", "APPROVED"):
                analysis.pass_count += 1
            elif verdict in ("FAIL", "FAILED", "BLOCKED", "REJECTED"):
                analysis.fail_count += 1
                # Extraer regla que falló
                rule = entry.get("rule", entry.get("rule_id", entry.get("check", "unknown")))
                rule_fail_counts[rule] = rule_fail_counts.get(rule, 0) + 1

        total = analysis.total_decisions
        analysis.pass_rate = round(analysis.pass_count / total * 100, 2) if total > 0 else 0.0
        analysis.fail_rate = round(analysis.fail_count / total * 100, 2) if total > 0 else 0.0

        # Top 5 reglas que más fallan
        sorted_rules = sorted(rule_fail_counts.items(), key=lambda x: x[1], reverse=True)
        analysis.top_failing_rules = sorted_rules[:5]

        # Trend: primera mitad vs segunda mitad
        mid = len(entries) // 2
        if mid > 0:
            first_half = entries[:mid]
            second_half = entries[mid:]

            first_fails = sum(
                1 for e in first_half
                if e.get("verdict", e.get("status", "")).upper()
                in ("FAIL", "FAILED", "BLOCKED", "REJECTED")
            )
            second_fails = sum(
                1 for e in second_half
                if e.get("verdict", e.get("status", "")).upper()
                in ("FAIL", "FAILED", "BLOCKED", "REJECTED")
            )

            first_rate = first_fails / len(first_half) * 100 if first_half else 0
            second_rate = second_fails / len(second_half) * 100 if second_half else 0

            analysis.first_half_fail_rate = round(first_rate, 2)
            analysis.second_half_fail_rate = round(second_rate, 2)

            if second_rate < first_rate - 2:
                analysis.trend = "improving"
            elif second_rate > first_rate + 2:
                analysis.trend = "worsening"
            else:
                analysis.trend = "stable"
        else:
            analysis.trend = "unknown"

        return analysis

    # ── b) Mesh Performance Analysis ──

    def analyze_mesh_performance(self, log_path: str = DEFAULT_MESH_LOG) -> MeshAnalysis:
        """Lee orchestrator.jsonl y calcula métricas de mesh.

        Args:
            log_path: Ruta al archivo orchestrator.jsonl

        Returns:
            MeshAnalysis con estadísticas de nodos.
        """
        analysis = MeshAnalysis()

        if not os.path.exists(log_path):
            return analysis

        entries = []
        with open(log_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        if not entries:
            return analysis

        analysis.total_events = len(entries)

        # Agrupar por nodo
        node_latencies: dict[str, list[float]] = {}
        node_successes: dict[str, int] = {}
        node_totals: dict[str, int] = {}
        cb_open_nodes: set = set()

        for entry in entries:
            node = entry.get("selected_node", entry.get("routed_node", "unknown"))
            latency = entry.get("latency_ms", 0.0)
            success = entry.get("success", True)
            circuit = entry.get("circuit_state", "CLOSED")

            if node not in node_latencies:
                node_latencies[node] = []
                node_successes[node] = 0
                node_totals[node] = 0

            node_latencies[node].append(latency)
            node_totals[node] += 1
            if success:
                node_successes[node] += 1

            if circuit == "OPEN":
                cb_open_nodes.add(node)

        # Calcular promedios por nodo
        all_latencies = []
        total_success = 0
        total_events = 0

        for node, latencies in node_latencies.items():
            avg = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
            analysis.avg_latency_by_node[node] = avg
            all_latencies.extend(latencies)

            total = node_totals[node]
            rate = round(node_successes[node] / total * 100, 2) if total > 0 else 0.0
            analysis.success_rate_by_node[node] = rate

            total_success += node_successes[node]
            total_events += total

        analysis.circuit_breaker_open_nodes = sorted(cb_open_nodes)
        analysis.overall_avg_latency = round(
            sum(all_latencies) / len(all_latencies), 2
        ) if all_latencies else 0.0
        analysis.overall_success_rate = round(
            total_success / total_events * 100, 2
        ) if total_events > 0 else 0.0

        # Nodo más eficiente: mejor ratio éxito/latencia
        best_node = ""
        best_efficiency = -1.0
        for node in node_latencies:
            rate = analysis.success_rate_by_node.get(node, 0)
            avg_lat = analysis.avg_latency_by_node.get(node, 1)
            if avg_lat > 0:
                efficiency = rate / avg_lat
                if efficiency > best_efficiency:
                    best_efficiency = efficiency
                    best_node = node

        analysis.most_efficient_node = best_node

        return analysis

    # ── c) Test Results Analysis ──

    def analyze_test_results(self, test_output: str) -> TestAnalysis:
        """Parsea output de unittest y extrae métricas.

        Args:
            test_output: String con el output de unittest (stderr).

        Returns:
            TestAnalysis con estadísticas de tests.
        """
        analysis = TestAnalysis()

        if not test_output:
            return analysis

        # Parsear "Ran N test(s)"
        ran_match = re.search(r"Ran (\d+) tests?", test_output)
        if ran_match:
            analysis.total = int(ran_match.group(1))

        # Parsear failures y errors del resumen
        fail_match = re.search(r"failures=(\d+)", test_output)
        error_match = re.search(r"errors=(\d+)", test_output)
        skip_match = re.search(r"skipped=(\d+)", test_output)

        if fail_match:
            analysis.failed = int(fail_match.group(1))
        if error_match:
            analysis.errors = int(error_match.group(1))
        if skip_match:
            analysis.skipped = int(skip_match.group(1))

        analysis.passed = analysis.total - analysis.failed - analysis.errors - analysis.skipped

        # Extraer archivos con fallos
        file_fails: dict[str, int] = {}
        # Patrones: FAIL: test_method (tests.test_file)
        for m in re.finditer(r"(?:FAIL|ERROR): \S+ \(([^)]+)\)", test_output):
            module = m.group(1)
            file_fails[module] = file_fails.get(module, 0) + 1

        analysis.failing_files = sorted(file_fails.items(), key=lambda x: x[1], reverse=True)

        # Trend vs resultado anterior
        prev = self._load_previous_test_result()
        if prev is not None:
            analysis.previous_passed = prev.get("passed", -1)
            analysis.previous_failed = prev.get("failed", -1)
            if analysis.previous_passed >= 0:
                if analysis.passed > analysis.previous_passed:
                    analysis.trend = "improving"
                elif analysis.passed < analysis.previous_passed:
                    analysis.trend = "worsening"
                else:
                    analysis.trend = "stable"

        return analysis

    def _load_previous_test_result(self) -> Optional[dict]:
        """Carga el resultado de tests del último ciclo."""
        history = self.get_improvement_history()
        if not history:
            return None
        last = history[-1]
        tests = last.get("tests")
        if tests:
            return tests
        return None

    # ── d) Analyze Drift (PDR) — del issue #1 ──

    def analyze_drift(
        self,
        scores: list[float],
        threshold: float = 0.8,
        window_size: int = 0,
    ) -> DriftAnalysis:
        """Calcula Performance Drift Ratio sobre una serie temporal de scores.

        PDR = 1 - (observed / baseline)
        Basado en propuesta de nanookclaw (issue #1, tracer-protocol).

        Args:
            scores: Lista de scores temporales (0.0 a 1.0).
            threshold: Umbral de governance (default 0.8 para INV-6).
            window_size: Tamaño de ventana (0 = auto, mitad de datos).

        Returns:
            DriftAnalysis con PDR, trend, near-misses.
        """
        if not scores or len(scores) < 2:
            return DriftAnalysis(threshold=threshold)

        n = len(scores)
        ws = window_size if window_size > 0 else max(n // 2, 1)

        baseline = sum(scores[:ws]) / ws
        observed = sum(scores[-ws:]) / ws

        pdr = 1.0 - (observed / baseline) if baseline > 0 else 0.0

        # Near-misses: scores entre threshold y threshold+0.05
        margin = 0.05
        near_misses = sum(
            1 for s in scores
            if threshold <= s < threshold + margin
        )

        # Trend detection: monotonic vs oscillating
        if n >= 4:
            q1 = sum(scores[:n // 4]) / (n // 4)
            q2 = sum(scores[n // 4:n // 2]) / (n // 2 - n // 4)
            q3 = sum(scores[n // 2:3 * n // 4]) / (3 * n // 4 - n // 2)
            q4 = sum(scores[3 * n // 4:]) / (n - 3 * n // 4)
            quarters = [q1, q2, q3, q4]

            diffs = [quarters[i + 1] - quarters[i] for i in range(3)]
            if all(d < -0.01 for d in diffs):
                trend = "degrading"
            elif all(d > 0.01 for d in diffs):
                trend = "improving"
            elif any(d > 0.01 for d in diffs) and any(d < -0.01 for d in diffs):
                trend = "oscillating"
            else:
                trend = "stable"
        else:
            if pdr > 0.05:
                trend = "degrading"
            elif pdr < -0.05:
                trend = "improving"
            else:
                trend = "stable"

        return DriftAnalysis(
            pdr=round(pdr, 4),
            baseline=round(baseline, 4),
            observed=round(observed, 4),
            trend=trend,
            window_size=ws,
            near_misses=near_misses,
            threshold=threshold,
        )

    # ── e) Extract Lessons ──

    def extract_lessons(
        self,
        governance: GovernanceAnalysis,
        mesh: MeshAnalysis,
        tests: TestAnalysis,
        drift: Optional[DriftAnalysis] = None,
    ) -> list[Lesson]:
        """Genera lecciones automáticas a partir de los análisis.

        Lógica de extracción:
        - Si % FAIL governance > 10% -> lesson alta severidad
        - Si latencia promedio > 2000ms -> lesson optimizar
        - Si un nodo tiene circuit breaker OPEN -> lesson evaluar reemplazo
        - Si tests empeoraron -> lesson regresión
        - Si governance mejorando -> lesson positiva
        - Si un nodo es 3x más rápido que el promedio -> lesson priorizar
        - Si PDR > 0.1 -> lesson drift detectado (issue #1)
        - Si near_misses > 3 -> lesson umbral en riesgo
        - Si trend oscillating -> lesson degradación no-monotónica

        Returns:
            Lista de Lesson dataclasses.
        """
        lessons: list[Lesson] = []
        now = self._now_iso()

        # 1. Governance fail rate alta
        if governance.total_decisions > 0 and governance.fail_rate > 10:
            top_rules = ", ".join(
                f"{r[0]} ({r[1]}x)" for r in governance.top_failing_rules[:3]
            ) if governance.top_failing_rules else "sin detalle"
            lessons.append(Lesson(
                id=self._next_lesson_id(),
                category="governance",
                finding=f"Tasa de fallo governance: {governance.fail_rate}% ({governance.fail_count}/{governance.total_decisions})",
                recommendation=f"Revisar reglas que más fallan: {top_rules}. Considerar ajustar thresholds o mejorar prompts.",
                severity="high",
                timestamp=now,
            ))

        # 2. Latencia promedio alta
        if mesh.total_events > 0 and mesh.overall_avg_latency > 2000:
            slow_nodes = [
                f"{n} ({l:.0f}ms)"
                for n, l in sorted(
                    mesh.avg_latency_by_node.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:3]
            ]
            lessons.append(Lesson(
                id=self._next_lesson_id(),
                category="performance",
                finding=f"Latencia promedio mesh: {mesh.overall_avg_latency:.0f}ms (>2000ms)",
                recommendation=f"Optimizar providers lentos: {', '.join(slow_nodes)}. Considerar cache o batch.",
                severity="high",
                timestamp=now,
            ))

        # 3. Circuit breaker OPEN
        for node in mesh.circuit_breaker_open_nodes:
            lessons.append(Lesson(
                id=self._next_lesson_id(),
                category="mesh",
                finding=f"Nodo '{node}' tiene circuit breaker OPEN",
                recommendation=f"Evaluar reemplazo o reparación del nodo '{node}'. Verificar conectividad y health checks.",
                severity="high",
                timestamp=now,
            ))

        # 4. Tests empeoraron
        if tests.trend == "worsening":
            files_str = ", ".join(
                f"{f[0]} ({f[1]})" for f in tests.failing_files[:3]
            ) if tests.failing_files else "sin detalle"
            lessons.append(Lesson(
                id=self._next_lesson_id(),
                category="testing",
                finding=f"Regresión detectada: {tests.passed} passed (antes {tests.previous_passed}), {tests.failed} failed",
                recommendation=f"Investigar regresiones en: {files_str}. Correr tests afectados de forma aislada.",
                severity="high",
                timestamp=now,
            ))

        # 5. Governance mejorando
        if governance.trend == "improving":
            lessons.append(Lesson(
                id=self._next_lesson_id(),
                category="governance",
                finding=f"Trend positivo: fail rate bajó de {governance.first_half_fail_rate}% a {governance.second_half_fail_rate}%",
                recommendation="Mantener curso actual. Las mejoras recientes están teniendo efecto.",
                severity="low",
                timestamp=now,
            ))

        # 6. Nodo 3x más rápido que el promedio
        if mesh.most_efficient_node and mesh.overall_avg_latency > 0:
            best_lat = mesh.avg_latency_by_node.get(mesh.most_efficient_node, 0)
            if best_lat > 0 and mesh.overall_avg_latency / best_lat >= 3:
                lessons.append(Lesson(
                    id=self._next_lesson_id(),
                    category="performance",
                    finding=f"Nodo '{mesh.most_efficient_node}' es {mesh.overall_avg_latency / best_lat:.1f}x más rápido que el promedio ({best_lat:.0f}ms vs {mesh.overall_avg_latency:.0f}ms)",
                    recommendation=f"Priorizar nodo '{mesh.most_efficient_node}' en el router. Considerar aumentar su peso en el load balancer.",
                    severity="medium",
                    timestamp=now,
                ))

        # 7. Governance empeorando
        if governance.trend == "worsening":
            lessons.append(Lesson(
                id=self._next_lesson_id(),
                category="governance",
                finding=f"Trend negativo: fail rate subió de {governance.first_half_fail_rate}% a {governance.second_half_fail_rate}%",
                recommendation="Investigar cambios recientes que deterioraron governance. Revisar últimos commits y configuración.",
                severity="medium",
                timestamp=now,
            ))

        # 8. Tests mejoraron
        if tests.trend == "improving":
            lessons.append(Lesson(
                id=self._next_lesson_id(),
                category="testing",
                finding=f"Tests mejoraron: {tests.passed} passed (antes {tests.previous_passed})",
                recommendation="Mantener la disciplina de testing. Considerar agregar más coverage.",
                severity="low",
                timestamp=now,
            ))

        # ── Drift lessons (PDR — issue #1) ──
        if drift:
            if drift.pdr > 0.1:
                lessons.append(Lesson(
                    id=self._next_lesson_id(),
                    category="drift",
                    finding=f"Performance Drift detectado: PDR={drift.pdr:.2%} (baseline={drift.baseline:.3f} → observed={drift.observed:.3f})",
                    recommendation="Investigar causa de degradación. Revisar providers, carga, o cambios recientes.",
                    severity="high" if drift.pdr > 0.2 else "medium",
                    timestamp=now,
                ))
            elif drift.pdr < -0.05:
                lessons.append(Lesson(
                    id=self._next_lesson_id(),
                    category="drift",
                    finding=f"Mejora detectada: PDR={drift.pdr:.2%} — el sistema está mejorando",
                    recommendation="Documentar qué cambios produjeron la mejora para replicar.",
                    severity="low",
                    timestamp=now,
                ))

            if drift.near_misses > 3:
                lessons.append(Lesson(
                    id=self._next_lesson_id(),
                    category="drift",
                    finding=f"{drift.near_misses} near-misses detectados (scores cerca del threshold {drift.threshold})",
                    recommendation="El sistema está operando al límite. Subir threshold o investigar causa.",
                    severity="high",
                    timestamp=now,
                ))

            if drift.trend == "oscillating":
                lessons.append(Lesson(
                    id=self._next_lesson_id(),
                    category="drift",
                    finding="Degradación no-monotónica detectada — oscilación alrededor de media declinante",
                    recommendation="Patrón de fallo intermitente. Revisar estabilidad de providers y circuit breakers.",
                    severity="medium",
                    timestamp=now,
                ))

        return lessons

    # ── f) Run Improvement Cycle ──

    def run_improvement_cycle(
        self,
        cycle_id: Optional[str] = None,
        governance_log: str = DEFAULT_GOVERNANCE_LOG,
        mesh_log: str = DEFAULT_MESH_LOG,
        test_output: str = "",
        drift_scores: Optional[list[float]] = None,
    ) -> ImprovementCycle:
        """Ejecuta un ciclo completo de auto-mejora.

        1. Analiza governance, mesh, tests, drift (si los datos existen)
        2. Extrae lecciones (incluyendo PDR del issue #1)
        3. Guarda resultado en cycles.jsonl y lessons.jsonl
        4. Retorna ImprovementCycle

        Args:
            cycle_id: ID del ciclo (auto-generado si None)
            governance_log: Ruta a governance_proofs.jsonl
            mesh_log: Ruta a orchestrator.jsonl
            test_output: Output de unittest (string)
            drift_scores: Serie temporal de scores para PDR (optional)

        Returns:
            ImprovementCycle con análisis y lecciones.
        """
        if cycle_id is None:
            cycle_id = str(uuid.uuid4())[:8]

        # Analizar
        gov = self.analyze_governance_logs(governance_log)
        mesh = self.analyze_mesh_performance(mesh_log)
        tests = self.analyze_test_results(test_output)
        drift = self.analyze_drift(drift_scores) if drift_scores else None

        # Extraer lecciones
        lessons = self.extract_lessons(gov, mesh, tests, drift)

        # Construir ciclo
        cycle = ImprovementCycle(
            cycle_id=cycle_id,
            timestamp=self._now_iso(),
            governance=gov.to_dict(),
            mesh=mesh.to_dict(),
            tests=tests.to_dict(),
            drift=drift.to_dict() if drift else None,
            lessons=[l.to_dict() for l in lessons],
            recommendations_count=len(lessons),
        )

        # Persistir
        self._save_cycle(cycle)
        self._save_lessons(lessons, cycle_id)

        logger.info(
            f"Ciclo de mejora {cycle_id} completado: "
            f"{len(lessons)} lecciones extraídas"
        )

        return cycle

    def _save_cycle(self, cycle: ImprovementCycle):
        """Guarda un ciclo en cycles.jsonl."""
        os.makedirs(self.improvement_dir, exist_ok=True)
        with open(self.cycles_file, "a") as f:
            f.write(json.dumps(cycle.to_dict(), default=str) + "\n")

    def _save_lessons(self, lessons: list[Lesson], cycle_id: str):
        """Guarda lecciones en lessons.jsonl."""
        os.makedirs(self.improvement_dir, exist_ok=True)
        with open(self.lessons_file, "a") as f:
            for lesson in lessons:
                entry = lesson.to_dict()
                entry["cycle_id"] = cycle_id
                f.write(json.dumps(entry, default=str) + "\n")

    # ── f) Get Improvement History ──

    def get_improvement_history(self) -> list[dict]:
        """Lee cycles.jsonl y retorna lista de ciclos anteriores.

        Returns:
            Lista de dicts con datos de cada ciclo.
        """
        if not os.path.exists(self.cycles_file):
            return []

        cycles = []
        with open(self.cycles_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    cycles.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return cycles

    # ── g) Compare Cycles ──

    def compare_cycles(self, cycle_a_id: str, cycle_b_id: str) -> dict:
        """Compara dos ciclos y muestra progreso/regresión.

        Args:
            cycle_a_id: ID del ciclo anterior (base)
            cycle_b_id: ID del ciclo posterior (actual)

        Returns:
            Dict con comparación: governance_delta, mesh_delta,
            tests_delta, new_lessons, resolved_lessons.
        """
        history = self.get_improvement_history()

        cycle_a = None
        cycle_b = None
        for c in history:
            if c.get("cycle_id") == cycle_a_id:
                cycle_a = c
            if c.get("cycle_id") == cycle_b_id:
                cycle_b = c

        if cycle_a is None or cycle_b is None:
            return {
                "error": f"Ciclo(s) no encontrado(s). "
                         f"a={cycle_a_id} {'OK' if cycle_a else 'NOT FOUND'}, "
                         f"b={cycle_b_id} {'OK' if cycle_b else 'NOT FOUND'}",
            }

        result: dict = {
            "cycle_a": cycle_a_id,
            "cycle_b": cycle_b_id,
            "timestamp_a": cycle_a.get("timestamp", ""),
            "timestamp_b": cycle_b.get("timestamp", ""),
        }

        # Comparar governance
        gov_a = cycle_a.get("governance", {})
        gov_b = cycle_b.get("governance", {})
        result["governance_delta"] = {
            "fail_rate": {
                "before": gov_a.get("fail_rate", 0),
                "after": gov_b.get("fail_rate", 0),
                "change": round(gov_b.get("fail_rate", 0) - gov_a.get("fail_rate", 0), 2),
            },
            "pass_rate": {
                "before": gov_a.get("pass_rate", 0),
                "after": gov_b.get("pass_rate", 0),
                "change": round(gov_b.get("pass_rate", 0) - gov_a.get("pass_rate", 0), 2),
            },
        }

        # Comparar mesh
        mesh_a = cycle_a.get("mesh", {})
        mesh_b = cycle_b.get("mesh", {})
        result["mesh_delta"] = {
            "avg_latency": {
                "before": mesh_a.get("overall_avg_latency", 0),
                "after": mesh_b.get("overall_avg_latency", 0),
                "change": round(
                    mesh_b.get("overall_avg_latency", 0) - mesh_a.get("overall_avg_latency", 0), 2
                ),
            },
            "success_rate": {
                "before": mesh_a.get("overall_success_rate", 0),
                "after": mesh_b.get("overall_success_rate", 0),
                "change": round(
                    mesh_b.get("overall_success_rate", 0) - mesh_a.get("overall_success_rate", 0), 2
                ),
            },
        }

        # Comparar tests
        tests_a = cycle_a.get("tests", {})
        tests_b = cycle_b.get("tests", {})
        result["tests_delta"] = {
            "passed": {
                "before": tests_a.get("passed", 0),
                "after": tests_b.get("passed", 0),
                "change": tests_b.get("passed", 0) - tests_a.get("passed", 0),
            },
            "failed": {
                "before": tests_a.get("failed", 0),
                "after": tests_b.get("failed", 0),
                "change": tests_b.get("failed", 0) - tests_a.get("failed", 0),
            },
        }

        # Contar lecciones
        result["lessons_a_count"] = len(cycle_a.get("lessons", []))
        result["lessons_b_count"] = len(cycle_b.get("lessons", []))
        result["lessons_delta"] = result["lessons_b_count"] - result["lessons_a_count"]

        # Determinar veredicto general
        improvements = 0
        regressions = 0

        gov_change = result["governance_delta"]["fail_rate"]["change"]
        if gov_change < -1:
            improvements += 1
        elif gov_change > 1:
            regressions += 1

        mesh_lat_change = result["mesh_delta"]["avg_latency"]["change"]
        if mesh_lat_change < -50:
            improvements += 1
        elif mesh_lat_change > 50:
            regressions += 1

        test_change = result["tests_delta"]["passed"]["change"]
        if test_change > 0:
            improvements += 1
        elif test_change < 0:
            regressions += 1

        if regressions > improvements:
            result["verdict"] = "REGRESSED"
        elif improvements > regressions:
            result["verdict"] = "IMPROVED"
        else:
            result["verdict"] = "STABLE"

        result["improvements"] = improvements
        result["regressions"] = regressions

        return result
