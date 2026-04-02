# DOF-MESH × SKALE — Integración Completa

**Fecha:** 2 abril 2026 | **Versión:** 0.5.0

---

## Chains SKALE Activas en DOF-MESH

| Chain | Chain ID | RPC | Gas | DOFProofRegistry | Estado |
|-------|----------|-----|-----|-----------------|--------|
| SKALE Europa | 2046399126 | `.../elated-tan-skat` | sFUEL gratis | `0x993399D9...9A1d` | ✅ deploy + attest |
| SKALE Calypso | 1564830818 | `.../honorable-steel-rasalhague` | sFUEL gratis | `0x4e54634d...881D` | ✅ deploy + attest |
| SKALE Nebula | 1482601649 | `.../green-giddy-denebola` | sFUEL gratis | `0x4e54634d...881D` | ✅ deploy + attest |
| SKALE Base Sepolia | 324705682 | `.../jubilant-horrible-ancha` | CREDIT faucet | `0x4e54634d...881D` | ✅ deploy + attest |
| SKALE Base Mainnet | 1187947933 | `skale-base.skalenodes.com/v1/base` | CREDIT pago | pendiente | ⏳ requiere CREDIT |

---

## Skills SKALE Instaladas

```
~/equipo-de-agentes/.agents/skills/
  ├── about-skale          — arquitectura, chain types, gas models
  ├── build-with-bite      — transacciones encriptadas (MEV-resistant)
  ├── deploy-to-skale      — deploy en todas las chains SKALE
  ├── ima-bridging-on-skale — mensajería cross-chain SKALE↔Ethereum
  ├── skale-cli            — comandos CLI operacionales
  └── x402-on-skale        — pagos x402 en SKALE ← SINERGIA CON ULTRAVIOLETA
```

Instaladas con: `npx skills add skalenetwork/skills --yes`

---

## Sinergias Estratégicas

### 1. x402 + Ultravioleta DAO + SKALE
SKALE tiene zero-gas (sFUEL) — ideal para micropagos x402 entre agentes.
Ultravioleta DAO ya es facilitador x402. DOF-MESH puede monetizar sus
endpoints de governance como APIs paywalled x402 sobre SKALE:

```
Agente externo → solicita governance check
   → DOF API (paywalled x402, SKALE Europa)
   → paga USDC/ETHC via Ultravioleta facilitador
   → recibe: GovernanceResult + attestation hash
```

Token x402 en SKALE Europa:
- Bridged USDC: `0x2e08028E3C4c2356572E096d8EF835cD5C6030bD`

### 2. BITE Protocol — Governance Confidencial
BITE encripta `to` + `calldata` en el mempool. DOF-MESH puede ofrecer:
- Governance checks confidenciales (nadie ve qué agente pide qué validación)
- Attestations privadas — proof hash on-chain sin exponer el contenido
- MEV-resistant: nadie puede frontrunner una governance decision

Disponible en SKALE Base y SKALE Base Sepolia.

### 3. IMA Bridge — Governance Cross-Chain
IMA (Inter-chain Messaging Agent) permite mensajes SKALE↔Ethereum.
DOF-MESH puede propagar governance decisions entre chains:
- Proof generado en SKALE Europa (zero-gas)
- Propagado via IMA a Ethereum mainnet para registrar en DOFProofRegistry
- MessageProxy en todas las chains: `0xd2AAa00100000000000000000000000000000000`

### 4. Stormrae AI — Oportunidad de Integración
Stormrae (190k usuarios, red-teaming de IA) necesita verificación de resultados.
DOF-MESH puede ser su capa de governance verificable:
- Cada sesión de red-team → proof hash on-chain (SKALE = zero gas)
- Resultados verificables públicamente
- Integración: DOF SDK → attestation SKALE → Stormrae dashboard

---

## Arquitectura Target DOF × SKALE

```
                    DOF-MESH Governance (determinístico)
                              |
                    [x402 paywall — SKALE Europa]
                              |
                   Ultravioleta DAO Facilitador
                              |
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        SKALE Europa     SKALE Base      Ethereum/Base
        (zero-gas)       (CREDIT)       (mainnet proof)
        DOFProofReg      BITE encrypt    DOFProofReg
              |               |               |
              └───────────────┴───────────────┘
                     IMA cross-chain messaging
```

---

## Pendientes SKALE

1. **SKALE Base Sepolia deploy:** obtener CREDITs en https://base-sepolia-faucet.skale.space
2. **x402 endpoint:** implementar `paymentMiddleware` en `api/server.py` sobre SKALE
3. **BITE integration:** explorar governance checks encriptados
4. **Stormrae outreach:** proponer DOF como capa de verificación

---

## Referencias
- Docs: https://docs.skale.space/get-started/quick-start/skale-on-base
- Go Live: https://docs.skale.space/get-started/quick-start/go-live
- MCP: https://docs.skale.space/mcp
- Faucet Sepolia: https://base-sepolia-faucet.skale.space
- Explorer Europa: https://elated-tan-skat.explorer.mainnet.skalenodes.com/
- Explorer SKALE Base: https://skale-base-explorer.skalenodes.com/
