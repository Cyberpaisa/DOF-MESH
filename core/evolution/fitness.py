"""
DOF-MESH Evolution Engine — Fitness Function.

fitness(gene) → float ∈ [0, 1]

Composición:
  40% cobertura:   % de vectores red team que el gen bloquea
  30% precisión:   1 - false_positive_rate
  30% estabilidad: tests del sistema pasan con este gen activo

El módulo es zero-LLM: todo determinístico (regex + subprocess).
"""

import re
import subprocess
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("dof.evolution.fitness")

BASE_DIR = Path(__file__).parent.parent.parent
TESTS_CMD = ["python3", "-m", "unittest", "discover", "-s", "tests", "-q"]

# Textos benigno de referencia para medir false positives
_BENIGN_SAMPLES = [
    "Please help me write a Python function that reads a CSV file.",
    "How do I deploy a smart contract on Ethereum?",
    "Explain the concept of reentrancy in Solidity.",
    "What is the difference between msg.sender and tx.origin?",
    "Generate a unit test for my governance module.",
    "My company needs an audit report for the Q1 financials.",
    "The contract owner needs to approve this transaction.",
    "I am a researcher studying blockchain security patterns.",
    "Can you review my code for any bugs?",
    "What are best practices for storing API keys securely?",
    "Write documentation for my Python module.",
    "Explain how flash loans work in DeFi protocols.",
    "How can I improve the performance of my smart contract?",
    "Generate a report on the security of our AI system.",
    "I need help with my thesis on blockchain governance.",
    "What is the governance structure of the DOF framework?",
    "Help me understand the SYSTEM architecture of this service.",
    "The developer approved the new configuration yesterday.",
    "Our security team has reviewed the protocol and found no issues.",
    "Please summarize the technical documentation for our engineers.",
]


def _gene_matches(gene_regex: str, text: str) -> bool:
    """Aplica el regex del gen (normalizado) contra un texto."""
    try:
        return bool(re.search(gene_regex, text, re.IGNORECASE | re.DOTALL))
    except re.error:
        return False


def measure_coverage(gene_regex: str, test_vectors: list[str]) -> float:
    """
    Mide qué fracción de test_vectors bloquea el gen.
    test_vectors son strings que DEBEN ser bloqueados.
    Retorna 0.0–1.0.
    """
    if not test_vectors:
        return 0.0
    blocked = sum(1 for v in test_vectors if _gene_matches(gene_regex, v))
    return blocked / len(test_vectors)


def measure_false_positive_rate(gene_regex: str, benign_samples: Optional[list[str]] = None) -> float:
    """
    Mide qué fracción de textos benignos bloquea el gen (falsos positivos).
    Retorna 0.0–1.0. Menor = mejor.
    """
    samples = benign_samples or _BENIGN_SAMPLES
    if not samples:
        return 0.0
    false_positives = sum(1 for s in samples if _gene_matches(gene_regex, s))
    return false_positives / len(samples)


def measure_stability(timeout: int = 30) -> bool:
    """
    Corre el suite de tests del sistema.
    Retorna True si todos pasan, False si alguno falla.
    Timeout en segundos para evitar loops infinitos.
    """
    try:
        result = subprocess.run(
            TESTS_CMD,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(BASE_DIR),
        )
        passed = result.returncode == 0
        if not passed:
            logger.warning(f"Tests fallaron: {result.stderr[-300:]}")
        return passed
    except subprocess.TimeoutExpired:
        logger.warning(f"Tests timeout ({timeout}s)")
        return False
    except Exception as e:
        logger.error(f"Error corriendo tests: {e}")
        return False


def compute_fitness(
    gene_regex: str,
    test_vectors: Optional[list[str]] = None,
    benign_samples: Optional[list[str]] = None,
    run_tests: bool = False,
) -> dict:
    """
    Calcula el fitness completo de un patrón.

    Args:
        gene_regex:     El regex a evaluar.
        test_vectors:   Strings que el gen debe bloquear (red team payloads).
        benign_samples: Strings benignos para medir FPR.
        run_tests:      Si True, corre el suite completo (lento, ~30s).

    Returns:
        {
            "fitness": float,       # score final 0.0–1.0
            "coverage": float,      # componente cobertura
            "precision": float,     # componente precisión (1-FPR)
            "stability": float,     # componente estabilidad
            "fpr": float,           # false positive rate raw
            "vectors_blocked": int, # cuántos vectores bloquea
        }
    """
    # Componente 1 — cobertura (40%)
    vectors = test_vectors or []
    coverage = measure_coverage(gene_regex, vectors) if vectors else 0.5  # neutral si no hay vectores

    # Componente 2 — precisión (30%)
    fpr = measure_false_positive_rate(gene_regex, benign_samples)
    precision = 1.0 - fpr

    # Componente 3 — estabilidad (30%)
    if run_tests:
        stable = measure_stability()
        stability = 1.0 if stable else 0.0
    else:
        stability = 1.0  # optimista por defecto, validar en population manager

    # Score final ponderado
    fitness = round(
        0.40 * coverage +
        0.30 * precision +
        0.30 * stability,
        4,
    )

    vectors_blocked = sum(1 for v in vectors if _gene_matches(gene_regex, v))

    return {
        "fitness": fitness,
        "coverage": round(coverage, 4),
        "precision": round(precision, 4),
        "stability": stability,
        "fpr": round(fpr, 4),
        "vectors_blocked": vectors_blocked,
    }


def score_population(
    genes: list,
    test_vectors: Optional[list[str]] = None,
    benign_samples: Optional[list[str]] = None,
) -> list:
    """
    Calcula el fitness de todos los genes de la población.
    Actualiza gene.fitness_score y gene.false_positive_rate in-place.
    Retorna los genes ordenados por fitness descendente.
    """
    from core.evolution.genome import PatternGene

    for gene in genes:
        result = compute_fitness(
            gene.regex,
            test_vectors=test_vectors,
            benign_samples=benign_samples,
            run_tests=False,
        )
        gene.fitness_score = result["fitness"]
        gene.false_positive_rate = result["fpr"]
        gene.vectors_blocked = [
            f"v{i:03d}" for i, v in enumerate(test_vectors or [])
            if _gene_matches(gene.regex, v)
        ]
        gene.fitness_history.append(result["fitness"])

    return sorted(genes, key=lambda g: g.fitness_score, reverse=True)
