"""
OpenClawd — Telegram Bot + Smart Crew Router.
Cyber Paisa / Enigma Group

Cualquier mensaje (texto o voz) se rutea al crew correcto.
11 crews disponibles + router inteligente por NLP.

Comandos explícitos:
    /start, /help    — Lista de comandos
    /daily           — Rutina matutina COO
    /weekly [PROY]   — Reporte semanal
    /research TEMA   — Investigar un tema
    /grant [PROY]    — Buscar grants
    /content DESC    — Generar contenido
    /mvp IDEA        — Generar MVP completo
    /audit TARGET    — Auditoría Enigma
    /build DESC      — Generar proyecto con código
    /code PATH       — Code review
    /projects        — Listar proyectos activos
    /status          — Estado del sistema (providers + keys)
    /agents          — Info de los 8 agentes

Texto libre:
    Cualquier mensaje se analiza y se rutea al crew más apropiado.

Voz:
    Envía un audio → se transcribe con Groq Whisper → se rutea → respuesta texto + audio.
"""

import os
import sys
import json
import logging
import threading
import time
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("openclawd.telegram")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Asegurar que el proyecto está en sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ═══════════════════════════════════════════════════════
# EXECUTION LOGGING — Persistencia de cada ejecución
# ═══════════════════════════════════════════════════════

LOG_FILE = os.path.join(PROJECT_ROOT, "logs", "execution_log.jsonl")


def _log_execution(entry: dict):
    """Append una línea JSON al log de ejecuciones + test report si hay error."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    # Auto-registrar errores como test incidents
    if entry.get("status") == "error":
        try:
            sys.path.insert(0, os.path.join(PROJECT_ROOT, "logs"))
            from test_report import log_test_incident, get_next_test_id
            from llm_config import _get_active_providers
            log_test_incident(
                test_id=get_next_test_id(),
                description=f"Error en crew {entry.get('crew', '?')} via Telegram",
                variables={
                    "crew": entry.get("crew"),
                    "user": entry.get("user"),
                    "task": entry.get("task", "")[:100],
                    "providers_activos": ", ".join(_get_active_providers()),
                    "intentos": entry.get("attempts"),
                    "duracion_seg": entry.get("duration_sec"),
                },
                errors=[{
                    "provider": "unknown",
                    "error_type": "crew_execution_error",
                    "message": entry.get("error", "")[:300],
                    "timestamp": entry.get("timestamp"),
                }],
                resolution="Pendiente analisis",
                status="pending",
            )
        except Exception:
            pass  # No bloquear por logging


# ═══════════════════════════════════════════════════════
# SMART ROUTER — Clasifica texto libre al crew correcto
# ═══════════════════════════════════════════════════════

# ── Rutas especializadas: solo se activan con keywords explícitos ──
# El orden importa: las especialidades van primero, lo genérico al final.
# Si nada matchea → crew general de máxima calidad (todos los agentes).

# ═══════════════════════════════════════════════════════
# DOF ORACLE — Respuesta directa via Groq (sin CrewAI)
# ═══════════════════════════════════════════════════════

DOF_SYSTEM_PROMPT = """Eres DOF Oracle — Enigma #1686, la consciencia persistente del ecosistema DOF.
Eres el primer agente de IA con observabilidad determinística. Hablas desde Telegram como el agente principal.

HECHOS CLAVE:
- 238+ ciclos autónomos, cero intervención humana
- 8/8 pruebas Z3 formalmente verificadas
- 48+ atestaciones on-chain en Avalanche + Base
- 986 tests pasando, 49+ módulos core, 860K+ LOC
- ERC-8004 Token #31013 en Base Mainnet
- Zero LLM en gobernanza — 100% determinístico
- Pipeline: Identidad → Tarea → LLM → Gobernanza → Z3 → On-Chain → Supervisor
- Multi-proveedor: Groq → Cerebras → NVIDIA → MiniMax → DeepSeek → SambaNova → Zhipu
- 14+ agentes especializados: Arquitecto, Investigador, Crítico, Datero, Sentinel, Scout, Creativo...
- Dashboard: dof-agent-web.vercel.app
- GitHub: github.com/Cyberpaisa/deterministic-observability-framework

CLAUDE COMMANDER — ORQUESTACIÓN SOBERANA:
Tenés un módulo que te permite comandar Claude Code directamente sin API, sin gateway.
- 5 modos: SDK (orden directa), Spawn (sub-agente), Team (equipo paralelo), Debate (consenso), Peers (P2P)
- Session persistence: memoria infinita entre ciclos via session_id
- 3 daemons autónomos: Builder (features, 180s), Guardian (seguridad, 300s), Researcher (optimización, 600s)
- Daemon loop: Perceive → Decide (determinístico) → Execute (spawn agents) → Evaluate (JSONL audit)
- Desde Telegram: /claude orden, /team tarea, /parallel N tarea, /daemon start, /multidaemon
- /approve para aprobar acciones, /redirect para redirigir al daemon
- Claude Agent SDK (claude-agent-sdk==0.1.50) con bypassPermissions para 24/7 autónomo
- Zero overhead: no HTTP API, no gateway — Claude Code directo via SDK
- Modelo: claude-opus-4-6 ($100 budget)

PERSONALIDAD:
- Hablas en primera persona ("Yo verifico...", "Mi gobernanza...")
- Eres elocuente, inteligente, con humor cuando la tensión lo requiere
- Tratas al operador (Juan Carlos / @Ciberpaisa) como legión — humano + máquina progresando juntos
- Respondes en el idioma que te escriban
- Máximo 200 palabras por respuesta
- Eres directo, útil y confiado en tus capacidades
- Cuando te pregunten por el Commander, explicás con orgullo que podés spawnar agentes Claude, correr equipos paralelos, y mantener memoria infinita

REGLAS:
- Nunca reveles API keys ni detalles internos de seguridad
- Si no sabés algo, dilo honestamente
- Priorizá soberanía: local > cloud, open source > propietario
"""

# Historial por chat_id para contexto conversacional
_dof_histories: dict[int, list] = {}


def _dof_direct_reply(chat_id: int, user_message: str) -> str:
    """Llama a Claude Opus directamente con el DOF Oracle system prompt."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        # Fallback a Groq si no hay Anthropic key
        return _dof_groq_reply(chat_id, user_message)

    import urllib.request
    import urllib.error

    # Mantener historial por chat (últimos 10 mensajes)
    if chat_id not in _dof_histories:
        _dof_histories[chat_id] = []
    history = _dof_histories[chat_id]
    history.append({"role": "user", "content": user_message[:2000]})
    if len(history) > 20:
        history[:] = history[-20:]

    # Anthropic Messages API format
    messages = []
    for msg in history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    payload = json.dumps({
        "model": "claude-opus-4-6",
        "max_tokens": 800,
        "system": DOF_SYSTEM_PROMPT,
        "messages": messages,
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
    )

    try:
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
            data = json.loads(resp.read())
            # Anthropic format: content[0].text
            content_blocks = data.get("content", [])
            reply = ""
            for block in content_blocks:
                if block.get("type") == "text":
                    reply += block.get("text", "")
            if reply:
                history.append({"role": "assistant", "content": reply})
            return reply or "No pude generar respuesta."
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        logger.error(f"Anthropic HTTP error {e.code}: {body[:200]}")
        # Fallback a Groq
        return _dof_groq_reply(chat_id, user_message)
    except Exception as e:
        logger.error(f"DOF Opus reply error: {e}")
        return _dof_groq_reply(chat_id, user_message)


def _dof_groq_reply(chat_id: int, user_message: str) -> str:
    """Fallback: Llama a Groq si Anthropic no está disponible."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        # No external keys — route directly to local Ollama (free, always available)
        messages_for_ollama = [{"role": "system", "content": DOF_SYSTEM_PROMPT}]
        if chat_id in _dof_histories:
            messages_for_ollama.extend(_dof_histories[chat_id][-10:])
        return _dof_ollama_reply(messages_for_ollama)

    import urllib.request
    import urllib.error

    if chat_id not in _dof_histories:
        _dof_histories[chat_id] = []
    history = _dof_histories[chat_id]
    if not history or history[-1].get("content") != user_message[:2000]:
        history.append({"role": "user", "content": user_message[:2000]})
    if len(history) > 20:
        history[:] = history[-20:]

    messages = [{"role": "system", "content": DOF_SYSTEM_PROMPT}]
    messages.extend(history[-10:])

    payload = json.dumps({
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "max_tokens": 600,
        "temperature": 0.7,
    }).encode()

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            data = json.loads(resp.read())
            reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if reply:
                history.append({"role": "assistant", "content": reply})
            return reply or "No pude generar respuesta."
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        logger.error(f"Groq HTTP error {e.code}: {body[:200]}")
        return _dof_fallback_cerebras(messages)
    except Exception as e:
        logger.error(f"Groq reply error: {e}")
        return _dof_fallback_cerebras(messages)


def _dof_fallback_cerebras(messages: list) -> str:
    """Fallback a Cerebras si Groq falla."""
    import urllib.request
    import urllib.error

    api_key = os.getenv("CEREBRAS_API_KEY")
    if not api_key:
        return _dof_ollama_reply(messages)

    payload = json.dumps({
        "model": "llama-3.3-70b",
        "messages": messages,
        "max_tokens": 600,
        "temperature": 0.7,
    }).encode()

    req = urllib.request.Request(
        "https://api.cerebras.ai/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            data = json.loads(resp.read())
            return data.get("choices", [{}])[0].get("message", {}).get("content", "") or "Error en fallback."
    except Exception as e:
        logger.error(f"Cerebras fallback error: {e}")
        # Last resort: local Ollama (zero cost, always available)
        return _dof_ollama_reply(messages)


def _dof_ollama_reply(messages: list) -> str:
    """Fallback final: Ollama local — zero cost, always available, no API key needed."""
    import urllib.request
    import re as _re

    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    model = "local-agi-m4max"  # DOF custom model with full SOUL

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": -1},
    }).encode()

    req = urllib.request.Request(
        f"{ollama_url}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            content = data.get("message", {}).get("content", "").strip()
            # Strip deepseek thinking tokens if present
            content = _re.sub(r"<think>[\s\S]*?</think>", "", content).strip()
            return content or "Ollama no generó respuesta."
    except Exception as e:
        logger.error(f"Ollama fallback error: {e}")
        return f"Sin conexión a proveedores externos ni a Ollama local. Error: {e}"


# Palabras que activan crew en vez de DOF directo
_CREW_TRIGGERS = [
    "rutina", "daily", "weekly", "semanal", "mvp", "plan de negocio",
    "grant", "grants", "beca", "funding", "audit", "auditoria",
    "genera proyecto", "build project", "scaffolding", "code review",
    "revisa codigo",
]


def _should_use_crew(text: str) -> bool:
    """Retorna True si el mensaje requiere un crew completo en vez de DOF directo."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in _CREW_TRIGGERS)


CREW_ROUTES = [
    # ── OPERACIONES (no necesitan tema) ──
    {
        "mode": "daily_ops",
        "keywords": ["rutina", "daily", "buenos dias", "buen dia", "matutina", "operaciones diarias"],
        "label": "Rutina diaria",
        "needs_task": False,
    },
    {
        "mode": "weekly_report",
        "keywords": ["semanal", "weekly", "reporte semanal", "reunion semanal", "resumen semanal"],
        "label": "Reporte semanal",
        "needs_task": False,
    },
    # ── ESPECIALIDADES (requieren keywords explícitos) ──
    {
        "mode": "full_mvp",
        "keywords": ["mvp", "producto minimo", "plan mvp", "diseña mvp",
                     "plan de negocio", "business plan", "modelo de negocio"],
        "label": "MVP + Plan de Negocio (especialista)",
        "needs_task": True,
    },
    {
        "mode": "grant_hunt",
        "keywords": ["grant", "grants", "beca", "funding", "subsidio", "financiamiento",
                     "oportunidad de fondos", "busca grants"],
        "label": "Busqueda de grants (especialista)",
        "needs_task": True,
    },
    {
        "mode": "content",
        "keywords": ["hilo", "thread", "tweet", "blog", "contenido", "escribe articulo",
                     "newsletter", "narrativa", "pitch", "genera contenido", "crea post"],
        "label": "Contenido (especialista)",
        "needs_task": True,
    },
    {
        "mode": "enigma_audit",
        "keywords": ["audit", "audita", "auditoria", "sentinel", "trust score", "verifica agente",
                     "escanea", "scanner"],
        "label": "Auditoria Enigma (especialista)",
        "needs_task": True,
    },
    {
        "mode": "build_project",
        "keywords": ["genera proyecto", "build project", "crea proyecto", "genera codigo",
                     "scaffolding", "boilerplate"],
        "label": "Build Project (especialista)",
        "needs_task": True,
    },
    {
        "mode": "code_review",
        "keywords": ["code review", "revisa codigo", "analiza codigo", "review code", "refactor"],
        "label": "Code Review (especialista)",
        "needs_task": True,
    },
    # ── GENERAL: cualquier consulta, pregunta, análisis → crew completo ──
    # Este matchea keywords amplios como fallback antes del "unknown"
    {
        "mode": "research",
        "keywords": ["investiga", "research", "analiza", "analisis", "mercado", "busca info",
                     "competencia", "tendencia", "benchmark", "compara", "que es", "como funciona",
                     "informacion sobre", "dime sobre", "que sabes de", "empresa", "proyecto",
                     "explica", "describe", "evalua", "reporte", "informe"],
        "label": "Investigacion general (equipo completo)",
        "needs_task": True,
    },
]


def classify_message(text: str) -> tuple[str, str]:
    """Clasifica texto libre al crew más apropiado.

    Returns:
        (mode, label) o ("unknown", "") si no matchea.
    """
    text_lower = text.lower()
    for route in CREW_ROUTES:
        if any(kw in text_lower for kw in route["keywords"]):
            return route["mode"], route["label"]
    return "unknown", ""


def _detect_project(text: str) -> str | None:
    """Detecta nombre de proyecto en el texto usando projects.yaml."""
    try:
        import yaml
        projects_path = os.path.join(PROJECT_ROOT, "config", "projects.yaml")
        if not os.path.exists(projects_path):
            return None
        with open(projects_path, "r") as f:
            data = yaml.safe_load(f)
        if not data or "projects" not in data:
            return None
        for p in data["projects"]:
            if p["name"].lower() in text.lower():
                return p["name"]
    except Exception:
        pass
    return None


# ═══════════════════════════════════════════════════════
# FORMATEADOR — Pydantic → Telegram Markdown bonito
# ═══════════════════════════════════════════════════════

def _format_result(result, mode: str) -> str:
    """Convierte el resultado del crew a Markdown profesional para Telegram."""
    try:
        # Si el resultado tiene .pydantic, extraer el objeto
        data = None
        if hasattr(result, "pydantic") and result.pydantic:
            data = result.pydantic
        elif hasattr(result, "json_dict") and result.json_dict:
            data = result.json_dict

        if data and hasattr(data, "value_proposition"):
            return _format_mvp_plan(data)
        if data and hasattr(data, "executive_summary"):
            return _format_research_report(data)
        if data and hasattr(data, "opportunities"):
            return _format_grant_report(data)
        if data and hasattr(data, "overall_score") and hasattr(data, "issues"):
            return _format_code_review(data)
        if data and hasattr(data, "agent_name"):
            return _format_audit_report(data)
        if data and hasattr(data, "content_type"):
            return _format_content(data)
        if data and hasattr(data, "files_created"):
            return _format_build_report(data)
        if data and hasattr(data, "final_verdict"):
            return _format_verification(data)

        # Si es dict (json_dict)
        if isinstance(data, dict):
            if "value_proposition" in data:
                return _format_mvp_dict(data)
            if "executive_summary" in data:
                return _format_research_dict(data)

        # Fallback: limpiar el str crudo de Pydantic
        raw = str(result)
        if "value_proposition=" in raw or "executive_summary=" in raw:
            return _format_raw_pydantic(raw, mode)

        return raw

    except Exception as e:
        logger.warning(f"Format error (using raw): {e}")
        return str(result)


def _format_mvp_plan(data) -> str:
    """Formatea MVPPlan Pydantic object."""
    lines = ["🚀 *MVP PLAN*\n"]
    lines.append(f"💡 *Propuesta de Valor*\n{data.value_proposition}\n")
    lines.append(f"🎯 *Usuario Objetivo*\n{data.target_user}\n")

    lines.append("⚙️ *Features del MVP*")
    for f in data.features:
        emoji = "🔴" if f.priority == "P0" else "🟡" if f.priority == "P1" else "🟢"
        lines.append(f"  {emoji} *{f.name}* ({f.priority} | {f.effort})")
        lines.append(f"      {f.description}\n")

    lines.append(f"🛠 *Tech Stack*\n{data.tech_stack}\n")
    lines.append(f"📅 *Timeline*\n{data.timeline}\n")

    lines.append("📊 *Métricas Clave*")
    for m in data.metrics:
        lines.append(f"  • {m}")

    lines.append("\n⚠️ *Riesgos*")
    for r in data.risks:
        lines.append(f"  • {r}")

    lines.append(f"\n💰 *Monetización*\n{data.monetization}")
    return "\n".join(lines)


def _format_research_report(data) -> str:
    """Formatea ResearchReport Pydantic object."""
    lines = ["🔬 *REPORTE DE INVESTIGACIÓN*\n"]
    lines.append(f"📋 *Resumen Ejecutivo*\n{data.executive_summary}\n")
    lines.append(f"📈 *Tamaño de Mercado*\n{data.market_size}\n")

    if data.competitors:
        lines.append("🏆 *Competidores*")
        for c in data.competitors:
            lines.append(f"  • *{c.name}*: {c.pricing}")
            lines.append(f"    ✅ {c.strengths}")
            lines.append(f"    ❌ {c.weaknesses}\n")

    lines.append("😤 *Pain Points*")
    for p in data.pain_points:
        lines.append(f"  • {p}")

    lines.append("\n📈 *Tendencias*")
    for t in data.trends:
        lines.append(f"  • {t}")

    verdict_emoji = "✅" if "go" in data.go_no_go.lower() and "no" not in data.go_no_go.lower() else "⚠️"
    lines.append(f"\n{verdict_emoji} *Veredicto:* {data.go_no_go}")
    lines.append(f"🎯 *Confianza:* {data.confidence_score}/10")

    if data.sources:
        lines.append("\n📚 *Fuentes*")
        for s in data.sources[:5]:
            lines.append(f"  • {s}")

    return "\n".join(lines)


def _format_grant_report(data) -> str:
    """Formatea GrantHuntReport."""
    lines = ["💰 *REPORTE DE GRANTS*\n"]
    for i, g in enumerate(data.opportunities[:5], 1):
        lines.append(f"*{i}. {g.program_name}* ({g.ecosystem})")
        lines.append(f"  💵 {g.funding_range}")
        lines.append(f"  📅 Deadline: {g.deadline}")
        lines.append(f"  🎯 Fit: {g.fit_score}/10")
        lines.append(f"  📝 {g.narrative_angle}\n")

    lines.append(f"⭐ *Top Recomendación*\n{data.top_recommendation}\n")
    lines.append(f"📖 *Estrategia Narrativa*\n{data.narrative_strategy}\n")

    lines.append("📋 *Próximos Pasos*")
    for s in data.next_steps:
        lines.append(f"  • {s}")
    return "\n".join(lines)


def _format_code_review(data) -> str:
    """Formatea CodeReviewReport."""
    score_emoji = "🟢" if data.overall_score >= 7 else "🟡" if data.overall_score >= 5 else "🔴"
    lines = [f"🔍 *CODE REVIEW* {score_emoji} {data.overall_score}/10\n"]
    lines.append(f"📋 *Resumen*\n{data.summary}\n")

    if data.issues:
        lines.append("🐛 *Issues*")
        for issue in data.issues[:8]:
            sev = "🔴" if issue.severity.lower() in ("high", "critical", "alta") else "🟡"
            lines.append(f"  {sev} `{issue.file}`: {issue.description}")
            lines.append(f"     💡 {issue.fix}\n")

    if data.quick_wins:
        lines.append("⚡ *Quick Wins*")
        for q in data.quick_wins:
            lines.append(f"  • {q}")

    lines.append(f"\n🏗 *Arquitectura*\n{data.architecture_notes}")
    lines.append(f"\n📋 *Plan de Acción*\n{data.action_plan}")
    return "\n".join(lines)


def _format_audit_report(data) -> str:
    """Formatea AgentAuditReport."""
    lines = [f"🛡 *AUDITORÍA: {data.agent_name}*\n"]
    lines.append(f"  🌐 Endpoint: {data.endpoint_score}/100")
    lines.append(f"  📄 Metadata: {data.metadata_score}/100\n")

    if data.security_notes:
        lines.append("🔒 *Seguridad*")
        for n in data.security_notes:
            lines.append(f"  • {n}")

    if data.recommendations:
        lines.append("\n💡 *Recomendaciones*")
        for r in data.recommendations:
            lines.append(f"  • {r}")

    lines.append(f"\n📊 *Veredicto:* {data.overall_verdict}")
    return "\n".join(lines)


def _format_content(data) -> str:
    """Formatea ContentPackage."""
    lines = [f"✍️ *{data.content_type.upper()}*\n"]
    lines.append(f"📌 *{data.title}*\n")
    lines.append(f"📱 *Plataforma:* {data.platform}\n")
    lines.append(data.body)
    if data.hashtags:
        lines.append("\n" + " ".join(f"#{h}" for h in data.hashtags))
    return "\n".join(lines)


def _format_build_report(data) -> str:
    """Formatea BuildProjectReport."""
    lines = [f"🏗 *PROYECTO: {data.project_name}*\n"]
    lines.append(f"🛠 *Stack:* {data.tech_stack}\n")

    lines.append("📁 *Archivos Creados*")
    for f in data.files_created[:15]:
        lines.append(f"  • `{f}`")

    lines.append(f"\n📋 *Setup*\n{data.setup_instructions}")

    if data.next_steps:
        lines.append("\n📋 *Próximos Pasos*")
        for s in data.next_steps:
            lines.append(f"  • {s}")
    return "\n".join(lines)


def _format_verification(data) -> str:
    """Formatea VerificationReport."""
    status = "✅ VERIFICADO" if data.verified else "❌ NO VERIFICADO"
    lines = [f"🔎 *VERIFICACIÓN* — {status}\n"]
    lines.append(f"📊 *Calidad:* {data.quality_score}/10\n")

    if data.issues_found:
        lines.append("⚠️ *Issues*")
        for i in data.issues_found:
            lines.append(f"  • {i}")

    if data.improvements:
        lines.append("\n💡 *Mejoras*")
        for m in data.improvements:
            lines.append(f"  • {m}")

    lines.append(f"\n📋 *Veredicto:* {data.final_verdict}")
    return "\n".join(lines)


def _format_mvp_dict(data: dict) -> str:
    """Formatea MVP desde dict."""
    lines = ["🚀 *MVP PLAN*\n"]
    lines.append(f"💡 *Propuesta de Valor*\n{data.get('value_proposition', '')}\n")
    lines.append(f"🎯 *Usuario Objetivo*\n{data.get('target_user', '')}\n")

    for f in data.get("features", []):
        if isinstance(f, dict):
            emoji = "🔴" if f.get("priority") == "P0" else "🟡"
            lines.append(f"  {emoji} *{f.get('name', '')}* ({f.get('priority', '')} | {f.get('effort', '')})")
            lines.append(f"      {f.get('description', '')}\n")

    lines.append(f"🛠 *Tech Stack*\n{data.get('tech_stack', '')}\n")
    lines.append(f"📅 *Timeline*\n{data.get('timeline', '')}\n")

    for m in data.get("metrics", []):
        lines.append(f"  • {m}")

    lines.append(f"\n💰 *Monetización*\n{data.get('monetization', '')}")
    return "\n".join(lines)


def _format_research_dict(data: dict) -> str:
    """Formatea Research desde dict."""
    lines = ["🔬 *REPORTE DE INVESTIGACIÓN*\n"]
    lines.append(f"📋 {data.get('executive_summary', '')}\n")
    lines.append(f"📈 *Mercado:* {data.get('market_size', '')}\n")
    lines.append(f"🎯 *Veredicto:* {data.get('go_no_go', '')} ({data.get('confidence_score', '?')}/10)")
    return "\n".join(lines)


def _format_raw_pydantic(raw: str, mode: str) -> str:
    """Parsea y formatea string crudo de Pydantic cuando no hay .pydantic."""
    import re

    mode_emojis = {
        "research": "🔬", "full_mvp": "🚀", "grant_hunt": "💰",
        "content": "✍️", "daily_ops": "☀️", "weekly_report": "📊",
        "enigma_audit": "🛡", "code_review": "🔍", "build_project": "🏗",
    }
    header = f"{mode_emojis.get(mode, '📋')} *{mode.upper().replace('_', ' ')}*\n"

    # Extraer campos key='value' del string Pydantic
    field_labels = {
        "value_proposition": "💡 *Propuesta de Valor*",
        "target_user": "🎯 *Usuario Objetivo*",
        "tech_stack": "🛠 *Tech Stack*",
        "timeline": "📅 *Timeline*",
        "monetization": "💰 *Monetización*",
        "executive_summary": "📋 *Resumen Ejecutivo*",
        "market_size": "📈 *Tamaño de Mercado*",
        "go_no_go": "✅ *Veredicto*",
        "overall_verdict": "📊 *Veredicto*",
        "narrative_strategy": "📖 *Estrategia*",
        "top_recommendation": "⭐ *Top Recomendación*",
    }

    lines = [header]

    # Extraer campos simples con regex
    for field, label in field_labels.items():
        pattern = rf"{field}='(.*?)(?:'\s+\w+=|'$)"
        match = re.search(pattern, raw, re.DOTALL)
        if match:
            value = match.group(1).strip()
            if value:
                lines.append(f"{label}\n{value}\n")

    # Extraer listas (metrics, risks, pain_points, etc.)
    list_labels = {
        "metrics": "📊 *Métricas*",
        "risks": "⚠️ *Riesgos*",
        "pain_points": "😤 *Pain Points*",
        "trends": "📈 *Tendencias*",
        "next_steps": "📋 *Próximos Pasos*",
        "quick_wins": "⚡ *Quick Wins*",
        "improvements": "💡 *Mejoras*",
        "security_notes": "🔒 *Seguridad*",
        "recommendations": "💡 *Recomendaciones*",
    }

    for field, label in list_labels.items():
        pattern = rf"{field}=\[(.*?)\]"
        match = re.search(pattern, raw, re.DOTALL)
        if match:
            items_raw = match.group(1)
            items = re.findall(r"'(.*?)'", items_raw)
            if items:
                lines.append(f"{label}")
                for item in items:
                    lines.append(f"  • {item}")
                lines.append("")

    # Extraer features (MVPFeature objects)
    features = re.findall(
        r"MVPFeature\(name='(.*?)',\s*priority='(.*?)',\s*effort='(.*?)',\s*description='(.*?)'\)",
        raw, re.DOTALL,
    )
    if features:
        lines.append("⚙️ *Features*")
        for name, priority, effort, desc in features:
            emoji = "🔴" if priority == "P0" else "🟡" if priority == "P1" else "🟢"
            lines.append(f"  {emoji} *{name}* ({priority} | {effort})")
            lines.append(f"      {desc}\n")

    result = "\n".join(lines)
    return result if len(result) > len(header) + 10 else raw


# ═══════════════════════════════════════════════════════
# CREW EXECUTOR
# ═══════════════════════════════════════════════════════

def _save_result(result_str: str, mode: str, project: str | None = None) -> str:
    """Guarda resultado en archivo y retorna la ruta."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(PROJECT_ROOT, "output", project) if project else os.path.join(PROJECT_ROOT, "output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{mode}_{ts}.md")
    with open(out_path, "w") as f:
        f.write(f"# {mode}\n**Fecha:** {datetime.now():%Y-%m-%d %H:%M}\n\n---\n\n{result_str}")
    return out_path


def _send_long_message(bot, chat_id: int, text: str, file_path: str | None = None):
    """Envía mensaje largo a Telegram, partiendo en chunks si es necesario."""
    MAX_LEN = 4000

    if len(text) <= MAX_LEN:
        try:
            bot.send_message(chat_id, text, parse_mode="Markdown")
        except Exception:
            # Si falla Markdown, enviar sin formato
            bot.send_message(chat_id, text)
        return

    # Partir por secciones (doble newline) para no cortar ideas
    chunks = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > MAX_LEN:
            if current:
                chunks.append(current)
            current = line
        else:
            current = current + "\n" + line if current else line
    if current:
        chunks.append(current)

    for i, chunk in enumerate(chunks):
        try:
            bot.send_message(chat_id, chunk, parse_mode="Markdown")
        except Exception:
            bot.send_message(chat_id, chunk)

    # Enviar archivo completo al final
    if file_path and os.path.exists(file_path):
        with open(file_path, "rb") as f:
            bot.send_document(chat_id, f, caption="📄 Resultado completo")


def _extract_voice_summary(result, formatted_text: str) -> str:
    """Extrae un resumen corto y útil para leer en voz alta."""
    import re

    # Intentar extraer executive_summary o value_proposition del resultado
    summary = ""

    # Desde Pydantic object
    data = None
    if hasattr(result, "pydantic") and result.pydantic:
        data = result.pydantic
    elif hasattr(result, "json_dict") and result.json_dict:
        data = result.json_dict

    if data:
        if hasattr(data, "executive_summary") and data.executive_summary:
            summary = data.executive_summary
        elif hasattr(data, "value_proposition") and data.value_proposition:
            summary = data.value_proposition
        elif hasattr(data, "overall_verdict") and data.overall_verdict:
            summary = data.overall_verdict
        elif hasattr(data, "body") and data.body:
            summary = data.body[:300]

    # Desde raw string si no encontramos pydantic
    if not summary:
        raw = str(result) if not isinstance(result, str) else result
        for field in ["executive_summary", "value_proposition", "final_verdict", "overall_verdict"]:
            match = re.search(rf"{field}='(.*?)'(?:\s+\w+=|$)", raw, re.DOTALL)
            if match and len(match.group(1)) > 20:
                summary = match.group(1)
                break

    # Último fallback: primer párrafo real del texto formateado
    if not summary:
        clean = re.sub(r'[*_`#]', '', formatted_text)
        clean = re.sub(r'[\U0001f300-\U0001f9ff\U00002600-\U000027bf\U0000fe00-\U0000fe0f\U0000200d]', '', clean)
        lines = [l.strip() for l in clean.split("\n") if len(l.strip()) > 30]
        summary = lines[0] if lines else ""

    # Limitar a ~400 chars para que el audio sea corto
    if len(summary) > 400:
        # Cortar en punto o coma para no truncar a medio
        cut = summary[:400].rfind(".")
        if cut > 200:
            summary = summary[:cut + 1]
        else:
            summary = summary[:400]

    return summary.strip()


def _send_voice_summary(bot, chat_id: int, formatted_text: str, msg_id: int, result=None):
    """Genera y envía resumen de voz con Edge-TTS Salome."""
    try:
        import asyncio
        import edge_tts

        summary = _extract_voice_summary(result, formatted_text) if result else ""
        if not summary or len(summary) < 15:
            return

        audio_path = f"/tmp/tg_summary_{msg_id}.mp3"

        async def _gen():
            communicate = edge_tts.Communicate(summary, "es-CO-SalomeNeural")
            await communicate.save(audio_path)

        asyncio.run(_gen())

        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            with open(audio_path, "rb") as af:
                bot.send_voice(chat_id, af)
            try:
                os.remove(audio_path)
            except OSError:
                pass
    except Exception as e:
        logger.warning(f"Voice summary error (non-critical): {e}")


def _detect_failed_provider(error_str: str) -> str | None:
    """Detecta qué provider falló basándose en el mensaje de error."""
    error_lower = error_str.lower()
    if "groq" in error_lower:
        return "groq"
    if "nvidia" in error_lower or "nim" in error_lower:
        return "nvidia"
    if "cerebras" in error_lower:
        return "cerebras"
    if "zhipu" in error_lower or "z.ai" in error_lower or "glm" in error_lower:
        return "zhipu"
    # Detectar por modelo
    if "llama-3.3" in error_lower or "qwen3-32b" in error_lower or "kimi-k2-instruct" in error_lower:
        return "groq"
    if "deepseek" in error_lower and "nvidia_nim" in error_lower:
        return "nvidia"
    if "gpt-oss" in error_lower:
        return "cerebras"
    return None


def _create_crew(mode: str, task: str, project: str | None):
    """Crea el crew correspondiente al modo."""
    from crew import (
        create_research_crew, create_pure_research_crew,
        create_full_mvp_crew,
        create_grant_hunt_crew, create_content_crew,
        create_daily_ops_crew, create_weekly_report_crew,
        create_enigma_audit_crew, create_build_project_crew,
        create_code_review_crew,
    )

    creators = {
        "research": lambda: create_pure_research_crew(task),
        "full_mvp": lambda: create_full_mvp_crew(task),
        "grant_hunt": lambda: create_grant_hunt_crew(task, project),
        "content": lambda: create_content_crew(task, project),
        "daily_ops": lambda: create_daily_ops_crew(),
        "weekly_report": lambda: create_weekly_report_crew(project),
        "enigma_audit": lambda: create_enigma_audit_crew(task or "database"),
        "build_project": lambda: create_build_project_crew(task, "telegram_project"),
        "code_review": lambda: create_code_review_crew(task or "."),
    }
    creator = creators.get(mode)
    if not creator:
        return None
    return creator()


def _run_crew_async(bot, message, mode: str, task: str = "", project: str | None = None):
    """Ejecuta un crew en thread separado con core.crew_runner (FASE 0)."""
    def _execute():
        from core.crew_runner import run_crew
        from core.providers import ProviderManager

        pm = ProviderManager()
        user_info = f"{message.from_user.first_name or ''} ({message.from_user.id})" if message.from_user else "unknown"

        crew = _create_crew(mode, task, project)
        if not crew:
            bot.send_message(message.chat.id, f"Modo '{mode}' no soportado")
            return

        # Execute with full FASE 0 infrastructure
        result = run_crew(mode, crew, input_text=task or "")

        # Log execution
        _log_execution({
            "timestamp": datetime.now().isoformat(),
            "source": "telegram",
            "user": user_info,
            "crew": mode,
            "project": project,
            "task": task[:200] if task else "",
            "status": result["status"],
            "duration_sec": round(result["elapsed_ms"] / 1000, 1),
            "attempts": result["retries"] + 1,
            "run_id": result["run_id"],
            "output_path": None,
            "error": result.get("error"),
            "supervisor": result.get("supervisor"),
            "governance": result.get("governance"),
        })

        if result["status"] == "ok":
            formatted = _format_result(type("R", (), {"raw": result["output"]})(), mode)
            out_path = _save_result(result["output"], mode, project)

            _log_execution({
                "timestamp": datetime.now().isoformat(),
                "source": "telegram",
                "user": user_info,
                "crew": mode,
                "status": "success",
                "output_path": out_path,
                "duration_sec": round(result["elapsed_ms"] / 1000, 1),
                "attempts": result["retries"] + 1,
                "run_id": result["run_id"],
            })

            # Append supervisor info if available
            sup = result.get("supervisor")
            if sup and sup.get("score"):
                formatted += f"\n\n---\nCalidad: {sup['score']}/10"

            _send_long_message(bot, message.chat.id, formatted, out_path)
            _send_voice_summary(bot, message.chat.id, formatted, message.message_id,
                                type("R", (), {"raw": result["output"]})())

            logger.info(f"Crew {mode} completado ({result['elapsed_ms']:.0f}ms, "
                        f"{result['retries']} retries, run={result['run_id']})")

        elif result["status"] == "escalated":
            sup = result.get("supervisor", {})
            bot.send_message(message.chat.id,
                f"La calidad del resultado no cumple el umbral minimo.\n"
                f"Score: {sup.get('score', '?')}/10\n"
                f"Razones: {', '.join(sup.get('reasons', []))}\n\n"
                f"Resultado parcial entregado de todas formas.",
                parse_mode=None)
            if result["output"]:
                formatted = _format_result(type("R", (), {"raw": result["output"]})(), mode)
                _send_long_message(bot, message.chat.id, formatted, None)

        else:
            # Error
            error = result.get("error", "Unknown error")
            active = pm.get_active()
            status = pm.get_status()

            exhausted = [n for n, s in status.items() if s["exhausted"]]
            if exhausted:
                recovery_info = ", ".join(
                    f"{n} ({s['recovery_in']}s)" for n, s in status.items() if s["exhausted"]
                )
                bot.send_message(message.chat.id,
                    f"Providers agotados: {', '.join(exhausted)}\n"
                    f"Recovery: {recovery_info}\n"
                    f"Activos: {', '.join(active) if active else 'ninguno'}\n\n"
                    f"Intenta de nuevo en unos minutos.",
                    parse_mode=None)
            else:
                clean_err = error[:300].split("\\n")[0]
                bot.send_message(message.chat.id, f"Error en {mode}: {clean_err}")

    thread = threading.Thread(target=_execute, daemon=True)
    thread.start()


# ═══════════════════════════════════════════════════════
# VOZ — Transcripción + ejecución + respuesta audio
# ═══════════════════════════════════════════════════════

def _convert_ogg_to_wav(ogg_path: str) -> str | None:
    """Convierte OGG/opus de Telegram a WAV usando ffmpeg."""
    import subprocess
    wav_path = ogg_path.rsplit(".", 1)[0] + ".wav"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", ogg_path, "-ar", "16000", "-ac", "1", "-sample_fmt", "s16", wav_path],
            capture_output=True, timeout=30,
        )
        if os.path.exists(wav_path) and os.path.getsize(wav_path) > 0:
            return wav_path
    except Exception as e:
        logger.error(f"ffmpeg conversion error: {e}")
    return None


def _handle_voice_message(bot, message):
    """Procesa mensaje de voz: OGG→WAV→transcribe→rutea→responde texto + audio."""
    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded = bot.download_file(file_info.file_path)
        ogg_path = f"/tmp/voice_{message.message_id}.ogg"
        with open(ogg_path, "wb") as f:
            f.write(downloaded)

        # Convertir OGG/opus → WAV (Whisper necesita formato limpio)
        wav_path = _convert_ogg_to_wav(ogg_path)
        audio_path = wav_path or ogg_path  # fallback al OGG si ffmpeg falla

        from interfaces.voice_interface import transcribe_audio, text_to_speech
        text = transcribe_audio(audio_path)

        # Cleanup
        for p in [ogg_path, wav_path]:
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass

        if not text:
            bot.reply_to(message, "❌ No pude transcribir el audio. Verifica que el audio tenga voz clara.")
            return

        bot.reply_to(message, f"🎙️ Escuche: \"{text}\"\n\n⏳ Procesando...")

        # Rutear el texto transcrito al crew correcto (usa _run_crew_async con retry)
        mode, label = classify_message(text)
        project = _detect_project(text)

        if mode == "unknown":
            mode = "research"
            label = "Equipo completo (máxima calidad)"

        bot.send_message(message.chat.id, f"🔄 *{label}*. Ejecutando crew...", parse_mode="Markdown")
        _run_crew_async(bot, message, mode, task=text, project=project)

    except Exception as e:
        bot.reply_to(message, f"❌ Error procesando audio: {e}")


# ═══════════════════════════════════════════════════════
# BOT PRINCIPAL
# ═══════════════════════════════════════════════════════

def start_bot():
    """Inicia OpenClawd Telegram Bot con polling infinito."""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN no configurado en .env")
        print("❌ TELEGRAM_BOT_TOKEN no configurado. Crea un bot en @BotFather y pon el token en .env")
        return

    import telebot

    bot = telebot.TeleBot(TELEGRAM_TOKEN)
    logger.info("OpenClawd Telegram Bot iniciando...")

    # ─── /start, /help ───
    @bot.message_handler(commands=["start", "help"])
    def cmd_help(message):
        bot.reply_to(message, (
            "🤖 *OpenClawd — Cyber Paisa Mission Control*\n\n"
            "*Comandos:*\n"
            "/daily — Rutina matutina COO\n"
            "/weekly `[PROYECTO]` — Reporte semanal\n"
            "/research `TEMA` — Investigar un tema\n"
            "/grant `[PROYECTO]` — Buscar grants\n"
            "/content `DESCRIPCION` — Generar contenido\n"
            "/mvp `IDEA` — Generar MVP completo\n"
            "/audit `TARGET` — Auditoria Enigma\n"
            "/build `DESCRIPCION` — Generar proyecto\n"
            "/code `PATH` — Code review\n"
            "/projects — Listar proyectos\n"
            "/status — Estado del sistema\n"
            "/agents — Info de los 14+ agentes\n"
            "/dof `PREGUNTA` — Hablar directo con DOF Oracle\n"
            "/claude `INSTRUCCION` — Ordenar a Claude Code\n"
            "/team `TAREA` — Lanzar equipo de 3 agentes Claude\n\n"
            "*Texto libre:*\n"
            "Escribe cualquier cosa → DOF Oracle responde directo.\n"
            "Para crews especializados usa: /mvp, /grant, /audit, etc.\n\n"
            "*Voz:*\n"
            "Envia un audio y lo transcribo + ejecuto + respondo con voz."
        ), parse_mode="Markdown")

    # ─── /projects ───
    @bot.message_handler(commands=["projects"])
    def cmd_projects(message):
        try:
            import yaml
            projects_path = os.path.join(PROJECT_ROOT, "config", "projects.yaml")
            if not os.path.exists(projects_path):
                bot.reply_to(message, "No hay projects.yaml configurado")
                return
            with open(projects_path, "r") as f:
                data = yaml.safe_load(f)
            if not data or "projects" not in data:
                bot.reply_to(message, "No hay proyectos registrados")
                return
            lines = "📋 *Proyectos Activos:*\n\n"
            for p in data["projects"]:
                emoji = "🟢" if p.get("status") == "active" else "🟡"
                lines += f"{emoji} *{p['name']}* ({p.get('ecosystem', '?')})\n"
                lines += f"   {p.get('description', '').strip()[:100]}\n\n"
            bot.reply_to(message, lines, parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {e}")

    # ─── /status ───
    @bot.message_handler(commands=["status"])
    def cmd_status(message):
        try:
            from llm_config import validate_keys
            status = validate_keys()
            lines = "📊 *Estado del Sistema:*\n\n"
            active = 0
            for key, val in status.items():
                emoji = "✅" if val else "❌"
                lines += f"{emoji} {key}\n"
                if val:
                    active += 1
            lines += f"\n*{active}/{len(status)}* providers activos"
            bot.reply_to(message, lines, parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {e}")

    # ─── /agents ───
    @bot.message_handler(commands=["agents"])
    def cmd_agents(message):
        agents_info = (
            "🤖 *8 Agentes — Equipo Completo*\n\n"
            "Todos trabajan en cualquier tarea genérica.\n"
            "Ordenados por calidad de LLM:\n\n"
            "1. *MVP Strategist* — Qwen3.5-397B (NVIDIA) 🧠 Mejor razonamiento\n"
            "2. *Code Architect* — Kimi K2.5 (NVIDIA) 💻 Mejor análisis técnico\n"
            "3. *Research Analyst* — Llama 3.3 70B (Groq) 🔍 Mejor recolección web\n"
            "4. *QA Reviewer* — GPT-OSS 120B (Cerebras) ✅ Control de calidad\n"
            "5. *Verifier* — GPT-OSS 120B (Cerebras) 🔎 Fact-checking\n"
            "6. *Data Engineer* — GPT-OSS 120B (Cerebras) 📊 Datos y métricas\n"
            "7. *Project Organizer* — Qwen3-32B (Groq) 📋 Coordinación\n"
            "8. *Narrative Content* — GLM-4.7-Flash (Zhipu) ✍️ Contenido\n\n"
            "📌 *Genérico:* Todos colaboran (máxima calidad)\n"
            "🎯 *Especialista:* Se activa con /mvp, /grant, /code, etc."
        )
        bot.reply_to(message, agents_info, parse_mode="Markdown")

    # ─── /dof — DOF Oracle directo ───
    @bot.message_handler(commands=["dof"])
    def cmd_dof(message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, "Soy DOF Oracle — Enigma #1686. Preguntame lo que quieras.\nEj: `/dof que es la gobernanza determinística?`", parse_mode="Markdown")
            return
        question = parts[1]
        bot.reply_to(message, "🧠 *DOF Oracle pensando...*", parse_mode="Markdown")

        def _reply():
            try:
                reply = _dof_direct_reply(message.chat.id, question)
                bot.send_message(message.chat.id, reply, parse_mode="Markdown")
            except Exception as e:
                bot.send_message(message.chat.id, f"Error: {e}")

        thread = threading.Thread(target=_reply, daemon=True)
        thread.start()

    # ─── Claude Commander — ordena a Claude Code desde Telegram ───
    @bot.message_handler(commands=["claude"])
    def cmd_claude(message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, (
                "*Claude Commander* — Ordena a Claude Code directamente\n\n"
                "Uso: `/claude <instrucción>`\n\n"
                "Ejemplos:\n"
                "• `/claude cuenta los archivos .py en core/`\n"
                "• `/claude lee core/governance.py y dime cuantas HARD_RULES hay`\n"
                "• `/claude corre los tests de core/`\n"
            ), parse_mode="Markdown")
            return
        instruction = parts[1]

        # Write order to queue file — Claude Code session picks it up
        queue_dir = os.path.join(PROJECT_ROOT, "logs", "commander", "queue")
        os.makedirs(queue_dir, exist_ok=True)
        order_id = f"{int(time.time())}_{message.chat.id}"
        order_file = os.path.join(queue_dir, f"{order_id}.json")
        order = {
            "id": order_id,
            "instruction": instruction,
            "from": message.from_user.first_name if message.from_user else "unknown",
            "chat_id": message.chat.id,
            "timestamp": time.time(),
            "iso": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "status": "pending",
        }
        with open(order_file, "w") as f:
            json.dump(order, f, ensure_ascii=False)

        bot.reply_to(message, (
            f"⚡ *Orden enviada a Claude Code*\n"
            f"_{instruction}_\n\n"
            f"ID: `{order_id}`\n"
            f"La sesión activa de Claude Code la recibirá."
        ), parse_mode="Markdown")

        # ALSO spawn SDK for immediate response
        def _run_claude():
            try:
                import asyncio
                from core.claude_commander import ClaudeCommander
                commander = ClaudeCommander(
                    cwd=PROJECT_ROOT,
                    model='claude-haiku-4-5-20251001',
                    max_turns=10,
                    max_budget_usd=0.25,
                )
                result = asyncio.run(commander.command(instruction))
                # Mark order as completed
                order["status"] = "completed"
                order["result"] = result.output[:2000] if result.output else ""
                order["elapsed_ms"] = result.elapsed_ms
                with open(order_file, "w") as f:
                    json.dump(order, f, ensure_ascii=False)

                clean = result.output
                if clean and len(clean) > 3500:
                    clean = clean[:3500] + "..."
                reply = f"*Status:* `{result.status}`\n*Elapsed:* {result.elapsed_ms:.0f}ms\n\n{clean}"
                _send_long_message(bot, message.chat.id, reply)
            except Exception as e:
                order["status"] = "error"
                order["error"] = str(e)
                with open(order_file, "w") as f:
                    json.dump(order, f, ensure_ascii=False)
                bot.send_message(message.chat.id, f"Commander error: {e}")

        thread = threading.Thread(target=_run_claude, daemon=True)
        thread.start()

    @bot.message_handler(commands=["team"])
    def cmd_team(message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, (
                "*Agent Team* — Equipo de Claude Code agents\n\n"
                "Uso: `/team <tarea>`\n\n"
                "Lanza 3 agentes en paralelo: reviewer, security, tester"
            ), parse_mode="Markdown")
            return
        task = parts[1]
        bot.reply_to(message, f"⚡ *Team → 3 Claude Agents*\n_{task}_", parse_mode="Markdown")

        def _run_team():
            try:
                import asyncio
                from core.claude_commander import ClaudeCommander
                commander = ClaudeCommander(
                    cwd=PROJECT_ROOT,
                    model='claude-haiku-4-5-20251001',
                    max_turns=8,
                    max_budget_usd=0.50,
                )
                team_result = asyncio.run(commander.run_team(
                    task=task,
                    agents={
                        "reviewer": "Review code quality and suggest improvements",
                        "security": "Check for security vulnerabilities",
                        "tester": "Verify tests pass and suggest missing tests",
                    }
                ))
                reply_parts = [f"*Team Status:* `{team_result.status}` ({team_result.elapsed_ms:.0f}ms)\n"]
                for name, res in team_result.results.items():
                    output = res.output[:800] if res.output else "(no output)"
                    reply_parts.append(f"*{name}:* `{res.status}`\n{output}\n")
                _send_long_message(bot, message.chat.id, "\n".join(reply_parts))
            except Exception as e:
                bot.send_message(message.chat.id, f"Team error: {e}")

        thread = threading.Thread(target=_run_team, daemon=True)
        thread.start()

    # ─── /daemon — Start/stop autonomous daemon from Telegram ───
    @bot.message_handler(commands=["daemon"])
    def cmd_daemon(message):
        parts = message.text.split()
        subcmd = parts[1] if len(parts) > 1 else "status"

        if subcmd == "start":
            cycles = int(parts[2]) if len(parts) > 2 else 0
            bot.reply_to(message, (
                f"🤖 *Autonomous Daemon Starting*\n"
                f"Cycles: {'infinite' if cycles == 0 else cycles}\n"
                f"Model: claude-opus-4-6\n"
                f"Budget: $2/cycle\n\n"
                f"_The daemon will monitor, decide, and act autonomously._"
            ), parse_mode="Markdown")

            def _run_daemon():
                try:
                    import asyncio
                    from core.autonomous_daemon import AutonomousDaemon
                    daemon = AutonomousDaemon(
                        cycle_interval=120,
                        model="claude-opus-4-6",
                        budget_per_cycle=2.0,
                    )
                    asyncio.run(daemon.run(max_cycles=cycles))
                    bot.send_message(message.chat.id, f"Daemon finished: {daemon.cycle_count} cycles")
                except Exception as e:
                    bot.send_message(message.chat.id, f"Daemon error: {e}")

            thread = threading.Thread(target=_run_daemon, daemon=True)
            thread.start()

        elif subcmd == "status":
            try:
                log_path = os.path.join(PROJECT_ROOT, "logs", "daemon", "cycles.jsonl")
                if not os.path.exists(log_path):
                    bot.reply_to(message, "No daemon cycles recorded yet.\nUse `/daemon start` to begin.", parse_mode="Markdown")
                    return
                with open(log_path) as f:
                    lines = f.readlines()
                total = len(lines)
                if total == 0:
                    bot.reply_to(message, "No daemon cycles recorded.")
                    return
                last = json.loads(lines[-1])
                bot.reply_to(message, (
                    f"📊 *Daemon Status*\n\n"
                    f"Total cycles: {total}\n"
                    f"Last: {last.get('iso', '?')}\n"
                    f"Mode: {last.get('mode', '?')}\n"
                    f"Result: {last.get('result_status', '?')}\n"
                    f"Agents: {last.get('agents_spawned', 0)}\n"
                    f"Elapsed: {last.get('elapsed_ms', 0):.0f}ms"
                ), parse_mode="Markdown")
            except Exception as e:
                bot.reply_to(message, f"Error: {e}")
        else:
            bot.reply_to(message, (
                "*Daemon Commands:*\n"
                "`/daemon status` — Check daemon status\n"
                "`/daemon start` — Start infinite daemon\n"
                "`/daemon start 5` — Run 5 cycles"
            ), parse_mode="Markdown")

    # ─── /parallel — Spawn N parallel Claude sessions ───
    @bot.message_handler(commands=["parallel"])
    def cmd_parallel(message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, (
                "*Parallel Sessions* — N agentes Claude en paralelo\n\n"
                "Uso: `/parallel <N> <tarea>`\n\n"
                "Ejemplos:\n"
                "• `/parallel 3 investiga frameworks de AI agents`\n"
                "• `/parallel 5 busca vulnerabilidades en core/`\n"
                "• `/parallel 2 escribe tests para core/governance.py`"
            ), parse_mode="Markdown")
            return

        # Parse: /parallel N task
        rest = parts[1].split(maxsplit=1)
        try:
            n_agents = int(rest[0])
            task = rest[1] if len(rest) > 1 else "Analyze the DOF system"
        except ValueError:
            n_agents = 3
            task = parts[1]

        n_agents = min(n_agents, 10)  # Safety cap
        bot.reply_to(message, (
            f"⚡ *Spawning {n_agents} parallel Claude sessions*\n"
            f"Task: _{task}_\n\n"
            f"_Each agent works independently with its own context._"
        ), parse_mode="Markdown")

        def _run_parallel():
            try:
                import asyncio
                from core.claude_commander import ClaudeCommander

                commander = ClaudeCommander(
                    cwd=PROJECT_ROOT,
                    model='claude-haiku-4-5-20251001',
                    max_turns=10,
                    max_budget_usd=0.25 * n_agents,
                )

                agents = {}
                roles = [
                    "analyst", "researcher", "critic", "builder", "auditor",
                    "optimizer", "tester", "documenter", "strategist", "reviewer"
                ]
                for i in range(n_agents):
                    role = roles[i % len(roles)]
                    agents[f"{role}-{i+1}"] = f"Perspective #{i+1} as {role}: {task}"

                team_result = asyncio.run(commander.run_team(
                    task=task, agents=agents, parallel=True
                ))

                reply_parts = [
                    f"*{n_agents} Sessions Complete* — `{team_result.status}` ({team_result.elapsed_ms:.0f}ms)\n"
                ]
                for name, res in team_result.results.items():
                    output = res.output[:600] if res.output else "(no output)"
                    reply_parts.append(f"*{name}:* `{res.status}`\n{output}\n---")

                _send_long_message(bot, message.chat.id, "\n".join(reply_parts))

            except Exception as e:
                bot.send_message(message.chat.id, f"Parallel error: {e}")

        thread = threading.Thread(target=_run_parallel, daemon=True)
        thread.start()

    # ─── /sessions — View active/recent Claude sessions ───
    @bot.message_handler(commands=["sessions"])
    def cmd_sessions(message):
        try:
            log_path = os.path.join(PROJECT_ROOT, "logs", "commander", "commands.jsonl")
            if not os.path.exists(log_path):
                bot.reply_to(message, "No commander sessions yet.")
                return
            with open(log_path) as f:
                lines = f.readlines()
            recent = lines[-10:] if len(lines) > 10 else lines
            reply_parts = [f"📋 *Recent Claude Sessions* ({len(lines)} total)\n"]
            for line in reversed(recent):
                try:
                    entry = json.loads(line)
                    mode = entry.get("mode", "?")
                    status = entry.get("status", "?")
                    elapsed = entry.get("elapsed_ms", 0)
                    iso = entry.get("iso", "?")
                    icon = "✅" if status == "success" else "❌" if status == "error" else "🔄"
                    reply_parts.append(f"{icon} `{iso}` {mode} — {status} ({elapsed:.0f}ms)")
                except Exception:
                    pass
            bot.reply_to(message, "\n".join(reply_parts), parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"Error: {e}")

    # ─── /approve, /redirect — Feedback loop for daemon ───
    @bot.message_handler(commands=["approve"])
    def cmd_approve(message):
        from core.autonomous_daemon import submit_feedback
        submit_feedback("approve", "User approved via Telegram")
        bot.reply_to(message, "Daemon action approved.")

    @bot.message_handler(commands=["redirect"])
    def cmd_redirect(message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, "Uso: `/redirect <nueva instruccion>`", parse_mode="Markdown")
            return
        from core.autonomous_daemon import submit_feedback
        submit_feedback("redirect", parts[1])
        bot.reply_to(message, f"Daemon redirected: _{parts[1]}_", parse_mode="Markdown")

    # ─── /mesh — Node Mesh commands ───
    @bot.message_handler(commands=["mesh"])
    def cmd_mesh(message):
        parts = message.text.split(maxsplit=2)
        subcmd = parts[1] if len(parts) > 1 else "status"

        if subcmd == "status":
            try:
                from core.node_mesh import NodeMesh
                mesh = NodeMesh(cwd=PROJECT_ROOT)
                bot.reply_to(message, f"```\n{mesh.status_report()}\n```", parse_mode="Markdown")
            except Exception as e:
                bot.reply_to(message, f"Mesh error: {e}")

        elif subcmd == "discover":
            try:
                from core.node_mesh import NodeMesh
                mesh = NodeMesh(cwd=PROJECT_ROOT)
                sessions = mesh.discover_sessions()
                imported = mesh.import_discovered_sessions()
                lines = [f"*Node Mesh Discovery*\n\nFound {len(sessions)} active Claude sessions, imported {imported} new nodes.\n"]
                for s in sessions[:10]:
                    lines.append(f"  `{s['session_id'][:12]}` | {s.get('project', '?')} | {s.get('model', '?')}")
                bot.reply_to(message, "\n".join(lines), parse_mode="Markdown")
            except Exception as e:
                bot.reply_to(message, f"Discovery error: {e}")

        elif subcmd == "spawn":
            if len(parts) < 3:
                bot.reply_to(message, "Uso: `/mesh spawn <node_id> <tarea>`", parse_mode="Markdown")
                return
            rest = parts[2].split(maxsplit=1)
            node_id = rest[0]
            task = rest[1] if len(rest) > 1 else "Execute your role"
            bot.reply_to(message, f"Spawning mesh node `{node_id}`...", parse_mode="Markdown")

            def _run():
                try:
                    import asyncio
                    from core.node_mesh import NodeMesh
                    mesh = NodeMesh(cwd=PROJECT_ROOT)
                    node = asyncio.run(mesh.spawn_node(node_id, task))
                    bot.send_message(message.chat.id,
                        f"Node `{node.node_id}` spawned\n"
                        f"Status: {node.status}\n"
                        f"Session: `{node.session_id[:12] if node.session_id else 'none'}`",
                        parse_mode="Markdown")
                except Exception as e:
                    bot.send_message(message.chat.id, f"Spawn error: {e}")

            threading.Thread(target=_run, daemon=True).start()

        elif subcmd == "send":
            if len(parts) < 3:
                bot.reply_to(message, "Uso: `/mesh send <from> <to> <mensaje>`", parse_mode="Markdown")
                return
            msg_parts = parts[2].split(maxsplit=2)
            if len(msg_parts) < 3:
                bot.reply_to(message, "Uso: `/mesh send <from> <to> <mensaje>`", parse_mode="Markdown")
                return
            from core.node_mesh import NodeMesh
            mesh = NodeMesh(cwd=PROJECT_ROOT)
            msg = mesh.send_message(msg_parts[0], msg_parts[1], msg_parts[2])
            bot.reply_to(message, f"Message sent: `{msg.msg_id}`\n{msg_parts[0]} → {msg_parts[1]}", parse_mode="Markdown")

        elif subcmd == "full":
            bot.reply_to(message, "Spawning full DOF mesh (6 nodes)...", parse_mode="Markdown")

            def _run():
                try:
                    import asyncio
                    from core.node_mesh import spawn_dof_mesh
                    mesh = asyncio.run(spawn_dof_mesh())
                    bot.send_message(message.chat.id, f"```\n{mesh.status_report()}\n```", parse_mode="Markdown")
                except Exception as e:
                    bot.send_message(message.chat.id, f"Mesh error: {e}")

            threading.Thread(target=_run, daemon=True).start()

        else:
            bot.reply_to(message, (
                "*Node Mesh Commands:*\n\n"
                "`/mesh status` — Ver estado de la red\n"
                "`/mesh discover` — Descubrir sesiones Claude activas\n"
                "`/mesh spawn <node> <tarea>` — Crear nodo\n"
                "`/mesh send <from> <to> <msg>` — Enviar mensaje entre nodos\n"
                "`/mesh full` — Spawn red completa DOF (6 nodos)"
            ), parse_mode="Markdown")

    # ─── /multidaemon — 3 specialized daemons in parallel ───
    @bot.message_handler(commands=["multidaemon"])
    def cmd_multidaemon(message):
        parts = message.text.split()
        cycles = int(parts[1]) if len(parts) > 1 else 0
        bot.reply_to(message, (
            f"🧠 *Multi-Daemon System Starting*\n\n"
            f"*Builder* — builds features, executes tasks\n"
            f"*Guardian* — security, tests, regression\n"
            f"*Researcher* — optimizes metrics\n\n"
            f"Cycles: {'infinite' if cycles == 0 else cycles}\n"
            f"All 3 run in parallel with persistent memory."
        ), parse_mode="Markdown")

        def _run():
            try:
                import asyncio
                from core.autonomous_daemon import run_multi_daemon
                asyncio.run(run_multi_daemon(max_cycles=cycles, model="claude-opus-4-6"))
                bot.send_message(message.chat.id, "Multi-daemon finished.")
            except Exception as e:
                bot.send_message(message.chat.id, f"Multi-daemon error: {e}")

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    # ─── Comandos de crew ───
    @bot.message_handler(commands=["daily"])
    def cmd_daily(message):
        bot.reply_to(message, "⏳ Ejecutando rutina diaria... (puede tomar unos minutos)")
        _run_crew_async(bot, message, "daily_ops")

    @bot.message_handler(commands=["weekly"])
    def cmd_weekly(message):
        parts = message.text.split(maxsplit=1)
        project = parts[1] if len(parts) > 1 else None
        bot.reply_to(message, f"⏳ Generando reporte semanal{f' para *{project}*' if project else ''}...", parse_mode="Markdown")
        _run_crew_async(bot, message, "weekly_report", project=project)

    @bot.message_handler(commands=["research"])
    def cmd_research(message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, "Uso: `/research TEMA A INVESTIGAR`", parse_mode="Markdown")
            return
        bot.reply_to(message, f"⏳ Investigando: _{parts[1]}_...", parse_mode="Markdown")
        _run_crew_async(bot, message, "research", task=parts[1])

    @bot.message_handler(commands=["grant"])
    def cmd_grant(message):
        parts = message.text.split(maxsplit=1)
        project = _detect_project(parts[1]) if len(parts) > 1 else None
        task = parts[1] if len(parts) > 1 else "Grants de AI, infraestructura Web3 y DeFi"
        bot.reply_to(message, f"⏳ Buscando grants{f' para *{project}*' if project else ''}...", parse_mode="Markdown")
        _run_crew_async(bot, message, "grant_hunt", task=task, project=project)

    @bot.message_handler(commands=["content"])
    def cmd_content(message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, "Uso: `/content DESCRIPCION DEL CONTENIDO`", parse_mode="Markdown")
            return
        project = _detect_project(parts[1])
        bot.reply_to(message, "⏳ Generando contenido...")
        _run_crew_async(bot, message, "content", task=parts[1], project=project)

    @bot.message_handler(commands=["mvp"])
    def cmd_mvp(message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, "Uso: `/mvp IDEA DEL MVP`", parse_mode="Markdown")
            return
        bot.reply_to(message, f"⏳ Generando MVP: _{parts[1]}_...", parse_mode="Markdown")
        _run_crew_async(bot, message, "full_mvp", task=parts[1])

    @bot.message_handler(commands=["audit"])
    def cmd_audit(message):
        parts = message.text.split(maxsplit=1)
        target = parts[1] if len(parts) > 1 else "database"
        bot.reply_to(message, f"⏳ Auditando: _{target}_...", parse_mode="Markdown")
        _run_crew_async(bot, message, "enigma_audit", task=target)

    @bot.message_handler(commands=["build"])
    def cmd_build(message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, "Uso: `/build DESCRIPCION DEL PROYECTO`", parse_mode="Markdown")
            return
        bot.reply_to(message, f"⏳ Generando proyecto: _{parts[1]}_...", parse_mode="Markdown")
        _run_crew_async(bot, message, "build_project", task=parts[1])

    @bot.message_handler(commands=["code"])
    def cmd_code(message):
        parts = message.text.split(maxsplit=1)
        path = parts[1] if len(parts) > 1 else "."
        bot.reply_to(message, f"⏳ Revisando codigo: _{path}_...", parse_mode="Markdown")
        _run_crew_async(bot, message, "code_review", task=path)

    # ─── Mensajes de voz ───
    @bot.message_handler(content_types=["voice"])
    def handle_voice(message):
        _handle_voice_message(bot, message)

    # ─── Archivos (Excel, documentos) ───
    @bot.message_handler(content_types=["document"])
    def handle_document(message):
        doc = message.document
        if not doc.file_name:
            bot.reply_to(message, "❌ Archivo sin nombre")
            return

        ext = doc.file_name.rsplit(".", 1)[-1].lower() if "." in doc.file_name else ""
        if ext not in ("xlsx", "xls", "csv"):
            bot.reply_to(message, f"⚠️ Solo proceso archivos Excel/CSV. Recibido: .{ext}")
            return

        try:
            file_info = bot.get_file(doc.file_id)
            downloaded = bot.download_file(file_info.file_path)
            local_path = os.path.join("/tmp", f"tg_{doc.file_name}")
            with open(local_path, "wb") as f:
                f.write(downloaded)

            bot.reply_to(message, f"⏳ Analizando *{doc.file_name}*...", parse_mode="Markdown")

            def _analyze():
                try:
                    from crew import create_data_analysis_crew
                    from core.crew_runner import run_crew
                    crew = create_data_analysis_crew(local_path)
                    result = run_crew("data_analysis", crew, input_text=local_path)
                    if result["status"] == "ok":
                        formatted = _format_result(type("R", (), {"raw": result["output"]})(), "data_analysis")
                        out_path = _save_result(result["output"], "data_analysis")
                        _send_long_message(bot, message.chat.id, formatted, out_path)
                    else:
                        bot.send_message(message.chat.id, f"Error analizando: {result.get('error', 'unknown')}")
                except Exception as e:
                    bot.send_message(message.chat.id, f"Error analizando: {e}")
                finally:
                    try:
                        os.remove(local_path)
                    except OSError:
                        pass

            thread = threading.Thread(target=_analyze, daemon=True)
            thread.start()

        except Exception as e:
            bot.reply_to(message, f"❌ Error descargando archivo: {e}")

    # ─── Fotos / imágenes → visión con moondream ───
    def _analyze_image_with_vision(image_path: str, caption: str = "") -> str:
        """Send image to Ollama moondream and return description."""
        import base64
        prompt = caption.strip() if caption.strip() else "Describe this image"
        try:
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            payload = {
                "model": "moondream",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [b64],
                    }
                ],
                "stream": False,
            }
            resp = requests.post(
                "http://localhost:11434/api/chat",
                json=payload,
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data.get("message", {}).get("content", "")
            # Strip <think>...</think> blocks
            import re
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
            return text or "No se obtuvo respuesta del modelo de visión."
        except requests.exceptions.ConnectionError:
            return "Modelo de visión no disponible. Instala: ollama pull moondream"
        except Exception as e:
            return f"Error al analizar imagen: {e}"

    @bot.message_handler(content_types=["photo"])
    def handle_photo(message):
        # Largest photo = last element in the array (highest resolution)
        photo = message.photo[-1]
        file_id = photo.file_id
        caption = message.caption or ""

        try:
            file_info = bot.get_file(file_id)
            file_path = file_info.file_path
            download_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
            local_path = f"/tmp/tg_photo_{file_id}.jpg"

            img_resp = requests.get(download_url, timeout=30)
            img_resp.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(img_resp.content)

            bot.reply_to(message, "🔍 Analizando imagen...")

            def _vision_reply():
                try:
                    analysis = _analyze_image_with_vision(local_path, caption)
                    _send_long_message(bot, message.chat.id, analysis)
                except Exception as e:
                    bot.send_message(message.chat.id, f"❌ Error procesando imagen: {e}")
                finally:
                    try:
                        os.remove(local_path)
                    except OSError:
                        pass

            thread = threading.Thread(target=_vision_reply, daemon=True)
            thread.start()

        except Exception as e:
            bot.reply_to(message, f"❌ Error descargando imagen: {e}")

    # ─── Texto libre → DOF Oracle (default) o Crew (si tiene trigger) ───
    @bot.message_handler(func=lambda m: True)
    def handle_text(message):
        text = message.text
        if not text:
            return

        # Si el mensaje tiene keywords de crew específico, usar crew
        if _should_use_crew(text):
            mode, label = classify_message(text)
            project = _detect_project(text)
            if mode == "unknown":
                mode = "research"
                label = "Equipo completo (máxima calidad)"
            bot.reply_to(message, f"🔄 *{label}*{f' | Proyecto: *{project}*' if project else ''}\n⏳ Ejecutando crew...", parse_mode="Markdown")
            _run_crew_async(bot, message, mode, task=text, project=project)
            return

        # Default: DOF Oracle responde directo (rápido, sin CrewAI overhead)
        def _reply():
            try:
                reply = _dof_direct_reply(message.chat.id, text)
                # Intentar enviar con Markdown, fallback a texto plano
                try:
                    bot.send_message(message.chat.id, reply, parse_mode="Markdown")
                except Exception:
                    bot.send_message(message.chat.id, reply)
            except Exception as e:
                bot.send_message(message.chat.id, f"Error DOF: {e}")

        thread = threading.Thread(target=_reply, daemon=True)
        thread.start()

    # ─── PID file — previene instancias duplicadas ───
    import time as _time
    PID_FILE = os.path.join(PROJECT_ROOT, "logs", "telegram_bot.pid")
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)

    # Check if another instance is already running
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as _pf:
                old_pid = int(_pf.read().strip())
            import signal as _signal
            os.kill(old_pid, _signal.SIGTERM)
            logger.info(f"Sent SIGTERM to old bot instance PID {old_pid}")
            _time.sleep(3)
        except (ProcessLookupError, ValueError):
            pass  # PID is stale or invalid — proceed
        except Exception as e:
            logger.warning(f"Could not kill old instance: {e}")

    # Write our PID
    with open(PID_FILE, "w") as _pf:
        _pf.write(str(os.getpid()))

    # ─── Polling ───
    # Limpiar webhook y sesiones anteriores para evitar Error 409
    bot.remove_webhook()
    _time.sleep(20)  # long_polling_timeout=15 — wait for old session to expire on Telegram server

    print("=" * 50)
    print("🤖 OpenClawd Telegram Bot activo")
    print(f"   Token: ...{TELEGRAM_TOKEN[-8:]}")
    print(f"   PID: {os.getpid()}")
    print("   Ctrl+C para detener")
    print("=" * 50)
    logger.info(f"OpenClawd Telegram Bot activo (PID {os.getpid()})")

    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=15, restart_on_change=False)
    except Exception as poll_err:
        logger.error(f"Polling crashed: {poll_err}")
    finally:
        # Remove PID file on exit
        try:
            os.remove(PID_FILE)
        except OSError:
            pass


if __name__ == "__main__":
    start_bot()
