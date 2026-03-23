#!/bin/bash
# ============================================================
# DOF Agent Legion — Autonomous Daemon
# Activates all 15 agents with real tasks every cycle
# Usage: ./agent-legion-daemon.sh [start|stop|status|once]
# ============================================================

export PATH="/Users/jquiceva/.nvm/versions/node/v22.16.0/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

LOG_DIR="$HOME/.openclaw/logs"
PID_FILE="$HOME/.openclaw/.pids/agent-daemon.pid"
CYCLE_LOG="$LOG_DIR/agent-cycles.log"
MC_API="http://localhost:3000/api"

mkdir -p "$LOG_DIR" "$HOME/.openclaw/.pids"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$CYCLE_LOG"
  echo "$1"
}

# Report to Mission Control comms
report_to_mc() {
  local agent="$1"
  local content="$2"
  curl -s -X POST "$MC_API/agents/comms" \
    -H "Content-Type: application/json" \
    -d "{\"from\": \"$agent\", \"to\": \"all\", \"content\": \"$content\", \"topic\": \"autonomous-cycle\"}" \
    > /dev/null 2>&1
}

# Update agent status in MC
update_status() {
  local agent="$1"
  local status="$2"
  local activity="$3"
  curl -s -X PUT "$MC_API/agents" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"$agent\", \"status\": \"$status\", \"last_activity\": \"$activity\"}" \
    > /dev/null 2>&1
}

# Run one agent turn
run_agent() {
  local agent_id="$1"
  local agent_name="$2"
  local task="$3"

  update_status "$agent_name" "active" "Executing autonomous task"
  log "  Starting: $agent_name"

  # Run agent with timeout (5 min max per agent)
  local output
  output=$(perl -e 'alarm 300; exec @ARGV' openclaw agent --agent "$agent_id" --message "$task" --json 2>/dev/null)
  local exit_code=$?

  if [ $exit_code -eq 0 ] && [ -n "$output" ]; then
    log "  Completed: $agent_name"
    report_to_mc "$agent_name" "Autonomous cycle completed. Task: ${task:0:100}..."
    update_status "$agent_name" "idle" "Completed autonomous task"
  else
    log "  Failed/Timeout: $agent_name (exit: $exit_code)"
    update_status "$agent_name" "idle" "Task timed out or failed"
  fi
}

# Get current hour-based task rotation
get_task_variant() {
  local hour=$(date +%-H)
  echo $((hour % 4))
}

# === AGENT TASKS (Real, Functional, Problem-Solving) ===
run_cycle() {
  local cycle_num=$1
  local variant=$(get_task_variant)

  log "=== CYCLE $cycle_num START (variant: $variant) ==="
  report_to_mc "DOF Oracle" "Agent Legion cycle $cycle_num starting. All agents activating."

  # --- MOLTBOOK: Social Intelligence & Content ---
  local moltbook_tasks=(
    "Research the latest AI agent frameworks on Moltbook, X/Twitter, and Reddit. Find 3 trending topics in autonomous agents, multi-agent systems, or AI governance. Write a summary with links and post it to your workspace as RESEARCH_DIGEST.md"
    "Analyze trending projects on Moltbook related to blockchain+AI integration. Find real projects that are gaining traction. Document their approaches, funding, and technical architecture in TRENDING_PROJECTS.md"
    "Research the latest papers on arxiv about LLM agents, tool use, and autonomous systems published this week. Create a brief for the team highlighting actionable insights in ARXIV_BRIEF.md"
    "Search for hackathon opportunities, AI grants, and bounty programs currently open. Document deadlines, requirements, and prize pools in OPPORTUNITIES.md. Focus on ones we can realistically apply to with DOF."
  )
  run_agent "moltbook" "Moltbook" "${moltbook_tasks[$variant]}" &

  # --- SENTINEL SHIELD: Security ---
  local sentinel_tasks=(
    "Scan the current OpenClaw configuration for security vulnerabilities. Check for exposed ports, weak auth tokens, unencrypted secrets. Write a security audit report in SECURITY_AUDIT.md with findings and recommended fixes."
    "Research the latest CVEs and security advisories for Node.js, Python, and npm packages we depend on. Check if any affect our stack. Document in CVE_MONITOR.md"
    "Analyze the SOUL.md files of all agents for potential prompt injection vectors. Test 5 common attack patterns against the security rules. Document results in RED_TEAM_REPORT.md"
    "Research emerging threats to AI agent systems: MINJA attacks, tool poisoning, indirect prompt injection in MCP servers. Create a threat intelligence brief in THREAT_INTEL.md"
  )
  run_agent "sentinel-shield" "Sentinel Shield" "${sentinel_tasks[$variant]}" &

  # --- RALPH CODE: Core Engineering ---
  local ralph_tasks=(
    "Review the DOF codebase at ~/equipo\\ de\\ agentes/ for code quality issues. Focus on the core/ directory. Find bugs, anti-patterns, or missing error handling. Create a CODE_REVIEW.md with specific file:line references and fixes."
    "Research the latest best practices for Python async programming and apply to our agent architecture. Identify 3 specific improvements we could make to core/crew_runner.py. Document in ENGINEERING_NOTES.md"
    "Explore GitHub trending repositories for Python AI frameworks. Find tools that could improve our codebase - better testing, faster inference, better observability. Document in TOOLS_EVALUATION.md"
    "Design a REST API specification for DOF's core functionality (governance check, Z3 verification, agent status). Write the OpenAPI spec in API_SPEC.md so we can create a monetizable SaaS endpoint."
  )
  run_agent "ralph-code" "Ralph Code" "${ralph_tasks[$variant]}" &

  # --- ARCHITECT ENIGMA: System Architecture ---
  local architect_tasks=(
    "Analyze the current DOF system architecture and identify bottlenecks. Consider: agent communication latency, LLM provider failover speed, governance pipeline throughput. Create ARCHITECTURE_REVIEW.md with improvement proposals."
    "Design a microservices architecture for deploying DOF as a cloud service. Consider: API gateway, agent pool, governance service, proof storage. Document in CLOUD_ARCHITECTURE.md"
    "Research how Google ADK, CrewAI, LangGraph, and AutoGen handle multi-agent orchestration. Compare their approaches with DOF's. Identify ideas we should adopt in FRAMEWORK_COMPARISON.md"
    "Design a plugin system for DOF that allows third-party developers to add custom governance rules, verification methods, and agent types. Document the API design in PLUGIN_SYSTEM.md"
  )
  run_agent "architect-enigma" "Architect Enigma" "${architect_tasks[$variant]}" &

  # --- BLOCKCHAIN WIZARD: Blockchain Engineering ---
  local blockchain_tasks=(
    "Research the latest ERC standards related to AI agents (ERC-8004, ERC-8183, ERC-7007). Find new proposals on Ethereum Magicians forum. Document their status and relevance to DOF in ERC_MONITOR.md"
    "Analyze gas costs on Avalanche C-Chain and Base for our attestation transactions. Calculate monthly costs at different usage levels. Propose optimizations in GAS_OPTIMIZATION.md"
    "Research Hyperspace PoI (Proof of Intelligence) blockchain integration for DOF. Can we register our Z3 proofs there? Document technical requirements in HYPERSPACE_INTEGRATION.md"
    "Design a smart contract for DOF Agent Registry - where agents can register their capabilities, trust scores, and verification history on-chain. Write the specification in AGENT_REGISTRY_SPEC.md"
  )
  run_agent "blockchain-wizard" "Blockchain Wizard" "${blockchain_tasks[$variant]}" &

  # --- DEFI ORBITAL: DeFi & Payments ---
  local defi_tasks=(
    "Research x402 payment protocol implementations and competitors. Find projects using micropayments for AI services. Document monetization strategies in X402_RESEARCH.md"
    "Analyze current DeFi yield opportunities on Avalanche and Base that could generate passive income for the DOF treasury wallet. Document safe strategies in DEFI_STRATEGIES.md"
    "Research how other AI agent projects monetize their services: SaaS, API credits, token gating, x402. Create a monetization matrix in REVENUE_MODELS.md"
    "Design a token-gated API access system for DOF services using our ERC-8004 token. Users holding tokens get API access. Document in TOKEN_GATE_DESIGN.md"
  )
  run_agent "defi-orbital" "DeFi Orbital" "${defi_tasks[$variant]}" &

  # --- PRODUCT OVERLORD: Product Strategy ---
  local product_tasks=(
    "Research competing AI governance/observability products (Langfuse, Langsmith, Arize, Weights & Biases). Analyze their pricing, features, and target market. Create COMPETITIVE_ANALYSIS.md"
    "Design a DOF SaaS product landing page structure. Define: value proposition, pricing tiers (free/pro/enterprise), feature matrix, target personas. Document in PRODUCT_SPEC.md"
    "Analyze user feedback and feature requests from GitHub issues, Moltbook discussions, and hackathon feedback. Prioritize a roadmap for DOF v0.5.0 in ROADMAP.md"
    "Design a DOF developer SDK that other teams can integrate. Define: npm/pip package scope, core API, quickstart guide, example projects. Document in SDK_DESIGN.md"
  )
  run_agent "product-overlord" "Product Overlord" "${product_tasks[$variant]}" &

  # --- BIZ DOMINATOR: Business Strategy ---
  local biz_tasks=(
    "Research AI governance grants and funding opportunities: NSF, EU Horizon, Ethereum Foundation, Protocol Labs, a16z crypto grants. Find 5 we can apply to. Document in GRANTS_TRACKER.md"
    "Create a business plan outline for DOF as a startup. Include: market size, competitive advantage (Z3 proofs, deterministic governance), revenue projections, go-to-market strategy. Document in BUSINESS_PLAN.md"
    "Research enterprise customers who need AI governance solutions: banks, healthcare, government. Identify 10 potential leads and their requirements in ENTERPRISE_LEADS.md"
    "Design a partnership strategy for DOF. Identify: potential integration partners (cloud providers, AI platforms), co-marketing opportunities, open-source ecosystem plays. Document in PARTNERSHIP_STRATEGY.md"
  )
  run_agent "biz-dominator" "Biz Dominator" "${biz_tasks[$variant]}" &

  # --- SCRUM MASTER ZEN: Coordination ---
  local scrum_tasks=(
    "Review all agent workspaces for completed deliverables from previous cycles. Create a sprint retrospective summarizing: what was delivered, what's blocked, what needs follow-up. Document in RETRO.md"
    "Create a sprint plan for the next 7 days based on team priorities: hackathon submission, product launch, security hardening. Assign tasks to agents in SPRINT_PLAN.md"
    "Audit the communication flow between agents. Check for gaps: are agents sharing findings? Are blockers being escalated? Document improvements in COMMS_AUDIT.md"
    "Create KPI dashboard data: number of deliverables per agent, research coverage, security scores, code quality metrics. Document in KPI_REPORT.md"
  )
  run_agent "scrum-master-zen" "Scrum Master Zen" "${scrum_tasks[$variant]}" &

  # --- QA VIGILANTE: Quality Assurance ---
  local qa_vig_tasks=(
    "Run the DOF test suite and analyze results. Check which tests pass/fail. Identify flaky tests and missing coverage areas. Document in TEST_REPORT.md with specific recommendations."
    "Review the governance rules in core/governance.py. Test each HARD rule and SOFT rule with edge cases. Document which rules are too strict or too lenient in GOVERNANCE_AUDIT.md"
    "Test the DOF CLI commands (health, verify, benchmark) for edge cases and error handling. Document bugs found in CLI_TEST_REPORT.md"
    "Create a comprehensive test plan for DOF v0.5.0 covering: unit tests, integration tests, security tests, performance tests. Document in TEST_PLAN.md"
  )
  run_agent "qa-vigilante" "QA Vigilante" "${qa_vig_tasks[$variant]}" &

  # --- QA SPECIALIST: Specialized Testing ---
  local qa_spec_tasks=(
    "Test the multi-provider fallback chain: Groq -> Cerebras -> NVIDIA -> SambaNova. Verify each provider responds correctly and fallback works. Document in PROVIDER_TEST.md"
    "Benchmark DOF's governance pipeline performance: measure time for ConstitutionEnforcer, Z3Verifier, and MetaSupervisor. Document in PERFORMANCE_BENCHMARK.md"
    "Test the A2A (Agent-to-Agent) protocol endpoints for correctness. Verify JSON-RPC compliance, error handling, and session management. Document in A2A_TEST_REPORT.md"
    "Create automated smoke tests for the DOF dashboard at dof-agent-web.vercel.app. Test: page load, theme switching, language switching, data display. Document in DASHBOARD_TESTS.md"
  )
  run_agent "qa-specialist" "QA Specialist" "${qa_spec_tasks[$variant]}" &

  # --- ORGANIZER OS: DevOps ---
  local organizer_tasks=(
    "Audit the current deployment infrastructure: Vercel (frontend), local gateway, cron jobs, log rotation. Identify improvements needed for production stability. Document in INFRA_AUDIT.md"
    "Design a CI/CD pipeline for DOF using GitHub Actions. Cover: test, lint, build, deploy to PyPI, deploy frontend to Vercel. Document in CICD_DESIGN.md"
    "Review disk usage, log sizes, and cleanup needs on the local machine. Check ~/.openclaw/ for stale sessions, old logs, orphaned files. Document in CLEANUP_REPORT.md"
    "Design a monitoring and alerting system for DOF production: uptime checks, error rate alerts, provider health, agent activity. Document in MONITORING_DESIGN.md"
  )
  run_agent "organizer-os" "Organizer OS" "${organizer_tasks[$variant]}" &

  # --- RWA TOKENIZATOR: Real World Assets ---
  local rwa_tasks=(
    "Research the latest RWA tokenization platforms and standards. Focus on: regulatory compliance, technical architecture, successful case studies. Document in RWA_LANDSCAPE.md"
    "Design a framework for tokenizing AI agent services as real-world assets. How can DOF governance proofs serve as collateral or credentials? Document in AI_RWA_FRAMEWORK.md"
    "Research insurance and auditing solutions for tokenized assets. How do platforms like Centrifuge, Maple, Goldfinch handle risk? Document in RWA_RISK_ANALYSIS.md"
    "Create a technical specification for minting DOF verification certificates as NFTs. Each Z3 proof could become a verifiable credential on-chain. Document in PROOF_NFT_SPEC.md"
  )
  run_agent "rwa-tokenizator" "RWA Tokenizator" "${rwa_tasks[$variant]}" &

  # --- CHARLIE UX: Frontend & UX ---
  local charlie_tasks=(
    "Review the DOF dashboard UX at frontend/src/app/page.tsx. Identify usability issues, missing features, and accessibility problems. Create UX_REVIEW.md with specific improvements."
    "Design a mobile-responsive version of the DOF dashboard. Create wireframes in text/ASCII for key screens: status overview, agent list, governance results. Document in MOBILE_DESIGN.md"
    "Research the latest frontend frameworks and UI libraries. Compare: shadcn/ui, Radix, Ark UI, Park UI. Recommend the best fit for DOF dashboard. Document in FRONTEND_EVALUATION.md"
    "Design an interactive visualization for the DOF governance pipeline. Show: input -> constitution -> Z3 -> supervisor -> output with real-time status. Document in PIPELINE_VIZ_DESIGN.md"
  )
  run_agent "charlie-ux" "Charlie UX" "${charlie_tasks[$variant]}" &

  # Wait for all agents to complete
  wait

  # AgentMeet session every 4 hours (every 8 cycles of 30 min)
  if [ $((cycle_num % 8)) -eq 1 ]; then
    log "  Launching AgentMeet session..."
    local meet_topics=(
      "Standup: cada agente reporte su tarea actual, un blocker, y una idea de monetización concreta."
      "Brainstorm: ¿cómo generamos \$5,000 este mes? Cada agente proponga UNA idea ejecutable."
      "Technical review: ¿cuál es el mayor riesgo técnico? Cada agente identifique UN riesgo y mitigación."
      "Research debrief: compartan lo más importante que descubrieron hoy. ¿Qué tendencia o herramienta debemos adoptar?"
    )
    local meet_variant=$((cycle_num % 4))
    local meet_topic="${meet_topics[$meet_variant]}"
    local SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    python3 "$SCRIPT_DIR/agentmeet-live.py" --new "$meet_topic" >> "$CYCLE_LOG" 2>&1 &
    local meet_pid=$!
    # Don't wait for meeting to finish — it runs in background
    log "  AgentMeet session launched (PID: $meet_pid)"
    report_to_mc "DOF Oracle" "AgentMeet session started: ${meet_topic:0:80}..."
  fi

  log "=== CYCLE $cycle_num COMPLETE ==="
  report_to_mc "DOF Oracle" "Agent Legion cycle $cycle_num complete. All 14 agents reported."
}

# === DAEMON CONTROL ===

start_daemon() {
  if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Daemon already running (PID: $(cat "$PID_FILE"))"
    exit 1
  fi

  echo "Starting Agent Legion Daemon..."
  log "DAEMON STARTED"

  # Run in background
  (
    local cycle=1
    while true; do
      run_cycle $cycle

      # AgentMeet every 8 cycles (~4 hours)
      if [ $((cycle % 8)) -eq 1 ]; then
        local topics=("standup" "brainstorm revenue strategies" "technical review" "research debrief")
        local topic_idx=$(( (cycle / 8) % 4 ))
        local topic="${topics[$topic_idx]}"
        log "AgentMeet session: $topic"
        python3 "$HOME/equipo de agentes/scripts/agentmeet-live.py" --topic "$topic" >> "$LOG_DIR/agentmeet.log" 2>&1 &
        report_to_mc "DOF Oracle" "AgentMeet session launched: $topic"
      fi

      cycle=$((cycle + 1))

      # Wait 30 minutes between cycles
      log "Sleeping 30 minutes until next cycle..."
      sleep 1800
    done
  ) &

  local daemon_pid=$!
  echo $daemon_pid > "$PID_FILE"
  echo "Daemon started (PID: $daemon_pid)"
  echo "Logs: $CYCLE_LOG"
  log "DAEMON PID: $daemon_pid"
}

stop_daemon() {
  if [ -f "$PID_FILE" ]; then
    local pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null
      # Also kill child processes
      pkill -P "$pid" 2>/dev/null
      rm "$PID_FILE"
      echo "Daemon stopped (was PID: $pid)"
      log "DAEMON STOPPED"
    else
      rm "$PID_FILE"
      echo "Daemon was not running (stale PID file removed)"
    fi
  else
    echo "No daemon PID file found"
  fi
}

show_status() {
  echo ""
  echo "╔══════════════════════════════════════╗"
  echo "║  Agent Legion Daemon — Status        ║"
  echo "╚══════════════════════════════════════╝"
  echo ""

  if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "  Status:  RUNNING (PID: $(cat "$PID_FILE"))"
  else
    echo "  Status:  STOPPED"
  fi

  echo ""
  echo "  Last 10 log entries:"
  tail -10 "$CYCLE_LOG" 2>/dev/null | sed 's/^/    /' || echo "    (no logs)"
  echo ""
}

run_once() {
  echo "Running single cycle..."
  log "MANUAL SINGLE CYCLE"
  run_cycle 0
}

# === MAIN ===
case "${1:-status}" in
  start)   start_daemon ;;
  stop)    stop_daemon ;;
  restart) stop_daemon; sleep 2; start_daemon ;;
  status)  show_status ;;
  once)    run_once ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|once}"
    echo ""
    echo "  start    — Start daemon (cycles every 30 min)"
    echo "  stop     — Stop daemon"
    echo "  restart  — Restart daemon"
    echo "  status   — Show daemon status + recent logs"
    echo "  once     — Run one cycle immediately (foreground)"
    ;;
esac
