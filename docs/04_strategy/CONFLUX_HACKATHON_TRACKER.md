# Conflux Global Hackfest 2026 — Tracker DOF-MESH

> Documento de seguimiento interno. Actualizar después de cada sesión de trabajo.
> Deadline: **20 abr 2026 @ 11:59 PM ET**

---

## Identidad en el hackathon

| Campo | Valor |
|---|---|
| Evento | Conflux Global Hackfest 2026 |
| Portal | Discord oficial de Conflux |
| Prize pool | $10,000 USD total |
| Objetivos | Best AI+Conflux ($500) + Best Dev Tool ($500) + Main Award ($1,500) |
| Proyecto | DOF-MESH — Deterministic Governance Framework |
| Repo hackathon | `github.com/Cyberpaisa/deterministic-observability-framework` |
| Branch | `conflux-hackathon` (pendiente crear) |
| Workshop | 8 abr 2026 — Conflux Builder Toolkit en Discord |

---

## Wallets y contratos

### Wallet activa (Conflux Testnet)
| Campo | Valor |
|---|---|
| Dirección | `0xEAFdc9C3019fC80620f16c30313E3B663248A655` |
| Variable .env | `CONFLUX_PRIVATE_KEY` |
| Balance testnet | 1,098 CFX (verificado 06 abr 2026) |
| Explorer | https://evmtestnet.confluxscan.io/address/0xEAFdc9C3019fC80620f16c30313E3B663248A655 |

### DOFProofRegistry — Conflux eSpace Testnet
| Campo | Valor |
|---|---|
| Contrato | `0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83` |
| Chain ID | 71 |
| Red | Conflux eSpace Testnet |
| RPC | https://evmtestnet.confluxrpc.com |
| Explorer contrato | https://evmtestnet.confluxscan.io/address/0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83 |
| Proofs registradas al 06 abr | 36+ |
| Tipo | `testnet` (mainnet pendiente) |

---

## Transacciones on-chain (historial)

| Fecha | TX Hash | Tipo | Explorer |
|---|---|---|---|
| 06 abr 2026 | `bf98ea58265dcd8433f594376d0d679fde65d93ae8cc18d841627308bebf740c` | Attestation DOF-1687 hackathon demo | https://evmtestnet.confluxscan.io/tx/bf98ea58265dcd8433f594376d0d679fde65d93ae8cc18d841627308bebf740c |
| 06 abr 2026 | `77d4ddea0043bf6df5a916cd7040886e0a97480ab12465e5842ce7c2f26b4b10` | Attestation prueba directa | https://evmtestnet.confluxscan.io/tx/77d4ddea0043bf6df5a916cd7040886e0a97480ab12465e5842ce7c2f26b4b10 |

---

## Lo que se construyó (sesión 06 abr 2026)

### Archivos creados / modificados

| Archivo | Descripción |
|---|---|
| `core/adapters/conflux_gateway.py` | Fix web3 v7 middleware import + dry_run mode con MagicMock |
| `scripts/conflux_demo.py` | Demo ciclo completo — 6 pasos, auto-load .env, TX real en Conflux |
| `tests/test_conflux_gateway.py` | 5 tests — import, dry_run, sponsor address, registry address, RPCs |
| `tests/test_conflux_integration.py` | 4 tests — adapter load, contract address, publish dry_run, full cycle |
| `docs/04_strategy/CONFLUX_README.md` | README para jueces del hackathon |

### Commits
```
95d1ac5 fix(conflux-demo): auto-load .env + CONFLUX_PRIVATE_KEY → DOF_PRIVATE_KEY fallback
193818b feat(conflux): governance cycle completo + tests + demo para Global Hackfest 2026
```

---

## Demo script — cómo correrlo

```bash
cd ~/equipo-de-agentes

# Modo real (TX on-chain) — carga CONFLUX_PRIVATE_KEY del .env automáticamente
python3 scripts/conflux_demo.py

# Modo dry-run (sin wallet, sin TX)
python3 scripts/conflux_demo.py --dry-run

# Tests (9/9 OK)
python3 -m unittest tests.test_conflux_gateway tests.test_conflux_integration -v
```

### Output esperado del demo (real):
```
Constitution:     ✅ PASSED (score=1.0000)
Z3 Verification:  ✅ 4/4 PROVEN (~44ms)
TRACER Score:     ✅ 0.504/1.0
Proof Hash:       0x...
Attestation:      CONFIRMED
TX Hash:          bf98ea58...
Verificar en:     https://evmtestnet.confluxscan.io/tx/...
```

---

## Arquitectura Conflux en DOF

```
DOFChainAdapter.from_chain_name("conflux_testnet")
        ↓
    chains_config.json
        ↓
    RPC: https://evmtestnet.confluxrpc.com (chain 71)
    Contract: 0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83
        ↓
    publish_attestation(proof_hash, agent_id=1687, metadata)
        ↓
    DOFProofRegistry.sol → ProofRecord on-chain
        ↓
    ConfluxScan explorer
```

**Gas Sponsorship** (ventaja nativa de Conflux):
- `SponsorWhitelistControl` en `0x0888000000000000000000000000000000000001`
- Implementado en `ConfluxGateway.get_sponsor_contract()`
- Permite que agentes registren proofs sin tener CFX

---

## Métricas para la submission

Actualizar antes de enviar:

| Métrica | Valor | Cómo verificar |
|---|---|---|
| Ciclos autónomos | 238+ | `logs/daemon/cycles.jsonl` |
| Z3 theorems PROVEN | 4/4 | `python3 -m dof verify-states` |
| Proofs en Conflux testnet | 38+ (después de sesión) | ConfluxScan |
| Proofs en todas las chains | 80+ | 8 chains activas |
| Tests pasando | 4,308 | `python3 -m unittest discover -s tests` |
| Zero LLM en governance | ✅ | Determinístico: regex + Z3 + AST |
| Balance CFX testnet | 1,098 CFX | ConfluxScan wallet |

---

## Checklist de submission

### Técnico
- [x] Contrato DOFProofRegistry live en Conflux Testnet (chain 71)
- [x] ConfluxGateway funcional (`core/adapters/conflux_gateway.py`)
- [x] Demo script corre TX real (`scripts/conflux_demo.py`)
- [x] 9/9 tests pasando (gateway + integration)
- [x] TX real confirmada en ConfluxScan
- [ ] Branch `conflux-hackathon` creado en repo del hackathon
- [ ] `CONFLUX_README.md` como root README del branch
- [ ] Video demo 90s grabado

### Video demo — estructura sugerida
```
0:00-0:15  Problema: ¿cómo saber que un agente IA actuó correctamente?
0:15-0:40  DOF-MESH: Constitution → Z3 → TRACER → Proof Hash
0:40-1:05  python3 scripts/conflux_demo.py corriendo en vivo
1:05-1:20  TX en ConfluxScan — proof hash on-chain verificable
1:20-1:30  Tagline: "Agent acted autonomously. Math proved it. Blockchain recorded it. On Conflux."
```

### Submission
- [ ] Enviar antes del 20 abr 2026 @ 11:59 PM ET
- [ ] Incluir TX hash de la attestation demo en la descripción
- [ ] Mencionar Gas Sponsorship como diferenciador Conflux
- [ ] Asistir al workshop 8 abr (Discord) — preguntar sobre criterios de evaluación

---

## Diferenciadores frente a otros proyectos

1. **Zero LLM en governance** — decisiones 100% determinísticas (regex, AST, Z3)
2. **Z3 formal proofs** — 4 teoremas matemáticamente PROVEN, no "pretty good"
3. **Gas Sponsorship nativo** — agentes registran proofs sin tener CFX propio
4. **238+ ciclos autónomos documentados** — evidencia real, no un demo fabricado
5. **Mismo contrato en 8 chains** — DOFProofRegistry portable, Conflux es una más del ecosistema

---

## Lecciones aplicadas de Synthesis 2026

- No inscribirse en tracks sin integración nativa → Conflux no tiene tracks fijos ✅
- Jueces quieren: repo + docs + demo funcional → los tres listos ✅
- Video en <3 min con tx real visible → pendiente grabar
- Problema claro en 2 oraciones → "¿Cómo saber que un agente actuó correctamente? DOF-MESH lo prueba matemáticamente y lo registra en Conflux."

---

## Próximas sesiones

### Sesión 7 (pendiente)
- Grabar video demo
- Crear branch `conflux-hackathon` con README limpio
- Submission en portal

### Sesión 8 (pendiente — de CLAUDE.md)
- `scripts/release.sh` — crear desde cero
- DOF Leaderboard — diseño e implementación
- Voice test
- markitdown sync ESTADO_ACTUAL.md
