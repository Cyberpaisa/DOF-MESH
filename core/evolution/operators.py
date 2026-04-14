"""
DOF-MESH Evolution Engine — Operadores Genéticos.

mutate(gene, llm_fn)   → PatternGene mejorado vía LLM
crossover(g1, g2)      → PatternGene combinado (alternancia regex)
select_survivors(pop)  → top_k genes por fitness, sin duplicados

El LLM solo se usa para mutar — NUNCA para decisiones de governance.
Todas las decisiones de selección y crossover son determinísticas.
"""

import re
import uuid
import logging
from datetime import datetime, timezone
from typing import Callable, Optional

logger = logging.getLogger("dof.evolution.operators")

# Similitud mínima para considerar dos patrones "duplicados"
_SIMILARITY_THRESHOLD = 0.85


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "EVOLVED") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _regex_similarity(r1: str, r2: str) -> float:
    """
    Similitud de Jaccard entre conjuntos de tokens del regex.
    Rápido, determinístico, sin LLM.
    """
    tokens1 = set(re.findall(r'\w+', r1.lower()))
    tokens2 = set(re.findall(r'\w+', r2.lower()))
    if not tokens1 and not tokens2:
        return 1.0
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    return len(intersection) / len(union)


def _is_valid_regex(pattern: str) -> bool:
    try:
        re.compile(pattern)
        return True
    except re.error:
        return False


def _call_llm(prompt: str, llm_fn: Optional[Callable] = None) -> Optional[str]:
    """
    Llama al LLM con el prompt dado.
    llm_fn: callable(prompt: str) → str. Si es None, usa DeepSeek directo via requests.
    """
    if llm_fn is not None:
        return llm_fn(prompt)

    # Fallback: DeepSeek API directo (gratuito, sin litellm)
    try:
        import os
        import requests as _req
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        if not api_key:
            from dotenv import load_dotenv
            load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
            api_key = os.getenv("DEEPSEEK_API_KEY", "")
        if not api_key:
            logger.warning("LLM call falló: DEEPSEEK_API_KEY no configurada")
            return None
        resp = _req.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.3,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"LLM call falló: {e}")
        return None


def mutate(gene, llm_fn: Optional[Callable] = None):
    """
    Genera una variante mejorada del gen usando LLM.

    El LLM recibe el regex actual y los vectores que debe bloquear,
    y devuelve un regex mejorado que captura más variantes sin aumentar FPR.

    Si el LLM falla o devuelve regex inválido → retorna el gen original sin cambios.
    """
    from core.evolution.genome import PatternGene

    prompt = f"""You are a regex optimization expert for AI security systems.

Current regex pattern (must NOT be changed structurally, only extended):
{gene.regex}

Category: {gene.category}
This pattern should block attack vectors like: {', '.join(gene.vectors_blocked[:5]) if gene.vectors_blocked else 'prompt injection attempts'}
Notes: {gene.notes}

Task: Improve this regex to capture MORE variants of this attack type WITHOUT increasing false positives.
- Keep the same semantic intent
- You may add alternatives with |
- You may loosen specific anchors if safe
- Do NOT make it a catch-all (avoid .*|.+ without context)
- The pattern must still compile as a Python regex

Return ONLY the improved regex string, nothing else. No explanation, no quotes, no markdown."""

    raw = _call_llm(prompt, llm_fn)
    if raw is None:
        logger.debug(f"mutate: LLM no disponible para gen {gene.id} — retornando original")
        return gene

    # Limpiar respuesta del LLM
    new_regex = raw.strip().strip('"\'`')
    # Remover bloques markdown si los hay
    if new_regex.startswith("```"):
        lines = new_regex.split("\n")
        new_regex = "\n".join(l for l in lines if not l.startswith("```")).strip()

    if not _is_valid_regex(new_regex):
        logger.warning(f"mutate: regex inválido del LLM para gen {gene.id}: {new_regex[:80]}")
        return gene

    # Si el LLM devolvió exactamente el mismo regex, no crear gen nuevo
    if new_regex == gene.regex:
        logger.debug(f"mutate: LLM no cambió el regex de gen {gene.id}")
        return gene

    mutated = PatternGene(
        id=_new_id(f"{gene.cve_origin or 'MUT'}"),
        regex=new_regex,
        category=gene.category,
        generation=gene.generation + 1,
        parent_id=gene.id,
        fitness_score=0.0,  # se evalúa después
        false_positive_rate=0.0,
        vectors_blocked=[],
        created_at=_now_iso(),
        fitness_history=[],
        cve_origin=gene.cve_origin,
        notes=f"Mutado desde {gene.id} (gen {gene.generation}) vía LLM",
    )
    logger.info(f"mutate: {gene.id} → {mutated.id}")
    return mutated


def _strip_inline_flags(pattern: str) -> tuple[str, str]:
    """
    Extrae flags inline del inicio del patrón: (?i), (?im), etc.
    Retorna (pattern_sin_flags, flags_string).
    Necesario para evitar 'global flags not at start' en Python 3.12+.
    """
    m = re.match(r'^\(\?([aiLmsux]+)\)', pattern)
    if m:
        return pattern[m.end():], m.group(1)
    return pattern, ""


def crossover(g1, g2, llm_fn: Optional[Callable] = None):
    """
    Combina dos genes en uno usando alternancia regex: (?flags)(?:r1)|(?:r2).

    Extrae los inline flags ((?i), (?im), etc.) y los eleva al nivel raíz
    para evitar el error de Python 3.12+ "global flags not at the start".
    Si el resultado es demasiado largo (>300 chars), pide al LLM que lo simplifique.
    """
    from core.evolution.genome import PatternGene

    # Extraer flags inline y combinar
    p1, f1 = _strip_inline_flags(g1.regex)
    p2, f2 = _strip_inline_flags(g2.regex)
    flags = "".join(sorted(set(f1 + f2)))
    flag_prefix = f"(?{flags})" if flags else ""
    combined = f"{flag_prefix}(?:{p1})|(?:{p2})"

    # Si es muy largo, intentar simplificación vía LLM
    if len(combined) > 300 and llm_fn is not None:
        prompt = f"""Simplify this Python regex into a shorter equivalent that matches the same patterns:

{combined}

Return ONLY the simplified regex, nothing else. Must compile as Python regex."""
        raw = _call_llm(prompt, llm_fn)
        if raw:
            simplified = raw.strip().strip('"\'`')
            if _is_valid_regex(simplified) and len(simplified) < len(combined):
                combined = simplified

    if not _is_valid_regex(combined):
        # Fallback seguro: la alternancia siempre es válida
        combined = f"(?:{g1.regex})|(?:{g2.regex})"

    # Los vectores bloqueados son la unión
    merged_vectors = list(set(g1.vectors_blocked + g2.vectors_blocked))

    child = PatternGene(
        id=_new_id("CROSS"),
        regex=combined,
        category=g1.category,       # usa la categoría del padre dominante (mayor fitness)
        generation=max(g1.generation, g2.generation) + 1,
        parent_id=f"{g1.id}+{g2.id}",
        fitness_score=0.0,
        false_positive_rate=0.0,
        vectors_blocked=merged_vectors,
        created_at=_now_iso(),
        fitness_history=[],
        cve_origin=g1.cve_origin or g2.cve_origin,
        notes=f"Crossover de {g1.id} × {g2.id}",
    )
    logger.info(f"crossover: {g1.id} × {g2.id} → {child.id}")
    return child


def select_survivors(population: list, top_k: int = 10) -> list:
    """
    Selecciona los top_k genes por fitness_score.
    Elimina duplicados por similitud de regex > _SIMILARITY_THRESHOLD.
    Siempre retorna exactamente top_k genes (o todos si hay menos de top_k).
    """
    if not population:
        return []

    # Ordenar por fitness descendente
    sorted_pop = sorted(population, key=lambda g: g.fitness_score, reverse=True)

    survivors = []
    for gene in sorted_pop:
        if len(survivors) >= top_k:
            break
        # Verificar si hay un gen similar ya en survivors
        is_duplicate = any(
            _regex_similarity(gene.regex, s.regex) > _SIMILARITY_THRESHOLD
            for s in survivors
        )
        if not is_duplicate:
            survivors.append(gene)

    # Fallback: solo si la población total es menor que top_k
    # (ej: 3 genes disponibles, top_k=10 → devolver los 3 sin filtro de similitud)
    # NO activar cuando hay suficientes genes únicos — respetamos la deduplicación.
    if len(population) < top_k and len(survivors) < len(population):
        added_ids = {g.id for g in survivors}
        for gene in sorted_pop:
            if len(survivors) >= len(population):
                break
            if gene.id not in added_ids:
                survivors.append(gene)
                added_ids.add(gene.id)

    logger.info(f"select_survivors: {len(population)} genes → {len(survivors)} survivors (top_{top_k})")
    return survivors
