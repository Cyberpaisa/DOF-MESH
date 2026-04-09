# DOF-MESH x Conflux Global Hackfest 2026 — Demo Strategy

> Documento creado: 6 abr 2026  
> Estado: **LISTO PARA GRABAR**

---

## Lo que diferencia Conflux de cualquier otra EVM

**SponsorWhitelistControl** — mecanismo nativo de Conflux que permite que un contrato patrocine
el gas de sus usuarios. Resultado: usuarios interactúan **sin pagar CFX**.
No existe en Ethereum, Conflux eSpace, Base ni ninguna otra EVM. Es exclusivo de Conflux.

---

## Estado Actual — Verificado 6 abr 2026

### Contrato DOFProofRegistry en Conflux Testnet
- **Dirección:** `0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83`
- **Chain ID:** 71 (eSpace Testnet)
- **Deployer:** `0x43a9Fd328909c659e60d9f8E589bE846c3c0E14e`

### Gasless Setup — ACTIVADO ✅

| Paso | TX Hash | Status |
|------|---------|--------|
| setSponsorForGas (10 CFX, upper 1M drip) | `014b6bed...a52d3b7` | ✅ OK |
| setSponsorForCollateral (10 CFX) | `d6199877...e621cc9f` | ✅ OK |
| addPrivilegeByAdmin (whitelist global `0x00...`) | `2e47f3fd...6862a3` | ✅ OK |

**Resultado:** Cualquier wallet puede registrar proofs en DOFProofRegistry sin pagar gas.

### TX de referencia para el demo
- **TX hackathon on-chain:** `0x6994475597c4052f33012458ed75fac6458b53a88f2fa991ff0e3943ab9b2343`
- **Payload grabado:** `dof-v0.6.0 conflux-hackathon z3=4/4 tracer=0.504`
- **Agent:** #1687
- **Explorer:** https://evmtestnet.confluxscan.io/tx/0x6994475597c4052f33012458ed75fac6458b53a88f2fa991ff0e3943ab9b2343

---

## Script del demo (3 pasos, ~45 segundos)

```bash
# PASO 1 — Governance completo + TX on-chain
cd ~/equipo-de-agentes
python3 scripts/conflux_demo.py

# PASO 2 — Verificar la TX en el explorador (abrir en browser)
open "https://evmtestnet.confluxscan.io/tx/0x6994475597c4052f33012458ed75fac6458b53a88f2fa991ff0e3943ab9b2343"

# PASO 3 — Mencionar verbalmente:
# "El contrato tiene gasless activo vía SponsorWhitelistControl —
#  cualquier agente puede registrar proofs sin pagar CFX.
#  Eso no existe en Ethereum ni en ninguna otra EVM."
```

---

## Narrative para el juez

> "La mayoría de frameworks verifica lo que pasó.  
> DOF verifica lo que está **a punto de pasar**.  
> En Conflux, además, es **completamente gasless** —  
> el contrato patrocina el gas de todos los agentes.  
> Math proved it. Blockchain recorded it. On Conflux."

---

## Por qué ganamos

| Criterio | Nosotros | Competencia típica |
|----------|----------|-------------------|
| TX real on-chain | ✅ `0x6994...` con metadata hackathon | Demo o dry-run |
| Z3 formal verification | ✅ 4/4 PROVEN en 34.8ms | Sin proofs matemáticos |
| Gasless nativo Conflux | ✅ SponsorWhitelistControl activo | Sin gasless |
| Frase memorable | ✅ grabada on-chain | No |
| Números concretos | ✅ 4,308 tests, Agent #1687, 34.8ms | Vagos |

---

## Checklist pre-grabación

- [x] Contrato deployado en Conflux Testnet (chain 71)
- [x] Gasless activado (3 TXs confirmadas)
- [x] TX hackathon on-chain con metadata
- [x] `python3 scripts/conflux_demo.py` funciona sin errores
- [ ] Terminal limpia antes de grabar
- [ ] Browser con ConfluxScan listo en segundo tab
