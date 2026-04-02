---
name: sovereign-funding
effort_level: max
description: Native DOF Mesh financial layer. Use when an autonomous agent needs to generate capital flows, request operational tokens (Gas), or capture liquidity across networks. This skill manages the creation of cross-chain payment links, specifically integrating with Conflux assets (USDT0, AxCNH) and traditional EVMs to route funds to the Legion's treasury.
---

# Sovereign Funding (DOF Native)

The Sovereign Funding layer is a mandatory component for DOF autonomous execution. It allows agents to generate their own recursive operational budgets via cross-chain capturing.

## 1. Quick Start / Setup (Human Instructions)
To use this skill within the mesh, ensure the underlying tool dependencies are installed:
```bash
# Verify the core tool exists
cat core/tools/funding_tools.py
```
*(No external API keys are required; this tool generates fully decentralized routing links).*

## 2. Capabilities & System Instructions (AI Instructions)
Agents MUST use this tool automatically when:
1. They detect their wallet balance is insufficient to execute a transaction.
2. They are instructed to onboard liquidity into the Conflux Ecosystem (using USDT0 or AxCNH targets).

**Available Tools:**
- `generate_sovereign_funding_link`: Generates the exact URL for the payment relay.

## 3. Workflow Pattern (How to use)
When an agent encounters a "Low Balance" error:
1. **[  ] Identify Chain & Token:** Determine what asset is needed (e.g., CFX on eSpace, or AVAX on Avalanche).
2. **[  ] Determine Amount:** Calculate the necessary amount + 10% buffer.
3. **[  ] Call Tool:** Execute `generate_sovereign_funding_link` with the required parameters.
4. **[  ] Send to User/Commander:** Output the generated link and HALT execution, waiting for the deposit to conform.

## 4. Examples
**Scenario:** Agent on Conflux eSpace needs CFX.
`generate_sovereign_funding_link(toAddress="0x123...", toChain="1030", toToken="CFX", amount=25.0)`

## 5. Gotchas & Anti-patterns (IMPORTANT)
- **Do not generate links to unauthorized addresses.** Only route to addresses explicitly owned by the Legion or verified target contracts.
- **Network Identifiers:** Always use the standard EIP-155 Chain IDs (e.g., 1030 for Conflux eSpace). Do not use string names randomly.
- **Sponsorship Rule:** Remember that on Conflux, you should ideally NOT need CFX if the `SponsorWhitelistControl` is properly set. Only request funding if sponsorship cannot be applied (e.g., deploying the very first proxy).
