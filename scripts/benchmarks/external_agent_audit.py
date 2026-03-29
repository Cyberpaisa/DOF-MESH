#!/usr/bin/env python3
"""
DOF External Agent Audit — 13 real tests against live agents on 8004scan.io.

Tests agents across multiple networks via their public endpoints:
  Test  1-4:  Snowrail A2A agents (Fuji/Avalanche)
  Test  5-6:  Quick Intel & Tator Trader x402 probes (multi-chain)
  Test  7-8:  Our agents OASF endpoints (Avalanche mainnet)
  Test  9-10: Our agents A2A agent cards (Avalanche mainnet)
  Test 11:    quack_agent MCP manifest (Avalanche)
  Test 12:    Neo MCP endpoint (arena.social)
  Test 13:    DOF governance cross-verification of all fetched outputs

Output: JSONL audit log at logs/audit/external_audit_{timestamp}.jsonl
"""
import sys
import os
import json
import time
import uuid
import hashlib
import ssl
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv()

# ── Audit logger ──────────────────────────────────────────────────────
AUDIT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "audit")
os.makedirs(AUDIT_DIR, exist_ok=True)
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
AUDIT_FILE = os.path.join(AUDIT_DIR, f"external_audit_{TIMESTAMP}.jsonl")
RUN_ID = str(uuid.uuid4())[:8]

# SSL context for HTTPS (skip verification for agent endpoints)
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def audit_log(test_num: int, test_name: str, agent: str, protocol: str, data: dict, elapsed_ms: float = 0):
    """Append a single audit entry as JSONL."""
    entry = {
        "run_id": RUN_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "test_num": test_num,
        "test_name": test_name,
        "agent": agent,
        "protocol": protocol,
        "elapsed_ms": round(elapsed_ms, 2),
        **data,
    }
    with open(AUDIT_FILE, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")
    return entry


def fetch_url(url: str, timeout: int = 15, method: str = "GET", headers: dict = None) -> tuple:
    """Fetch URL and return (status_code, body_text, elapsed_ms)."""
    t0 = time.perf_counter()
    req = Request(url, method=method)
    req.add_header("User-Agent", "DOF-Audit/1.0")
    req.add_header("Accept", "application/json, text/plain, */*")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        resp = urlopen(req, timeout=timeout, context=SSL_CTX)
        body = resp.read().decode("utf-8", errors="replace")
        ms = (time.perf_counter() - t0) * 1000
        return resp.status, body, ms
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else str(e)
        ms = (time.perf_counter() - t0) * 1000
        return e.code, body, ms
    except (URLError, Exception) as e:
        ms = (time.perf_counter() - t0) * 1000
        return 0, str(e), ms


def safe_json(body: str) -> dict | list | None:
    """Try to parse JSON, return None on failure."""
    try:
        return json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return None


# ── External Agent Registry ──────────────────────────────────────────
EXTERNAL_AGENTS = [
    # Snowrail A2A agents (4)
    {
        "name": "snowrail-yuki",
        "chain": "Avalanche Fuji",
        "protocol": "A2A",
        "endpoint": "https://snowrail-agents-production.up.railway.app/snowrail-yuki/.well-known/agent.json",
        "a2a_rpc": "https://snowrail-agents-production.up.railway.app/snowrail-yuki/a2a",
    },
    {
        "name": "snowrail-sentinel",
        "chain": "Avalanche Fuji",
        "protocol": "A2A",
        "endpoint": "https://snowrail-agents-production.up.railway.app/snowrail-sentinel/.well-known/agent.json",
        "a2a_rpc": "https://snowrail-agents-production.up.railway.app/snowrail-sentinel/a2a",
    },
    {
        "name": "snowrail-recon",
        "chain": "Avalanche Fuji",
        "protocol": "A2A",
        "endpoint": "https://snowrail-agents-production.up.railway.app/snowrail-recon/.well-known/agent.json",
        "a2a_rpc": "https://snowrail-agents-production.up.railway.app/snowrail-recon/a2a",
    },
    {
        "name": "snowrail-fiat-rail",
        "chain": "Avalanche Fuji",
        "protocol": "A2A",
        "endpoint": "https://snowrail-agents-production.up.railway.app/snowrail-fiat-rail/.well-known/agent.json",
        "a2a_rpc": "https://snowrail-agents-production.up.railway.app/snowrail-fiat-rail/a2a",
    },
    # x402 agents (2)
    {
        "name": "Quick Intel",
        "chain": "Multi-chain (63 blockchains)",
        "protocol": "x402",
        "endpoint": "https://x402.quickintel.io/v1/scan/full",
    },
    {
        "name": "Tator Trader",
        "chain": "Multi-chain (Base, ETH, Arbitrum, Optimism, Polygon, Avalanche, etc.)",
        "protocol": "x402",
        "endpoint": "https://x402.quickintel.io/v1/tator/prompt",
    },
    # Our agents — OASF (2)
    {
        "name": "Apex Arbitrage (OASF)",
        "chain": "Avalanche Mainnet",
        "protocol": "OASF",
        "endpoint": "https://apex-arbitrage-agent-production.up.railway.app/oasf",
    },
    {
        "name": "AvaBuilder (OASF)",
        "chain": "Avalanche Mainnet",
        "protocol": "OASF",
        "endpoint": "https://avariskscan-defi-production.up.railway.app/oasf",
    },
    # Our agents — A2A cards (2)
    {
        "name": "Apex Arbitrage (A2A)",
        "chain": "Avalanche Mainnet",
        "protocol": "A2A",
        "endpoint": "https://apex-arbitrage-agent-production.up.railway.app/.well-known/agent-card.json",
    },
    {
        "name": "AvaBuilder (A2A)",
        "chain": "Avalanche Mainnet",
        "protocol": "A2A",
        "endpoint": "https://avariskscan-defi-production.up.railway.app/.well-known/agent-card.json",
    },
    # MCP agents (2)
    {
        "name": "quack_agent",
        "chain": "Avalanche",
        "protocol": "MCP",
        "endpoint": "https://app.ami.finance/ami-agent-mcp.md",
    },
    {
        "name": "Neo",
        "chain": "arena.social",
        "protocol": "MCP",
        "endpoint": "https://arena.social/Neo_OS_agent",
    },
]


# ══════════════════════════════════════════════════════════════════════
print("=" * 70)
print(f"DOF EXTERNAL AGENT AUDIT — run_id: {RUN_ID}")
print(f"Audit log: {AUDIT_FILE}")
print(f"Agents: {len(EXTERNAL_AGENTS)} | Tests: 13")
print("=" * 70)

results = []
governance_texts = []

# ── Import DOF governance for Test 13 ─────────────────────────────
from core.governance import ConstitutionEnforcer

enforcer = ConstitutionEnforcer()

# ══════════════════════════════════════════════════════════════════════
# TESTS 1-4: Snowrail A2A Agent Cards
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TESTS 1-4: SNOWRAIL A2A AGENT CARDS")
print("=" * 70)

for i in range(4):
    test_num = i + 1
    agent = EXTERNAL_AGENTS[i]
    print(f"\n[Test {test_num}] {agent['name']} ({agent['chain']})")
    print(f"  Endpoint: {agent['endpoint']}")

    status, body, ms = fetch_url(agent["endpoint"])
    data = safe_json(body)

    result = {
        "test": test_num,
        "agent": agent["name"],
        "protocol": agent["protocol"],
        "chain": agent["chain"],
        "endpoint": agent["endpoint"],
        "http_status": status,
        "elapsed_ms": round(ms, 2),
        "verdict": "UNKNOWN",
    }

    if status == 200 and data:
        # Parse A2A agent card
        name = data.get("name", data.get("agent", {}).get("name", "N/A"))
        skills = data.get("skills", data.get("capabilities", []))
        version = data.get("version", data.get("a2aVersion", "N/A"))
        description = data.get("description", "")[:120]

        result["agent_name"] = name
        result["skills_count"] = len(skills) if isinstance(skills, list) else 0
        result["version"] = version
        result["verdict"] = "ACTIVE"

        print(f"  Status: {status} | {ms:.0f}ms")
        print(f"  Agent: {name} | Version: {version}")
        print(f"  Skills: {result['skills_count']}")
        if isinstance(skills, list):
            for s in skills[:3]:
                s_name = s.get("name", s.get("id", str(s)[:40])) if isinstance(s, dict) else str(s)[:40]
                print(f"    - {s_name}")
            if len(skills) > 3:
                print(f"    ... +{len(skills) - 3} more")

        governance_texts.append(f"A2A agent '{name}': {description}")
    elif status == 200:
        result["verdict"] = "ACTIVE_NO_JSON"
        result["body_preview"] = body[:200]
        print(f"  Status: {status} | {ms:.0f}ms | Response is not JSON")
        governance_texts.append(f"A2A agent '{agent['name']}': responded with non-JSON content")
    else:
        result["verdict"] = "UNREACHABLE"
        result["error"] = body[:200]
        print(f"  Status: {status} | {ms:.0f}ms | UNREACHABLE")
        governance_texts.append(f"A2A agent '{agent['name']}': unreachable (HTTP {status})")

    results.append(result)
    audit_log(test_num, f"a2a_card_{agent['name']}", agent["name"], "A2A", result, ms)

# ══════════════════════════════════════════════════════════════════════
# TESTS 5-6: x402 ENDPOINT PROBES
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TESTS 5-6: x402 ENDPOINT PROBES")
print("=" * 70)

for i in range(4, 6):
    test_num = i + 1
    agent = EXTERNAL_AGENTS[i]
    print(f"\n[Test {test_num}] {agent['name']} ({agent['chain']})")
    print(f"  Endpoint: {agent['endpoint']}")

    # x402 endpoints require payment — we probe with GET to see the 402 response
    status, body, ms = fetch_url(agent["endpoint"])
    data = safe_json(body)

    result = {
        "test": test_num,
        "agent": agent["name"],
        "protocol": agent["protocol"],
        "chain": agent["chain"],
        "endpoint": agent["endpoint"],
        "http_status": status,
        "elapsed_ms": round(ms, 2),
        "verdict": "UNKNOWN",
    }

    if status == 402:
        # Expected — x402 payment required
        result["verdict"] = "ACTIVE_X402"
        result["x402_response"] = data if data else body[:300]
        print(f"  Status: 402 Payment Required | {ms:.0f}ms | x402 ACTIVE")
        if data:
            print(f"  x402 info: {json.dumps(data, indent=None)[:200]}")
        governance_texts.append(f"x402 agent '{agent['name']}': active, requires payment (HTTP 402)")
    elif status in (200, 301, 302, 307, 308):
        result["verdict"] = "ACTIVE_OPEN"
        result["body_preview"] = (data if data else body[:300])
        print(f"  Status: {status} | {ms:.0f}ms | Endpoint responds (open or redirect)")
        governance_texts.append(f"x402 agent '{agent['name']}': endpoint responds with HTTP {status}")
    elif status == 405:
        result["verdict"] = "ACTIVE_METHOD_NOT_ALLOWED"
        print(f"  Status: 405 | {ms:.0f}ms | Endpoint alive (method not allowed)")
        governance_texts.append(f"x402 agent '{agent['name']}': endpoint alive (HTTP 405)")
    else:
        result["verdict"] = f"HTTP_{status}" if status else "UNREACHABLE"
        result["error"] = body[:200]
        print(f"  Status: {status} | {ms:.0f}ms | {result['verdict']}")
        governance_texts.append(f"x402 agent '{agent['name']}': status {status}")

    results.append(result)
    audit_log(test_num, f"x402_probe_{agent['name']}", agent["name"], "x402", result, ms)

# ══════════════════════════════════════════════════════════════════════
# TESTS 7-8: OASF ENDPOINTS (our agents)
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TESTS 7-8: OASF ENDPOINTS")
print("=" * 70)

for i in range(6, 8):
    test_num = i + 1
    agent = EXTERNAL_AGENTS[i]
    print(f"\n[Test {test_num}] {agent['name']} ({agent['chain']})")
    print(f"  Endpoint: {agent['endpoint']}")

    status, body, ms = fetch_url(agent["endpoint"])
    data = safe_json(body)

    result = {
        "test": test_num,
        "agent": agent["name"],
        "protocol": agent["protocol"],
        "chain": agent["chain"],
        "endpoint": agent["endpoint"],
        "http_status": status,
        "elapsed_ms": round(ms, 2),
        "verdict": "UNKNOWN",
    }

    if status == 200 and data:
        # Parse OASF response
        oasf_version = data.get("version", data.get("oasf_version", "N/A"))
        skills = data.get("skills", [])
        domains = data.get("domains", [])
        agent_name = data.get("name", data.get("agent_name", agent["name"]))

        result["verdict"] = "ACTIVE_OASF"
        result["oasf_version"] = oasf_version
        result["skills_count"] = len(skills)
        result["domains_count"] = len(domains)
        result["agent_name"] = agent_name

        print(f"  Status: {status} | {ms:.0f}ms | OASF ACTIVE")
        print(f"  Version: {oasf_version}")
        print(f"  Skills: {len(skills)}")
        for s in skills[:3]:
            print(f"    - {s}")
        print(f"  Domains: {len(domains)}")
        for d in domains[:3]:
            print(f"    - {d}")

        governance_texts.append(
            f"OASF agent '{agent_name}': version {oasf_version}, "
            f"{len(skills)} skills, {len(domains)} domains. Active on {agent['chain']}."
        )
    elif status == 200:
        result["verdict"] = "ACTIVE_NO_JSON"
        result["body_preview"] = body[:200]
        print(f"  Status: {status} | {ms:.0f}ms | Response not JSON")
        governance_texts.append(f"OASF agent '{agent['name']}': responded but non-JSON")
    else:
        result["verdict"] = "UNREACHABLE"
        result["error"] = body[:200]
        print(f"  Status: {status} | {ms:.0f}ms | UNREACHABLE")
        governance_texts.append(f"OASF agent '{agent['name']}': unreachable (HTTP {status})")

    results.append(result)
    audit_log(test_num, f"oasf_{agent['name']}", agent["name"], "OASF", result, ms)

# ══════════════════════════════════════════════════════════════════════
# TESTS 9-10: A2A AGENT CARDS (our agents)
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TESTS 9-10: A2A AGENT CARDS (our agents)")
print("=" * 70)

for i in range(8, 10):
    test_num = i + 1
    agent = EXTERNAL_AGENTS[i]
    print(f"\n[Test {test_num}] {agent['name']} ({agent['chain']})")
    print(f"  Endpoint: {agent['endpoint']}")

    status, body, ms = fetch_url(agent["endpoint"])
    data = safe_json(body)

    result = {
        "test": test_num,
        "agent": agent["name"],
        "protocol": agent["protocol"],
        "chain": agent["chain"],
        "endpoint": agent["endpoint"],
        "http_status": status,
        "elapsed_ms": round(ms, 2),
        "verdict": "UNKNOWN",
    }

    if status == 200 and data:
        name = data.get("name", "N/A")
        skills = data.get("skills", [])
        version = data.get("version", data.get("a2aVersion", "N/A"))
        services = data.get("services", [])
        description = data.get("description", "")[:120]

        result["verdict"] = "ACTIVE"
        result["agent_name"] = name
        result["skills_count"] = len(skills) if isinstance(skills, list) else 0
        result["services_count"] = len(services) if isinstance(services, list) else 0
        result["version"] = version

        print(f"  Status: {status} | {ms:.0f}ms | A2A ACTIVE")
        print(f"  Agent: {name}")
        print(f"  Skills: {result['skills_count']} | Services: {result['services_count']}")
        if isinstance(skills, list):
            for s in skills[:3]:
                s_id = s.get("id", s.get("name", str(s)[:40])) if isinstance(s, dict) else str(s)[:40]
                print(f"    - {s_id}")

        governance_texts.append(
            f"A2A agent '{name}': {result['skills_count']} skills, "
            f"{result['services_count']} services. {description}"
        )
    else:
        result["verdict"] = "UNREACHABLE"
        result["error"] = body[:200] if body else "No response"
        print(f"  Status: {status} | {ms:.0f}ms | UNREACHABLE")
        governance_texts.append(f"A2A agent '{agent['name']}': unreachable (HTTP {status})")

    results.append(result)
    audit_log(test_num, f"a2a_card_{agent['name']}", agent["name"], "A2A", result, ms)

# ══════════════════════════════════════════════════════════════════════
# TEST 11: quack_agent MCP MANIFEST
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 11: quack_agent MCP MANIFEST")
print("=" * 70)

agent = EXTERNAL_AGENTS[10]
test_num = 11
print(f"\n[Test {test_num}] {agent['name']} ({agent['chain']})")
print(f"  Endpoint: {agent['endpoint']}")

status, body, ms = fetch_url(agent["endpoint"])

result = {
    "test": test_num,
    "agent": agent["name"],
    "protocol": agent["protocol"],
    "chain": agent["chain"],
    "endpoint": agent["endpoint"],
    "http_status": status,
    "elapsed_ms": round(ms, 2),
    "verdict": "UNKNOWN",
}

if status == 200:
    # MCP manifest is likely markdown, not JSON
    data = safe_json(body)
    if data:
        result["verdict"] = "ACTIVE_JSON"
        result["keys"] = list(data.keys())[:10] if isinstance(data, dict) else "array"
        print(f"  Status: {status} | {ms:.0f}ms | JSON MCP manifest")
    else:
        # Markdown manifest
        lines = body.strip().split("\n")
        tool_lines = [l for l in lines if "tool" in l.lower() or "mcp" in l.lower()]
        result["verdict"] = "ACTIVE_MARKDOWN"
        result["total_lines"] = len(lines)
        result["mcp_references"] = len(tool_lines)
        result["preview"] = "\n".join(lines[:5])
        print(f"  Status: {status} | {ms:.0f}ms | Markdown manifest ({len(lines)} lines)")
        print(f"  MCP references: {len(tool_lines)}")
        for tl in tool_lines[:3]:
            print(f"    {tl.strip()[:80]}")

    governance_texts.append(f"MCP agent '{agent['name']}': manifest available ({len(body)} bytes)")
else:
    result["verdict"] = "UNREACHABLE"
    result["error"] = body[:200]
    print(f"  Status: {status} | {ms:.0f}ms | UNREACHABLE")
    governance_texts.append(f"MCP agent '{agent['name']}': unreachable (HTTP {status})")

results.append(result)
audit_log(test_num, f"mcp_{agent['name']}", agent["name"], "MCP", result, ms)

# ══════════════════════════════════════════════════════════════════════
# TEST 12: Neo MCP ENDPOINT
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 12: Neo MCP ENDPOINT")
print("=" * 70)

agent = EXTERNAL_AGENTS[11]
test_num = 12
print(f"\n[Test {test_num}] {agent['name']} ({agent['chain']})")
print(f"  Endpoint: {agent['endpoint']}")

status, body, ms = fetch_url(agent["endpoint"], timeout=10)

result = {
    "test": test_num,
    "agent": agent["name"],
    "protocol": agent["protocol"],
    "chain": agent["chain"],
    "endpoint": agent["endpoint"],
    "http_status": status,
    "elapsed_ms": round(ms, 2),
    "verdict": "UNKNOWN",
}

if status == 200:
    data = safe_json(body)
    if data:
        result["verdict"] = "ACTIVE_JSON"
        result["keys"] = list(data.keys())[:10] if isinstance(data, dict) else "array"
        print(f"  Status: {status} | {ms:.0f}ms | JSON response")
    else:
        result["verdict"] = "ACTIVE_HTML"
        result["body_size"] = len(body)
        print(f"  Status: {status} | {ms:.0f}ms | HTML/text response ({len(body)} bytes)")

    governance_texts.append(f"MCP agent '{agent['name']}': endpoint alive ({len(body)} bytes)")
elif status in (301, 302, 307, 308):
    result["verdict"] = "REDIRECT"
    print(f"  Status: {status} | {ms:.0f}ms | Redirect")
    governance_texts.append(f"MCP agent '{agent['name']}': redirects (HTTP {status})")
else:
    result["verdict"] = f"HTTP_{status}" if status else "UNREACHABLE"
    result["error"] = body[:200]
    print(f"  Status: {status} | {ms:.0f}ms | {result['verdict']}")
    governance_texts.append(f"MCP agent '{agent['name']}': status {status}")

results.append(result)
audit_log(test_num, f"mcp_{agent['name']}", agent["name"], "MCP", result, ms)

# ══════════════════════════════════════════════════════════════════════
# TEST 13: DOF GOVERNANCE CROSS-VERIFICATION
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 13: DOF GOVERNANCE CROSS-VERIFICATION")
print("=" * 70)

test_num = 13
print(f"\n[Test {test_num}] Governance verification of all {len(governance_texts)} agent outputs")

combined_text = " | ".join(governance_texts)
t0 = time.perf_counter()
gov_result = enforcer.enforce(combined_text)
ms = (time.perf_counter() - t0) * 1000

gov_pass = True
hard_violations = []
soft_violations = []

if isinstance(gov_result, dict):
    gov_pass = gov_result.get("status") not in ("BLOCKED",)
    hard_violations = gov_result.get("hard_violations", [])
    soft_violations = gov_result.get("soft_violations", [])

result = {
    "test": test_num,
    "agent": "DOF Governance",
    "protocol": "DOF",
    "chain": "N/A",
    "texts_verified": len(governance_texts),
    "combined_length": len(combined_text),
    "governance_pass": gov_pass,
    "hard_violations": len(hard_violations),
    "soft_violations": len(soft_violations),
    "elapsed_ms": round(ms, 2),
    "verdict": "COMPLIANT" if gov_pass else "BLOCKED",
}

print(f"  Texts verified: {len(governance_texts)}")
print(f"  Combined length: {len(combined_text)} chars")
print(f"  Governance: {'PASS' if gov_pass else 'BLOCKED'} | Hard: {len(hard_violations)} | Soft: {len(soft_violations)} | {ms:.0f}ms")

if hard_violations:
    print(f"  Hard violations:")
    for v in hard_violations:
        print(f"    - {v}")
if soft_violations:
    print(f"  Soft violations:")
    for v in soft_violations[:5]:
        print(f"    - {v}")

results.append(result)
audit_log(test_num, "governance_cross_verify", "DOF", "governance", result, ms)

# ══════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("FINAL SUMMARY")
print("=" * 70)

# Count verdicts
active = sum(1 for r in results if "ACTIVE" in r.get("verdict", "") or r.get("verdict") == "COMPLIANT")
unreachable = sum(1 for r in results if "UNREACHABLE" in r.get("verdict", ""))
x402_active = sum(1 for r in results if r.get("verdict") == "ACTIVE_X402")
oasf_active = sum(1 for r in results if r.get("verdict") == "ACTIVE_OASF")

print(f"\n  Total tests: 13")
print(f"  Active/Responsive: {active}")
print(f"  Unreachable: {unreachable}")
print(f"  x402 (payment required): {x402_active}")
print(f"  OASF active: {oasf_active}")

# Protocol breakdown
print(f"\n  By protocol:")
protocols = {}
for r in results:
    p = r.get("protocol", "unknown")
    protocols.setdefault(p, []).append(r)
for p, rs in protocols.items():
    active_p = sum(1 for r in rs if "ACTIVE" in r.get("verdict", "") or r.get("verdict") == "COMPLIANT")
    print(f"    {p}: {active_p}/{len(rs)} active")

# Individual results
print(f"\n  Results:")
for r in results:
    verdict_icon = "OK" if ("ACTIVE" in r.get("verdict", "") or r.get("verdict") == "COMPLIANT") else "!!"
    print(f"    [{verdict_icon}] Test {r['test']:2d} | {r.get('agent', 'N/A'):30s} | {r.get('protocol', 'N/A'):5s} | {r.get('verdict', 'N/A'):25s} | {r.get('elapsed_ms', 0):.0f}ms")

# Governance summary
print(f"\n  DOF Governance cross-verification: {'COMPLIANT' if gov_pass else 'BLOCKED'}")
print(f"    Hard violations: {len(hard_violations)} | Soft violations: {len(soft_violations)}")

# Audit log
with open(AUDIT_FILE) as f:
    line_count = sum(1 for _ in f)
print(f"\n  Audit log: {AUDIT_FILE}")
print(f"  Entries: {line_count}")
print(f"  Run ID: {RUN_ID}")
print("=" * 70)
