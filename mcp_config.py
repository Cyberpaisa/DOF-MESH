"""
Configuración de MCP Servers — herramientas externas para agentes.

Arquitectura escalable:
  1. MCP_REGISTRY: define cada MCP server disponible (command, args, env)
  2. ROLE_MCP_MAP: asigna MCPs a roles de agentes (config-driven, no hardcoded)
  3. get_mcp_for_role(): construye los MCPServerStdio según el mapa

Para agregar un MCP nuevo:
  1. Agregar entrada en MCP_REGISTRY
  2. Agregar a los roles relevantes en ROLE_MCP_MAP
  3. Listo — no necesitas escribir funciones nuevas

Para agregar un agente nuevo:
  1. Agregar entrada en ROLE_MCP_MAP con lista de MCPs
  2. Listo

Auditoría Guardian (26 mar 2026): todos los paquetes auditados.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")


# ═══════════════════════════════════════════════════════
# MCP REGISTRY — fuente única de verdad
# ═══════════════════════════════════════════════════════

MCP_REGISTRY = {
    # ── Originales ──
    "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem"],
        "needs_dir": True,  # se le append el directorio permitido
        "description": "Leer/escribir archivos en directorios permitidos",
    },
    "web_search": {
        "command": "npx",
        "args": ["-y", "@pskill9/web-search"],
        "description": "Búsqueda Google gratis (sin API key)",
    },
    "fetch": {
        "command": "npx",
        "args": ["-y", "@anthropics/mcp-server-fetch"],
        "description": "Fetch URLs y conversión a markdown",
    },
    "memory": {
        "command": "npx",
        "args": ["-y", "@anthropics/mcp-server-memory"],
        "description": "Knowledge graph persistente (complementa ChromaDB)",
    },

    # ── Nuevos (auditados Guardian — 26 mar 2026) ──
    "context7": {
        "command": "npx",
        "args": ["-y", "@upstash/context7-mcp"],
        "description": "Docs actualizados de librerías (CrewAI, ethers, Z3, etc.)",
        "publisher": "Upstash (oficial) — 430K dl/sem",
    },
    "sequential_thinking": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
        "description": "Razonamiento paso a paso para decisiones complejas",
        "publisher": "Anthropic (oficial) — 94K dl/sem",
    },
    "playwright": {
        "command": "npx",
        "args": ["-y", "@playwright/mcp", "--headless"],
        "description": "Browser automation headless (navigate, click, screenshot, etc.)",
        "publisher": "Microsoft (oficial) — 1.86M dl/sem",
    },
    "evm": {
        "command": "npx",
        "args": ["-y", "@mcpdotdirect/evm-mcp-server"],
        "description": "Blockchain EVM 60+ redes (balances, contratos, txs)",
        "publisher": "mcpdotdirect — SLSA provenance",
        "warning": "NUNCA conectar wallet principal. Solo wallet dedicada.",
    },
    "tavily": {
        "command": "npx",
        "args": ["-y", "tavily-mcp"],
        "description": "Búsqueda AI-optimizada + extracción de contenido",
        "publisher": "Tavily AI (oficial) — 137K dl/sem",
        "env": "TAVILY_API_KEY",
    },
    "brave_search": {
        "command": "npx",
        "args": ["-y", "@brave/brave-search-mcp-server"],
        "description": "Búsqueda web Brave (2K gratis/mes)",
        "publisher": "Brave Software (oficial)",
        "env": "BRAVE_API_KEY",
    },
    "supabase": {
        "command": "npx",
        "args": ["-y", "@supabase/mcp-server-supabase"],
        "description": "Acceso directo a Supabase (DB, auth, storage, edge functions)",
        "publisher": "Supabase (oficial) — 47K dl/sem",
        "env": "SUPABASE_ACCESS_TOKEN",
    },
}


# ═══════════════════════════════════════════════════════
# ROLE → MCP MAP — config-driven
# ═══════════════════════════════════════════════════════
# Cada rol tiene una lista de MCPs del registry.
# Para agregar/quitar un MCP de un rol, solo edita esta tabla.

ROLE_MCP_MAP = {
    # ── Roles originales (8) ──
    "code_architect":    ["filesystem", "fetch", "context7", "evm", "playwright"],
    "research_analyst":  ["tavily", "brave_search", "context7", "fetch"],
    "data_engineer":     ["filesystem", "supabase", "context7"],
    "project_organizer": ["filesystem", "supabase"],
    "narrative_content": ["brave_search", "fetch", "context7"],
    "mvp_strategist":    ["sequential_thinking", "brave_search", "context7"],
    "qa_reviewer":       ["playwright", "context7", "tavily"],
    "verifier":          ["evm", "sequential_thinking", "tavily"],

    # ── Roles de agents.yaml (17 agentes) ──
    "lider_orquestador":     ["sequential_thinking", "tavily", "context7", "supabase"],
    "organizador_archivos":  ["filesystem"],
    "product_manager":       ["sequential_thinking", "brave_search", "context7"],
    "director_operaciones":  ["supabase", "tavily", "sequential_thinking"],
    "bizdev":                ["brave_search", "tavily", "fetch"],
    "arquitecto":            ["filesystem", "context7", "evm", "sequential_thinking"],
    "developer":             ["filesystem", "context7", "fetch", "playwright"],
    "qa_engineer":           ["playwright", "context7", "tavily"],
    "investigador":          ["tavily", "brave_search", "fetch", "context7"],
    "devops":                ["filesystem", "supabase", "playwright"],
    "seguridad_blockchain":  ["evm", "sequential_thinking", "tavily"],
    "experto_ideacion":      ["brave_search", "fetch", "sequential_thinking"],
    "experto_multichain":    ["evm", "tavily", "context7"],
    "experto_cuantico":      ["sequential_thinking", "context7", "tavily"],
    "seguridad_informatica": ["evm", "playwright", "sequential_thinking"],
    "experto_metodologias":  ["sequential_thinking", "context7", "fetch"],
    "experto_bpm":           ["sequential_thinking", "supabase", "context7"],
}

# Alias para compatibilidad con nombres en inglés/español
ROLE_ALIASES = {
    "orchestrator": "lider_orquestador",
    "file_organizer": "organizador_archivos",
    "operations": "director_operaciones",
    "architect": "arquitecto",
    "security_blockchain": "seguridad_blockchain",
    "security": "seguridad_informatica",
    "researcher": "investigador",
    "ideation": "experto_ideacion",
    "multichain": "experto_multichain",
    "quantum": "experto_cuantico",
    "methodologies": "experto_metodologias",
    "bpm": "experto_bpm",
}


# ═══════════════════════════════════════════════════════
# BUILDER — construye MCPServerStdio desde el registry
# ═══════════════════════════════════════════════════════

def _build_mcp(name: str, project_dir: str | None = None):
    """Construye un MCPServerStdio a partir de una entrada del registry."""
    from crewai.mcp import MCPServerStdio

    entry = MCP_REGISTRY[name]
    args = list(entry["args"])

    if entry.get("needs_dir"):
        target_dir = project_dir or OUTPUT_DIR
        os.makedirs(target_dir, exist_ok=True)
        args.append(target_dir)

    return MCPServerStdio(
        command=entry["command"],
        args=args,
        cache_tools_list=True,
    )


def get_mcp_for_role(role: str, project_dir: str | None = None) -> list:
    """
    Retorna lista de MCPServerStdio según el rol del agente.

    Acepta tanto nombres en español (agents.yaml) como en inglés (aliases).
    Si el rol no existe, retorna lista vacía.
    """
    role = role.lower().strip()
    role = ROLE_ALIASES.get(role, role)

    mcp_names = ROLE_MCP_MAP.get(role, [])
    return [_build_mcp(name, project_dir) for name in mcp_names if name in MCP_REGISTRY]


def get_available_mcps() -> dict:
    """Retorna el registry completo para inspección/debug."""
    return {
        name: {
            "description": entry["description"],
            "env_required": entry.get("env"),
            "warning": entry.get("warning"),
        }
        for name, entry in MCP_REGISTRY.items()
    }


def get_role_map() -> dict:
    """Retorna el mapa completo de roles → MCPs para inspección/debug."""
    return dict(ROLE_MCP_MAP)


# ═══════════════════════════════════════════════════════
# LEGACY — funciones individuales para compatibilidad
# ═══════════════════════════════════════════════════════

def get_filesystem_mcp(allowed_dir=None):
    return _build_mcp("filesystem", allowed_dir)

def get_web_search_mcp():
    return _build_mcp("web_search")

def get_fetch_mcp():
    return _build_mcp("fetch")

def get_memory_mcp():
    return _build_mcp("memory")

def get_context7_mcp():
    return _build_mcp("context7")

def get_sequential_thinking_mcp():
    return _build_mcp("sequential_thinking")

def get_playwright_mcp():
    return _build_mcp("playwright")

def get_evm_mcp():
    return _build_mcp("evm")

def get_tavily_mcp():
    return _build_mcp("tavily")

def get_brave_search_mcp():
    return _build_mcp("brave_search")

def get_supabase_mcp():
    return _build_mcp("supabase")
