# Conflux Global Hackfest 2026 — Official Demo Pitch
**Project:** DOF-MESH
**Track:** Best AI + Conflux / Best Developer Tool / Best USDT0 Integration
**Target Duration:** ~3 Minutes (Fast Paced)

---

## 🎬 Act 1: The Hook (0:00 - 0:30)

*(Start with screen recording of DOF-MESH architecture on dofmesh.com)*

**Speaker (You):** 
"Hello everyone, I’m Juan Carlos Quiceno from Cyber Paisa. Today I’m presenting **DOF-MESH** for the Conflux Global Hackfest 2026.

Right now, autonomous AI agents are executing billions of dollars in volume across DeFi, but there’s a massive problem: *We just have to trust them.* We trust that their prompts won't hallucinate. 

DOF-MESH changes this. We are the first framework that **mathematically proves** an AI agent behaved correctly *before* it signs a transaction, using Microsoft's Z3 Formal Verification. And we are doing it exclusively on Conflux."

## 🎬 Act 2: The Conflux MCP Synergy (0:30 - 1:30)

*(Switch to your IDE or Terminal showing the `dof_conflux_mcp.py` code)*

**Speaker:**
"For this hackathon, we built the **First Model Context Protocol (MCP) Server** optimized for Conflux eSpace. Any AI agent, like Claude or Cursor, can plug into this server.

Let’s look at a real DeFi problem: We want an agent to manage a treasury of **USDT0 on eSpace**. We don't want it to hallucinate and drain the wallet. 

So, I’ve built a specific tool in our MCP called `analyze_defi_compliance`. Before the agent can transfer any USDT0, the MCP mathematically bounds the request against systemic rules, and physically queries the Conflux eSpace Testnet via RPC to ensure the wallet has the reserves *deterministically*, with zero LLM guesswork."

## 🎬 Act 3: The Live Demo & Sponsorship (1:30 - 2:30)

*(Run the test script `test_defi_screenshot.py` in the terminal to show the Matrix-style output)*

**Speaker:**
"Let's see it in action. I request the Agent to transfer 250 USDT0. 

As you can see, the Agent hits our Conflux MCP Server. DOF-MESH runs the checking. Z3 validates the invariant theorems in 44 milliseconds. The MCP calls the Conflux testnet, checks the USDT0 Token ABI... and gives us a `DEFI_COMPLIANCE_STATUS: APPROVED_GASLESS`.

Notice the 'Gasless' part? This is where Conflux shines. Because the agent mathematically proved it behaved correctly, we instantly register its compliance on our `DOFProofRegistry` smart contract using **Conflux's native Gas Sponsorship**. The agent pays ZERO gas."

## 🎬 Act 4: The Closing (2:30 - 3:00)

*(Show the ConfluxScan block explorer with the verified Transactions)*

**Speaker:**
"Here is the proof permanently registered on ConfluxScan. 
A verifiable hash. A compliant agent. Zero gas fees for the AI execution.

DOF-MESH is a developer tool, a DeFi safeguard, and the missing infrastructure layer for AI on blockchain. 

Thank you to the Conflux team. The code is open source, and the future is deterministically autonomous."
