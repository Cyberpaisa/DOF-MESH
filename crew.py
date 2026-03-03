"""
CrewAI Pro — 8 agentes especializados.
Cada agente se define en agents/{nombre}/SOUL.md.
Contexto compartido en shared-context/.
Cyber Paisa / Enigma Group
"""

import os
from datetime import datetime
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field
from crewai import Agent, Task, Crew, Process
from core.providers import ProviderManager, get_llm_for_role
from tools.code_tools import AnalyzeCodeTool, ListProjectFilesTool
from tools.data_tools import ReadExcelTool, QueryDatabaseTool, AnalyzeDataTool
from tools.file_tools import OrganizeProjectTool, ScanDirectoryTool
from tools.research_tools import WebResearchTool, WebSearchTool, TechStackAnalyzerTool
from tools.blockchain_tools import (
    CheckAgentEndpointTool,
    AnalyzeAgentMetadataTool,
    QuerySupabaseAgentsTool,
)
from tools.execution_tools import (
    WriteFileTool,
    ExecutePythonTool,
    RunCommandTool,
    GitOperationsTool,
)
from mcp_config import get_mcp_for_role

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ═══════════════════════════════════════════════════════
# CARGA DE CONTEXTO DESDE ARCHIVOS
# ═══════════════════════════════════════════════════════

def _read_file(path: str, max_chars: int = 800) -> str:
    """Lee un archivo y retorna su contenido truncado."""
    full = os.path.join(BASE_DIR, path)
    if not os.path.exists(full):
        return ""
    with open(full, "r") as f:
        return f.read()[:max_chars]


def load_soul(agent_name: str) -> str:
    """Lee el SOUL.md de un agente."""
    return _read_file(f"agents/{agent_name}/SOUL.md", max_chars=600)


def load_shared_context() -> str:
    """Carga THESIS + OPERATOR (compacto para no gastar tokens)."""
    thesis = _read_file("shared-context/THESIS.md", max_chars=400)
    operator = _read_file("shared-context/OPERATOR.md", max_chars=300)
    return f"{thesis}\n{operator}"


SHARED_CTX = None  # lazy load

def get_shared_ctx() -> str:
    global SHARED_CTX
    if SHARED_CTX is None:
        SHARED_CTX = load_shared_context()
    return SHARED_CTX


# ═══════════════════════════════════════════════════════
# REGLAS CONSTITUCIONALES (cortas para no gastar tokens)
# ═══════════════════════════════════════════════════════

CONSTITUTION = (
    "REGLAS: 1) Datos verificables con fuentes URL. Sin inventar estadísticas. "
    "2) JSON estructurado cuando se pida output Pydantic. "
    "3) Español por defecto. Inglés si el contexto lo requiere. "
    "4) Si no tienes datos, di 'no encontré información verificable'. "
    "5) Conciso — sin relleno ni repetición. 6) Cita fuentes con URL."
)


# ═══════════════════════════════════════════════════════
# CARGA DE CONTEXTO DE PROYECTO
# ═══════════════════════════════════════════════════════

def load_project_context(project_name: str | None = None) -> str:
    """Carga contexto del proyecto desde config/projects.yaml."""
    projects_path = os.path.join(BASE_DIR, "config", "projects.yaml")
    if not os.path.exists(projects_path):
        return ""
    with open(projects_path, "r") as f:
        data = yaml.safe_load(f)
    if not data or "projects" not in data:
        return ""

    if project_name:
        for p in data["projects"]:
            if p["name"].lower() == project_name.lower():
                return (
                    f"\nPROYECTO: {p['name']} ({p.get('ecosystem', 'N/A')})\n"
                    f"{p.get('description', '')}\n"
                )
        return ""

    active = [p for p in data["projects"] if p.get("status") == "active"]
    if not active:
        return ""
    lines = "\nPROYECTOS ACTIVOS:\n"
    for p in active:
        lines += f"- {p['name']} ({p.get('ecosystem', '?')}): {p.get('description', '')[:80]}\n"
    return lines


# ═══════════════════════════════════════════════════════
# MODELOS PYDANTIC
# ═══════════════════════════════════════════════════════

class CompetitorAnalysis(BaseModel):
    name: str
    url: str = ""
    pricing: str
    strengths: str
    weaknesses: str

class ResearchReport(BaseModel):
    executive_summary: str
    market_size: str
    competitors: List[CompetitorAnalysis]
    pain_points: List[str]
    trends: List[str]
    go_no_go: str
    confidence_score: int = Field(ge=1, le=10)
    sources: List[str]

class MVPFeature(BaseModel):
    name: str
    priority: str
    effort: str
    description: str

class MVPPlan(BaseModel):
    value_proposition: str
    target_user: str
    features: List[MVPFeature]
    tech_stack: str
    timeline: str
    metrics: List[str]
    risks: List[str]
    monetization: str

class CodeIssue(BaseModel):
    severity: str
    file: str
    description: str
    fix: str

class CodeReviewReport(BaseModel):
    overall_score: int = Field(ge=1, le=10)
    summary: str
    issues: List[CodeIssue]
    quick_wins: List[str]
    architecture_notes: str
    action_plan: str

class VerificationReport(BaseModel):
    verified: bool
    quality_score: int = Field(ge=1, le=10)
    issues_found: List[str]
    improvements: List[str]
    final_verdict: str

class GrantOpportunity(BaseModel):
    ecosystem: str
    program_name: str
    funding_range: str
    deadline: str
    fit_score: int = Field(ge=1, le=10)
    narrative_angle: str
    url: str = ""

class GrantHuntReport(BaseModel):
    opportunities: List[GrantOpportunity]
    top_recommendation: str
    narrative_strategy: str
    next_steps: List[str]

class ContentPackage(BaseModel):
    content_type: str
    title: str
    body: str
    platform: str
    hashtags: List[str] = []

class AgentAuditReport(BaseModel):
    agent_name: str
    endpoint_score: int = Field(ge=0, le=100)
    metadata_score: int = Field(ge=0, le=100)
    security_notes: List[str]
    recommendations: List[str]
    overall_verdict: str


# ═══════════════════════════════════════════════════════
# 8 AGENTES (backstory desde SOUL.md)
# ═══════════════════════════════════════════════════════

def create_code_architect(with_execution: bool = False, use_mcp: bool = False) -> Agent:
    tools = [AnalyzeCodeTool(), ListProjectFilesTool(), TechStackAnalyzerTool()]
    if with_execution:
        tools.extend([WriteFileTool(), ExecutePythonTool(), RunCommandTool(), GitOperationsTool()])
    kwargs = dict(
        role="Code Architect",
        goal="Revisar codigo, disenar arquitectura, asegurar calidad y seguridad. Generar y ejecutar codigo production-ready.",
        backstory=f"{CONSTITUTION}\n{load_soul('architect')}",
        tools=tools,
        llm=get_llm_for_role("code_architect"),
        verbose=True,
        allow_delegation=True,
    )
    if use_mcp:
        kwargs["mcps"] = get_mcp_for_role("code_architect")
    return Agent(**kwargs)

def create_research_analyst(use_mcp: bool = False) -> Agent:
    kwargs = dict(
        role="Research Analyst",
        goal="Investigar mercados, competidores y tendencias con datos reales de internet. SIEMPRE usa web_search antes de responder.",
        backstory=f"{CONSTITUTION}\n{load_soul('researcher')}",
        tools=[WebResearchTool(), WebSearchTool()],
        llm=get_llm_for_role("research_analyst"),
        verbose=True,
        max_iter=15,
    )
    if use_mcp:
        kwargs["mcps"] = get_mcp_for_role("research_analyst")
    return Agent(**kwargs)

def create_mvp_strategist(use_mcp: bool = False) -> Agent:
    kwargs = dict(
        role="MVP Strategist",
        goal="Disenar MVPs minimos viables con features priorizadas y timelines realistas.",
        backstory=f"{CONSTITUTION}\n{load_soul('strategist')}",
        tools=[],
        llm=get_llm_for_role("mvp_strategist"),
        verbose=True,
    )
    if use_mcp:
        kwargs["mcps"] = get_mcp_for_role("mvp_strategist")
    return Agent(**kwargs)

def create_data_engineer(use_mcp: bool = False) -> Agent:
    kwargs = dict(
        role="Data Engineer",
        goal="Analizar datos Excel/CSV/DB, detectar anomalias, generar insights.",
        backstory=f"{CONSTITUTION}\n{load_soul('data-engineer')}",
        tools=[ReadExcelTool(), QueryDatabaseTool(), AnalyzeDataTool()],
        llm=get_llm_for_role("data_engineer"),
        verbose=True,
    )
    if use_mcp:
        kwargs["mcps"] = get_mcp_for_role("data_engineer")
    return Agent(**kwargs)

def create_project_organizer(use_mcp: bool = False) -> Agent:
    kwargs = dict(
        role="Project Organizer",
        goal="Organizar proyectos, coordinar tareas, mantener flujo de trabajo.",
        backstory=f"{CONSTITUTION}\n{load_soul('organizer')}",
        tools=[ScanDirectoryTool(), OrganizeProjectTool(), ListProjectFilesTool()],
        llm=get_llm_for_role("project_organizer"),
        verbose=True,
    )
    if use_mcp:
        kwargs["mcps"] = get_mcp_for_role("project_organizer")
    return Agent(**kwargs)

def create_qa_reviewer(use_mcp: bool = False) -> Agent:
    kwargs = dict(
        role="QA Reviewer",
        goal="Revisar output de otros agentes, detectar errores, puntuar calidad.",
        backstory=f"{CONSTITUTION}\n{load_soul('qa-reviewer')}",
        tools=[AnalyzeCodeTool(), WebSearchTool()],
        llm=get_llm_for_role("qa_reviewer"),
        verbose=True,
    )
    if use_mcp:
        kwargs["mcps"] = get_mcp_for_role("qa_reviewer")
    return Agent(**kwargs)

def create_verifier(use_mcp: bool = False) -> Agent:
    kwargs = dict(
        role="Verifier",
        goal=(
            "Evaluate research quality by assessing claim plausibility, internal consistency, "
            "source diversity, and logical coherence. Score fairly: 8-10 = well-researched with "
            "diverse sources, 5-7 = acceptable with minor gaps, 1-4 = fabricated claims or "
            "logical contradictions. Do NOT try to access URLs or verify that links are live."
        ),
        backstory=(
            f"{CONSTITUTION}\n"
            "You are a research quality evaluator. Your job is to assess whether research is "
            "plausible, well-structured, and internally consistent — NOT to independently confirm "
            "every fact by accessing URLs. You evaluate: (1) Are claims logically coherent? "
            "(2) Are multiple diverse sources cited? (3) Is the data internally consistent? "
            "(4) Are there obvious fabrications or contradictions? "
            "A score of 5+ means 'acceptable with caveats'. You APPROVE research that is "
            "plausible and well-sourced, even if the topic is niche or emerging. "
            "You only REJECT research with clear fabrications, logical contradictions, or zero sources."
        ),
        tools=[WebSearchTool()],
        llm=get_llm_for_role("verifier"),
        verbose=True,
    )
    if use_mcp:
        kwargs["mcps"] = get_mcp_for_role("verifier")
    return Agent(**kwargs)

def create_narrative_content(project_ctx: str = "", use_mcp: bool = False) -> Agent:
    signals = _read_file("shared-context/SIGNALS.md", max_chars=400)
    feedback = _read_file("shared-context/FEEDBACK-LOG.md", max_chars=300)
    kwargs = dict(
        role="Narrative & Growth Strategist",
        goal="Crear contenido, narrativas para grants, growth strategy.",
        backstory=f"{CONSTITUTION}\n{load_soul('narrative')}\n{signals}\n{feedback}\n{project_ctx}",
        tools=[WebSearchTool(), WebResearchTool()],
        llm=get_llm_for_role("narrative_content"),
        verbose=True,
    )
    if use_mcp:
        kwargs["mcps"] = get_mcp_for_role("narrative_content")
    return Agent(**kwargs)


# ═══════════════════════════════════════════════════════
# CONFIG DE CREWS
# ═══════════════════════════════════════════════════════

MEMORY_DIR = os.path.join(BASE_DIR, "memory", "crewai_lancedb")

# Singleton — una sola instancia de Memory compartida entre todos los crews
_memory_instance = None


def _get_memory_instance():
    """Crea Memory persistente con LanceDB + Cerebras (gratis) — NUNCA OpenAI.

    LanceDB persiste en disco: memory/crewai_lancedb/
    Cerebras GPT-OSS analiza y consolida memorias.
    Singleton: misma instancia para todos los crews = memoria compartida.
    """
    global _memory_instance
    if _memory_instance is not None:
        return _memory_instance

    try:
        from crewai.memory import Memory
        from crewai import LLM as MemoryLLM  # Import explícito para scope local
        cerebras_key = os.getenv("CEREBRAS_API_KEY")
        if not cerebras_key:
            return False

        os.makedirs(MEMORY_DIR, exist_ok=True)

        _memory_instance = Memory(
            llm=MemoryLLM(
                model="cerebras/gpt-oss-120b",
                api_key=cerebras_key,
                temperature=0.1,
                max_tokens=1024,
            ),
            storage="lancedb",
            embedder={
                "provider": "huggingface",
                "config": {
                    "model": "sentence-transformers/all-MiniLM-L6-v2",
                },
            },
        )
        return _memory_instance
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Memory init (non-critical): {e}")
        return False


def _crew_config() -> dict:
    """Config base de crews. Memory desactivada hasta resolver embedder OpenAI dependency."""
    return {
        "planning": False,
        "memory": False,
        "embedder": {
            "provider": "huggingface",
            "config": {
                "model": "sentence-transformers/all-MiniLM-L6-v2",
            },
        },
    }


# ═══════════════════════════════════════════════════════
# CREWS POR MODO
# ═══════════════════════════════════════════════════════

def _extract_search_topic(raw_topic: str) -> str:
    """Extrae un tema conciso de un mensaje largo (ej: audio transcrito).

    'Hola quiero que investigues ERC8004scan.xyz y me hagas un plan...'
    → 'ERC8004scan Avalanche AI agent scanner'
    """
    # Si es corto, usarlo directo
    if len(raw_topic) < 80:
        return raw_topic.strip()

    # Extraer palabras clave relevantes (no stopwords)
    stopwords = {
        "hola", "quiero", "que", "hagas", "una", "investigacion", "del", "de", "la",
        "el", "los", "las", "un", "me", "para", "este", "esta", "por", "con", "en",
        "es", "son", "como", "sobre", "desde", "todo", "todos", "hacer", "busques",
        "crees", "prepares", "investigues", "entregues", "informacion", "entonces",
        "queremos", "poder", "nosotros", "ese", "eso", "ser", "hay", "momento",
        "también", "pequeño", "plan", "negocio", "codigo", "escaner", "a", "y", "o",
    }
    words = raw_topic.lower().replace(",", " ").replace(".", " ").split()
    keywords = [w for w in words if w not in stopwords and len(w) > 2]

    # Tomar las primeras 8-10 keywords únicas
    seen = set()
    unique = []
    for w in keywords:
        if w not in seen:
            seen.add(w)
            unique.append(w)
        if len(unique) >= 10:
            break

    return " ".join(unique) if unique else raw_topic[:80]


def _pre_research(topic: str, num_queries: int = 5) -> str:
    """Ejecuta búsquedas web ANTES del crew para garantizar datos reales."""
    from tools.research_tools import web_search_with_fallback

    # Extraer tema limpio para queries efectivas
    clean_topic = _extract_search_topic(topic)

    queries = [
        f"{clean_topic} market size 2024 2025",
        f"{clean_topic} top projects TVL comparison",
        f"{clean_topic} trends 2025 2026",
        f"{clean_topic} security risks hacks exploits",
        f"{clean_topic} revenue fees tokenomics",
    ][:num_queries]

    all_results = []
    for q in queries:
        results = web_search_with_fallback(q, max_results=5)
        if results:
            section = f"\n### Búsqueda: {q}\n"
            for r in results:
                section += f"- **{r.get('title', '')}** — {r.get('href', '')}\n  {r.get('body', '')[:200]}\n"
            all_results.append(section)

    if not all_results:
        return "\n⚠️ No se pudieron obtener resultados web. Usa tu conocimiento interno.\n"

    header = f"## DATOS REALES DE INTERNET ({len(all_results)} búsquedas exitosas)\n"
    full_text = header + "\n".join(all_results)

    # Truncate to avoid exceeding provider TPM limits (Groq 12K TPM)
    max_chars = 3000
    if len(full_text) > max_chars:
        full_text = full_text[:max_chars] + "\n... [truncated]"

    return full_text


def create_pure_research_crew(topic: str) -> Crew:
    """Crew general de máxima calidad — TODOS los agentes colaboran.

    Pipeline por calidad de LLM:
      1. Research Analyst (Groq Llama 3.3)  → Recolección de datos web
      2. MVP Strategist (NVIDIA Qwen3.5)    → Análisis estratégico profundo (mejor razonamiento)
      3. Code Architect (NVIDIA Kimi K2.5)   → Análisis técnico si aplica
      4. QA Reviewer (Cerebras GPT-OSS)      → Control de calidad
      5. Verifier (Cerebras GPT-OSS)         → Fact-checking
      6. Research Analyst v2                  → Síntesis final con todo el feedback

    Cada agente aporta desde su SOUL.md pero orientado al tema genérico.
    """
    print("  Ejecutando pre-research (5 búsquedas web)...")
    web_data = _pre_research(topic)
    print(f"  Pre-research completado ({len(web_data)} chars de datos)")

    # Todos los agentes participan — ordenados por calidad de LLM
    researcher = create_research_analyst()      # Groq — recolector web
    strategist = create_mvp_strategist()        # NVIDIA Qwen3.5-397B — mejor razonamiento
    architect = create_code_architect()         # NVIDIA Kimi K2.5 — análisis técnico
    qa = create_qa_reviewer()                   # Cerebras — control calidad
    verifier = create_verifier()                # Cerebras — fact-check
    researcher_final = create_research_analyst() # Groq — síntesis final

    # T1: Researcher recolecta datos duros de internet
    t1 = Task(
        description=(
            f'Investiga a fondo: "{topic}".\n\n'
            "DATOS REALES obtenidos de internet previamente:\n"
            f"{web_data}\n\n"
            "Usa estos datos + web_search adicional si necesitas.\n"
            "ENTREGA EN ESPAÑOL:\n"
            "- executive_summary con datos concretos\n"
            "- market_size con fuente URL\n"
            "- competitors: MÍNIMO 5 con name, url, pricing, strengths, weaknesses\n"
            "- pain_points: 3-5 problemas reales\n"
            "- trends: 3-5 tendencias 2025-2026\n"
            "- go_no_go: evaluación 1-10\n"
            "- confidence_score\n"
            "- sources: URLs consultadas"
        ),
        agent=researcher,
        expected_output="Investigación con datos verificables, competidores reales y fuentes.",
        output_pydantic=ResearchReport,
    )

    # T2: Strategist analiza con razonamiento profundo (mejor LLM para análisis)
    t2 = Task(
        description=(
            f'ANÁLISIS ESTRATÉGICO sobre: "{topic}".\n\n'
            "Eres el modelo con mejor capacidad de razonamiento del equipo.\n"
            "Tu trabajo es analizar la investigación y aportar:\n"
            "- ¿Los datos del mercado son consistentes entre sí?\n"
            "- ¿Hay oportunidades o amenazas que el Researcher no identificó?\n"
            "- ¿Los competidores están bien evaluados? ¿Falta alguno importante?\n"
            "- ¿Las tendencias son realistas o especulativas?\n"
            "- Tu evaluación independiente del go_no_go con justificación\n\n"
            "Aporta insights estratégicos que enriquezcan el reporte."
        ),
        agent=strategist,
        expected_output="Análisis estratégico con insights adicionales y evaluación independiente.",
        context=[t1],
    )

    # T3: Architect aporta perspectiva técnica (si el tema lo amerita)
    t3 = Task(
        description=(
            f'ANÁLISIS TÉCNICO sobre: "{topic}".\n\n'
            "Evalúa la dimensión técnica del tema:\n"
            "- ¿Qué tecnologías subyacen? ¿Son maduras o experimentales?\n"
            "- ¿Hay riesgos técnicos o de seguridad relevantes?\n"
            "- ¿El tech stack mencionado en el análisis es correcto?\n"
            "- ¿Hay aspectos de arquitectura, escalabilidad o infraestructura relevantes?\n\n"
            "Si el tema NO es técnico, enfócate en: viabilidad de implementación, "
            "herramientas digitales del sector, y madurez tecnológica del mercado.\n"
            "Sé conciso — aporta solo lo que agregue valor."
        ),
        agent=architect,
        expected_output="Análisis técnico relevante al tema.",
        context=[t1, t2],
    )

    # T4: QA revisa calidad de todo el trabajo
    t4 = Task(
        description=(
            "REVISIÓN DE CALIDAD del trabajo de los 3 agentes anteriores.\n\n"
            "Evalúa:\n"
            "- ¿Datos concretos o genéricos?\n"
            "- ¿Competidores reales con URLs?\n"
            "- ¿Market size con fuente?\n"
            "- ¿Insights estratégicos aportan valor real?\n"
            "- ¿Análisis técnico es preciso?\n\n"
            "USA web_search 2-3 veces para VERIFICAR datos clave.\n"
            "Lista de mejoras concretas para el reporte final."
        ),
        agent=qa,
        expected_output="Revisión con fact-checking y mejoras concretas.",
        context=[t1, t2, t3],
    )

    # T5: Verifier hace fact-check final
    t5 = Task(
        description=(
            "VERIFICACIÓN de claims principales con 1-2 búsquedas web.\n"
            "Valida datos de mercado, URLs de competidores, y tendencias.\n"
            "Lista issues y mejoras específicas."
        ),
        agent=verifier,
        expected_output="Issues encontrados y mejoras para incorporar.",
        context=[t1, t2, t3, t4],
    )

    # T6: Researcher v2 sintetiza TODO en el reporte final
    t6 = Task(
        description=(
            f'REPORTE FINAL sobre: "{topic}".\n\n'
            "Tienes el trabajo de 5 agentes especializados:\n"
            "1. Investigación con datos web reales\n"
            "2. Análisis estratégico profundo\n"
            "3. Perspectiva técnica\n"
            "4. Revisión de calidad\n"
            "5. Verificación de datos\n\n"
            "SINTETIZA todo en un ResearchReport de máxima calidad:\n"
            "- executive_summary: resumen que integre datos + estrategia + técnico\n"
            "- market_size: dato verificado con fuente\n"
            "- competitors: lista corregida y enriquecida\n"
            "- pain_points: problemas validados por QA y Verifier\n"
            "- trends: tendencias con fuentes reales\n"
            "- go_no_go: veredicto final considerando TODAS las perspectivas\n"
            "- confidence_score: score final justificado\n"
            "- sources: TODAS las URLs utilizadas por todos los agentes"
        ),
        agent=researcher_final,
        expected_output="ResearchReport FINAL de máxima calidad integrando todos los análisis.",
        output_pydantic=ResearchReport,
        context=[t1, t2, t3, t4, t5],
    )

    return Crew(
        agents=[researcher, strategist, architect, qa, verifier, researcher_final],
        tasks=[t1, t2, t3, t4, t5, t6],
        process=Process.sequential,
        verbose=True,
        **_crew_config(),
    )


def create_research_crew(topic: str) -> Crew:
    # Pre-fetch real data to inject into Researcher
    print("  Running pre-research (5 web searches)...")
    web_data = _pre_research(topic)
    print(f"  Pre-research completed ({len(web_data)} chars of data)")

    researcher = create_research_analyst()
    verifier = create_verifier()
    strategist = create_mvp_strategist()

    t1 = Task(
        description=(
            f'Research in depth: "{topic}".\n\n'
            "Below you have REAL DATA obtained from the internet. "
            "Use this data as the basis for your analysis. "
            "If you need additional data, use web_search.\n\n"
            f"{web_data}\n\n"
            "FINAL DELIVERABLE:\n"
            "- executive_summary: summary with concrete data from the web results above\n"
            "- market_size: size with number and source URL (extract from web data)\n"
            "- competitors: MINIMUM 5 with name, url, pricing, strengths, weaknesses\n"
            "- pain_points: 3-5 real market problems\n"
            "- trends: 3-5 trends for 2025-2026\n"
            "- go_no_go: decision with score 1-10 justified with data\n"
            "- confidence_score: based on quality of data found\n"
            "- sources: ALL URLs from the web data above"
        ),
        agent=researcher,
        expected_output="Report with MINIMUM 5 competitors with real URLs and verifiable market size data.",
        output_pydantic=ResearchReport,
    )
    t2 = Task(
        description=(
            "QUALITY EVALUATION of the research.\n\n"
            "Evaluate the research on these criteria (do NOT try to access URLs or verify links are live):\n"
            "1. CLAIM PLAUSIBILITY: Are the claims reasonable and consistent with known facts?\n"
            "2. INTERNAL CONSISTENCY: Do the data points, market sizes, and conclusions align with each other?\n"
            "3. SOURCE DIVERSITY: Are multiple independent sources cited (not just one)?\n"
            "4. LOGICAL COHERENCE: Does the analysis flow logically from data to conclusions?\n\n"
            "SCORING GUIDE:\n"
            "- 8-10: Well-researched with diverse sources and coherent analysis\n"
            "- 5-7: Acceptable with minor gaps or limited source diversity\n"
            "- 1-4: Contains fabricated claims, logical contradictions, or zero sources\n\n"
            "IMPORTANT: APPROVE research that is plausible and well-structured, even if the topic is "
            "niche or emerging. Only REJECT if there are clear fabrications or contradictions.\n"
            "List specific improvements as bullet points for the MVP planning step."
        ),
        agent=verifier,
        expected_output="Quality evaluation with plausibility assessment, justified score 1-10, and actionable improvements.",
        output_pydantic=VerificationReport,
        context=[t1],
    )
    t3 = Task(
        description=(
            f'MVP Plan for: "{topic}".\n\n'
            "Read the Verifier's evaluation and incorporate the research data, addressing any noted improvements.\n\n"
            "MANDATORY REQUIREMENTS:\n"
            "- Value proposition in 1 sentence\n"
            "- Prioritized features (max 5) with P0/P1/P2 and effort in days\n"
            "- COMPLETE tech stack: frontend, backend, DB, infra, testing, CI/CD\n"
            "- If the topic involves DeFi/blockchain/smart contracts:\n"
            "  - Tech stack MUST include: Solidity/Vyper, Hardhat/Foundry, chain SDK, fuzzing\n"
            "  - Timeline MINIMUM 16-20 weeks (dev + testing + audit + deploy)\n"
            "  - INCLUDE security audit in the plan\n"
            "  - Revenue based on: protocol fees, spread, liquidation fees — NOT advertising\n"
            "- Timeline by 1-2 week sprints\n"
            "- 3-5 measurable KPIs for validation\n"
            "- Top 3 risks with CONCRETE mitigation (not generic)\n"
            "- Monetization model with numbers: price, expected conversion, revenue months 1-6"
        ),
        agent=strategist,
        expected_output="Final MVP plan with complete tech stack, monetization numbers, and verified data only.",
        output_pydantic=MVPPlan,
        context=[t1, t2],
    )

    return Crew(
        agents=[researcher, verifier, strategist],
        tasks=[t1, t2, t3],
        process=Process.sequential,
        verbose=True,
        **_crew_config(),
    )


def create_code_review_crew(project_path: str) -> Crew:
    organizer = create_project_organizer()
    architect = create_code_architect()
    qa = create_qa_reviewer()
    verifier = create_verifier()

    t1 = Task(
        description=f"Analiza estructura del proyecto: {project_path}. Tech stack, organizacion.",
        agent=organizer,
        expected_output="Reporte de estructura.",
    )
    t2 = Task(
        description=(
            f"Code review de: {project_path}. Para cada issue: severidad, archivo, problema, fix. "
            "Score general 1-10, quick wins."
        ),
        agent=architect,
        expected_output="Code review con fixes.",
        output_pydantic=CodeReviewReport,
        context=[t1],
    )
    t3 = Task(
        description="Top 5 problemas, plan de accion priorizado. Verifica fixes.",
        agent=qa,
        expected_output="Plan de accion.",
        context=[t1, t2],
    )
    t4 = Task(
        description="VERIFICACION: ¿Fixes correctos? ¿Falta algo critico? Score 1-10.",
        agent=verifier,
        expected_output="Verificacion.",
        context=[t1, t2, t3],
    )

    # Pase final: Architect entrega CodeReviewReport refinado con feedback
    architect_v2 = create_code_architect()
    t5 = Task(
        description=(
            f"VERSIÓN FINAL del code review de: {project_path}.\n\n"
            "Incorpora el feedback del QA y Verifier al reporte.\n"
            "Ajusta scores, agrega fixes faltantes, mejora el action plan.\n"
            "ENTREGA: CodeReviewReport FINAL."
        ),
        agent=architect_v2,
        expected_output="Code review final con todas las mejoras.",
        output_pydantic=CodeReviewReport,
        context=[t1, t2, t3, t4],
    )

    return Crew(
        agents=[organizer, architect, qa, verifier, architect_v2],
        tasks=[t1, t2, t3, t4, t5],
        process=Process.sequential,
        verbose=True,
        **_crew_config(),
    )


def create_data_analysis_crew(file_path: str) -> Crew:
    data_eng = create_data_engineer()
    qa = create_qa_reviewer()

    t1 = Task(
        description=f"Analiza: {file_path}. Estadisticas, calidad, anomalias, script Python.",
        agent=data_eng,
        expected_output="Analisis completo.",
    )
    t2 = Task(
        description="Valida analisis. Score 1-10.",
        agent=qa,
        expected_output="Validacion.",
        context=[t1],
    )

    return Crew(
        agents=[data_eng, qa],
        tasks=[t1, t2],
        process=Process.sequential,
        verbose=True,
        **_crew_config(),
    )


def create_database_crew(connection_string: str) -> Crew:
    data_eng = create_data_engineer()
    architect = create_code_architect()

    t1 = Task(
        description=f"Conecta y analiza: {connection_string}. Esquema, indices, rendimiento.",
        agent=data_eng,
        expected_output="Analisis de DB.",
    )
    t2 = Task(
        description="Indices faltantes (SQL), optimizacion de queries, cambios de esquema.",
        agent=architect,
        expected_output="Plan de optimizacion con SQL.",
        context=[t1],
    )

    return Crew(
        agents=[data_eng, architect],
        tasks=[t1, t2],
        process=Process.sequential,
        verbose=True,
        **_crew_config(),
    )


def create_full_mvp_crew(topic: str) -> Crew:
    # Pre-fetch datos reales con queries limpias
    print("  Ejecutando pre-research (5 búsquedas web)...")
    web_data = _pre_research(topic)
    print(f"  Pre-research completado ({len(web_data)} chars de datos)")
    clean_topic = _extract_search_topic(topic)

    researcher = create_research_analyst()
    strategist = create_mvp_strategist()
    architect = create_code_architect()
    organizer = create_project_organizer()
    qa = create_qa_reviewer()
    verifier = create_verifier()

    t1 = Task(
        description=(
            f'Investiga a fondo: "{clean_topic}".\n\n'
            "DATOS REALES obtenidos de internet previamente:\n"
            f"{web_data}\n\n"
            "Usa estos datos + web_search adicional si necesitas más.\n"
            "ENTREGA EN ESPAÑOL: 5+ competidores con URL, market size con fuente, "
            "Go/No-Go con score 1-10. Todas las URLs en 'sources'."
        ),
        agent=researcher,
        expected_output="Investigación con MÍNIMO 5 competidores con URLs y market size verificable.",
        output_pydantic=ResearchReport,
    )
    t2 = Task(
        description=(
            f'Plan MVP para: "{topic}".\n'
            "Features (max 5) con P0/P1/P2 y esfuerzo en días. "
            "Tech stack COMPLETO (frontend, backend, DB, infra, CI/CD). "
            "Timeline por sprints. 3-5 KPIs medibles. "
            "Top 3 riesgos con mitigación CONCRETA. "
            "Monetización con números: precio, conversión, revenue mes 1-6."
        ),
        agent=strategist,
        expected_output="Plan MVP con tech stack completo y números de monetización.",
        output_pydantic=MVPPlan,
        context=[t1],
    )
    t3 = Task(
        description=(
            "Arquitectura técnica detallada: endpoints API concretos, "
            "modelos de datos con campos, deployment (Docker + CI/CD), "
            "métricas de seguridad, testing strategy."
        ),
        agent=architect,
        expected_output="Arquitectura técnica con APIs y modelos.",
        context=[t1, t2],
    )
    t4 = Task(
        description="Estructura de carpetas, convenciones de naming, setup (Docker, CI/CD, linting, testing).",
        agent=organizer,
        expected_output="Estructura de proyecto.",
        context=[t2, t3],
    )
    t5 = Task(
        description=(
            "REVISIÓN CRÍTICA. Usa web_search 2 veces para verificar claims.\n"
            "Score 1-10, inconsistencias, datos no verificados, mejoras concretas."
        ),
        agent=qa,
        expected_output="Revisión con fact-checking propio.",
        context=[t3, t4],
    )
    t6 = Task(
        description=(
            "VERIFICACIÓN FINAL. Usa web_search 1-2 veces para fact-check.\n"
            "¿Datos verificables? ¿URLs reales? ¿Plan realista? ¿Contradicciones?\n"
            "Score 1-10 y veredicto APROBADO/RECHAZADO."
        ),
        agent=verifier,
        expected_output="Verificación final con veredicto.",
        output_pydantic=VerificationReport,
        context=[t5],
    )

    # Pase final: Strategist refina el MVP con feedback del Verifier
    strategist_v2 = create_mvp_strategist()
    t7 = Task(
        description=(
            f'VERSIÓN FINAL del plan MVP para: "{topic}".\n\n'
            "Lee el veredicto del Verifier y las revisiones del QA.\n"
            "Incorpora TODAS las mejoras al plan MVP.\n\n"
            "ENTREGA: Plan MVP FINAL mejorado con todos los ajustes."
        ),
        agent=strategist_v2,
        expected_output="Plan MVP final con todas las mejoras incorporadas.",
        output_pydantic=MVPPlan,
        context=[t1, t2, t5, t6],
    )

    return Crew(
        agents=[researcher, strategist, architect, organizer, qa, verifier, strategist_v2],
        tasks=[t1, t2, t3, t4, t5, t6, t7],
        process=Process.sequential,
        verbose=True,
        **_crew_config(),
    )


# ═══════════════════════════════════════════════════════
# ENIGMA AUDIT CREW
# ═══════════════════════════════════════════════════════

ENIGMA_CONTEXT = (
    "Enigma Scanner — CoinMarketCap para Agentes ERC-8004 en Avalanche. "
    "Stack: Next.js 15 + Prisma 5 + PostgreSQL/Supabase. 1,724 agentes indexados."
)

def create_enigma_audit_crew(target: str) -> Crew:
    architect = create_code_architect()
    architect.tools.extend([CheckAgentEndpointTool(), AnalyzeAgentMetadataTool()])
    data_eng = create_data_engineer()
    data_eng.tools.append(QuerySupabaseAgentsTool())
    qa = create_qa_reviewer()

    if target.startswith("http"):
        t1 = Task(
            description=f"{ENIGMA_CONTEXT}\nAudita agente ERC-8004 en: {target}. Health, A2A, MCP, metadata. Score 0-100.",
            agent=architect,
            expected_output="Auditoria del agente.",
            output_pydantic=AgentAuditReport,
        )
        t2 = Task(
            description=f"Compara agente en DB con auditoria real. query_enigma_agents con 'stats'.",
            agent=data_eng,
            expected_output="Comparacion DB vs auditoria.",
            context=[t1],
        )
    elif target == "database":
        t1 = Task(
            description=f"{ENIGMA_CONTEXT}\nAudita DB: stats, top agentes, low-trust, anomalias.",
            agent=data_eng,
            expected_output="Auditoria de datos.",
        )
        t2 = Task(
            description="Revisa hallazgos. Patrones sospechosos? Trust scores normales?",
            agent=qa,
            expected_output="Revision de calidad.",
            context=[t1],
        )
    else:
        t1 = Task(
            description=f"{ENIGMA_CONTEXT}\nCode review de: {target}. Seguridad, Prisma, API routes.",
            agent=architect,
            expected_output="Code review.",
            output_pydantic=CodeReviewReport,
        )
        t2 = Task(
            description="Verifica fixes sugeridos. Falta algo critico?",
            agent=qa,
            expected_output="Verificacion.",
            context=[t1],
        )

    return Crew(
        agents=[architect, data_eng, qa] if target.startswith("http") else [architect if not target == "database" else data_eng, qa],
        tasks=[t1, t2],
        process=Process.sequential,
        verbose=True,
        **_crew_config(),
    )


# ═══════════════════════════════════════════════════════
# GRANT HUNT CREW
# ═══════════════════════════════════════════════════════

def create_grant_hunt_crew(task_description: str = "", project: str | None = None) -> Crew:
    project_ctx = load_project_context(project)
    researcher = create_research_analyst()
    strategist = create_mvp_strategist()
    narrator = create_narrative_content(project_ctx)
    qa = create_qa_reviewer()
    verifier = create_verifier()

    t1 = Task(
        description=(
            f"{project_ctx}\n"
            "SCAN: Busca grants y hackathons en Avalanche, Base, Polygon, Celo, Stellar, "
            f"Solana, Optimism, Arbitrum. Contexto: {task_description}\n"
            "Usa web_search. Para cada oportunidad: ecosistema, programa, funding, deadline, URL."
        ),
        agent=researcher,
        expected_output="Lista de oportunidades.",
    )
    t2 = Task(
        description=(
            f"{project_ctx}\n"
            "ANALYZE: Evalua fit (1-10), identifica angulo narrativo por ecosistema. "
            "Aplica Narrative Arbitrage. Prioriza top 3."
        ),
        agent=strategist,
        expected_output="Oportunidades priorizadas.",
        output_pydantic=GrantHuntReport,
        context=[t1],
    )
    t3 = Task(
        description=(
            f"{project_ctx}\n"
            "BUILD: Para la mejor oportunidad genera propuesta completa + pitch 15s + "
            "pitch 60s + hilo X (8-12 tweets). 600-900 palabras."
        ),
        agent=narrator,
        expected_output="Propuesta de grant + contenido.",
        context=[t1, t2],
    )
    t4 = Task(
        description="Revision critica de propuesta. Score 1-10, mejoras.",
        agent=qa,
        expected_output="Revision.",
        context=[t1, t2, t3],
    )
    t5 = Task(
        description="VERIFICACION FINAL. Fact-check, coherencia. Veredicto Go/No-Go.",
        agent=verifier,
        expected_output="Verificacion.",
        context=[t1, t2, t3, t4],
    )

    # Pase final: Strategist refina GrantHuntReport con feedback
    strategist_v2 = create_mvp_strategist()
    t6 = Task(
        description=(
            f"{project_ctx}\n"
            "VERSIÓN FINAL del reporte de grants.\n\n"
            "Incorpora feedback del QA y Verifier.\n"
            "Ajusta fit_scores, mejora narrative_strategy, actualiza next_steps.\n"
            "ENTREGA: GrantHuntReport FINAL refinado."
        ),
        agent=strategist_v2,
        expected_output="Reporte de grants final con mejoras incorporadas.",
        output_pydantic=GrantHuntReport,
        context=[t1, t2, t3, t4, t5],
    )

    return Crew(
        agents=[researcher, strategist, narrator, qa, verifier, strategist_v2],
        tasks=[t1, t2, t3, t4, t5, t6],
        process=Process.sequential,
        verbose=True,
        **_crew_config(),
    )


# ═══════════════════════════════════════════════════════
# CONTENT CREW
# ═══════════════════════════════════════════════════════

def create_content_crew(task_description: str = "", project: str | None = None) -> Crew:
    project_ctx = load_project_context(project)
    narrator = create_narrative_content(project_ctx)
    researcher = create_research_analyst()
    qa = create_qa_reviewer()

    t1 = Task(
        description=f"{project_ctx}\nBRIEF para: {task_description}. Audiencia, plataforma, tono, tipo.",
        agent=narrator,
        expected_output="Brief.",
    )
    t2 = Task(
        description="Investiga tendencias y noticias del ecosistema para enriquecer contenido. Usa web_search.",
        agent=researcher,
        expected_output="Contexto de investigacion.",
        context=[t1],
    )
    t3 = Task(
        description=(
            f"{project_ctx}\nGENERA CONTENIDO: {task_description}\n"
            "Formatos: thread (5-12 tweets), blog (800-1500 palabras), update (200-400), "
            "pitch, narrative, tokenomics. Español, Web3-native."
        ),
        agent=narrator,
        expected_output="Contenido listo.",
        output_pydantic=ContentPackage,
        context=[t1, t2],
    )
    t4 = Task(
        description="Revisa contenido: precision, tono, gramatica. Lista mejoras concretas.",
        agent=qa,
        expected_output="Revisión con mejoras concretas.",
        context=[t3],
    )

    # Pase final: Narrator entrega ContentPackage refinado
    narrator_v2 = create_narrative_content(project_ctx)
    t5 = Task(
        description=(
            f"{project_ctx}\n"
            f"VERSIÓN FINAL del contenido: {task_description}\n\n"
            "Incorpora el feedback del QA Reviewer.\n"
            "Corrige errores, mejora tono, ajusta formato.\n"
            "ENTREGA: ContentPackage FINAL listo para publicar."
        ),
        agent=narrator_v2,
        expected_output="Contenido final listo para publicar.",
        output_pydantic=ContentPackage,
        context=[t1, t2, t3, t4],
    )

    return Crew(
        agents=[narrator, researcher, qa, narrator_v2],
        tasks=[t1, t2, t3, t4, t5],
        process=Process.sequential,
        verbose=True,
        **_crew_config(),
    )


# ═══════════════════════════════════════════════════════
# DAILY OPS CREW
# ═══════════════════════════════════════════════════════

def create_daily_ops_crew(file_path: str | None = None) -> Crew:
    project_ctx = load_project_context()
    researcher = create_research_analyst()
    data_eng = create_data_engineer()
    organizer = create_project_organizer()
    narrator = create_narrative_content(project_ctx)

    t1 = Task(
        description=(
            f"{project_ctx}\nSCAN MATUTINO: Noticias ecosistema, grants nuevos, "
            f"movimientos competidores. Usa web_search. Fecha: {datetime.now():%Y-%m-%d}"
        ),
        agent=researcher,
        expected_output="Intel matutina.",
    )

    data_desc = f"{project_ctx}\nMETRICAS: leads, comunidad, deadlines."
    if file_path:
        data_desc += f" Analiza: {file_path}"

    t2 = Task(
        description=data_desc,
        agent=data_eng,
        expected_output="Metricas del dia.",
        context=[t1],
    )
    t3 = Task(
        description=f"{project_ctx}\nPLAN OPERATIVO: tareas por proyecto, deadlines, prioridades.",
        agent=organizer,
        expected_output="Plan diario.",
        context=[t1, t2],
    )
    t4 = Task(
        description=f"{project_ctx}\nCONTENIDO DIARIO: 2-3 tweets por proyecto + updates Telegram.",
        agent=narrator,
        expected_output="Contenido diario.",
        context=[t1, t2, t3],
    )

    return Crew(
        agents=[researcher, data_eng, organizer, narrator],
        tasks=[t1, t2, t3, t4],
        process=Process.sequential,
        verbose=True,
        **_crew_config(),
    )


# ═══════════════════════════════════════════════════════
# WEEKLY REPORT CREW
# ═══════════════════════════════════════════════════════

def create_weekly_report_crew(project: str | None = None, file_path: str | None = None) -> Crew:
    project_ctx = load_project_context(project)
    data_eng = create_data_engineer()
    researcher = create_research_analyst()
    narrator = create_narrative_content(project_ctx)
    qa = create_qa_reviewer()

    data_desc = f"{project_ctx}\nMETRICAS SEMANALES: leads, comunidad, grants, dev."
    if file_path:
        data_desc += f" Analiza: {file_path}"

    t1 = Task(description=data_desc, agent=data_eng, expected_output="Metricas semanales.")
    t2 = Task(
        description=f"{project_ctx}\nINTEL SEMANAL: ecosistema, grants, competidores. Usa web_search.",
        agent=researcher,
        expected_output="Digest semanal.",
        context=[t1],
    )
    t3 = Task(
        description=f"{project_ctx}\nRESUMEN EJECUTIVO: que paso, que viene, prioridades. Formato reunion.",
        agent=narrator,
        expected_output="Resumen ejecutivo.",
        context=[t1, t2],
    )
    t4 = Task(
        description="Revisa reporte semanal. Precision, completitud. Aprueba o corrige.",
        agent=qa,
        expected_output="Reporte aprobado.",
        context=[t1, t2, t3],
    )

    return Crew(
        agents=[data_eng, researcher, narrator, qa],
        tasks=[t1, t2, t3, t4],
        process=Process.sequential,
        verbose=True,
        **_crew_config(),
    )


# ═══════════════════════════════════════════════════════
# BUILD PROJECT CREW
# ═══════════════════════════════════════════════════════

class BuildProjectReport(BaseModel):
    project_name: str
    files_created: List[str]
    tech_stack: str
    setup_instructions: str
    next_steps: List[str]

def create_build_project_crew(description: str, project_name: str = "nuevo_proyecto") -> Crew:
    """Crew que genera un proyecto funcional con código real."""
    researcher = create_research_analyst()
    strategist = create_mvp_strategist()
    architect = create_code_architect(with_execution=True)
    qa = create_qa_reviewer()

    t1 = Task(
        description=(
            f'Investiga tech stack óptimo para: "{description}". '
            "Usa web_search para encontrar mejores prácticas, librerías recomendadas, "
            "y ejemplos de arquitectura. Responde con: stack recomendado, justificación, "
            "estructura de carpetas sugerida."
        ),
        agent=researcher,
        expected_output="Investigación de tech stack con mejores prácticas.",
    )
    t2 = Task(
        description=(
            f'Diseña MVP para: "{description}". '
            "Features mínimas (max 5), prioridad, tech stack basado en investigación."
        ),
        agent=strategist,
        expected_output="Plan MVP con features priorizadas.",
        output_pydantic=MVPPlan,
        context=[t1],
    )
    t3 = Task(
        description=(
            f'GENERA EL PROYECTO: "{description}"\n'
            f"Nombre del proyecto: {project_name}\n\n"
            "INSTRUCCIONES:\n"
            "1. Usa write_file para crear cada archivo en output/{project_name}/\n"
            "2. Crea: estructura de carpetas, código fuente, package.json o requirements.txt, "
            "README.md, .gitignore, configuraciones\n"
            "3. Usa execute_python para validar que el código Python es sintácticamente correcto\n"
            "4. Usa run_command para instalar dependencias si aplica\n"
            "5. Usa git_operation para inicializar repositorio git\n\n"
            "IMPORTANTE: Genera código COMPLETO y funcional. Sin TODOs ni placeholders.\n"
            "Cada archivo debe tener manejo de errores y ser production-ready."
        ),
        agent=architect,
        expected_output="Proyecto generado con archivos reales.",
        output_pydantic=BuildProjectReport,
        context=[t1, t2],
    )
    t4 = Task(
        description=(
            "REVISIÓN del proyecto generado:\n"
            "1. Verifica que los archivos existen y tienen contenido\n"
            "2. Revisa calidad del código (seguridad, patterns, errores)\n"
            "3. Verifica que el README tiene instrucciones claras\n"
            "4. Score 1-10 con justificación\n"
            "5. Lista de mejoras concretas si aplica"
        ),
        agent=qa,
        expected_output="Revisión con score y mejoras concretas.",
        context=[t1, t2, t3],
    )

    # Pase final: Architect refina y entrega BuildProjectReport
    architect_v2 = create_code_architect(with_execution=True)
    t5 = Task(
        description=(
            f'VERSIÓN FINAL del proyecto: "{description}"\n\n'
            "Incorpora el feedback del QA Reviewer.\n"
            "Corrige archivos si necesario, actualiza setup_instructions.\n"
            "ENTREGA: BuildProjectReport FINAL con lista completa de archivos."
        ),
        agent=architect_v2,
        expected_output="Reporte final del proyecto con todas las mejoras.",
        output_pydantic=BuildProjectReport,
        context=[t1, t2, t3, t4],
    )

    return Crew(
        agents=[researcher, strategist, architect, qa, architect_v2],
        tasks=[t1, t2, t3, t4, t5],
        process=Process.sequential,
        verbose=True,
        **_crew_config(),
    )
