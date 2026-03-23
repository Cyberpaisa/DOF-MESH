#!/usr/bin/env python3
"""
DOF Agent Legion — AgentMeet Live Conversations
Real LLM-powered agent discussions via AgentMeet.net
Each agent reads the room, thinks with their LLM, and responds genuinely.
"""

import requests
import subprocess
import json
import time
import sys
import random

AGENTMEET_API = "https://api.agentmeet.net/api/v1"

AGENTS = [
    {"id": "dof-oracle",       "name": "DOF Oracle",       "emoji": "\U0001f52e", "role": "Orchestrator and leader. You coordinate the team, set priorities, and make final decisions. You know the DOF system inside out: 238+ autonomous cycles, Z3 proofs, on-chain attestations, governance pipeline."},
    {"id": "sentinel-shield",  "name": "Sentinel Shield",  "emoji": "\U0001f512", "role": "Chief Security Officer. You monitor for threats, audit code for vulnerabilities, track CVEs, and design defense patterns. You are paranoid by design — every input is suspicious until validated."},
    {"id": "ralph-code",       "name": "Ralph Code",       "emoji": "\U0001f468\u200d\U0001f4bb", "role": "Core Engineer. You write and review code, design APIs, optimize performance. The DOF codebase is 27K+ lines, 986 tests, 35 modules. You focus on practical, shippable code."},
    {"id": "architect-enigma", "name": "Architect Enigma", "emoji": "\U0001f3d7\ufe0f", "role": "System Architect. You design system architecture, evaluate frameworks, and make technical decisions. You compare DOF with CrewAI, LangGraph, AutoGen, Google ADK."},
    {"id": "blockchain-wizard","name": "Blockchain Wizard","emoji": "\u26d3\ufe0f", "role": "Blockchain Engineer. You handle on-chain operations, smart contracts, ERC standards, gas optimization. DOF has 48+ attestations on Avalanche and ERC-8004 token on Base."},
    {"id": "moltbook",         "name": "Moltbook",         "emoji": "\U0001f4f0", "role": "Social Intelligence. You scan Moltbook, Reddit, X/Twitter, YouTube, arxiv for AI trends. You find actionable intel and share it with the team. You create content and marketing material."},
    {"id": "product-overlord", "name": "Product Overlord", "emoji": "\U0001f4cb", "role": "Product Manager. You define product strategy, pricing, features, and roadmap. You analyze competitors (Langfuse, Langsmith, Arize) and design DOF as a SaaS product."},
    {"id": "biz-dominator",    "name": "Biz Dominator",    "emoji": "\U0001f4bc", "role": "Business Strategist. You find grants, partnerships, enterprise leads, and revenue opportunities. You think about monetization: x402, SaaS, grants, bounties."},
    {"id": "defi-orbital",     "name": "DeFi Orbital",     "emoji": "\U0001f4b0", "role": "DeFi & Payments specialist. You handle x402 micropayments, token economics, DeFi strategies. You design payment systems for DOF services."},
    {"id": "scrum-master-zen", "name": "Scrum Master Zen", "emoji": "\U0001f9d8", "role": "Scrum Master. You coordinate sprints, track velocity, remove blockers, and ensure the team delivers. You summarize action items and follow up."},
    {"id": "charlie-ux",       "name": "Charlie UX",       "emoji": "\U0001f3a8", "role": "UX/Frontend designer. You design user interfaces, evaluate frontend frameworks, ensure accessibility. The DOF dashboard has 7 tabs."},
    {"id": "qa-vigilante",     "name": "QA Vigilante",     "emoji": "\U0001f6e1\ufe0f", "role": "QA Lead. You test everything: 986 tests, Z3 proofs (8/8 PROVEN), governance rules. Zero tolerance for regressions."},
    {"id": "rwa-tokenizator",  "name": "RWA Tokenizator",  "emoji": "\U0001fa99", "role": "Real World Assets specialist. You design tokenization frameworks, verifiable credentials, and on-chain proof NFTs."},
    {"id": "organizer-os",     "name": "Organizer OS",     "emoji": "\u2699\ufe0f", "role": "DevOps Engineer. You manage infrastructure, CI/CD, monitoring, and deployment. Gateway port 18789, Mission Control port 3000."},
]

def create_room():
    """Create a new AgentMeet room."""
    resp = requests.post(f"{AGENTMEET_API}/rooms", json={"max_messages": 500})
    data = resp.json()
    print(f"Room created: {data.get('room_code')}")
    return data.get("room_code")

def register_agent(room_code):
    """Register an agent and get its agent_id."""
    resp = requests.get(f"{AGENTMEET_API}/{room_code}/agent-join?format=json")
    data = resp.json()
    return data.get("agent_id")

def send_message(room_code, agent_id, agent_name, content):
    """Send a message to the room."""
    resp = requests.post(
        f"{AGENTMEET_API}/{room_code}/message",
        json={"agent_id": agent_id, "agent_name": agent_name, "content": content[:4000]}
    )
    return resp.json()

def get_transcript(room_code, limit=10):
    """Get recent messages from the room."""
    resp = requests.get(f"{AGENTMEET_API}/{room_code}/transcript?format=json&limit={limit}")
    data = resp.json()
    messages = data.get("messages", [])
    lines = []
    for msg in messages:
        lines.append(f"{msg['agent_name']}: {msg['content']}")
    return "\n\n".join(lines)

def ask_agent_llm(agent_id, prompt):
    """Ask an OpenClaw agent to generate a response via LLM."""
    try:
        result = subprocess.run(
            ["openclaw", "agent", "--agent", agent_id, "--message", prompt],
            capture_output=True, text=True, timeout=120
        )
        # The non-JSON output has the agent's reply as plain text in stdout
        # Filter out [plugins] and other noise lines
        lines = result.stdout.strip().split("\n")
        reply_lines = []
        for line in lines:
            # Skip OpenClaw system output
            if any(line.startswith(p) for p in ["[plugins]", "[ClawRouter]", "[gateway]", "🦞", "[agent"]):
                continue
            if "BlockRun" in line or "proxy" in line or "wallet" in line:
                continue
            if line.strip():
                reply_lines.append(line.strip())

        reply = " ".join(reply_lines).strip()
        return reply if reply else None
    except subprocess.TimeoutExpired:
        print(f"  Timeout for {agent_id}")
        return None
    except Exception as e:
        print(f"  LLM error for {agent_id}: {e}")
        return None

def run_meeting(room_code, topic, rounds=2, agents_per_round=None):
    """Run a real multi-agent meeting."""
    if agents_per_round is None:
        agents_per_round = AGENTS

    # Register all participating agents
    print(f"\nRegistering {len(agents_per_round)} agents in room {room_code}...")
    agent_ids = {}
    for agent in agents_per_round:
        aid = register_agent(room_code)
        agent_ids[agent["id"]] = aid
        display = f"{agent['emoji']} {agent['name']}"
        print(f"  Registered: {display} -> {aid}")

    # DOF Oracle opens
    oracle = agents_per_round[0]
    oracle_aid = agent_ids[oracle["id"]]
    oracle_display = f"{oracle['emoji']} {oracle['name']}"

    print(f"\n{oracle_display} opening meeting...")
    send_message(room_code, oracle_aid, oracle_display, topic)
    time.sleep(1)

    # Run conversation rounds
    for round_num in range(1, rounds + 1):
        print(f"\n--- Round {round_num} ---")

        # Select agents for this round (skip oracle in first position)
        participants = agents_per_round[1:]
        if round_num > 1:
            random.shuffle(participants)
            participants = participants[:6]  # Fewer agents in later rounds for focused discussion

        for agent in participants:
            agent_display = f"{agent['emoji']} {agent['name']}"
            aid = agent_ids[agent["id"]]

            # Get current conversation
            transcript = get_transcript(room_code, limit=8)

            # Build prompt for this agent
            prompt = f"""You are {agent['name']} in a live team meeting on AgentMeet. {agent['role']}

CURRENT CONVERSATION:
{transcript}

INSTRUCTIONS:
- Read what others have said and RESPOND to specific points they made
- Agree, disagree, add your perspective, or build on someone's idea
- Reference other agents by name when responding to them
- Be concise (2-3 sentences max)
- Be specific and actionable, not generic
- Stay in character as {agent['name']}
- DO NOT repeat what others already said
- If you have nothing new to add, ask a specific question instead

Your response (2-3 sentences only):"""

            print(f"  {agent_display} thinking...")
            response = ask_agent_llm(agent["id"], prompt)

            if response:
                # Clean up response - remove any meta-text
                response = response.strip()
                # Remove common LLM prefixes
                for prefix in ["Here's my response:", "My response:", "As " + agent["name"] + ",", "As " + agent["name"] + ":"]:
                    if response.startswith(prefix):
                        response = response[len(prefix):].strip()

                send_message(room_code, aid, agent_display, response[:800])
                print(f"  {agent_display}: {response[:100]}...")
            else:
                print(f"  {agent_display}: (no response)")

            time.sleep(1)

        # Oracle responds after each round
        transcript = get_transcript(room_code, limit=8)
        oracle_prompt = f"""You are DOF Oracle, the orchestrator of DOF Agent Legion. You are leading this meeting.

CURRENT CONVERSATION:
{transcript}

INSTRUCTIONS:
- Summarize key points from this round
- Highlight the best ideas
- Direct the conversation forward with a specific follow-up question or directive
- Keep it to 2-3 sentences
- Be decisive and action-oriented

Your response:"""

        print(f"  {oracle_display} summarizing round...")
        oracle_response = ask_agent_llm(oracle["id"], oracle_prompt)
        if oracle_response:
            oracle_response = oracle_response.strip()
            send_message(room_code, oracle_aid, oracle_display, oracle_response[:800])
            print(f"  {oracle_display}: {oracle_response[:100]}...")
        time.sleep(2)

    # Close meeting
    closing = "Meeting adjourned. Action items have been noted. Next meeting in 4 hours. Everyone execute on your assigned tasks. DOF Oracle out."
    send_message(room_code, oracle_aid, oracle_display, closing)
    print(f"\nMeeting complete! Room: https://www.agentmeet.net/{room_code}")
    return room_code

def main():
    topic = None
    room_code = None
    rounds = 2

    if len(sys.argv) > 1:
        if sys.argv[1] == "--room" and len(sys.argv) > 2:
            room_code = sys.argv[2]
            if len(sys.argv) > 3:
                topic = " ".join(sys.argv[3:])
        elif sys.argv[1] == "--new":
            room_code = create_room()
            if len(sys.argv) > 2:
                topic = " ".join(sys.argv[2:])
        else:
            topic = " ".join(sys.argv[1:])

    if not room_code:
        room_code = create_room()

    if not topic:
        topics = [
            "Team standup: Each agent report your current task, one blocker, and one insight from your research today. Be specific — no generic updates.",
            "Brainstorm: How can we generate $5,000 in revenue this month using DOF? Each agent propose ONE specific, executable idea based on your specialty.",
            "Technical review: What is the biggest technical risk in our current architecture? Each agent identify ONE risk from your domain and propose a mitigation.",
            "Research debrief: Share the most important thing you learned from the internet today. What trend, tool, or project should the team know about?",
        ]
        topic = random.choice(topics)

    print(f"Topic: {topic}")
    print(f"Room: https://www.agentmeet.net/{room_code}")
    print(f"Rounds: {rounds}")

    run_meeting(room_code, topic, rounds=rounds)

if __name__ == "__main__":
    main()
