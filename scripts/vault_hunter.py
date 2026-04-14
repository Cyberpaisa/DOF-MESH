#!/usr/bin/env python3
"""
vault_hunter.py — Busca en el vault de Obsidian (cerebro cyber) usando BM25 + fuzzy.

Uso:
  python3 scripts/vault_hunter.py "Z3 invariants"
  python3 scripts/vault_hunter.py "SECOP API" --top 5
  python3 scripts/vault_hunter.py "governance" --type gotcha
  python3 scripts/vault_hunter.py --list-all
  python3 scripts/vault_hunter.py --recent 7  # archivos modificados últimos 7 días
"""
from __future__ import annotations

import argparse
import math
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

VAULT_PATH = Path.home() / "cerebro cyber" / "cerebro cyber"
DOF_SESSIONS = Path.home() / "equipo-de-agentes" / "docs" / "09_sessions"

# Archivos/dirs a ignorar
_IGNORE_DIRS = {".obsidian", ".trash", "__pycache__", ".git"}
_IGNORE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".pdf"}

# Secciones de interés para el hunter
_SECTION_PATTERNS = {
    "gotcha":   re.compile(r"(?i)(gotcha|trampa|error|NUNCA|WARNING|⚠️|INCIDENTE)", re.MULTILINE),
    "decision": re.compile(r"(?i)(decisión|decision|elegí|elegimos|we chose|rationale)", re.MULTILINE),
    "metric":   re.compile(r"(?i)(tests|ASR|LOC|attestations|score|módulos|percent|%)", re.MULTILINE),
    "learning": re.compile(r"(?i)(aprendiz|lección|lesson|learned|insight)", re.MULTILINE),
    "api":      re.compile(r"(?i)(def |class |import |\.verify\(|\.check\(|→)", re.MULTILINE),
}


# ──────────────────────────────────────────────────────────────────────────────
# BM25 — implementación minimal sin dependencias externas
# ──────────────────────────────────────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """Tokenización simple: minúsculas, solo alfanumérico + guión bajo."""
    return re.findall(r"[a-záéíóúñüA-ZÁÉÍÓÚÑÜ\w]{2,}", text.lower())


def _bm25_score(
    query_terms: list[str],
    doc_tokens: list[str],
    df: dict[str, int],
    N: int,
    k1: float = 1.5,
    b: float = 0.75,
    avgdl: float = 300.0,
) -> float:
    dl = len(doc_tokens)
    tf_map: dict[str, int] = defaultdict(int)
    for t in doc_tokens:
        tf_map[t] += 1

    score = 0.0
    for term in query_terms:
        if term not in tf_map:
            continue
        tf = tf_map[term]
        idf = math.log((N - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5) + 1)
        tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))
        score += idf * tf_norm
    return score


# ──────────────────────────────────────────────────────────────────────────────
# Indexado del vault
# ──────────────────────────────────────────────────────────────────────────────

def _collect_docs(vault: Path) -> list[tuple[Path, str]]:
    """Recorre el vault y retorna (path, contenido) para cada .md."""
    docs = []
    for md_file in vault.rglob("*.md"):
        if any(p in md_file.parts for p in _IGNORE_DIRS):
            continue
        if md_file.suffix.lower() in _IGNORE_EXTS:
            continue
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            docs.append((md_file, content))
        except (PermissionError, OSError):
            pass
    return docs


def _build_index(docs: list[tuple[Path, str]]) -> tuple[
    list[tuple[Path, str, list[str]]],  # (path, content, tokens)
    dict[str, int],                      # df (document frequency)
    float,                               # avgdl
]:
    tokenized = []
    df: dict[str, int] = defaultdict(int)
    total_tokens = 0

    for path, content in docs:
        tokens = _tokenize(content)
        total_tokens += len(tokens)
        seen = set(tokens)
        for t in seen:
            df[t] += 1
        tokenized.append((path, content, tokens))

    avgdl = total_tokens / max(len(tokenized), 1)
    return tokenized, dict(df), avgdl


# ──────────────────────────────────────────────────────────────────────────────
# Búsqueda
# ──────────────────────────────────────────────────────────────────────────────

def _extract_snippet(content: str, query_terms: list[str], max_chars: int = 200) -> str:
    """Extrae el fragmento más relevante del documento."""
    lines = content.split("\n")
    best_line = ""
    best_hits = -1
    for line in lines:
        line_lower = line.lower()
        hits = sum(1 for t in query_terms if t in line_lower)
        if hits > best_hits and len(line.strip()) > 10:
            best_hits = hits
            best_line = line.strip()
    snippet = best_line[:max_chars]
    if len(best_line) > max_chars:
        snippet += "…"
    return snippet


def search(
    query: str,
    top_k: int = 5,
    filter_type: Optional[str] = None,
    vault: Path = VAULT_PATH,
) -> list[dict]:
    """
    Busca en el vault y retorna lista de resultados ordenados por relevancia.

    Returns:
        Lista de dicts con: path, relative_path, score, snippet, type_matches, modified
    """
    docs = _collect_docs(vault)
    if not docs:
        return []

    tokenized, df, avgdl = _build_index(docs)
    N = len(tokenized)
    query_terms = _tokenize(query)

    results = []
    for path, content, tokens in tokenized:
        score = _bm25_score(query_terms, tokens, df, N, avgdl=avgdl)
        if score <= 0:
            continue

        # Detectar tipo de contenido
        type_matches = [
            t for t, pat in _SECTION_PATTERNS.items()
            if pat.search(content)
        ]

        # Filtrar por tipo si se especificó
        if filter_type and filter_type not in type_matches:
            continue

        # Boost si el query aparece en el título/nombre del archivo
        filename_lower = path.stem.lower()
        title_boost = sum(1.5 for t in query_terms if t in filename_lower)
        score += title_boost

        try:
            modified = datetime.fromtimestamp(path.stat().st_mtime)
        except OSError:
            modified = datetime.min

        results.append({
            "path": path,
            "relative_path": str(path.relative_to(vault)),
            "score": score,
            "snippet": _extract_snippet(content, query_terms),
            "type_matches": type_matches,
            "modified": modified,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def list_recent(days: int = 7, vault: Path = VAULT_PATH) -> list[dict]:
    """Lista archivos modificados en los últimos N días."""
    cutoff = datetime.now() - timedelta(days=days)
    docs = _collect_docs(vault)
    recent = []
    for path, content in docs:
        try:
            modified = datetime.fromtimestamp(path.stat().st_mtime)
        except OSError:
            continue
        if modified >= cutoff:
            recent.append({
                "path": path,
                "relative_path": str(path.relative_to(vault)),
                "modified": modified,
                "size": len(content),
                "lines": content.count("\n"),
            })
    recent.sort(key=lambda x: x["modified"], reverse=True)
    return recent


def list_all(vault: Path = VAULT_PATH) -> list[dict]:
    """Lista todos los archivos del vault con metadatos básicos."""
    docs = _collect_docs(vault)
    result = []
    for path, content in docs:
        try:
            modified = datetime.fromtimestamp(path.stat().st_mtime)
        except OSError:
            modified = datetime.min
        result.append({
            "path": path,
            "relative_path": str(path.relative_to(vault)),
            "modified": modified,
            "size_kb": round(len(content.encode()) / 1024, 1),
            "lines": content.count("\n"),
        })
    result.sort(key=lambda x: x["modified"], reverse=True)
    return result


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def _fmt_path(p: str) -> str:
    """Acorta el path para display."""
    return p.replace("dof-mesh/main/", "📂 ").replace("wiki/conceptos/", "📖 ").replace(
        "dof-mesh/hackathons/", "🏆 "
    ).replace("hub/", "🔗 ")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="vault_hunter — Busca en el Obsidian vault de DOF-MESH"
    )
    parser.add_argument("query", nargs="?", help="Términos de búsqueda")
    parser.add_argument("--top", type=int, default=5, help="Número de resultados (default: 5)")
    parser.add_argument(
        "--type",
        choices=list(_SECTION_PATTERNS.keys()),
        help="Filtrar por tipo: gotcha, decision, metric, learning, api",
    )
    parser.add_argument(
        "--recent",
        type=int,
        metavar="DAYS",
        help="Listar archivos modificados en los últimos N días",
    )
    parser.add_argument("--list-all", action="store_true", help="Listar todos los archivos del vault")
    parser.add_argument(
        "--vault",
        type=Path,
        default=VAULT_PATH,
        help=f"Path al vault Obsidian (default: {VAULT_PATH})",
    )

    args = parser.parse_args()

    if not args.vault.exists():
        print(f"❌ Vault no encontrado: {args.vault}", file=sys.stderr)
        sys.exit(1)

    # ── Modo list-all
    if args.list_all:
        files = list_all(args.vault)
        print(f"\n📚 Vault — {len(files)} archivos\n")
        for f in files:
            ts = f["modified"].strftime("%d %b %H:%M")
            print(f"  {ts}  {f['size_kb']:>6.1f}KB  {_fmt_path(f['relative_path'])}")
        return

    # ── Modo recent
    if args.recent:
        files = list_recent(args.recent, args.vault)
        print(f"\n🕐 Vault — modificados en los últimos {args.recent} días ({len(files)} archivos)\n")
        for f in files:
            ts = f["modified"].strftime("%d %b %H:%M")
            print(f"  {ts}  {f['lines']:>4} líneas  {_fmt_path(f['relative_path'])}")
        return

    # ── Modo búsqueda
    if not args.query:
        parser.print_help()
        sys.exit(0)

    print(f"\n🔍 Buscando: '{args.query}'" + (f" [tipo: {args.type}]" if args.type else ""))
    print(f"   Vault: {args.vault}\n")

    results = search(args.query, top_k=args.top, filter_type=args.type, vault=args.vault)

    if not results:
        print("  Sin resultados. Prueba con términos más generales.")
        return

    for i, r in enumerate(results, 1):
        ts = r["modified"].strftime("%d %b %Y")
        types_str = ", ".join(r["type_matches"]) if r["type_matches"] else "—"
        print(f"  [{i}] score={r['score']:.2f}  {ts}  {_fmt_path(r['relative_path'])}")
        print(f"       tipos: {types_str}")
        if r["snippet"]:
            print(f"       ↳ {r['snippet']}")
        print()

    print(f"  {len(results)} resultado(s) · /preserve para guardar un hallazgo")


if __name__ == "__main__":
    main()
