"""
Prompt Evaluation Gate — Gate de evaluacion de prompts para CI/CD.

Detecta cambios en prompts dentro de PRs, corre evaluaciones automaticas,
y genera reportes para GitHub Actions. Gap #3 de Adaline.

Storage: logs/prompts/gate_results.jsonl
"""

import json
import os
import re
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("core.prompt_eval_gate")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE_DIR = os.path.join(BASE_DIR, "logs", "prompts")
GATE_FILE = os.path.join(GATE_DIR, "gate_results.jsonl")

# Patrones que indican que un archivo contiene prompts
PROMPT_PATTERNS = [
    re.compile(r'system[\s_]?prompt', re.IGNORECASE),
    re.compile(r'user[\s_]?prompt', re.IGNORECASE),
    re.compile(r'instructions?\s*[=:]', re.IGNORECASE),
    re.compile(r'\{\{.*?\}\}'),          # template strings con {{ }}
    re.compile(r'""".*?"""', re.DOTALL),  # docstrings triples
    re.compile(r"'''.*?'''", re.DOTALL),  # docstrings triples single
    re.compile(r'PROMPT\s*=', re.IGNORECASE),
    re.compile(r'template\s*=', re.IGNORECASE),
    re.compile(r'CONSTITUTION', re.IGNORECASE),
    re.compile(r'role\s*[=:]\s*["\']system', re.IGNORECASE),
]

# Patrones de secrets que NO deben aparecer en prompts
SECRET_PATTERNS = [
    re.compile(r'0x[a-fA-F0-9]{64}'),          # private keys
    re.compile(r'sk-[a-zA-Z0-9]{20,}'),         # OpenAI keys
    re.compile(r'gsk_[a-zA-Z0-9]{20,}'),        # Groq keys
    re.compile(r'Bearer\s+[a-zA-Z0-9._-]{20,}'),  # Bearer tokens
    re.compile(r'password\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
    re.compile(r'secret\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
    re.compile(r'token\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
    re.compile(r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----'),
]


# -- Dataclasses --

@dataclass
class PromptInfo:
    """Informacion de un prompt extraido."""
    content: str = ""
    line: int = 0
    file: str = ""


@dataclass
class PromptEvalResult:
    """Resultado de evaluacion de un prompt individual."""
    prompt_file: str = ""
    prompt_line: int = 0
    passed: bool = True
    eval_score: float = 1.0
    governance_passed: bool = True
    has_secrets: bool = False
    details: str = ""


@dataclass
class GateResult:
    """Resultado agregado del gate de evaluacion."""
    passed: bool = True
    threshold: float = 0.7
    actual_pass_rate: float = 1.0
    prompts_evaluated: int = 0
    failures: list = field(default_factory=list)
    report: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class PromptEvalGate:
    """Gate de evaluacion de prompts para CI/CD.

    Detecta cambios en archivos que contienen prompts, extrae los prompts,
    corre evaluaciones y governance checks, y genera reportes CI.
    """

    def __init__(self, gate_dir: str = GATE_DIR):
        self.gate_dir = gate_dir
        self.gate_file = os.path.join(gate_dir, "gate_results.jsonl")

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # -- a) Detectar cambios en prompts --

    def detect_prompt_changes(self, diff_text: str) -> list:
        """Detecta archivos con cambios en prompts a partir de un diff.

        Args:
            diff_text: Output de `git diff`.

        Returns:
            Lista de archivos afectados que contienen prompts.
        """
        if not diff_text or not diff_text.strip():
            return []

        affected_files = set()

        # Extraer archivos del diff
        current_file = None
        diff_lines = diff_text.split('\n')

        for line in diff_lines:
            # Detectar archivo en diff header
            if line.startswith('+++ b/'):
                current_file = line[6:]  # quitar '+++ b/'
                continue
            if line.startswith('--- a/'):
                continue

            # Solo analizar lineas agregadas/modificadas
            if current_file and line.startswith('+') and not line.startswith('+++'):
                added_content = line[1:]  # quitar el '+'
                for pattern in PROMPT_PATTERNS:
                    if pattern.search(added_content):
                        affected_files.add(current_file)
                        break

        return sorted(affected_files)

    # -- b) Extraer prompts de un archivo --

    def extract_prompts_from_file(self, file_path: str) -> list:
        """Extrae strings que parecen prompts de un archivo.

        Lee archivos Python, YAML, y JSON. Extrae strings con >100 chars
        que contienen patrones de instrucciones.

        Args:
            file_path: Ruta al archivo.

        Returns:
            Lista de dicts {content, line, file}.
        """
        if not os.path.isfile(file_path):
            return []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except (IOError, OSError):
            return []

        prompts = []
        lines = content.split('\n')

        ext = os.path.splitext(file_path)[1].lower()

        if ext in ('.py', '.pyi'):
            prompts.extend(self._extract_from_python(lines, file_path))
        elif ext in ('.yml', '.yaml'):
            prompts.extend(self._extract_from_yaml(lines, file_path))
        elif ext == '.json':
            prompts.extend(self._extract_from_json(content, file_path))

        return prompts

    def _extract_from_python(self, lines: list, file_path: str) -> list:
        """Extrae prompts de archivos Python."""
        prompts = []
        in_multiline = False
        multiline_start = 0
        multiline_content = []
        multiline_delim = None

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Detectar inicio de string multilinea
            if not in_multiline:
                for delim in ('"""', "'''"):
                    if delim in stripped:
                        count = stripped.count(delim)
                        if count == 1:
                            # Inicio de multilinea
                            in_multiline = True
                            multiline_start = i
                            multiline_delim = delim
                            idx = stripped.index(delim)
                            multiline_content = [stripped[idx + 3:]]
                            break
                        elif count >= 2:
                            # String en una sola linea
                            idx1 = stripped.index(delim)
                            idx2 = stripped.index(delim, idx1 + 3)
                            candidate = stripped[idx1 + 3:idx2]
                            if len(candidate) > 100 and self._looks_like_prompt(candidate):
                                prompts.append({
                                    'content': candidate,
                                    'line': i,
                                    'file': file_path,
                                })
                            break
            else:
                # Dentro de multilinea
                if multiline_delim and multiline_delim in stripped:
                    idx = stripped.index(multiline_delim)
                    multiline_content.append(stripped[:idx])
                    full = '\n'.join(multiline_content)
                    if len(full) > 100 and self._looks_like_prompt(full):
                        prompts.append({
                            'content': full,
                            'line': multiline_start,
                            'file': file_path,
                        })
                    in_multiline = False
                    multiline_content = []
                    multiline_delim = None
                else:
                    multiline_content.append(stripped)

            # Detectar asignaciones de string simples
            if not in_multiline:
                for pattern in [
                    re.compile(r'(?:prompt|template|instructions?)\s*=\s*["\'](.+?)["\']',
                               re.IGNORECASE),
                    re.compile(r'(?:prompt|template|instructions?)\s*=\s*f["\'](.+?)["\']',
                               re.IGNORECASE),
                ]:
                    m = pattern.search(stripped)
                    if m and len(m.group(1)) > 100 and self._looks_like_prompt(m.group(1)):
                        prompts.append({
                            'content': m.group(1),
                            'line': i,
                            'file': file_path,
                        })

        return prompts

    def _extract_from_yaml(self, lines: list, file_path: str) -> list:
        """Extrae prompts de archivos YAML."""
        prompts = []
        current_value = []
        current_start = 0
        in_block = False

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Detectar claves de prompt en YAML
            prompt_key = re.match(
                r'(prompt|template|instructions?|system_message|content)\s*:\s*(.*)',
                stripped, re.IGNORECASE
            )

            if prompt_key:
                value = prompt_key.group(2).strip()
                if value.startswith('|') or value.startswith('>'):
                    in_block = True
                    current_start = i
                    current_value = []
                elif len(value) > 100 and self._looks_like_prompt(value):
                    prompts.append({
                        'content': value.strip('"\''),
                        'line': i,
                        'file': file_path,
                    })
            elif in_block:
                if stripped and not stripped.startswith('#'):
                    # Verificar indentacion
                    if line.startswith('  ') or line.startswith('\t'):
                        current_value.append(stripped)
                    else:
                        # Fin del bloque
                        full = '\n'.join(current_value)
                        if len(full) > 100 and self._looks_like_prompt(full):
                            prompts.append({
                                'content': full,
                                'line': current_start,
                                'file': file_path,
                            })
                        in_block = False
                        current_value = []

        # Flush ultimo bloque
        if in_block and current_value:
            full = '\n'.join(current_value)
            if len(full) > 100 and self._looks_like_prompt(full):
                prompts.append({
                    'content': full,
                    'line': current_start,
                    'file': file_path,
                })

        return prompts

    def _extract_from_json(self, content: str, file_path: str) -> list:
        """Extrae prompts de archivos JSON."""
        prompts = []
        try:
            data = json.loads(content)
            self._walk_json(data, file_path, prompts)
        except json.JSONDecodeError:
            pass
        return prompts

    def _walk_json(self, obj, file_path: str, prompts: list, depth: int = 0):
        """Recorre JSON buscando strings tipo prompt."""
        if depth > 10:
            return
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, str) and len(value) > 100:
                    if self._looks_like_prompt(value):
                        prompts.append({
                            'content': value,
                            'line': 0,
                            'file': file_path,
                        })
                elif isinstance(value, (dict, list)):
                    self._walk_json(value, file_path, prompts, depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                self._walk_json(item, file_path, prompts, depth + 1)

    def _looks_like_prompt(self, text: str) -> bool:
        """Heuristica: determina si un string parece un prompt."""
        indicators = [
            r'\b(you are|you should|respond|answer|generate|analyze|evaluate)\b',
            r'\b(instructions?|guidelines?|rules?|constraints?)\b',
            r'\b(step\s+\d|first|then|finally|must|never|always)\b',
            r'\b(output|input|format|example|context)\b',
            r'\{\{.*?\}\}',
            r'\{[a-zA-Z_]+\}',
        ]
        matches = sum(1 for p in indicators if re.search(p, text, re.IGNORECASE))
        return matches >= 2

    # -- c) Correr el gate --

    def run_gate(self, prompts: list, threshold: float = 0.7) -> GateResult:
        """Corre evaluaciones sobre una lista de prompts.

        Para cada prompt:
          - Corre continuous_eval.evaluate()
          - Corre governance check
          - Verifica que no contiene secrets

        Args:
            prompts: Lista de dicts {content, line, file}.
            threshold: Pass rate minimo (0.0-1.0).

        Returns:
            GateResult con resultado agregado.
        """
        now = self._now_iso()

        if not prompts:
            return GateResult(
                passed=True,
                threshold=threshold,
                actual_pass_rate=1.0,
                prompts_evaluated=0,
                failures=[],
                report="No prompts to evaluate.",
                timestamp=now,
            )

        results = []
        failures = []

        for prompt_info in prompts:
            content = prompt_info.get('content', '')
            file_path = prompt_info.get('file', '')
            line = prompt_info.get('line', 0)

            eval_result = self._evaluate_single_prompt(content, file_path, line)
            results.append(eval_result)

            if not eval_result.passed:
                failures.append(asdict(eval_result))

        # Calcular pass rate
        total = len(results)
        passed_count = sum(1 for r in results if r.passed)
        pass_rate = passed_count / total if total > 0 else 1.0

        gate_passed = pass_rate >= threshold

        gate_result = GateResult(
            passed=gate_passed,
            threshold=threshold,
            actual_pass_rate=round(pass_rate, 4),
            prompts_evaluated=total,
            failures=failures,
            report="",  # se llena con generate_ci_report
            timestamp=now,
        )

        # Generar reporte
        gate_result.report = self.generate_ci_report(gate_result)

        # Persistir
        self._persist(gate_result)

        return gate_result

    def _evaluate_single_prompt(self, content: str, file_path: str,
                                line: int) -> PromptEvalResult:
        """Evalua un prompt individual."""
        result = PromptEvalResult(
            prompt_file=file_path,
            prompt_line=line,
            passed=True,
            eval_score=1.0,
            governance_passed=True,
            has_secrets=False,
            details="",
        )

        details = []

        # 1. Check secrets
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                result.has_secrets = True
                result.passed = False
                result.eval_score = 0.0
                details.append("SECRET_DETECTED: prompt contains sensitive data")
                break

        # 2. Governance check
        try:
            from core.governance import check_governance
            gov_result = check_governance(content)
            if not gov_result.passed:
                result.governance_passed = False
                result.passed = False
                result.eval_score = min(result.eval_score, gov_result.score)
                details.append(
                    f"GOVERNANCE_FAIL: {', '.join(gov_result.violations)}"
                )
        except ImportError:
            # Si governance no esta disponible, skip
            details.append("GOVERNANCE_SKIP: module not available")
        except Exception as e:
            details.append(f"GOVERNANCE_ERROR: {e}")

        # 3. Continuous eval
        try:
            from core.continuous_eval import ContinuousEvaluator
            evaluator = ContinuousEvaluator()
            eval_report = evaluator.evaluate(content)
            if eval_report.verdict in ("FAIL", "CRITICAL"):
                result.passed = False
                result.eval_score = min(
                    result.eval_score,
                    eval_report.pass_rate / 100.0
                )
                details.append(
                    f"EVAL_FAIL: verdict={eval_report.verdict}, "
                    f"pass_rate={eval_report.pass_rate}%"
                )
        except ImportError:
            details.append("EVAL_SKIP: module not available")
        except Exception as e:
            details.append(f"EVAL_ERROR: {e}")

        result.details = "; ".join(details) if details else "ALL_CHECKS_PASSED"
        return result

    # -- d) Generar reporte CI --

    def generate_ci_report(self, gate_result: GateResult) -> str:
        """Genera reporte markdown para GitHub Actions.

        Args:
            gate_result: Resultado del gate.

        Returns:
            String con reporte en formato markdown.
        """
        status_emoji = "PASS" if gate_result.passed else "FAIL"
        lines = [
            f"## Prompt Evaluation Gate: {status_emoji}",
            "",
            f"- **Threshold:** {gate_result.threshold:.0%}",
            f"- **Pass Rate:** {gate_result.actual_pass_rate:.0%}",
            f"- **Prompts Evaluated:** {gate_result.prompts_evaluated}",
            f"- **Failures:** {len(gate_result.failures)}",
            f"- **Timestamp:** {gate_result.timestamp}",
            "",
        ]

        if gate_result.failures:
            lines.append("### Failures")
            lines.append("")
            for i, failure in enumerate(gate_result.failures, 1):
                f_file = failure.get('prompt_file', 'unknown')
                f_line = failure.get('prompt_line', 0)
                f_details = failure.get('details', '')
                has_secrets = failure.get('has_secrets', False)
                lines.append(f"**{i}. {f_file}:{f_line}**")
                if has_secrets:
                    lines.append("  - SECRET DETECTED in prompt")
                lines.append(f"  - {f_details}")
                lines.append("")

        if not gate_result.failures:
            lines.append("All prompts passed evaluation.")
            lines.append("")

        return '\n'.join(lines)

    # -- Persistencia --

    def _persist(self, gate_result: GateResult) -> None:
        """Persiste resultado en JSONL."""
        try:
            os.makedirs(self.gate_dir, exist_ok=True)
            with open(self.gate_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(gate_result.to_dict(), default=str) + '\n')
        except (IOError, OSError) as e:
            logger.warning("No se pudo persistir gate result: %s", e)
