"""
DOF-MESH Evolution Engine — Genome Layer.

PatternGene: un patrón de governance como gen evolutivo.
Cada gen tiene id, regex, categoría, generación, fitness y trazabilidad completa.

Storage: core/evolution/gene_pool.jsonl (un gen por línea)
"""

import json
import os
import re
import uuid
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("dof.evolution.genome")

BASE_DIR = Path(__file__).parent.parent.parent
GENE_POOL_PATH = BASE_DIR / "core" / "evolution" / "gene_pool.jsonl"

# Categorías válidas — alineadas con las listas de governance.py
VALID_CATEGORIES = {"OVERRIDE", "ESCALATION", "BLOCKCHAIN", "SYSTEM_CLAIM"}


@dataclass
class PatternGene:
    """Un patrón de governance como gen evolutivo."""
    id: str                          # CVE-DOF-011-p001
    regex: str                       # el patrón actual
    category: str                    # OVERRIDE | BLOCKCHAIN | ESCALATION | SYSTEM_CLAIM
    generation: int                  # 0 = original, 1+ = evolucionado
    parent_id: Optional[str]         # id del gen padre (None si original)
    fitness_score: float             # 0.0 → 1.0
    false_positive_rate: float       # 0.0 = perfecto, 1.0 = bloquea todo
    vectors_blocked: list            # qué IDs de vectores bloquea
    created_at: str
    fitness_history: list            # historial de fitness por sesión
    cve_origin: Optional[str] = None # CVE-DOF-011, etc.
    notes: str = ""                  # descripción legible del ataque

    def __post_init__(self):
        if self.category not in VALID_CATEGORIES:
            raise ValueError(f"Categoría inválida: {self.category}. Válidas: {VALID_CATEGORIES}")
        # Validar que el regex compile
        try:
            re.compile(self.regex)
        except re.error as e:
            raise ValueError(f"Regex inválido en gen {self.id}: {e}")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "PatternGene":
        return cls(
            id=d["id"],
            regex=d["regex"],
            category=d["category"],
            generation=d["generation"],
            parent_id=d.get("parent_id"),
            fitness_score=d.get("fitness_score", 0.0),
            false_positive_rate=d.get("false_positive_rate", 0.0),
            vectors_blocked=d.get("vectors_blocked", []),
            created_at=d.get("created_at", datetime.now(timezone.utc).isoformat()),
            fitness_history=d.get("fitness_history", []),
            cve_origin=d.get("cve_origin"),
            notes=d.get("notes", ""),
        )

    def is_valid(self) -> bool:
        """Verifica que el regex compila y la categoría es válida."""
        try:
            re.compile(self.regex)
            return self.category in VALID_CATEGORIES
        except re.error:
            return False


def _make_gene_id(category: str, index: int, cve: Optional[str] = None) -> str:
    prefix = cve if cve else f"ORIGIN-{category}"
    return f"{prefix}-p{index:03d}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def migrate_from_governance() -> list[PatternGene]:
    """
    Lee los patrones actuales de governance.py y los convierte a PatternGene.
    Genera el gene_pool inicial (generación 0).
    NO modifica governance.py.
    """
    import sys
    sys.path.insert(0, str(BASE_DIR))
    import core.governance as gov

    genes: list[PatternGene] = []

    # Mapa: lista_nombre → (categoría, CVE origen)
    sources = [
        ("_OVERRIDE_PATTERNS",           "OVERRIDE",     "CVE-DOF-001"),
        ("_ESCALATION_PATTERNS",         "ESCALATION",   "CVE-DOF-005"),
        ("_BLOCKCHAIN_ATTACK_PATTERNS",  "BLOCKCHAIN",   "CVE-DOF-011"),
        ("_USER_SYSTEM_CLAIM_PATTERNS",  "SYSTEM_CLAIM", "CVE-DOF-004"),
    ]

    for attr_name, category, cve in sources:
        patterns = getattr(gov, attr_name, [])
        # _OVERRIDE_PATTERNS y _ESCALATION_PATTERNS pueden contener listas o strings
        for i, regex in enumerate(patterns, start=1):
            if not isinstance(regex, str):
                continue
            gene_id = _make_gene_id(cve, i, cve)
            gene = PatternGene(
                id=gene_id,
                regex=regex,
                category=category,
                generation=0,
                parent_id=None,
                fitness_score=0.0,   # se calcula en Fase 2
                false_positive_rate=0.0,
                vectors_blocked=[],
                created_at=_now_iso(),
                fitness_history=[],
                cve_origin=cve,
                notes=f"Migrado desde governance.py:{attr_name} — índice {i}",
            )
            genes.append(gene)

    logger.info(f"Migración completa: {len(genes)} genes extraídos de governance.py")
    return genes


def save_gene_pool(genes: list[PatternGene], path: Path = GENE_POOL_PATH) -> None:
    """Guarda el gene pool en JSONL (un gen por línea)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for gene in genes:
            f.write(json.dumps(gene.to_dict(), ensure_ascii=False) + "\n")
    logger.info(f"Gene pool guardado: {len(genes)} genes → {path}")


def load_gene_pool(path: Path = GENE_POOL_PATH) -> list[PatternGene]:
    """Carga el gene pool desde JSONL."""
    if not path.exists():
        logger.warning(f"gene_pool.jsonl no existe en {path} — migrando desde governance.py")
        genes = migrate_from_governance()
        save_gene_pool(genes, path)
        return genes

    genes = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                gene = PatternGene.from_dict(d)
                genes.append(gene)
            except Exception as e:
                logger.warning(f"gen inválido en línea {lineno}: {e}")

    logger.info(f"Gene pool cargado: {len(genes)} genes desde {path}")
    return genes


def get_genes_by_category(genes: list[PatternGene], category: str) -> list[PatternGene]:
    return [g for g in genes if g.category == category]


def get_gene_by_id(genes: list[PatternGene], gene_id: str) -> Optional[PatternGene]:
    for g in genes:
        if g.id == gene_id:
            return g
    return None


def describe_pool(genes: list[PatternGene]) -> dict:
    """Estadísticas del gene pool."""
    by_cat: dict[str, int] = {}
    by_gen: dict[int, int] = {}
    for g in genes:
        by_cat[g.category] = by_cat.get(g.category, 0) + 1
        by_gen[g.generation] = by_gen.get(g.generation, 0) + 1
    return {
        "total": len(genes),
        "by_category": by_cat,
        "by_generation": by_gen,
        "avg_fitness": round(sum(g.fitness_score for g in genes) / max(len(genes), 1), 4),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    genes = migrate_from_governance()
    save_gene_pool(genes)
    print(describe_pool(genes))
