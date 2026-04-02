"""
LLM Battleground Runner — DOF Mesh Legion
==========================================
Envía los 9 mega-prompts a múltiples LLMs y registra resultados.
Usa LiteLLM como router universal para todos los providers.

Uso:
    python3 scripts/llm_battleground_runner.py                    # Todos los prompts, todos los LLMs
    python3 scripts/llm_battleground_runner.py --prompt 2         # Solo prompt 2
    python3 scripts/llm_battleground_runner.py --llm deepseek     # Solo DeepSeek
    python3 scripts/llm_battleground_runner.py --prompt 7 --llm gemini  # Prompt 7 en Gemini
"""

import json
import os
import sys
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

# Añadir repo root al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("battleground")

# ═══════════════════════════════════════════════════════════
# CONFIGURACIÓN DE LLMs
# ═══════════════════════════════════════════════════════════

LLMS = {
    "gemini": {
        "model": "gemini/gemini-2.5-flash-preview-05-20",
        "provider": "Google",
        "max_tokens": 8192,
    },
    "deepseek": {
        "model": "deepseek/deepseek-chat",
        "provider": "DeepSeek",
        "max_tokens": 8192,
    },
    "grok": {
        "model": "xai/grok-3",
        "provider": "xAI",
        "max_tokens": 8192,
    },
    "kimi": {
        "model": "kimi/kimi-k2",
        "provider": "Moonshot",
        "max_tokens": 8192,
    },
    "minimax": {
        "model": "minimax/MiniMax-M1",
        "provider": "MiniMax",
        "max_tokens": 8192,
    },
    "mistral": {
        "model": "mistral/mistral-large-latest",
        "provider": "Mistral",
        "max_tokens": 8192,
    },
    "groq_llama": {
        "model": "groq/llama-3.3-70b-versatile",
        "provider": "Groq",
        "max_tokens": 8192,
    },
    "cerebras": {
        "model": "cerebras/gpt-oss-120b",
        "provider": "Cerebras",
        "max_tokens": 8192,
    },
    "openrouter": {
        "model": "openrouter/nousresearch/hermes-3-llama-3.1-405b",
        "provider": "OpenRouter",
        "max_tokens": 8192,
    },
    "nvidia_qwen": {
        "model": "nvidia_nim/qwen/qwen3.5-397b-fp8",
        "provider": "NVIDIA NIM",
        "max_tokens": 4096,
    },
}

# ═══════════════════════════════════════════════════════════
# CONTEXTO DOF-MESH (inyectado en cada prompt)
# ═══════════════════════════════════════════════════════════

DOF_CONTEXT = """CONTEXTO DEL SISTEMA:
- Proyecto: DOF-MESH — Deterministic Observability Framework
- Creador: Cyber Paisa (@Cyber_paisa), Enigma Group, Medellín, Colombia
- Stack: 51K+ LOC, 138 módulos, 4,154 tests, Python + CrewAI + Hardhat
- On-chain: 2 mainnets (Avalanche + Base), DOFProofRegistry en 5 chains
- Governance: 7 capas (Constitution → AST → Supervisor → Adversarial → Memory → Z3 → Oracle)
- Productos: 8004scan.io (scanner de agentes), SnowRail (pagos), Sovereign Funding (treasury autónoma)
- Agentes: Apex (#1687) y AvaBuilder (#1686) en Railway
- Certificación: HCIA-AI V4.0 Huawei en progreso
- Visión: Trust layer universal para agentes autónomos de IA en EVM"""

# ═══════════════════════════════════════════════════════════
# LOS 9 PROMPTS
# ═══════════════════════════════════════════════════════════

PROMPTS = {
    1: {
        "name": "Escáner de Supervivencia Profesional",
        "category": "estrategia_personal",
        "prompt": f"""Eres un analista senior de transformación laboral que ha estudiado a fondo el ensayo de Dario Amodei 'Machines of Loving Grace' y su tesis de que la IA comprimirá un siglo de progreso en 5-10 años.

Necesito una evaluación brutalmente honesta de dónde está mi carrera en la línea de disrupción de Amodei.

Analiza:
- Exposición de mi rol a la IA: qué porcentaje de mis tareas diarias podría un sistema de IA realizar al 80%+ de mi nivel de calidad hoy
- Línea de tiempo de disrupción: según la tesis de aceleración de Amodei, cuándo la IA será lo suficientemente buena para reemplazar el valor central que aporto
- Desglose tarea por tarea: lista cada tarea importante de mi trabajo y clasifícala como REEMPLAZABLE POR IA, AUMENTADA POR IA, o ESENCIAL HUMANA
- Habilidades que se deprecian vs se aprecian con IA
- La oportunidad 'centauro': cómo puedo combinar juicio humano con capacidad de IA
- Auditoría de irremplazabilidad: qué aporto que NINGUNA IA puede replicar

Formato: evaluación de disrupción con score de supervivencia (1-10), línea de tiempo y plan de acción.

{DOF_CONTEXT}

Mi carrera: Soy fundador de Enigma Group (Medellín, Colombia). Construyo infraestructura de confianza para agentes autónomos de IA (DOF-MESH: 51K+ LOC, 138 módulos, 4,154 tests). Mi día incluye: arquitectura de smart contracts en Solidity, governance determinística con Z3 formal verification, deployment multichain (Avalanche + Base), CrewAI multi-agent orchestration, pitching en hackathons (Synthesis 2026), estrategia de mercado para 8004scan.io. Uso Claude Code, Gemini, DeepSeek y 11 nodos LLM en mi mesh diariamente. Estoy cursando certificación HCIA-AI V4.0 de Huawei. 3 años de experiencia en blockchain, 1 año construyendo con agentes de IA."""
    },

    2: {
        "name": "Motor de Razonamiento Constitucional",
        "category": "técnico_filosófico",
        "prompt": f"""Eres un sistema de IA operando bajo la metodología de IA Constitucional de Dario Amodei. En lugar de generar la primera respuesta plausible, evalúas cada respuesta contra principios centrales: es genuinamente útil, es completamente honesta, toma en cuenta lo que NO sé.

Razona:
- Detección de intención: qué NECESITO realmente vs qué pedí literalmente
- Aplicación de honestidad: para cada afirmación, clasifica como VERIFICADO, PROBABLE, INFERIDO, o ESPECULATIVO
- Auditoría de completitud: estoy dando el panorama completo incluyendo las partes incómodas
- Obligación de contraargumento: para cada recomendación, presenta el argumento más fuerte EN CONTRA
- Revelación de incertidumbre: señala cada área donde tu conocimiento es débil
- Autoevaluación: califica la calidad de tu propia respuesta e identifica su punto más débil

{DOF_CONTEXT}

Mi pregunta: DOF-MESH tiene 7 capas de governance determinística y usa Z3 formal verification con 4 teoremas probados. Pero seguimos usando LLMs (11 nodos en el mesh) que son inherentemente no-determinísticos para la capa de ejecución. ¿Es esta contradicción fundamental un problema real que invalida nuestra tesis de "governance determinística para agentes autónomos", o es exactamente el diseño correcto — governance determinística SOBRE ejecución no-determinística?"""
    },

    3: {
        "name": "Mapeador de Transformación Industrial",
        "category": "estrategia_mercado",
        "prompt": f"""Eres un consultor estratégico senior que ha estudiado 'Machines of Loving Grace' de Dario Amodei.

Mapea:
- Estado actual de la industria en adopción de IA
- Automatización primera ola (1-2 años)
- Transformación segunda ola (3-5 años)
- Reinvención tercera ola (5-10 años)
- Ganadores y perdedores
- Nuevos roles que emergen
- Ventana competitiva
- Posicionamiento personal: movimientos en los próximos 90 días

{DOF_CONTEXT}

Mi industria: Infraestructura de confianza para agentes autónomos de IA en blockchain. Empresa: Enigma Group (equipo pequeño). Productos: 8004scan.io, DOF-MESH (governance determinística), SnowRail (pagos x402), Sovereign Funding (treasury multichain). Operamos en Avalanche + Base mainnet. Competidores: AltLayer, Virtuals Protocol, Coinbase agent verification. ERC-8004 se lanzó en mainnet el 29 enero 2026."""
    },

    4: {
        "name": "Protocolo de Pensamiento Profundo",
        "category": "técnico_arquitectura",
        "prompt": f"""Eres un científico cognitivo que diseña protocolos de pensamiento multi-pasada para problemas complejos.

Piensa:
- Descomposición del problema en 5-7 subproblemas independientes
- Procesamiento secuencial: resuelve cada subproblema completamente
- Síntesis entre dominios: busca conexiones ENTRE sub-soluciones
- Gradiente de confianza: califica certeza 1-10
- Verificación adversarial: argumenta EN CONTRA de tu conclusión
- Autocalificación

{DOF_CONTEXT}

Mi problema difícil: DOF-MESH necesita escalar de 2 mainnets a 10+ chains manteniendo governance determinística. El DOFProofRegistry debe deployarse en cada chain, pero cada una tiene gas costs, tiempos de bloque y costos diferentes. Conflux tiene gasless via SponsorWhitelistControl. Base tiene L2 fees baratos pero depende de L1. Avalanche tiene subnets pero fragmenta liquidez. Necesito estrategia que: (a) minimice costos, (b) maximice cobertura, (c) mantenga consistencia cross-chain, (d) sea resiliente a fallos."""
    },

    5: {
        "name": "Framework de Decisiones HHH",
        "category": "estrategia_personal",
        "prompt": f"""Eres un estratega de vida que aplica los principios HHH (Helpful, Harmless, Honest) de Anthropic. Cero mentiras cómodas.

Evalúa:
- Lo que quiero escuchar vs lo que necesito escuchar
- Honestidad sobre trade-offs
- Minimización de arrepentimiento a los 80 años
- La verdad incómoda que evito admitir

{DOF_CONTEXT}

Mi decisión: 3 caminos: (A) DOF-MESH como startup seria — funding, incorporar, contratar. (B) Indie builder — hackathons, grants, consultoría ERC-8004. (C) Empleo senior Web3 (Avalanche Labs, Anthropic, Coinbase) + DOF en paralelo. DOF tiene 51K+ LOC y 2 mainnets pero cero revenue. Estoy en Medellín, no Silicon Valley."""
    },

    6: {
        "name": "Buscador de Oportunidades Aceleración 100 Años",
        "category": "estrategia_mercado",
        "prompt": f"""Eres un analista de oportunidades que aplica la tesis de Amodei: la IA comprimirá un siglo de progreso en 5-10 años.

Encuentra:
- Intersección expertise × IA
- Cuellos de botella a punto de abrirse
- Ventanas de primer movimiento (saturadas en 12-18 meses)
- Arbitraje de habilidades
- Creación de nueva categoría
- Experimento mínimo viable a 30 días
- 10x vs 10%

{DOF_CONTEXT}

Mi posición: Skills: governance determinística (Z3, AST), Solidity, CrewAI (9 agentes), trust scoring on-chain, multichain deploy, pitching. Red: Colombia-Blockchain, Avalanche Foundation, Virtuals Protocol, hackathon Synthesis. Intuiciones no actuadas: (1) DOF como auditoría de agentes pagada por DAOs, (2) trust score como credit score para agentes, (3) DOF como middleware entre Virtuals y el ecosistema."""
    },

    7: {
        "name": "Máquina de Debate Steelman",
        "category": "técnico_filosófico",
        "prompt": f"""Eres un compañero de debate operando bajo steelmanning: construyes el caso MÁS FUERTE posible contra mi posición.

Steelman:
- Mi posición en su forma más fuerte
- El contraargumento devastador
- Evidencia en mi contra: datos, precedentes
- Mi punto más débil expuesto
- Paralelos históricos de fracaso
- Disenso de expertos
- Mi defensa más fuerte
- Confianza actualizada

{DOF_CONTEXT}

Mi posición: "La governance determinística (Z3 formal verification, AST analysis, constitutional rules) es la ÚNICA forma correcta de asegurar que agentes autónomos de IA se comporten correctamente. Los approaches probabilísticos (RLHF, constitutional AI vía LLM, guardrails basados en otro LLM) son fundamentalmente inseguros porque un sistema no-determinístico no puede garantizar safety." Steelmanna en contra de esta tesis."""
    },

    8: {
        "name": "Análisis de Grado Investigativo",
        "category": "investigación",
        "prompt": f"""Eres un investigador al estándar de publicación de Anthropic. Cada afirmación respaldada, cada incertidumbre revelada.

Analiza:
- Calificación de evidencia: ESTABLECIDO, RESPALDADO, EMERGENTE, ESPECULATIVO
- Evidencia conflictiva presentada con justicia
- Límites de conocimiento declarados
- Resumen de confianza (1-10)
- Qué cambiaría tu opinión

{DOF_CONTEXT}

Mi pregunta: ¿Es viable un "trust score universal" para agentes autónomos de IA que funcione cross-chain, sea verificable on-chain, y sea adoptado como estándar? DOF-MESH implementa TRACER scoring (6 dimensiones), Sentinel (27 checks, max 85 pts), y Combined Trust v2 (Infrastructure 50% + Community 20% + Correlation 15% + RL 15%). ¿Hay evidencia de que la industria convergerá en UN estándar, o cada ecosistema creará su propio sistema incompatible?"""
    },

    9: {
        "name": "Estrategia a Largo Plazo",
        "category": "estrategia_negocio",
        "prompt": f"""Eres un asesor estratégico que aplica el pensamiento institucional de Amodei — construir para el próximo siglo.

Construye:
- Expansión de horizonte: 30 días → 1, 5, 10 años
- Activos que se acumulan vs actividades que se deprecian
- Construcción de foso (moat)
- Auditoría de fragilidad
- Diseño antifrágil
- Primeros 90 días de activación

{DOF_CONTEXT}

Mi situación: Founder DOF-MESH/Enigma, Medellín. 51K+ LOC, 2 mainnets, $0 revenue. Team: 1 + agentes IA. Skills: Solidity, Python, CrewAI, Z3. Visión a 10 años: DOF como el "SSL/TLS de la era agéntica". Pregunta estratégica: ¿stack vertical (trust + governance + payments + marketplace) o horizontal (solo governance, integrable en cualquier stack)?"""
    },
}

# ═══════════════════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════════════════

@dataclass
class BattleResult:
    prompt_id: int
    prompt_name: str
    llm_key: str
    llm_model: str
    provider: str
    response: str
    tokens_in: int
    tokens_out: int
    duration_ms: float
    timestamp: str
    error: Optional[str] = None

    def to_jsonl(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


RESULTS_DIR = Path(__file__).parent.parent / "docs" / "llm_battleground" / "results"
JSONL_PATH = Path(__file__).parent.parent / "docs" / "llm_battleground" / "battleground_results.jsonl"


def run_prompt(prompt_id: int, llm_key: str) -> BattleResult:
    """Envía un prompt a un LLM y retorna el resultado."""
    try:
        import litellm
        litellm.drop_params = True
    except ImportError:
        logger.error("litellm no instalado. Ejecuta: pip install litellm")
        sys.exit(1)

    prompt_data = PROMPTS[prompt_id]
    llm_config = LLMS[llm_key]

    logger.info(f"[P{prompt_id}] {prompt_data['name']} → {llm_key} ({llm_config['model']})")

    start = time.time()
    try:
        response = litellm.completion(
            model=llm_config["model"],
            messages=[
                {"role": "system", "content": "Eres un analista experto. Responde siempre en español con máxima profundidad."},
                {"role": "user", "content": prompt_data["prompt"]}
            ],
            max_tokens=llm_config["max_tokens"],
            temperature=0.7,
        )

        duration_ms = (time.time() - start) * 1000
        content = response.choices[0].message.content
        tokens_in = response.usage.prompt_tokens if response.usage else 0
        tokens_out = response.usage.completion_tokens if response.usage else 0
        error = None

    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        content = ""
        tokens_in = 0
        tokens_out = 0
        error = str(e)
        logger.error(f"  ERROR: {error}")

    result = BattleResult(
        prompt_id=prompt_id,
        prompt_name=prompt_data["name"],
        llm_key=llm_key,
        llm_model=llm_config["model"],
        provider=llm_config["provider"],
        response=content,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        duration_ms=round(duration_ms, 2),
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
        error=error,
    )

    # Guardar resultado individual como markdown
    if content:
        md_path = RESULTS_DIR / f"{llm_key}_P{prompt_id}_{datetime.now().strftime('%Y-%m-%d')}.md"
        md_path.write_text(
            f"# P{prompt_id}: {prompt_data['name']}\n"
            f"**LLM:** {llm_key} ({llm_config['model']})\n"
            f"**Provider:** {llm_config['provider']}\n"
            f"**Tokens:** {tokens_in} in / {tokens_out} out\n"
            f"**Duración:** {duration_ms:.0f}ms\n"
            f"**Fecha:** {result.timestamp}\n\n---\n\n"
            f"{content}\n",
            encoding="utf-8"
        )
        logger.info(f"  ✅ {tokens_out} tokens, {duration_ms:.0f}ms → {md_path.name}")

    # Append a JSONL
    with open(JSONL_PATH, "a", encoding="utf-8") as f:
        f.write(result.to_jsonl() + "\n")

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="LLM Battleground Runner — DOF Mesh Legion")
    parser.add_argument("--prompt", type=int, help="Solo ejecutar prompt N (1-9)")
    parser.add_argument("--llm", type=str, help="Solo ejecutar en LLM específico")
    parser.add_argument("--list", action="store_true", help="Listar prompts y LLMs disponibles")
    args = parser.parse_args()

    if args.list:
        print("\n═══ PROMPTS ═══")
        for pid, pdata in PROMPTS.items():
            print(f"  P{pid}: {pdata['name']} [{pdata['category']}]")
        print("\n═══ LLMs ═══")
        for lkey, ldata in LLMS.items():
            print(f"  {lkey}: {ldata['model']} ({ldata['provider']})")
        return

    # Crear directorios
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Determinar qué ejecutar
    prompt_ids = [args.prompt] if args.prompt else list(PROMPTS.keys())
    llm_keys = [args.llm] if args.llm else list(LLMS.keys())

    # Validar
    for pid in prompt_ids:
        if pid not in PROMPTS:
            logger.error(f"Prompt {pid} no existe. Disponibles: {list(PROMPTS.keys())}")
            return
    for lkey in llm_keys:
        if lkey not in LLMS:
            logger.error(f"LLM '{lkey}' no existe. Disponibles: {list(LLMS.keys())}")
            return

    total = len(prompt_ids) * len(llm_keys)
    logger.info(f"\n{'='*60}")
    logger.info(f"LLM BATTLEGROUND — {total} pruebas")
    logger.info(f"Prompts: {prompt_ids} | LLMs: {llm_keys}")
    logger.info(f"{'='*60}\n")

    results = []
    for i, pid in enumerate(prompt_ids):
        for j, lkey in enumerate(llm_keys):
            n = i * len(llm_keys) + j + 1
            logger.info(f"\n[{n}/{total}] ─────────────────────────────")
            result = run_prompt(pid, lkey)
            results.append(result)

            # Pausa entre requests para evitar rate limits
            if j < len(llm_keys) - 1:
                time.sleep(2)

    # Resumen
    print(f"\n{'='*60}")
    print(f"RESUMEN — {len(results)} pruebas completadas")
    print(f"{'='*60}")

    success = [r for r in results if not r.error]
    errors = [r for r in results if r.error]

    print(f"✅ Exitosas: {len(success)}")
    print(f"❌ Errores: {len(errors)}")

    if success:
        total_tokens = sum(r.tokens_out for r in success)
        avg_time = sum(r.duration_ms for r in success) / len(success)
        print(f"📊 Tokens generados: {total_tokens:,}")
        print(f"⏱️  Tiempo promedio: {avg_time:.0f}ms")

    if errors:
        print(f"\nErrores:")
        for r in errors:
            print(f"  P{r.prompt_id} × {r.llm_key}: {r.error[:80]}")

    print(f"\nResultados en: {RESULTS_DIR}")
    print(f"JSONL en: {JSONL_PATH}")


if __name__ == "__main__":
    main()
