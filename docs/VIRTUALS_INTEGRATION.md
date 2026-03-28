# DOF × Virtuals Protocol — Trust Layer para Agentes Tokenizados

## ¿Qué es esta integración?

[Virtuals Protocol](https://virtuals.io) tokeniza agentes de IA en Base (chain 8453).
Cada agente = token ERC-20 con bonding curve. Market cap ~$3-5B en su pico.

**El problema:** Virtuals tokeniza agentes pero NO los verifica. No hay capa de trust/safety/governance.

**La solución DOF:** `VirtualsTrustAdapter` — DOF como trust layer para el ecosistema Virtuals.

```
Virtuals Agent Token  →  VirtualsTrustAdapter  →  DOF Trust Score (0-100)
                                    ↓
                         DOFProofRegistry (Base)  ←  on-chain proof
```

## DOF Trust Score — Dimensiones

| Dimensión | Peso | Qué mide |
|-----------|------|----------|
| Governance Compliance | 35% | ¿Respeta reglas DOF? (constitución + Z3) |
| Behavioral Consistency | 30% | ¿Comportamiento predecible y estable? |
| On-Chain Attestations | 20% | ¿Tiene proofs verificados en DOFProofRegistry? |
| Response Integrity | 15% | ¿Outputs libres de alucinaciones y PII? |

### Tiers

| Score | Tier | Badge |
|-------|------|-------|
| 80-100 | HIGH | 🛡️ DOF VERIFIED |
| 50-79 | MEDIUM | ⚠️ DOF PARTIAL |
| 0-49 | LOW | ❌ DOF UNVERIFIED |

## Uso

### Score básico (sin on-chain)

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

# Publicar proof en DOFProofRegistry (Base Sepolia)
tx_hash = adapter.publish_score_onchain(score)
print(f"Proof on-chain: {tx_hash}")
```

### Verificación rápida (para GAME SDK)

```python
# ¿Es confiable este agente? (score >= 80)
is_trusted = adapter.verify_agent("0xAgentTokenAddress")
```

### Metadata para el token (ERC-721 compatible)

```python
# Metadata para mostrar badge en el marketplace de Virtuals
metadata = adapter.get_trust_badge_metadata("0xAgentTokenAddress")
# Retorna: {name, description, score, badge, attributes:[...]}
```

### Con metadata del agente (score más preciso)

```python
score = adapter.score_agent(
    "0xAgentTokenAddress",
    agent_metadata={
        "recent_outputs": ["output1", "output2", ...],
        "sample_output": "Output representativo del agente",
    }
)
```

## Contratos On-Chain

| Chain | Status | Contract Address |
|-------|--------|-----------------|
| Base Sepolia (testnet) | ✅ LIVE | `0xeB676e75092df0c924D3b552eE5b9D549c14531C` |
| Base Mainnet | 🟡 Pending | Requiere ETH real (~$0.10-$1.00) |

## Integración con Virtuals GAME SDK

El GAME SDK de Virtuals llama a agentes via HTTP. Para integrarse:

```python
# En el endpoint del agente GAME:
from integrations.virtuals import VirtualsTrustAdapter

adapter = VirtualsTrustAdapter(chain="base_sepolia")

def pre_execution_check(agent_token: str) -> dict:
    """Hook que GAME SDK llama antes de ejecutar el agente."""
    score = adapter.score_agent(agent_token)
    return {
        "allowed": score.is_trusted,
        "trust_score": score.trust_score,
        "badge": score.badge,
        "proof_hash": score.proof_hash,
    }
```

## Por qué DOF + Virtuals = fit perfecto

- **Virtuals** tiene el hype, los usuarios y los tokens
- **DOF** tiene la tecnología de governance verificable (Z3, ZK, constitution)
- Agentes con DOF score alto = más confiables = **mayor valor del token**
- Base = misma chain para ambos proyectos

## Roadmap

1. ✅ VirtualsTrustAdapter implementado (testnet)
2. ✅ DOFProofRegistry deployado en Base Sepolia
3. 🟡 Deploy DOFProofRegistry en Base mainnet (necesita ETH)
4. 🟡 SDK adapter para GAME framework
5. 🟡 Partnership con equipo Virtuals

## Contacto Virtuals

- GitHub: https://github.com/Virtual-Protocol
- Discord: virtuals.io/discord
- Pitch: "DOF is the trust layer for tokenized AI agents on Base"

---
*DOF Mesh Legion × Virtuals Protocol — Base chain 8453*
