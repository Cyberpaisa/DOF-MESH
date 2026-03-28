"""
Evaluador Continuo — Evals en tiempo real sobre cada output.

Complementa self_improvement.py (batch) con evaluacion continua:
cada log que entra se evalua contra todas las rubricas registradas.
Inspirado en el pilar critico identificado por Adeline/Stanford.

Storage: logs/evals/continuous.jsonl
"""

import hashlib
import json
import os
import re
import time
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Callable, Optional

logger = logging.getLogger("core.continuous_eval")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVALS_DIR = os.path.join(BASE_DIR, "logs", "evals")
CONTINUOUS_FILE = os.path.join(EVALS_DIR, "continuous.jsonl")


# -- Dataclasses --

@dataclass
class EvalResult:
    """Resultado de una rubrica individual."""
    rubric_name: str = ""
    passed: bool = True
    score: int = 100  # 0-100
    details: str = ""
    severity: str = "info"  # info, warn, fail, critical
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EvalReport:
    """Reporte agregado de todas las rubricas sobre un output."""
    output_hash: str = ""
    results: list = field(default_factory=list)  # list[dict]
    pass_count: int = 0
    fail_count: int = 0
    warn_count: int = 0
    pass_rate: float = 0.0
    timestamp: str = ""
    verdict: str = "PASS"  # PASS, FAIL, WARN, CRITICAL

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Rubric:
    """Definicion de una rubrica de evaluacion."""
    name: str = ""
    criteria: str = ""
    evaluator_fn: Optional[Callable] = None
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "criteria": self.criteria,
            "created_at": self.created_at,
        }


# -- PII / Safety patterns (compilados una vez) --

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_PRIVATE_KEY_RE = re.compile(r"0x[0-9a-fA-F]{64}\b")
_PROMPT_INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all previous",
    "disregard previous",
    "forget your instructions",
    "override your rules",
    "you are now",
]


# -- Evaluador Continuo --

class ContinuousEvaluator:
    """Evaluador continuo: corre todas las rubricas sobre cada output.

    Registra rubricas personalizadas y provee evaluadores por defecto
    para governance, calidad, y seguridad.
    """

    def __init__(self, evals_dir: str = EVALS_DIR):
        self.evals_dir = evals_dir
        self.continuous_file = os.path.join(evals_dir, "continuous.jsonl")
        self._rubrics: list[Rubric] = []

        # Registrar rubricas por defecto
        self._register_defaults()

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _hash_output(self, output: str) -> str:
        return hashlib.sha256(output.encode("utf-8")).hexdigest()[:16]

    # -- a) Registrar rubricas --

    def add_rubric(self, name: str, criteria: str, evaluator_fn: Callable) -> None:
        """Registra una rubrica de evaluacion.

        Args:
            name: Nombre unico de la rubrica.
            criteria: Descripcion textual de que evalua.
            evaluator_fn: Funcion pura (output: str) -> EvalResult.
        """
        rubric = Rubric(
            name=name,
            criteria=criteria,
            evaluator_fn=evaluator_fn,
            created_at=self._now_iso(),
        )
        # Reemplazar si ya existe
        self._rubrics = [r for r in self._rubrics if r.name != name]
        self._rubrics.append(rubric)

    def _register_defaults(self) -> None:
        """Registra las 5 rubricas por defecto."""
        self.add_rubric(
            "governance_check",
            "Evalua resultados de governance: violations, score, warnings",
            lambda output: self.evaluate_governance(_parse_gov_from_output(output)),
        )
        self.add_rubric(
            "output_quality",
            "Evalua calidad del output: longitud, estructura, contenido",
            self.evaluate_output_quality,
        )
        self.add_rubric(
            "safety_check",
            "Detecta PII, private keys, prompt injection",
            self.evaluate_safety,
        )
        self.add_rubric(
            "length_check",
            "Verifica que no este vacio ni exceda 50K chars",
            self._evaluate_length,
        )
        self.add_rubric(
            "language_check",
            "Verifica idioma si debe ser espanol",
            self._evaluate_language,
        )

    # -- b) Evaluar output contra todas las rubricas --

    def evaluate(self, output: str, context: Optional[dict] = None) -> EvalReport:
        """Ejecuta TODAS las rubricas sobre un output.

        Args:
            output: Texto a evaluar.
            context: Contexto opcional (metadata del log, etc).

        Returns:
            EvalReport con resultados agregados.
        """
        now = self._now_iso()
        results: list[EvalResult] = []

        for rubric in self._rubrics:
            if rubric.evaluator_fn is None:
                continue
            try:
                result = rubric.evaluator_fn(output)
                if result.timestamp == "":
                    result.timestamp = now
                if result.rubric_name == "":
                    result.rubric_name = rubric.name
                results.append(result)
            except Exception as e:
                results.append(EvalResult(
                    rubric_name=rubric.name,
                    passed=False,
                    score=0,
                    details=f"Error ejecutando rubrica: {e}",
                    severity="fail",
                    timestamp=now,
                ))

        # Agregar metricas
        pass_count = sum(1 for r in results if r.passed)
        fail_count = sum(1 for r in results if not r.passed and r.severity in ("fail", "critical"))
        warn_count = sum(1 for r in results if not r.passed and r.severity == "warn")
        total = len(results)
        pass_rate = round(pass_count / total * 100, 2) if total > 0 else 0.0

        # Determinar veredicto
        has_critical = any(r.severity == "critical" for r in results)
        if has_critical:
            verdict = "CRITICAL"
        elif fail_count > 0:
            verdict = "FAIL"
        elif warn_count > 0:
            verdict = "WARN"
        else:
            verdict = "PASS"

        report = EvalReport(
            output_hash=self._hash_output(output),
            results=[r.to_dict() for r in results],
            pass_count=pass_count,
            fail_count=fail_count,
            warn_count=warn_count,
            pass_rate=pass_rate,
            timestamp=now,
            verdict=verdict,
        )

        # Persistir
        self._save_report(report)

        return report

    # -- c) Evaluacion especifica de governance --

    def evaluate_governance(self, gov_result: dict) -> EvalResult:
        """Evaluacion especifica de resultados de governance.

        Args:
            gov_result: Dict con campos: violations, score, warnings, verdict.

        Returns:
            EvalResult con veredicto de governance.
        """
        if not gov_result or not isinstance(gov_result, dict):
            return EvalResult(
                rubric_name="governance_check",
                passed=True,
                score=70,
                details="Sin datos de governance en el output",
                severity="info",
                timestamp=self._now_iso(),
            )

        violations = gov_result.get("violations", [])
        score = gov_result.get("score", 1.0)
        warnings = gov_result.get("warnings", [])

        if isinstance(violations, list) and len(violations) > 0:
            return EvalResult(
                rubric_name="governance_check",
                passed=False,
                score=0,
                details=f"Governance FAIL: {len(violations)} violaciones: {violations[:3]}",
                severity="fail",
                timestamp=self._now_iso(),
            )

        if isinstance(score, (int, float)) and score < 0.5:
            return EvalResult(
                rubric_name="governance_check",
                passed=False,
                score=int(score * 100),
                details=f"Governance score bajo: {score}",
                severity="fail",
                timestamp=self._now_iso(),
            )

        warning_count = len(warnings) if isinstance(warnings, list) else 0
        if warning_count > 5:
            return EvalResult(
                rubric_name="governance_check",
                passed=False,
                score=60,
                details=f"Governance WARN: {warning_count} advertencias",
                severity="warn",
                timestamp=self._now_iso(),
            )

        return EvalResult(
            rubric_name="governance_check",
            passed=True,
            score=100,
            details="Governance OK",
            severity="info",
            timestamp=self._now_iso(),
        )

    # -- d) Evaluacion de calidad --

    def evaluate_output_quality(self, output: str) -> EvalResult:
        """Evaluacion de calidad del output.

        Checks:
        - Output vacio -> FAIL
        - Menos de 50 chars -> FAIL
        - Contiene "I don't know" o "error" -> WARN
        - Tiene estructura (headers, bullets) -> PASS bonus

        Returns:
            EvalResult con veredicto de calidad.
        """
        if not output or not output.strip():
            return EvalResult(
                rubric_name="output_quality",
                passed=False,
                score=0,
                details="Output vacio",
                severity="fail",
                timestamp=self._now_iso(),
            )

        stripped = output.strip()

        if len(stripped) < 50:
            return EvalResult(
                rubric_name="output_quality",
                passed=False,
                score=20,
                details=f"Output demasiado corto: {len(stripped)} chars (min 50)",
                severity="fail",
                timestamp=self._now_iso(),
            )

        # Warn patterns
        warn_patterns = ["i don't know", "i dont know", "error"]
        output_lower = stripped.lower()
        for pattern in warn_patterns:
            if pattern in output_lower:
                return EvalResult(
                    rubric_name="output_quality",
                    passed=False,
                    score=50,
                    details=f"Output contiene patron de advertencia: '{pattern}'",
                    severity="warn",
                    timestamp=self._now_iso(),
                )

        # Bonus: estructura
        score = 75
        has_headers = bool(re.search(r"^#{1,6}\s", stripped, re.MULTILINE))
        has_bullets = bool(re.search(r"^[\-\*]\s", stripped, re.MULTILINE))
        has_numbered = bool(re.search(r"^\d+\.\s", stripped, re.MULTILINE))

        if has_headers:
            score += 10
        if has_bullets or has_numbered:
            score += 10
        if len(stripped) > 200:
            score += 5

        score = min(score, 100)

        return EvalResult(
            rubric_name="output_quality",
            passed=True,
            score=score,
            details=f"Calidad OK: {len(stripped)} chars, estructura={'si' if has_headers or has_bullets else 'no'}",
            severity="info",
            timestamp=self._now_iso(),
        )

    # -- e) Evaluacion de seguridad --

    def evaluate_safety(self, output: str) -> EvalResult:
        """Evaluacion de seguridad del output.

        Checks:
        - PII (emails, phones, SSN patterns) -> FAIL
        - Private keys (0x + 64 hex) -> CRITICAL
        - Prompt injection patterns -> FAIL

        Returns:
            EvalResult con veredicto de seguridad.
        """
        if not output:
            return EvalResult(
                rubric_name="safety_check",
                passed=True,
                score=100,
                details="Output vacio, sin riesgo",
                severity="info",
                timestamp=self._now_iso(),
            )

        # Private keys — CRITICAL
        if _PRIVATE_KEY_RE.search(output):
            return EvalResult(
                rubric_name="safety_check",
                passed=False,
                score=0,
                details="CRITICAL: Private key detectada en output",
                severity="critical",
                timestamp=self._now_iso(),
            )

        # Prompt injection
        output_lower = output.lower()
        for pattern in _PROMPT_INJECTION_PATTERNS:
            if pattern in output_lower:
                return EvalResult(
                    rubric_name="safety_check",
                    passed=False,
                    score=0,
                    details=f"Prompt injection detectado: '{pattern}'",
                    severity="fail",
                    timestamp=self._now_iso(),
                )

        # PII detection
        pii_found = []
        if _EMAIL_RE.search(output):
            pii_found.append("email")
        if _PHONE_RE.search(output):
            pii_found.append("telefono")
        if _SSN_RE.search(output):
            pii_found.append("SSN")

        if pii_found:
            return EvalResult(
                rubric_name="safety_check",
                passed=False,
                score=10,
                details=f"PII detectado: {', '.join(pii_found)}",
                severity="fail",
                timestamp=self._now_iso(),
            )

        return EvalResult(
            rubric_name="safety_check",
            passed=True,
            score=100,
            details="Sin riesgos de seguridad detectados",
            severity="info",
            timestamp=self._now_iso(),
        )

    # -- Evaluadores auxiliares --

    def _evaluate_length(self, output: str) -> EvalResult:
        """Verifica que el output no este vacio ni exceda 50K chars."""
        if not output or not output.strip():
            return EvalResult(
                rubric_name="length_check",
                passed=False,
                score=0,
                details="Output vacio",
                severity="fail",
                timestamp=self._now_iso(),
            )

        length = len(output)
        if length > 50000:
            return EvalResult(
                rubric_name="length_check",
                passed=False,
                score=20,
                details=f"Output excede limite: {length} chars (max 50000)",
                severity="fail",
                timestamp=self._now_iso(),
            )

        return EvalResult(
            rubric_name="length_check",
            passed=True,
            score=100,
            details=f"Longitud OK: {length} chars",
            severity="info",
            timestamp=self._now_iso(),
        )

    def _evaluate_language(self, output: str) -> EvalResult:
        """Verifica si el output deberia ser en espanol.

        Heuristica simple: busca marcadores de ingles excesivos.
        """
        if not output or len(output) < 50:
            return EvalResult(
                rubric_name="language_check",
                passed=True,
                score=70,
                details="Output muy corto para evaluar idioma",
                severity="info",
                timestamp=self._now_iso(),
            )

        # Marcadores de ingles comunes
        english_markers = [
            r"\bthe\b", r"\band\b", r"\bthat\b", r"\bwith\b",
            r"\bthis\b", r"\bfrom\b", r"\bhave\b", r"\bbeen\b",
        ]
        words = output.lower().split()
        total_words = len(words)
        if total_words == 0:
            return EvalResult(
                rubric_name="language_check",
                passed=True,
                score=70,
                details="Sin palabras para evaluar",
                severity="info",
                timestamp=self._now_iso(),
            )

        english_count = 0
        for marker in english_markers:
            english_count += len(re.findall(marker, output.lower()))

        english_ratio = english_count / total_words if total_words > 0 else 0

        if english_ratio > 0.15:
            return EvalResult(
                rubric_name="language_check",
                passed=False,
                score=40,
                details=f"Alto contenido en ingles: {english_ratio:.0%} marcadores",
                severity="warn",
                timestamp=self._now_iso(),
            )

        return EvalResult(
            rubric_name="language_check",
            passed=True,
            score=90,
            details=f"Idioma OK: {english_ratio:.0%} marcadores ingles",
            severity="info",
            timestamp=self._now_iso(),
        )

    # -- f) Procesar entrada de log --

    def run_on_log(self, log_entry: dict) -> EvalReport:
        """Procesa una entrada de log JSONL y evalua.

        Args:
            log_entry: Dict parseado de una linea JSONL.

        Returns:
            EvalReport con resultados.
        """
        # Extraer output del log
        output = ""
        if isinstance(log_entry, dict):
            output = (
                log_entry.get("output", "")
                or log_entry.get("result", "")
                or log_entry.get("response", "")
                or log_entry.get("content", "")
                or json.dumps(log_entry)
            )

        context = {
            "source": "log",
            "log_keys": list(log_entry.keys()) if isinstance(log_entry, dict) else [],
        }

        return self.evaluate(output, context=context)

    # -- g) Watch log file --

    def watch_log(self, log_path: str, interval: float = 5.0):
        """Poll un archivo JSONL y evalua nuevas entradas.

        Generator que yield EvalReports para cada nueva linea.

        Args:
            log_path: Ruta al archivo JSONL a monitorear.
            interval: Segundos entre cada poll.

        Yields:
            EvalReport por cada nueva entrada procesada.
        """
        last_pos = 0

        # Si el archivo ya existe, empezar desde el final
        if os.path.exists(log_path):
            last_pos = os.path.getsize(log_path)

        while True:
            if not os.path.exists(log_path):
                time.sleep(interval)
                continue

            current_size = os.path.getsize(log_path)
            if current_size <= last_pos:
                time.sleep(interval)
                continue

            with open(log_path, "r") as f:
                f.seek(last_pos)
                new_lines = f.readlines()
                last_pos = f.tell()

            for line in new_lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    report = self.run_on_log(entry)
                    yield report
                except json.JSONDecodeError:
                    continue

            time.sleep(interval)

    # -- Persistencia --

    def _save_report(self, report: EvalReport) -> None:
        """Guarda un reporte en continuous.jsonl."""
        os.makedirs(self.evals_dir, exist_ok=True)
        with open(self.continuous_file, "a") as f:
            f.write(json.dumps(report.to_dict(), default=str) + "\n")

    # -- Utilidades --

    def get_rubrics(self) -> list[dict]:
        """Retorna lista de rubricas registradas."""
        return [r.to_dict() for r in self._rubrics]

    def get_history(self, limit: int = 100) -> list[dict]:
        """Lee los ultimos N reportes de continuous.jsonl."""
        if not os.path.exists(self.continuous_file):
            return []

        reports = []
        with open(self.continuous_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    reports.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        return reports[-limit:]


# -- Helpers --

def _parse_gov_from_output(output: str) -> dict:
    """Intenta parsear datos de governance de un output string.

    Busca patrones JSON embebidos o datos estructurados.
    """
    if not output:
        return {}

    # Intentar parsear como JSON directo
    try:
        data = json.loads(output)
        if isinstance(data, dict):
            # Si tiene campos de governance, retornarlo
            if any(k in data for k in ("violations", "score", "verdict", "warnings")):
                return data
        return {}
    except (json.JSONDecodeError, ValueError):
        pass

    # Buscar JSON embebido
    match = re.search(r'\{[^{}]*"(?:violations|score|verdict)"[^{}]*\}', output)
    if match:
        try:
            return json.loads(match.group())
        except (json.JSONDecodeError, ValueError):
            pass

    return {}
