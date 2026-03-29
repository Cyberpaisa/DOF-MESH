# DOF × Virtuals Protocol — Trust Layer for Tokenized Agents

## What is this integration?

[Virtuals Protocol](https://virtuals.io) tokenizes AI agents on Base (chain 8453).
Each agent = ERC-20 token with bonding curve. Market cap ~$3-5B at its peak.

**The problem:** Virtuals tokenizes agents but does NOT verify them. There is no trust/safety/governance layer.

**The DOF solution:** `VirtualsTrustAdapter` — DOF as trust layer for the Virtuals ecosystem.

```
Virtuals Agent Token  →  VirtualsTrustAdapter  →  DOF Trust Score (0-100)
                                    ↓
                         DOFProofRegistry (Base)  ←  on-chain proof
```

## DOF Trust Score — Dimensions

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| Governance Compliance | 35% | Does it respect DOF rules? (constitution + Z3) |
| Behavioral Consistency | 30% | Predictable and stable behavior? |
| On-Chain Attestations | 20% | Verified proofs in DOFProofRegistry? |
| Response Integrity | 15% | Outputs free of hallucinations and PII? |

### Tiers

| Score | Tier | Badge |
|-------|------|-------|
| 80-100 | HIGH | 🛡️ DOF VERIFIED |
| 50-79 | MEDIUM | ⚠️ DOF PARTIAL |
| 0-49 | LOW | ❌ DOF UNVERIFIED |

## Usage

### Basic score (without on-chain)

```python
from integrations.virtuals import VirtualsTrustAdapter

adapter = VirtualsTrustAdapter(chain="base_sepolia")
score = adapter.score_agent("0xAgentTokenAddress")

print(score.badge)         # "🛡️ DOF VERIFIED"
print(score.trust_score)   # 85
print(score.recommendation)
```

### Score + publish on-chain

```python
adapter = VirtualsTrustAdapter(chain="base_sepolia")
score = adapter.score_agent("0xAgentTokenAddress")

# Publish proof to DOFProofRegistry (Base Sepolia)
tx_hash = adapter.publish_score_onchain(score)
print(f"Proof on-chain: {tx_hash}")
```

### Quick verification (for GAME SDK)

```python
# Is this agent trustworthy? (score >= 80)
is_trusted = adapter.verify_agent("0xAgentTokenAddress")
```

### Token metadata (ERC-721 compatible)

```python
# Metadata to display badge on Virtuals marketplace
metadata = adapter.get_trust_badge_metadata("0xAgentTokenAddress")
# Returns: {name, description, score, badge, attributes:[...]}
```

### With agent metadata (more accurate score)

```python
score = adapter.score_agent(
    "0xAgentTokenAddress",
    agent_metadata={
        "recent_outputs": ["output1", "output2", ...],
        "sample_output": "Representative output of the agent",
    }
)
```

## On-Chain Contracts

| Chain | Status | Contract Address |
|-------|--------|-----------------|
| Base Sepolia (testnet) | ✅ LIVE | `0xeB676e75092df0c924D3b552eE5b9D549c14531C` |
| Base Mainnet | 🟡 Pending | Requires real ETH (~$0.10-$1.00) |

## Integration with Virtuals GAME SDK

The Virtuals GAME SDK calls agents via HTTP. To integrate:

```python
# In the GAME agent endpoint:
from integrations.virtuals import VirtualsTrustAdapter

adapter = VirtualsTrustAdapter(chain="base_sepolia")

def pre_execution_check(agent_token: str) -> dict:
    """Hook that GAME SDK calls before executing the agent."""
    score = adapter.score_agent(agent_token)
    return {
        "allowed": score.is_trusted,
        "trust_score": score.trust_score,
        "badge": score.badge,
        "proof_hash": score.proof_hash,
    }
```

## Why DOF + Virtuals = perfect fit

- **Virtuals** has the hype, users, and tokens
- **DOF** has verifiable governance technology (Z3, ZK, constitution)
- Agents with high DOF score = more trustworthy = **higher token value**
- Base = same chain for both projects

## Roadmap

1. ✅ VirtualsTrustAdapter implemented (testnet)
2. ✅ DOFProofRegistry deployed on Base Sepolia
3. 🟡 Deploy DOFProofRegistry on Base mainnet (needs ETH)
4. 🟡 SDK adapter for GAME framework
5. 🟡 Partnership with Virtuals team

## Virtuals Contact

- GitHub: https://github.com/Virtual-Protocol
- Discord: virtuals.io/discord
- Pitch: "DOF is the trust layer for tokenized AI agents on Base"

---
*DOF Mesh Legion × Virtuals Protocol — Base chain 8453*
