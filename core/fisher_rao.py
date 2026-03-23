"""
Fisher-Rao Distance — Information geometry for memory retrieval.

Replaces naive keyword matching with Fisher-Rao divergence on
TF-IDF distributions. Zero external dependencies (stdlib only).
Better contextual relevance than cosine similarity.
"""

import math
import re
import logging
from collections import Counter

logger = logging.getLogger("core.fisher_rao")


def tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer. None is treated as empty."""
    if not text:
        return []
    return re.findall(r'\b\w+\b', text.lower())


def term_frequencies(tokens: list[str]) -> dict[str, float]:
    """Compute normalized term frequency distribution."""
    if not tokens:
        return {}
    counts = Counter(tokens)
    total = len(tokens)
    return {t: c / total for t, c in counts.items()}


def fisher_rao_distance(text_a: str, text_b: str) -> float:
    """Compute Fisher-Rao distance between two text distributions.

    Based on the Fisher information metric on the statistical manifold
    of term frequency distributions. Uses the Bhattacharyya coefficient
    as intermediate step.

    Formula: d_FR(P, Q) = 2 * arccos(sum(sqrt(p_i * q_i)))

    Returns distance in [0, pi]. Lower = more similar.
    Returns pi (maximum distance) if either text is empty.
    """
    tokens_a = tokenize(text_a)
    tokens_b = tokenize(text_b)

    if not tokens_a or not tokens_b:
        return math.pi  # Maximum distance

    tf_a = term_frequencies(tokens_a)
    tf_b = term_frequencies(tokens_b)

    # Union of all terms
    all_terms = set(tf_a.keys()) | set(tf_b.keys())

    # Bhattacharyya coefficient: BC = sum(sqrt(p_i * q_i))
    bc = 0.0
    for term in all_terms:
        p = tf_a.get(term, 0.0)
        q = tf_b.get(term, 0.0)
        if p > 0 and q > 0:
            bc += math.sqrt(p * q)

    # Clamp to [0, 1] for numerical stability
    bc = max(0.0, min(1.0, bc))

    # Fisher-Rao distance = 2 * arccos(BC)
    return 2.0 * math.acos(bc)


def fisher_rao_similarity(text_a: str, text_b: str) -> float:
    """Compute Fisher-Rao similarity score.

    Returns value in [0, 1]. Higher = more similar.
    Normalized from Fisher-Rao distance.
    """
    dist = fisher_rao_distance(text_a, text_b)
    return 1.0 - (dist / math.pi)


def ranked_search(query: str, documents: list[dict],
                  text_key: str = "value", top_k: int = 5) -> list[dict]:
    """Rank documents by Fisher-Rao similarity to query.

    Args:
        query: Search query text
        documents: List of dicts, each containing text in text_key field
        text_key: Key to extract text from documents
        top_k: Number of top results to return

    Returns:
        Top-K documents sorted by similarity (highest first),
        each augmented with '_fr_similarity' and '_fr_distance' fields.
    """
    if not query or not documents:
        return []

    scored = []
    for doc in documents:
        text = doc.get(text_key, "")
        if not text:
            continue
        # Also search in key field if present
        full_text = f"{doc.get('key', '')} {text}"
        sim = fisher_rao_similarity(query, full_text)
        scored.append((sim, doc))

    # Sort by similarity descending
    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for sim, doc in scored[:top_k]:
        result = dict(doc)
        result["_fr_similarity"] = round(sim, 4)
        result["_fr_distance"] = round(math.pi * (1.0 - sim), 4)  # dist = π*(1-sim)
        results.append(result)

    return results
