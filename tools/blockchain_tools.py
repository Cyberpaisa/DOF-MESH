"""Herramientas para analizar agentes ERC-8004 y blockchain."""

import os
import json
import ssl
import certifi
from crewai.tools import BaseTool


def _ssl_context():
    """SSL context que funciona en macOS (usa certifi)."""
    try:
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx


class CheckAgentEndpointTool(BaseTool):
    name: str = "check_agent_endpoint"
    description: str = (
        "Verifica los endpoints de un agente ERC-8004: health check, "
        ".well-known/agent-card.json (A2A), /mcp (MCP protocol). "
        "Input: URL base del agente (ej: https://mi-agente.up.railway.app)"
    )

    def _run(self, base_url: str) -> str:
        import urllib.request
        import urllib.error
        import time

        base_url = base_url.rstrip("/")
        ctx = _ssl_context()
        results = []

        endpoints = [
            ("/api/health", "Health Check"),
            ("/.well-known/agent-card.json", "A2A Agent Card"),
            ("/.well-known/agent.json", "ERC-8004 Agent JSON"),
        ]

        for path, label in endpoints:
            url = f"{base_url}{path}"
            start = time.time()
            try:
                req = urllib.request.Request(url, method="GET")
                req.add_header("User-Agent", "EnigmaCrew/1.0")
                with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                    elapsed = int((time.time() - start) * 1000)
                    body = resp.read().decode("utf-8", errors="replace")[:2000]
                    status = resp.status
                    results.append(f"  ✅ {label}: {status} ({elapsed}ms)\n     {body[:500]}")
            except urllib.error.HTTPError as e:
                elapsed = int((time.time() - start) * 1000)
                results.append(f"  ❌ {label}: HTTP {e.code} ({elapsed}ms)")
            except Exception as e:
                results.append(f"  ❌ {label}: {type(e).__name__}: {e}")

        # Test MCP with POST
        mcp_url = f"{base_url}/mcp"
        start = time.time()
        try:
            mcp_body = json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }).encode()
            req = urllib.request.Request(mcp_url, data=mcp_body, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("User-Agent", "EnigmaCrew/1.0")
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                elapsed = int((time.time() - start) * 1000)
                body = resp.read().decode("utf-8", errors="replace")[:2000]
                results.append(f"  ✅ MCP (tools/list): {resp.status} ({elapsed}ms)\n     {body[:500]}")
        except urllib.error.HTTPError as e:
            elapsed = int((time.time() - start) * 1000)
            body = e.read().decode("utf-8", errors="replace")[:500] if hasattr(e, "read") else ""
            results.append(f"  ⚠ MCP: HTTP {e.code} ({elapsed}ms)\n     {body}")
        except Exception as e:
            results.append(f"  ❌ MCP: {type(e).__name__}: {e}")

        report = f"""
🤖 AGENT ENDPOINT CHECK: {base_url}
{'='*60}
{chr(10).join(results)}

📋 RESUMEN:
  - Endpoints OK: {sum(1 for r in results if '✅' in r)}/{len(results)}
  - Endpoints FAIL: {sum(1 for r in results if '❌' in r)}/{len(results)}
"""
        return report


class AnalyzeAgentMetadataTool(BaseTool):
    name: str = "analyze_agent_metadata"
    description: str = (
        "Analiza el metadata JSON de un agente ERC-8004 desde su tokenURI o "
        "agent-card.json. Verifica campos requeridos, formato CAIP-10, "
        "servicios declarados. Input: URL del metadata JSON."
    )

    def _run(self, url: str) -> str:
        import urllib.request

        ctx = _ssl_context()
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "EnigmaCrew/1.0")
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return f"❌ Error fetching metadata: {e}"

        checks = []

        # Required fields
        required = ["name", "description"]
        for field in required:
            if field in data:
                checks.append(f"  ✅ {field}: {str(data[field])[:100]}")
            else:
                checks.append(f"  ❌ {field}: MISSING")

        # CAIP-10 wallet format
        wallet = data.get("wallet", data.get("url", {}).get("wallet", ""))
        if wallet:
            if wallet.startswith("eip155:"):
                checks.append(f"  ✅ wallet CAIP-10: {wallet}")
            else:
                checks.append(f"  ⚠ wallet NOT CAIP-10: {wallet}")
        else:
            checks.append("  ❌ wallet: MISSING")

        # Services
        services = data.get("services", data.get("url", {}).get("services", []))
        if services:
            for svc in services:
                name = svc.get("name", svc.get("type", "unknown"))
                endpoint = svc.get("endpoint", svc.get("url", "N/A"))
                checks.append(f"  📡 Service: {name} -> {endpoint}")
        else:
            checks.append("  ⚠ No services declared")

        # Capabilities / skills
        caps = data.get("capabilities", data.get("skills", []))
        if caps:
            checks.append(f"  🎯 Capabilities: {len(caps)} declared")

        report = f"""
📋 AGENT METADATA ANALYSIS
{'='*60}
URL: {url}

{chr(10).join(checks)}

📊 RAW METADATA (truncated):
{json.dumps(data, indent=2)[:2000]}
"""
        return report


class QuerySupabaseAgentsTool(BaseTool):
    name: str = "query_enigma_agents"
    description: str = (
        "Consulta agentes de la base de datos Enigma Scanner (Supabase). "
        "Input: tipo de consulta — 'stats' (resumen), 'top' (top trust scores), "
        "'search:nombre' (buscar por nombre), 'low-trust' (agentes con score bajo)."
    )

    def _run(self, query_type: str) -> str:
        from sqlalchemy import create_engine, text
        import pandas as pd

        db_url = os.getenv("ENIGMA_DATABASE_URL", os.getenv("DATABASE_URL", ""))
        if not db_url:
            return "❌ ENIGMA_DATABASE_URL no configurada en .env"

        engine = create_engine(db_url)
        query_type = query_type.strip().lower()

        try:
            with engine.connect() as conn:
                if query_type == "stats":
                    df = pd.read_sql(text("""
                        SELECT
                            count(*) as total_agents,
                            count(*) FILTER (WHERE status = 'VERIFIED') as verified,
                            count(*) FILTER (WHERE status = 'PENDING') as pending,
                            count(*) FILTER (WHERE status = 'FLAGGED') as flagged,
                            round(avg(trust_score)::numeric, 1) as avg_trust,
                            min(trust_score) as min_trust,
                            max(trust_score) as max_trust
                        FROM agents
                    """), conn)
                    return f"📊 ENIGMA SCANNER STATS\n{'='*40}\n{df.to_string(index=False)}"

                elif query_type == "top":
                    df = pd.read_sql(text("""
                        SELECT name, address, trust_score, type, status, created_at
                        FROM agents ORDER BY trust_score DESC LIMIT 20
                    """), conn)
                    return f"🏆 TOP 20 AGENTS BY TRUST SCORE\n{'='*40}\n{df.to_string(index=False)}"

                elif query_type.startswith("search:"):
                    term = query_type.split(":", 1)[1].strip()
                    df = pd.read_sql(text(
                        "SELECT name, address, trust_score, status FROM agents "
                        "WHERE name ILIKE :term LIMIT 20"
                    ), conn, params={"term": f"%{term}%"})
                    return f"🔍 SEARCH: '{term}'\n{'='*40}\n{df.to_string(index=False)}"

                elif query_type == "low-trust":
                    df = pd.read_sql(text("""
                        SELECT name, address, trust_score, status, created_at
                        FROM agents WHERE trust_score < 42
                        ORDER BY trust_score ASC LIMIT 20
                    """), conn)
                    return f"⚠ LOW TRUST AGENTS\n{'='*40}\n{df.to_string(index=False)}"

                else:
                    return "❌ Tipo de consulta no reconocido. Usa: stats, top, search:nombre, low-trust"

        except Exception as e:
            return f"❌ Error: {e}"
