from __future__ import annotations
"""
PromptTestBench — Batch testing de prompts con datasets JSONL.

Cierra gap #2 de Adaline: testing sistematico de prompts antes de deploy.
Permite crear datasets de test cases, correr benchmarks contra templates
de prompts, y comparar multiples versiones.

Storage: logs/prompts/datasets/ (un JSONL por dataset)
         logs/prompts/bench_results.jsonl
"""

import csv
import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS_DIR = os.path.join(BASE_DIR, "logs", "prompts", "datasets")
BENCH_RESULTS_FILE = os.path.join(BASE_DIR, "logs", "prompts", "bench_results.jsonl")


# -- Dataclasses --

@dataclass
class TestCase:
    __test__ = False
    """Un caso de prueba para un prompt."""
    id: str
    input_vars: dict
    expected_output: Optional[str] = None
    expected_verdict: Optional[str] = None  # 'pass' | 'fail'
    tags: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class TestResult:
    __test__ = False
    """Resultado de correr un test case contra un prompt."""
    test_case_id: str
    prompt_name: str
    prompt_version: int
    output: str
    passed: bool
    eval_results: list = field(default_factory=list)
    duration_ms: float = 0.0
    timestamp: str = ""


@dataclass
class BenchReport:
    """Reporte agregado de un benchmark completo."""
    bench_id: str
    prompt_name: str
    prompt_version: int
    total_cases: int
    passed: int
    failed: int
    pass_rate: float
    avg_duration_ms: float
    results: list = field(default_factory=list)  # list[TestResult as dict]
    timestamp: str = ""


# -- PromptTestBench --

class PromptTestBench:
    """
    Bench de testing para prompts con datasets JSONL.

    Permite crear, cargar y ejecutar datasets de test cases
    contra templates de prompts, evaluando resultados con
    el ContinuousEvaluator o evaluadores custom.
    """

    def __init__(
        self,
        datasets_dir: Optional[str] = None,
        results_file: Optional[str] = None,
    ):
        self._datasets_dir = datasets_dir or DATASETS_DIR
        self._results_file = results_file or BENCH_RESULTS_FILE
        os.makedirs(self._datasets_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self._results_file), exist_ok=True)

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _dataset_path(self, name: str) -> str:
        """Ruta al archivo JSONL de un dataset."""
        safe_name = re.sub(r"[^\w\-]", "_", name)
        return os.path.join(self._datasets_dir, f"{safe_name}.jsonl")

    # -- a) Crear dataset --

    def create_dataset(self, name: str, test_cases: list) -> str:
        """Guarda lista de TestCase en JSONL. Retorna dataset_id.

        Args:
            name: Nombre del dataset.
            test_cases: Lista de TestCase.

        Returns:
            dataset_id (nombre del dataset).
        """
        if not name or not name.strip():
            raise ValueError("Dataset name cannot be empty")

        path = self._dataset_path(name)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            for tc in test_cases:
                data = asdict(tc) if hasattr(tc, "__dataclass_fields__") else tc
                f.write(json.dumps(data, ensure_ascii=False) + "\n")

        return name

    # -- b) Cargar dataset --

    def load_dataset(self, name: str) -> list:
        """Lee dataset de JSONL. Retorna lista de TestCase.

        Args:
            name: Nombre del dataset.

        Returns:
            Lista de TestCase.

        Raises:
            FileNotFoundError: si el dataset no existe.
        """
        path = self._dataset_path(name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Dataset '{name}' not found at {path}")

        cases = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                cases.append(TestCase(**data))

        return cases

    # -- c) Agregar test case --

    def add_test_case(self, dataset_name: str, test_case) -> None:
        """Agrega un caso al dataset existente.

        Args:
            dataset_name: Nombre del dataset.
            test_case: TestCase a agregar.
        """
        path = self._dataset_path(dataset_name)
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Dataset '{dataset_name}' not found. Use create_dataset first."
            )

        data = asdict(test_case) if hasattr(test_case, "__dataclass_fields__") else test_case
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    # -- d) Importar CSV --

    def import_from_csv(
        self, dataset_name: str, csv_path: str, mapping: dict
    ) -> int:
        """Importa CSV a dataset JSONL.

        Args:
            dataset_name: Nombre del dataset destino.
            csv_path: Ruta al archivo CSV.
            mapping: Dict que mapea columnas CSV a campos TestCase.
                     Ejemplo: {"question": "input_vars.question",
                               "answer": "expected_output"}

        Returns:
            Cantidad de casos importados.
        """
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        cases = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                input_vars = {}
                expected_output = None
                expected_verdict = None
                tags = []
                metadata = {}

                for csv_col, target_field in mapping.items():
                    value = row.get(csv_col, "")

                    if target_field.startswith("input_vars."):
                        var_name = target_field.split(".", 1)[1]
                        input_vars[var_name] = value
                    elif target_field == "expected_output":
                        expected_output = value
                    elif target_field == "expected_verdict":
                        expected_verdict = value
                    elif target_field == "tags":
                        tags = [t.strip() for t in value.split(",") if t.strip()]
                    elif target_field.startswith("metadata."):
                        meta_key = target_field.split(".", 1)[1]
                        metadata[meta_key] = value

                tc = TestCase(
                    id=f"csv_{i}",
                    input_vars=input_vars,
                    expected_output=expected_output,
                    expected_verdict=expected_verdict,
                    tags=tags,
                    metadata=metadata,
                )
                cases.append(tc)

        # Crear o append al dataset
        path = self._dataset_path(dataset_name)
        if os.path.exists(path):
            for tc in cases:
                self.add_test_case(dataset_name, tc)
        else:
            self.create_dataset(dataset_name, cases)

        return len(cases)

    # -- e) Correr bench --

    def run_bench(
        self,
        dataset_name: str,
        prompt_name: str,
        prompt_content: str,
        evaluator=None,
        prompt_version: int = 1,
    ) -> BenchReport:
        """Corre benchmark de un prompt contra un dataset.

        Para cada test_case:
        - Renderiza el prompt reemplazando {{variables}} con input_vars
        - NO llama a un LLM (el bench evalua el prompt renderizado)
        - Corre el evaluator sobre el output esperado o renderizado
        - Registra TestResult

        Args:
            dataset_name: Nombre del dataset.
            prompt_name: Nombre del prompt.
            prompt_content: Template del prompt con {{variables}}.
            evaluator: Opcional. Objeto con metodo evaluate(output) -> EvalReport.
                       Compatible con ContinuousEvaluator.
            prompt_version: Version del prompt (default 1).

        Returns:
            BenchReport con metricas agregadas.
        """
        cases = self.load_dataset(dataset_name)
        results = []
        bench_id = str(uuid.uuid4())[:8]
        now = self._now_iso()

        for tc in cases:
            start = time.monotonic()

            # Renderizar prompt
            rendered = self.render_prompt(prompt_content, tc.input_vars)

            # El output a evaluar: si hay expected_output, usarlo;
            # sino, el prompt renderizado es el output
            output = tc.expected_output if tc.expected_output else rendered

            # Evaluar
            eval_results = []
            passed = True

            if evaluator is not None:
                try:
                    report = evaluator.evaluate(output)
                    eval_results = report.results if hasattr(report, "results") else []
                    # Determinar si pasa basandose en el veredicto del evaluator
                    verdict = getattr(report, "verdict", "PASS")
                    eval_passed = verdict in ("PASS", "WARN")
                except Exception as e:
                    eval_results = [{"error": str(e)}]
                    eval_passed = False

                # Si hay expected_verdict, comparar
                if tc.expected_verdict is not None:
                    passed = (
                        (tc.expected_verdict == "pass" and eval_passed)
                        or (tc.expected_verdict == "fail" and not eval_passed)
                    )
                else:
                    passed = eval_passed
            else:
                # Sin evaluator: pasa si expected_output coincide con rendered
                # o si no hay expected_output
                if tc.expected_output is not None:
                    passed = tc.expected_output.strip() == rendered.strip()
                else:
                    passed = True

            elapsed_ms = (time.monotonic() - start) * 1000

            tr = TestResult(
                test_case_id=tc.id,
                prompt_name=prompt_name,
                prompt_version=prompt_version,
                output=output,
                passed=passed,
                eval_results=eval_results,
                duration_ms=round(elapsed_ms, 2),
                timestamp=now,
            )
            results.append(tr)

        # Metricas agregadas
        total = len(results)
        passed_count = sum(1 for r in results if r.passed)
        failed_count = total - passed_count
        pass_rate = round(passed_count / total * 100, 2) if total > 0 else 0.0
        avg_dur = (
            round(sum(r.duration_ms for r in results) / total, 2)
            if total > 0
            else 0.0
        )

        report = BenchReport(
            bench_id=bench_id,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            total_cases=total,
            passed=passed_count,
            failed=failed_count,
            pass_rate=pass_rate,
            avg_duration_ms=avg_dur,
            results=[asdict(r) for r in results],
            timestamp=now,
        )

        # Persistir resultado
        self._save_bench_report(report)

        return report

    # -- f) Comparar prompts --

    def run_comparison(
        self,
        dataset_name: str,
        prompts: list,
        evaluator=None,
    ) -> list:
        """Corre el mismo dataset contra multiples versiones de prompt.

        Args:
            dataset_name: Nombre del dataset.
            prompts: Lista de tuplas (prompt_name, prompt_content).
            evaluator: Opcional. Evaluador compatible con ContinuousEvaluator.

        Returns:
            Lista de BenchReports para comparar.
        """
        reports = []
        for i, (name, content) in enumerate(prompts):
            report = self.run_bench(
                dataset_name=dataset_name,
                prompt_name=name,
                prompt_content=content,
                evaluator=evaluator,
                prompt_version=i + 1,
            )
            reports.append(report)
        return reports

    # -- g) Renderizar prompt --

    @staticmethod
    def render_prompt(template: str, variables: dict) -> str:
        """Reemplaza {{variable}} con valores del dict.

        Detecta variables faltantes y lanza ValueError.

        Args:
            template: Template con placeholders {{nombre}}.
            variables: Dict con valores a sustituir.

        Returns:
            Prompt renderizado.

        Raises:
            ValueError: si hay variables en el template sin valor en el dict.
        """
        # Encontrar todas las variables en el template
        pattern = r"\{\{(\w+)\}\}"
        found_vars = set(re.findall(pattern, template))

        # Detectar faltantes
        provided = set(variables.keys())
        missing = found_vars - provided
        if missing:
            raise ValueError(
                f"Variables faltantes en el template: {sorted(missing)}"
            )

        # Reemplazar
        result = template
        for var_name, value in variables.items():
            result = result.replace("{{" + var_name + "}}", str(value))

        return result

    # -- h) Generar resumen --

    def generate_report_summary(self, bench_report) -> str:
        """Genera resumen legible del bench.

        Args:
            bench_report: BenchReport a resumir.

        Returns:
            String con resumen formateado.
        """
        br = bench_report
        lines = [
            f"=== Bench Report: {br.bench_id} ===",
            f"Prompt: {br.prompt_name} (v{br.prompt_version})",
            f"Timestamp: {br.timestamp}",
            f"",
            f"Total: {br.total_cases} casos",
            f"Passed: {br.passed}",
            f"Failed: {br.failed}",
            f"Pass Rate: {br.pass_rate}%",
            f"Avg Duration: {br.avg_duration_ms}ms",
        ]

        if br.failed > 0:
            lines.append("")
            lines.append("--- Fallos ---")
            for r in br.results:
                r_dict = r if isinstance(r, dict) else asdict(r)
                if not r_dict.get("passed", True):
                    lines.append(
                        f"  [{r_dict['test_case_id']}] output={r_dict.get('output', '')[:80]}..."
                    )

        return "\n".join(lines)

    # -- Persistencia --

    def _save_bench_report(self, report: BenchReport) -> None:
        """Guarda reporte en bench_results.jsonl."""
        os.makedirs(os.path.dirname(self._results_file), exist_ok=True)
        with open(self._results_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(report), ensure_ascii=False, default=str) + "\n")
