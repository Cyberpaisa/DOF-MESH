"""
Streamlit Dashboard — Mission Control Visual.
Cyber Paisa / Enigma Group

Lanzar con: streamlit run interfaces/streamlit_dashboard.py --server.port 8501
"""

import os
import sys
import glob
from datetime import datetime

import streamlit as st
import yaml
import requests
import json
from core.local_model_node import LocalAGINode, sanitize_text

# Agregar directorio padre al path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cargar .env para que las API keys estén disponibles
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(_env_path):
    for _line in open(_env_path):
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

# ═══════════════════════════════════════════════════════
# CONFIGURACION DE PAGINA
# ═══════════════════════════════════════════════════════

st.set_page_config(
    page_title="Q-AION Legion Dashboard",
    page_icon="🛡️",
    layout="wide",
)

st.title("🛡️ Q-AION Legion Dashboard")
st.caption("Sovereign AI Node — Phase 4 Core — Clean & Pure")


# ═══════════════════════════════════════════════════════
# FUNCIONES AUXILIARES
# ═══════════════════════════════════════════════════════

def load_projects():
    """Carga proyectos desde projects.yaml."""
    projects_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config", "projects.yaml",
    )
    if not os.path.exists(projects_path):
        return []
    with open(projects_path, "r") as f:
        data = yaml.safe_load(f)
    return data.get("projects", []) if data else []


def load_api_status():
    """Verifica estado de API keys."""
    keys = {
        "DeepSeek": "DEEPSEEK_API_KEY",
        "SambaNova": "SAMBANOVA_API_KEY",
        "Cerebras": "CEREBRAS_API_KEY",
        "Gemini": "GEMINI_API_KEY",
        "Telegram": "TELEGRAM_BOT_TOKEN",
        "AVAX Wallet": "QAION_PRIVATE_KEY",
        "Oracle Cloud": "ORACLE_CLOUD_PASSWORD",
    }
    return {name: bool(os.getenv(env)) for name, env in keys.items()}


def get_output_files(project_filter=None):
    """Lista archivos de output recientes."""
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    if not os.path.exists(base):
        return []
    pattern = os.path.join(base, "**", "*.md")
    files = glob.glob(pattern, recursive=True)
    files.sort(key=os.path.getmtime, reverse=True)
    if project_filter:
        files = [f for f in files if project_filter.lower() in f.lower()]
    return files[:20]


# ═══════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════

with st.sidebar:
    st.header("⚙ Configuracion")

    # Selector de proyecto
    projects = load_projects()
    project_names = ["General (todos)"] + [p["name"] for p in projects]
    selected_project = st.selectbox("Proyecto:", project_names)
    project = None if selected_project == "General (todos)" else selected_project

    st.divider()

    # Selector de modo
    mode = st.selectbox("Modo de ejecucion:", [
        "grant-hunt", "content", "daily-ops", "weekly-report",
        "research", "full-mvp", "code-review", "data",
    ])

    # Input de tarea
    task_input = st.text_area("Descripcion de la tarea:", height=100)

    # Upload de archivo Excel
    uploaded_file = st.file_uploader("Archivo Excel/CSV (opcional):", type=["xlsx", "csv"])

    # Boton de ejecucion
    if st.button("🚀 Ejecutar Crew", type="primary", use_container_width=True):
        st.session_state["running"] = True
        st.session_state["mode"] = mode
        st.session_state["task"] = task_input
        st.session_state["project"] = project

    st.divider()

    # Status de APIs
    st.subheader("APIs")
    api_status = load_api_status()
    for name, active in api_status.items():
        emoji = "🟢" if active else "🔴"
        st.text(f"{emoji} {name}")


# ═══════════════════════════════════════════════════════
# TABS PRINCIPALES
# ═══════════════════════════════════════════════════════

tab_chat, tab_ops, tab_grants, tab_agents, tab_outputs, tab_excel, tab_projects, tab_sam = st.tabs([
    "💬 Legion Chat", "📊 Daily Ops", "🎯 Grants Pipeline", "🤖 Agentes",
    "📝 Outputs", "📈 Excel", "📋 Proyectos", "💎 SAM Yield Engine"
])

# --- TAB: Legion Chat ---
# noinspection PyBroadException
with tab_chat:
    st.subheader("💬 DOF Command Center")
    st.caption("DeepSeek API — Blindaje Unicode Activo")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Safe commands whitelist - ONLY these can execute
    SAFE_COMMANDS = {
        "status": "python3 core/autonomous_planner.py --report",
        "planner": "python3 core/autonomous_planner.py --once",
        "tasks": "python3 core/deepseek_mesh_worker.py --status",
        "worker": "python3 core/deepseek_mesh_worker.py --once --limit 10",
        "balance": "python3 scripts/phase12_real_arbitrageur.py --check-balance",
        "scan": "python3 scripts/phase12_real_arbitrageur.py --scan",
        "hyperion": "python3 core/hyperion_cli.py status",
        "tests": "python3 -m unittest tests.test_governance -v",
        "vps": "tail -20 logs/vm_grabber.log",
        "mesh": "ls logs/mesh/inbox/ | head -20",
        "inbox": "ls -lt logs/mesh/inbox/claude-session-1/*.json 2>/dev/null | head -10",
    }

    def _send_to_mesh(message, target="claude-session-1"):
        """Deposita un mensaje en el mesh inbox para que Claude lo procese."""
        import uuid, time, json as _json
        _inbox = os.path.join("logs", "mesh", "inbox", target)
        os.makedirs(_inbox, exist_ok=True)
        _task_id = f"dashboard-{uuid.uuid4().hex[:8]}"
        _task = {
            "task_id": _task_id,
            "from": "dashboard-commander",
            "to": target,
            "type": "task",
            "prompt": message,
            "priority": "HIGH",
            "timestamp": time.time(),
        }
        _path = os.path.join(_inbox, f"{_task_id}.json")
        with open(_path, "w") as f:
            _json.dump(_task, f, indent=2, ensure_ascii=False)
        return _task_id

    # Direct command detection from user input
    KEYWORD_MAP = {
        "test": "tests", "tests": "tests", "governance": "tests",
        "balance": "balance", "saldo": "balance", "wallet": "balance",
        "planner": "status", "reporte": "status", "status": "status", "estado": "status",
        "tasks": "tasks", "tareas": "tasks", "pendientes": "tasks",
        "worker": "worker", "procesa": "worker", "ejecuta tasks": "worker",
        "scan": "scan", "precios": "scan", "dex": "scan", "arbitraje": "scan",
        "hyperion": "hyperion",
        "vps": "vps", "oracle": "vps", "grabber": "vps",
    }

    def _detect_command(text):
        """Detect if user input matches a safe command keyword."""
        lower = text.lower()
        for keyword, cmd_key in KEYWORD_MAP.items():
            if keyword in lower:
                return cmd_key
        if "mesh" in lower and ("envía" in lower or "envia" in lower or "agenda" in lower or "dile" in lower):
            return "MESH"
        return None

    if prompt := st.chat_input("¿Qué necesitas, Commander?"):
        clean_prompt = sanitize_text(prompt)

        st.session_state.messages.append({"role": "user", "content": clean_prompt})
        with st.chat_message("user"):
            st.markdown(clean_prompt)

        # Auto-detect and execute commands directly from user input
        _auto_cmd = _detect_command(clean_prompt)
        _auto_exec = None
        if _auto_cmd and _auto_cmd != "MESH" and _auto_cmd in SAFE_COMMANDS:
            import subprocess as _sp_auto
            try:
                _r = _sp_auto.run(
                    SAFE_COMMANDS[_auto_cmd], shell=True, capture_output=True, text=True,
                    timeout=30, cwd="/Users/jquiceva/equipo-de-agentes"
                )
                _auto_exec = _r.stdout[-2000:] if _r.stdout else _r.stderr[-500:]
            except Exception as _e:
                _auto_exec = f"Error: {_e}"
        elif _auto_cmd == "MESH":
            _mesh_content = clean_prompt.replace("envía al mesh:", "").replace("envia al mesh:", "").replace("agenda:", "").strip()
            if _mesh_content:
                _tid = _send_to_mesh(_mesh_content)
                _auto_exec = f"✅ Tarea {_tid} enviada al mesh"

        # Show execution result immediately if detected
        if _auto_exec:
            with st.chat_message("assistant"):
                st.markdown(f"**Ejecutando: `{_auto_cmd}`**")
                st.code(_auto_exec, language="text")
                st.session_state.messages.append({"role": "assistant", "content": f"Ejecutado: {_auto_cmd}\n```\n{_auto_exec}\n```"})
        else:
            with st.chat_message("assistant"):
                with st.spinner("DeepSeek pensando..."):
                    try:
                        import requests as _req
                        import subprocess as _sp
                        import glob as _gl
                        _ds_key = os.getenv("DEEPSEEK_API_KEY", "")
                        _sys_ctx = "Eres el DOF Oracle — inteligencia soberana del proyecto Enigma/Q-AION.\n"
                        _sys_ctx += "Responde en español. Conciso y técnico. Operador: jquiceva.\n"
                        try:
                            _sys_ctx += f"Core: {len(_gl.glob('core/*.py'))} módulos | Tests: {len(_gl.glob('tests/test_*.py'))}\n"
                            _sys_ctx += f"Mesh: {sum(len(_gl.glob(d + '*.json')) for d in _gl.glob('logs/mesh/inbox/*/'))} pending\n"
                            _sys_ctx += f"Wallet: {os.getenv('QAION_WALLET_ADDRESS', 'N/A')}\n"
                        except:
                            pass
                        _chat_msgs = [{"role": "system", "content": _sys_ctx}]
                        for _m in st.session_state.messages[-10:]:
                            _chat_msgs.append({"role": _m["role"], "content": _m["content"]})
                        _resp = _req.post(
                            "https://api.deepseek.com/chat/completions",
                            headers={"Authorization": f"Bearer {_ds_key}", "Content-Type": "application/json"},
                            json={"model": "deepseek-chat", "messages": _chat_msgs, "max_tokens": 800, "temperature": 0.7},
                            timeout=30,
                        )
                        response = _resp.json().get("choices", [{}])[0].get("message", {}).get("content", "Error: sin respuesta")
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    except Exception as e:
                        st.error(f"Error DeepSeek: {e}")

# --- TAB: Daily Ops ---
with tab_ops:
    st.subheader("Operaciones Diarias")
    st.info("Ejecuta el modo 'daily-ops' para generar el reporte matutino.")

    # Mostrar ultimo reporte diario si existe
    daily_files = [f for f in get_output_files() if "daily" in os.path.basename(f)]
    if daily_files:
        latest = daily_files[0]
        st.caption(f"Ultimo reporte: {os.path.basename(latest)}")
        with open(latest, "r") as f:
            st.markdown(f.read()[:5000])
    else:
        st.caption("No hay reportes diarios aun. Ejecuta daily-ops para generar uno.")


# --- TAB: Grants Pipeline ---
with tab_grants:
    st.subheader("Grant Pipeline")
    st.info("Ejecuta el modo 'grant-hunt' para buscar oportunidades.")

    grant_files = [f for f in get_output_files() if "grant" in os.path.basename(f)]
    if grant_files:
        latest = grant_files[0]
        st.caption(f"Ultimo reporte: {os.path.basename(latest)}")
        with open(latest, "r") as f:
            st.markdown(f.read()[:5000])
    else:
        st.caption("No hay reportes de grants aun.")


# --- TAB: Agentes ---
with tab_agents:
    st.subheader("Agentes — Panel Operativo")

    # ── 1. Mesh Nodes ──────────────────────────────────────
    st.markdown("### Mesh Nodes")
    _mesh_inbox = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "mesh", "inbox")
    _node_rows = []
    if os.path.isdir(_mesh_inbox):
        for _node_name in sorted(os.listdir(_mesh_inbox)):
            _node_dir = os.path.join(_mesh_inbox, _node_name)
            if not os.path.isdir(_node_dir):
                continue
            _pending = len([f for f in os.listdir(_node_dir) if f.endswith(".json")])
            _done = len([f for f in os.listdir(_node_dir) if f.endswith(".done")])
            _node_rows.append({"Node": _node_name, "Pending": _pending, "Done": _done, "Total": _pending + _done})

    if _node_rows:
        import pandas as _pd_agents
        _df_nodes = _pd_agents.DataFrame(_node_rows)
        _total_pending = _df_nodes["Pending"].sum()
        _total_done = _df_nodes["Done"].sum()
        _total_nodes = len(_df_nodes)

        _mcols = st.columns(3)
        _mcols[0].metric("Active Nodes", _total_nodes)
        _mcols[1].metric("Pending Tasks", int(_total_pending))
        _mcols[2].metric("Completed Tasks", int(_total_done))

        st.dataframe(_df_nodes, use_container_width=True, hide_index=True)
    else:
        st.info("No mesh nodes found in logs/mesh/inbox/")

    st.divider()

    # ── 2. Provider Status ─────────────────────────────────
    st.markdown("### Provider Status")
    _provider_keys = {
        "DeepSeek": "DEEPSEEK_API_KEY",
        "SambaNova": "SAMBANOVA_API_KEY",
        "Cerebras": "CEREBRAS_API_KEY",
        "Gemini": "GEMINI_API_KEY",
        "Groq": "GROQ_API_KEY",
    }
    _prov_rows = []
    for _pname, _penv in _provider_keys.items():
        _val = os.getenv(_penv, "")
        _set = bool(_val)
        _masked = (_val[:6] + "..." + _val[-4:]) if len(_val) > 12 else ("***" if _val else "")
        _prov_rows.append({"Provider": _pname, "Status": "Active" if _set else "Missing", "Key": _masked})

    _pcols = st.columns(5)
    for _pi, _pr in enumerate(_prov_rows):
        _pcols[_pi].metric(_pr["Provider"], _pr["Status"])

    if _prov_rows:
        import pandas as _pd_prov
        st.dataframe(_pd_prov.DataFrame(_prov_rows), use_container_width=True, hide_index=True)

    st.divider()

    # ── 3. Running Processes ───────────────────────────────
    st.markdown("### Running Processes")
    import subprocess as _sp_agents
    _process_targets = ["telegram", "streamlit", "deepseek_worker", "vm_grabber"]
    _proc_rows = []
    try:
        _ps_out = _sp_agents.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=5
        ).stdout
        for _ptarget in _process_targets:
            _matches = [ln for ln in _ps_out.splitlines() if _ptarget in ln and "grep" not in ln]
            _proc_rows.append({
                "Process": _ptarget,
                "Status": "Running" if _matches else "Stopped",
                "PIDs": ", ".join(ln.split()[1] for ln in _matches) if _matches else "-",
            })
    except Exception:
        for _ptarget in _process_targets:
            _proc_rows.append({"Process": _ptarget, "Status": "Unknown", "PIDs": "-"})

    _running_count = sum(1 for r in _proc_rows if r["Status"] == "Running")
    st.metric("Running", f"{_running_count} / {len(_process_targets)}")
    if _proc_rows:
        import pandas as _pd_proc
        st.dataframe(_pd_proc.DataFrame(_proc_rows), use_container_width=True, hide_index=True)

    st.divider()

    # ── 4. Wallet Balance Summary ──────────────────────────
    st.markdown("### Wallet")
    _wallet_addr = os.getenv("QAION_WALLET_ADDRESS", "")
    if _wallet_addr:
        _wcols = st.columns(2)
        _wcols[0].metric("Network", "Avalanche C-Chain")
        _wcols[1].metric("Address", _wallet_addr[:8] + "..." + _wallet_addr[-6:] if len(_wallet_addr) > 16 else _wallet_addr)
        st.caption(f"Full address: `{_wallet_addr}`")
    else:
        st.warning("QAION_WALLET_ADDRESS not set in environment.")

    st.divider()

    # ── 5. Web Bridge Status ───────────────────────────────
    st.markdown("### Web Bridges")
    _web_targets = {
        "gemini": "https://gemini.google.com/app",
        "chatgpt": "https://chatgpt.com",
        "minimax": "https://agent.minimax.io/chat",
        "kimi": "https://www.kimi.com/",
        "deepseek": "https://chat.deepseek.com",
        "arena": "https://arena.ai/",
        "qwen": "https://chat.qwenlm.ai/",
        "mimo": "https://aistudio.xiaomimimo.com/",
    }
    _bridge_rows = []
    for _bname, _burl in _web_targets.items():
        _binbox = os.path.join(_mesh_inbox, _bname)
        _bpending = 0
        if os.path.isdir(_binbox):
            _bpending = len([f for f in os.listdir(_binbox) if f.endswith(".json")])
        _bridge_rows.append({"Bridge": _bname, "URL": _burl, "Inbox Pending": _bpending})

    st.metric("Web Bridges", len(_web_targets))
    if _bridge_rows:
        import pandas as _pd_bridge
        st.dataframe(_pd_bridge.DataFrame(_bridge_rows), use_container_width=True, hide_index=True)


# --- TAB: Outputs ---
with tab_outputs:
    st.subheader("Outputs Recientes")

    filter_project = project if project else None
    files = get_output_files(filter_project)

    if files:
        selected_file = st.selectbox(
            "Selecciona un archivo:",
            files,
            format_func=lambda x: os.path.basename(x),
        )
        if selected_file:
            with open(selected_file, "r") as f:
                content = f.read()
            st.markdown(content[:10000])
            st.download_button(
                "Descargar archivo",
                content,
                file_name=os.path.basename(selected_file),
            )
    else:
        st.caption("No hay outputs aun.")


# --- TAB: Excel ---
with tab_excel:
    st.subheader("Analisis de Excel/CSV")

    if uploaded_file:
        import pandas as pd
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            st.write(f"**Filas:** {len(df)} | **Columnas:** {len(df.columns)}")
            st.dataframe(df.head(50), use_container_width=True)

            st.subheader("Estadisticas")
            st.dataframe(df.describe(), use_container_width=True)

        except Exception as e:
            st.error(f"Error leyendo archivo: {e}")
    else:
        st.caption("Sube un archivo Excel/CSV en la barra lateral para analizarlo.")


# --- TAB: Proyectos ---
with tab_projects:
    st.subheader("Proyectos Registrados")
    if projects:
        for p in projects:
            status_emoji = "🟢" if p.get("status") == "active" else "🟡"
            with st.expander(f"{status_emoji} {p['name']} ({p.get('ecosystem', '?')})"):
                st.write(f"**Descripcion:** {p.get('description', 'N/A')}")
                st.write(f"**Estado:** {p.get('status', 'N/A')}")
                team = p.get("team", [])
                if team:
                    st.write(f"**Equipo:** {', '.join(team)}")
                else:
                    st.write("**Equipo:** Sin equipo definido")
    else:
        st.caption("No hay proyectos. Edita config/projects.yaml para agregar.")

    st.info("Para agregar proyectos, edita `config/projects.yaml`")

# --- TAB: SAM Yield Engine ---
with tab_sam:
    st.subheader("🧊 Sovereign Arbitrage Multidimensional (SAM)")
    st.caption("Conflux x Avalanche Autofinancing Engine")
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Avalanche Liquidity Engine")
        import scripts.avalanche_yield_engine as avax
        engine = avax.AvalancheYieldEngine()
        av_address = engine.setup_wallet()
        av_balance = engine.monitor_balance()
        st.metric("Wallet Address", av_address)
        st.metric("Balance (USDC)", f"${av_balance:.2f}")
        
        if st.button("Ejecutar Arbitraje", type="primary"):
            st.success("Estrategia de yield iniciada en Trader Joe/Aave...")

    with col2:
        st.markdown("### Conflux Sovereign Funding")
        st.caption("Emisión de tokens de patrocinio y liquidez DOF")
        f_amount = st.number_input("Cantidad a patrocinar (USDC)", min_value=1.0, value=10.0)
        f_address = st.text_input("Billetera Destino", value=av_address)
        if st.button("Generar Link Conflux Sponsor", type="secondary"):
            from core.sovereign_funding_skill import SovereignFundingSkill
            skill = SovereignFundingSkill()
            res = skill.run("generate_link", amount=f_amount, to_address=f_address, to_chain="43114")
            st.code(res.data.get("result", "Link generado con éxito"))


# ═══════════════════════════════════════════════════════
# EJECUCION DE CREW (si se presiono el boton)
# ═══════════════════════════════════════════════════════

if st.session_state.get("running"):
    st.session_state["running"] = False
    mode = st.session_state.get("mode", "")
    task = st.session_state.get("task", "")
    proj = st.session_state.get("project")

    with st.spinner(f"Ejecutando {mode}... esto puede tomar unos minutos"):
        try:
            # Suppress crewai signal handler warnings in Streamlit threads
            import warnings
            import logging
            logging.getLogger("crewai.telemetry").setLevel(logging.CRITICAL)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                from crew import (
                    create_research_crew, create_full_mvp_crew,
                    create_grant_hunt_crew, create_content_crew,
                    create_daily_ops_crew, create_weekly_report_crew,
                    create_code_review_crew, create_data_analysis_crew,
                )

            if mode == "research":
                crew = create_research_crew(task)
            elif mode == "full-mvp":
                crew = create_full_mvp_crew(task)
            elif mode == "grant-hunt":
                crew = create_grant_hunt_crew(task, proj)
            elif mode == "content":
                crew = create_content_crew(task, proj)
            elif mode == "daily-ops":
                crew = create_daily_ops_crew()
            elif mode == "weekly-report":
                crew = create_weekly_report_crew(proj)
            elif mode == "data":
                crew = create_data_analysis_crew(task or "Analizar datos")
            else:
                st.error(f"Modo {mode} no soportado en dashboard aun")
                crew = None

            if crew:
                result = crew.kickoff()
                st.success("Completado!")
                st.markdown(str(result)[:10000])

                # Guardar output
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                out_dir = f"output/{proj}" if proj else "output"
                os.makedirs(out_dir, exist_ok=True)
                out_path = f"{out_dir}/{mode}_{ts}.md"
                with open(out_path, "w") as f:
                    f.write(str(result))
                st.caption(f"Guardado en: {out_path}")

        except Exception as e:
            st.error(f"Error: {e}")
