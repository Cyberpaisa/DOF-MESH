"""
feynman_crew.py — Feynman Research Crew
Explica conceptos complejos desde primeros principios.
Método: Concept → Simplify → Identify Gaps → Synthesize

Filosofía Feynman:
    "Si no puedes explicarlo simple, no lo entiendes."
    Toma un tema complejo y produce una explicación desde cero.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("dof.feynman_crew")

# ── Log dir ──────────────────────────────────────────────────────────────────
_LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "feynman"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_SESSIONS_LOG = _LOG_DIR / "sessions.jsonl"

# ── Keywords por dominio para extracción determinística ───────────────────────
_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "formal_verification": [
        "z3", "smt", "theorem", "proof", "invariant", "constraint",
        "satisfiability", "formal", "verification", "logic", "predicate",
    ],
    "blockchain": [
        "chain", "contract", "transaction", "gas", "wallet", "block",
        "consensus", "attestation", "on-chain", "evm", "solidity",
    ],
    "machine_learning": [
        "model", "training", "inference", "embedding", "token", "llm",
        "neural", "gradient", "loss", "dataset", "fine-tuning",
    ],
    "multi_agent": [
        "agent", "crew", "task", "tool", "orchestrat", "governance",
        "supervisor", "mesh", "provider", "delegation",
    ],
    "security": [
        "encryption", "key", "hash", "signature", "vulnerability",
        "exploit", "injection", "adversarial", "red-team",
    ],
    "software_architecture": [
        "module", "interface", "pattern", "dependency", "singleton",
        "layer", "pipeline", "abstraction", "coupling",
    ],
}

# Palabras genéricas que casi siempre son relevantes en cualquier concepto técnico
_GENERIC_IMPORTANT = {
    "how", "why", "what", "when", "where",
    "cómo", "qué", "por qué", "cuándo", "dónde",
}


# ── Dataclass de resultado ────────────────────────────────────────────────────

@dataclass
class FeynmanResult:
    """Resultado de una ejecución del FeynmanCrew."""
    topic: str
    explanation: str
    key_concepts: list[str] = field(default_factory=list)
    analogies: list[str] = field(default_factory=list)
    gaps_identified: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "explanation": self.explanation,
            "key_concepts": self.key_concepts,
            "analogies": self.analogies,
            "gaps_identified": self.gaps_identified,
            "confidence": self.confidence,
        }


def _empty_result(topic: str) -> FeynmanResult:
    """Resultado vacío cuando el flag está deshabilitado."""
    return FeynmanResult(
        topic=topic,
        explanation="",
        key_concepts=[],
        analogies=[],
        gaps_identified=[],
        confidence=0.0,
    )


# ── Crew principal ────────────────────────────────────────────────────────────

class FeynmanCrew:
    """
    Feynman Research Crew — explicación desde primeros principios.

    Usa 3 pasos determinísticos (sin LLM para la lógica de control):
        1. _extract_concepts   — regex/keywords sobre topic + context
        2. _build_explanation  — estructura la explicación en 4 secciones
        3. _assess_confidence  — score 0-1 basado en cobertura de conceptos

    Feature-flagged: si flags.is_enabled("feynman_research_crew") es False,
    run() retorna un FeynmanResult vacío sin ejecutar nada.
    """

    def __init__(self, llm_config: Optional[dict[str, Any]] = None) -> None:
        self.llm_config = llm_config or {}
        self._flags = self._load_flags()

    # ── Flag loader ───────────────────────────────────────────────────────────

    def _load_flags(self):
        """Carga el singleton de feature_flags de forma lazy (evita import circular)."""
        try:
            from core.feature_flags import flags  # noqa: PLC0415
            return flags
        except Exception as exc:
            logger.warning(f"FeynmanCrew: no pudo cargar feature_flags ({exc}) — asumiendo enabled=True")
            return None

    def _is_enabled(self) -> bool:
        if self._flags is None:
            return True
        return self._flags.is_enabled("feynman_research_crew", default=False)

    # ── Paso 1 — Extracción de conceptos ─────────────────────────────────────

    def _extract_concepts(self, topic: str, context: str = "") -> list[str]:
        """
        Extrae conceptos clave del topic y el contexto de forma determinística.

        Estrategia:
          - Tokeniza en palabras (lowercase, alfanumérico + guión)
          - Busca coincidencias con los dominios de _DOMAIN_KEYWORDS
          - Deduplica preservando orden de primera aparición
          - Limita a 10 conceptos máximo para claridad
        """
        combined = f"{topic} {context}".lower()
        # Tokenización simple: palabras y fragmentos con guión
        tokens = re.findall(r"[a-z0-9][a-z0-9\-]*[a-z0-9]|[a-z0-9]", combined)
        token_set = set(tokens)

        found: list[str] = []
        seen: set[str] = set()

        # Buscar por dominio (orden determinístico)
        for _domain, keywords in sorted(_DOMAIN_KEYWORDS.items()):
            for kw in keywords:
                if kw in token_set and kw not in seen:
                    found.append(kw)
                    seen.add(kw)

        # Si el topic tiene términos compuestos significativos (2+ palabras), añadirlos
        topic_tokens = topic.strip().split()
        if len(topic_tokens) >= 2:
            phrase = " ".join(topic_tokens[:3]).lower()
            if phrase not in seen:
                found.insert(0, phrase)
                seen.add(phrase)

        return found[:10]

    # ── Paso 2 — Construcción de la explicación ───────────────────────────────

    def _build_explanation(self, topic: str, concepts: list[str]) -> tuple[str, list[str], list[str]]:
        """
        Estructura la explicación Feynman en 4 secciones.

        Retorna: (explanation: str, analogies: list[str], gaps: list[str])

        Las secciones siguen el método de los 4 pasos:
          1. Concepto en términos simples
          2. Analogía con algo cotidiano
          3. Identificación de brechas
          4. Síntesis refinada
        """
        concept_list = ", ".join(concepts) if concepts else "conceptos fundamentales"

        # ── Sección 1: Concepto simple ────────────────────────────────────────
        section_concept = (
            f"## Concepto: {topic}\n\n"
            f"En su forma más simple, **{topic}** trata sobre: {concept_list}.\n\n"
            f"Imagina que le explicas esto a alguien sin conocimiento técnico. "
            f"El núcleo del concepto es verificar que algo funciona como se espera "
            f"antes de que ocurra — no después."
        )

        # ── Sección 2: Analogías ──────────────────────────────────────────────
        analogies: list[str] = []
        analogy_text = "## Analogías\n\n"

        # Analogías determinísticas basadas en los conceptos encontrados
        analogy_map = {
            "proof": "Como un inspector de calidad que firma el certificado ANTES de que el producto salga de fábrica.",
            "invariant": "Como las reglas del ajedrez: siempre aplican, sin importar quién juega.",
            "constraint": "Como las paredes de un laberinto: definen dónde puedes ir, no dónde debes ir.",
            "agent": "Como un empleado con su propio manual de instrucciones que sigue sin supervisión constante.",
            "governance": "Como la constitución de un país: define lo que está permitido antes de que alguien lo intente.",
            "contract": "Como un contrato legal: especifica exactamente qué debe ocurrir y qué no.",
            "token": "Como fichas de casino: representan valor pero solo dentro del sistema que las reconoce.",
            "model": "Como un mapa: no es el territorio, pero te permite navegar el territorio.",
            "layer": "Como las capas de una cebolla: cada una protege o enriquece la siguiente.",
            "pipeline": "Como una línea de ensamblaje: cada estación hace una sola cosa, bien hecha.",
        }

        for concept in concepts[:4]:  # máximo 4 analogías
            for key, analogy in analogy_map.items():
                if key in concept and analogy not in analogies:
                    analogies.append(analogy)
                    analogy_text += f"- **{concept}**: {analogy}\n"
                    break

        if not analogies:
            default_analogy = f"**{topic}** es como construir un puente: primero calculas la carga que debe soportar (especificación), luego verificas cada componente (tests), y solo entonces lo abres al tráfico (producción)."
            analogies.append(default_analogy)
            analogy_text += f"- {default_analogy}\n"

        # ── Sección 3: Brechas ────────────────────────────────────────────────
        gaps: list[str] = []
        gap_text = "## Brechas de Comprensión\n\n"

        gap_patterns = [
            (["z3", "smt", "satisfiability"], "¿Cómo decide el solver si una fórmula es satisfacible en tiempo polinomial?"),
            (["proof", "theorem", "formal"], "¿Cuál es la diferencia entre verificación formal y testing exhaustivo?"),
            (["agent", "governance", "supervisor"], "¿Qué ocurre cuando dos capas de governance tienen reglas contradictorias?"),
            (["contract", "chain", "attestation"], "¿Cómo se garantiza la inmutabilidad si la VM subyacente tiene bugs?"),
            (["model", "llm", "inference"], "¿Cómo se mide la confiabilidad de un output sin ground truth?"),
            (["pipeline", "layer", "module"], "¿Cómo se maneja el estado compartido entre etapas del pipeline?"),
        ]

        for keywords, gap in gap_patterns:
            if any(kw in concepts for kw in keywords):
                gaps.append(gap)
                gap_text += f"- {gap}\n"

        if not gaps:
            generic_gap = f"¿Cuáles son los casos límite donde {topic} falla o se comporta de forma inesperada?"
            gaps.append(generic_gap)
            gap_text += f"- {generic_gap}\n"

        # ── Sección 4: Síntesis ───────────────────────────────────────────────
        section_synthesis = (
            f"\n## Síntesis\n\n"
            f"**{topic}** en una oración: un sistema que verifica matemáticamente "
            f"que los conceptos clave ({concept_list}) se comportan correctamente "
            f"— antes de que el error ocurra, no después.\n\n"
            f"Si puedes explicar esto sin usar el nombre del concepto, lo entiendes."
        )

        explanation = "\n\n".join([section_concept, analogy_text, gap_text, section_synthesis])

        return explanation, analogies, gaps

    # ── Paso 3 — Score de confianza ───────────────────────────────────────────

    def _assess_confidence(self, result: FeynmanResult) -> float:
        """
        Score 0.0-1.0 basado en cobertura de conceptos y calidad de la explicación.

        Criterios determinísticos:
          - 0.3 base si hay al menos 1 concepto
          - +0.1 por cada concepto adicional (hasta 0.6 total de este factor)
          - +0.2 si hay al menos 1 analogía
          - +0.1 si hay al menos 1 brecha identificada
          - +0.1 si la explicación tiene más de 200 caracteres
        """
        score = 0.0

        n_concepts = len(result.key_concepts)
        if n_concepts >= 1:
            score += 0.30
            score += min(0.30, (n_concepts - 1) * 0.06)  # +0.06 por concepto extra, max +0.30

        if result.analogies:
            score += 0.20

        if result.gaps_identified:
            score += 0.10

        if len(result.explanation) > 200:
            score += 0.10

        # Clampar a [0.0, 1.0]
        return round(min(1.0, max(0.0, score)), 4)

    # ── Log ───────────────────────────────────────────────────────────────────

    def _log_session(self, result: FeynmanResult, elapsed_ms: float) -> None:
        """Appends result to logs/feynman/sessions.jsonl."""
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "elapsed_ms": round(elapsed_ms, 2),
            **result.to_dict(),
        }
        try:
            with _SESSIONS_LOG.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning(f"FeynmanCrew: no pudo escribir log ({exc})")

    # ── Método principal ──────────────────────────────────────────────────────

    def run(self, topic: str, context: str = "") -> FeynmanResult:
        """
        Ejecuta el pipeline Feynman sobre el topic dado.

        Args:
            topic:   El concepto, módulo o paper a explicar.
            context: Texto adicional (código, documentación, abstract).

        Returns:
            FeynmanResult con explicación, conceptos, analogías, brechas y score.
        """
        t0 = time.perf_counter()

        # Feature flag gate — salida rápida si deshabilitado
        if not self._is_enabled():
            logger.info("FeynmanCrew: flag 'feynman_research_crew' deshabilitado — retornando vacío")
            return _empty_result(topic)

        try:
            # Paso 1 — Extracción de conceptos
            concepts = self._extract_concepts(topic, context)
            logger.debug(f"FeynmanCrew: {len(concepts)} conceptos extraídos de '{topic}'")

            # Paso 2 — Construcción de la explicación
            explanation, analogies, gaps = self._build_explanation(topic, concepts)

            # Ensamblado del resultado
            result = FeynmanResult(
                topic=topic,
                explanation=explanation,
                key_concepts=concepts,
                analogies=analogies,
                gaps_identified=gaps,
                confidence=0.0,  # se calcula en el paso 3
            )

            # Paso 3 — Score de confianza
            result.confidence = self._assess_confidence(result)

            elapsed_ms = (time.perf_counter() - t0) * 1000
            logger.info(
                f"FeynmanCrew: '{topic}' → {len(concepts)} conceptos, "
                f"conf={result.confidence:.2f}, {elapsed_ms:.1f}ms"
            )

        except Exception as exc:
            logger.error(f"FeynmanCrew: error inesperado en run('{topic}'): {exc}", exc_info=True)
            result = _empty_result(topic)
            result.gaps_identified = [f"Error durante el análisis: {exc}"]
            elapsed_ms = (time.perf_counter() - t0) * 1000

        self._log_session(result, elapsed_ms)
        return result
