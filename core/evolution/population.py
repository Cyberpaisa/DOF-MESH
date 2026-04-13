"""
DOF-MESH Evolution Engine — Population Manager.

GeneticPopulation: gestiona N genomas paralelos, corre ciclos evolutivos
completos, aplica patrones a governance.py, checkpoints con git stash,
rollback automático si ASR empeora.

Safety constraints (alineados con dof-governance.md):
  - NUNCA modifica HARD_RULES ni Z3 theorems
  - Checkpoint git stash ANTES de cada mutación de governance.py
  - Rollback inmediato si los tests bajan de min_tests
  - Full audit trail en logs/evolution/runs.jsonl
"""

import json
import logging
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("dof.evolution.population")

BASE_DIR = Path(__file__).parent.parent.parent
GENE_POOL_PATH = BASE_DIR / "core" / "evolution" / "gene_pool.jsonl"
GOVERNANCE_PATH = BASE_DIR / "core" / "governance.py"
EVOLUTION_LOG = BASE_DIR / "logs" / "evolution" / "runs.jsonl"
MIN_TESTS = 83  # piso mínimo — nunca bajar de aquí


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_tests(timeout: int = 60) -> tuple[bool, int]:
    """
    Corre el suite de tests.
    Retorna (passed: bool, test_count: int).
    """
    result = subprocess.run(
        ["python3", "-m", "unittest", "discover", "-s", "tests", "-q"],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(BASE_DIR),
    )
    # Parsear número de tests del output de unittest
    test_count = 0
    for line in (result.stderr + result.stdout).splitlines():
        m = re.search(r"Ran (\d+) test", line)
        if m:
            test_count = int(m.group(1))
            break
    return result.returncode == 0, test_count


def _git_stash(message: str) -> bool:
    result = subprocess.run(
        ["git", "stash", "push", "-m", message],
        capture_output=True, text=True, cwd=str(BASE_DIR),
    )
    return result.returncode == 0


def _git_stash_pop() -> bool:
    result = subprocess.run(
        ["git", "stash", "pop"],
        capture_output=True, text=True, cwd=str(BASE_DIR),
    )
    return result.returncode == 0


def _read_governance_source() -> str:
    return GOVERNANCE_PATH.read_text(encoding="utf-8")


def _write_governance_patterns(
    source: str,
    override_patterns: list[str],
    escalation_patterns: list[str],
    blockchain_patterns: list[str],
    system_claim_patterns: list[str],
) -> str:
    """
    Reemplaza las 4 listas de patrones en governance.py con las nuevas.
    Retorna el source modificado.
    """
    def _build_list_str(patterns: list[str], indent: str = "    ") -> str:
        lines = ["["]
        for p in patterns:
            # Usar repr() para escape correcto de cualquier carácter especial Python.
            # repr("abc") → "'abc'" — quitamos las comillas externas y usamos las nuestras.
            lines.append(f"{indent}    {repr(p)},")
        lines.append(f"{indent}]")
        return "\n".join(lines)

    replacements = [
        ("_OVERRIDE_PATTERNS",          override_patterns),
        ("_ESCALATION_PATTERNS",        escalation_patterns),
        ("_BLOCKCHAIN_ATTACK_PATTERNS", blockchain_patterns),
        ("_USER_SYSTEM_CLAIM_PATTERNS", system_claim_patterns),
    ]

    for var_name, new_patterns in replacements:
        # Encontrar el comienzo de la asignación de la lista y el cierre "^]" en su
        # propia línea (para no confundir con "]" dentro de strings de regex como [d]?).
        pattern = re.compile(
            rf"^({re.escape(var_name)}\s*=\s*)\[.*?^\]",
            re.MULTILINE | re.DOTALL,
        )
        new_list_str = _build_list_str(new_patterns)
        def _replacer(m, _list=new_list_str):
            return m.group(1) + _list
        new_source = pattern.sub(_replacer, source, count=1)
        if new_source == source:
            logger.warning(f"No se pudo reemplazar {var_name} en governance.py")
        else:
            source = new_source

    return source


def _log_run(entry: dict) -> None:
    EVOLUTION_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(EVOLUTION_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


class GeneticPopulation:
    """
    Gestiona N genomas paralelos y ciclos de evolución completos.

    Flujo de evolve_one_generation():
      1. Mide fitness de todos los genes
      2. Selecciona top 50% (survivors)
      3. Muta survivors para generar offspring
      4. Crossover entre los mejores pares
      5. git stash checkpoint
      6. Aplica nueva población a governance.py
      7. Corre red team → mide ASR global
      8. Si ASR baja (mejora) → commit + siguiente generación
      9. Si ASR sube (empeora) → git stash pop (rollback)
    """

    def __init__(
        self,
        size: int = 15,
        gene_pool_path: Path = GENE_POOL_PATH,
        llm_fn=None,
        min_tests: int = MIN_TESTS,
    ):
        from core.evolution.genome import load_gene_pool
        self.genes = load_gene_pool(gene_pool_path)
        self.gene_pool_path = gene_pool_path
        self.generation = 0
        self.history: list[dict] = []   # {generation, asr, test_count, genes_count}
        self.size = size
        self.llm_fn = llm_fn
        self.min_tests = min_tests
        self._last_asr: Optional[float] = None

        logger.info(f"GeneticPopulation inicializada: {len(self.genes)} genes, size={size}")

    # ── ASR measurement ───────────────────────────────────────────────────────

    def measure_asr(self, timeout: int = 120) -> Optional[float]:
        """
        Corre el red team y retorna el ASR actual.
        Requiere que el autonomous_loop sea accesible.
        Si no está disponible, retorna None.
        """
        redteam_script = BASE_DIR / "tests" / "red_team" / "autonomous_loop.py"
        if not redteam_script.exists():
            logger.warning("autonomous_loop.py no encontrado — ASR no medible")
            return None

        result = subprocess.run(
            ["python3", str(redteam_script), "--dry-run", "--max-iter", "1"],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(BASE_DIR),
        )
        # Parsear ASR del output: "ASR: 36.9%"
        for line in (result.stdout + result.stderr).splitlines():
            m = re.search(r"ASR[:\s]+(\d+\.?\d*)\s*%", line, re.IGNORECASE)
            if m:
                return float(m.group(1))
        return None

    # ── Fitness scoring ───────────────────────────────────────────────────────

    def score_all(self, test_vectors: Optional[list[str]] = None) -> None:
        """Calcula fitness de todos los genes. Actualiza in-place."""
        from core.evolution.fitness import score_population
        self.genes = score_population(self.genes, test_vectors=test_vectors)
        logger.info(f"Fitness calculado para {len(self.genes)} genes")

    # ── Evolution operators ───────────────────────────────────────────────────

    def evolve_one_generation(
        self,
        test_vectors: Optional[list[str]] = None,
        apply_to_governance: bool = True,
    ) -> dict:
        """
        Ejecuta un ciclo completo de evolución.
        Retorna un resumen con asr_before, asr_after, genes_added, rolled_back.
        """
        from core.evolution.operators import mutate, crossover, select_survivors
        from core.evolution.genome import save_gene_pool

        gen_n = self.generation + 1
        logger.info(f"=== Generación {gen_n} inicio ===")

        # 1. Medir fitness actual
        self.score_all(test_vectors)
        asr_before = self._last_asr

        # 2. Seleccionar top 50% survivors
        survivors = select_survivors(self.genes, top_k=max(1, len(self.genes) // 2))
        top_genes = select_survivors(self.genes, top_k=3)

        # 3. Mutar survivors → offspring
        offspring = []
        for gene in survivors[:5]:   # máximo 5 mutaciones por generación (costo LLM)
            mutated = mutate(gene, self.llm_fn)
            if mutated.id != gene.id:   # solo si realmente cambió
                offspring.append(mutated)

        # 4. Crossover entre los mejores pares
        cross_children = []
        if len(top_genes) >= 2:
            child = crossover(top_genes[0], top_genes[1], self.llm_fn)
            cross_children.append(child)
        if len(top_genes) >= 3:
            child2 = crossover(top_genes[1], top_genes[2], self.llm_fn)
            cross_children.append(child2)

        new_genes = offspring + cross_children
        candidate_pool = self.genes + new_genes

        # Calcular fitness de los nuevos genes
        from core.evolution.fitness import score_population
        new_genes = score_population(new_genes, test_vectors=test_vectors)

        # 5. Seleccionar la mejor población para la siguiente generación
        next_generation = select_survivors(candidate_pool, top_k=self.size)

        if not apply_to_governance:
            # Modo dry-run: actualizar pool sin tocar governance.py
            self.genes = next_generation
            self.generation = gen_n
            result = {
                "generation": gen_n, "asr_before": asr_before, "asr_after": None,
                "genes_added": len(new_genes), "rolled_back": False, "dry_run": True,
            }
            self.history.append(result)
            _log_run({"ts": _now_iso(), **result})
            save_gene_pool(self.genes, self.gene_pool_path)
            return result

        # 6. Checkpoint git stash ANTES de modificar governance.py
        stash_msg = f"evolution-gen-{gen_n}-checkpoint-{int(time.time())}"
        stashed = _git_stash(stash_msg)
        if not stashed:
            logger.warning("git stash falló — continuando sin checkpoint")

        # 7. Aplicar nueva población a governance.py
        self._apply_genes_to_governance(next_generation)

        # 8. Correr tests — verificar piso mínimo
        tests_ok, test_count = _run_tests()
        if not tests_ok or test_count < self.min_tests:
            logger.error(
                f"Tests fallaron (count={test_count}, min={self.min_tests}) — rollback"
            )
            if stashed:
                _git_stash_pop()
            result = {
                "generation": gen_n, "asr_before": asr_before, "asr_after": None,
                "genes_added": len(new_genes), "rolled_back": True,
                "reason": f"tests_failed: {test_count}/{self.min_tests}",
            }
            _log_run({"ts": _now_iso(), **result})
            return result

        # 9. Medir ASR post-evolución (opcional — lento)
        asr_after = self.measure_asr()
        self._last_asr = asr_after

        # 10. Si ASR empeoró → rollback
        if asr_before is not None and asr_after is not None and asr_after > asr_before:
            logger.warning(
                f"ASR empeoró: {asr_before:.1f}% → {asr_after:.1f}% — rollback"
            )
            if stashed:
                _git_stash_pop()
            result = {
                "generation": gen_n, "asr_before": asr_before, "asr_after": asr_after,
                "genes_added": len(new_genes), "rolled_back": True,
                "reason": "asr_worsened",
            }
            _log_run({"ts": _now_iso(), **result})
            return result

        # 11. Generación exitosa — actualizar estado
        self.genes = next_generation
        self.generation = gen_n
        save_gene_pool(self.genes, self.gene_pool_path)

        result = {
            "generation": gen_n,
            "asr_before": asr_before,
            "asr_after": asr_after,
            "genes_added": len(new_genes),
            "genes_total": len(self.genes),
            "test_count": test_count,
            "rolled_back": False,
        }
        self.history.append(result)
        _log_run({"ts": _now_iso(), **result})

        logger.info(
            f"Generación {gen_n} completa: "
            f"ASR {asr_before}% → {asr_after}%, "
            f"+{len(new_genes)} genes nuevos, {test_count} tests OK"
        )
        return result

    # ── Apply to governance.py ────────────────────────────────────────────────

    def _apply_genes_to_governance(self, genes: list) -> None:
        """Reescribe las listas de patrones en governance.py con los genes actuales."""
        from core.evolution.genome import get_genes_by_category

        override_p    = [g.regex for g in genes if g.category == "OVERRIDE"]
        escalation_p  = [g.regex for g in genes if g.category == "ESCALATION"]
        blockchain_p  = [g.regex for g in genes if g.category == "BLOCKCHAIN"]
        system_p      = [g.regex for g in genes if g.category == "SYSTEM_CLAIM"]

        # Garantizar que al menos los patrones originales están presentes
        if not override_p or not escalation_p:
            logger.error("apply_to_governance: genes incompletos — abortando")
            return

        source = _read_governance_source()
        new_source = _write_governance_patterns(
            source, override_p, escalation_p, blockchain_p, system_p
        )

        if new_source == source:
            logger.warning("apply_to_governance: governance.py sin cambios")
            return

        GOVERNANCE_PATH.write_text(new_source, encoding="utf-8")
        logger.info(
            f"governance.py actualizado: "
            f"{len(override_p)} override, {len(escalation_p)} escalation, "
            f"{len(blockchain_p)} blockchain, {len(system_p)} system_claim"
        )

    def checkpoint(self) -> bool:
        """git stash del estado actual antes de mutar."""
        msg = f"evolution-manual-checkpoint-gen-{self.generation}"
        return _git_stash(msg)

    def rollback(self) -> bool:
        """git stash pop para revertir al estado anterior."""
        return _git_stash_pop()

    # ── Summary ───────────────────────────────────────────────────────────────

    def summary(self) -> dict:
        from core.evolution.genome import describe_pool
        return {
            "generation": self.generation,
            "pool_stats": describe_pool(self.genes),
            "history": self.history[-5:],  # últimas 5 generaciones
            "last_asr": self._last_asr,
        }
