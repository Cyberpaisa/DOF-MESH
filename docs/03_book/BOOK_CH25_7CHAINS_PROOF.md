# Capítulo 25: La Prueba de las 7 Cadenas

**Fecha:** 2 de abril de 2026
**Versión DOF-MESH:** 0.5.0
**Autor:** Cyber Paisa — Enigma Group, Medellín

---

## El Reto

Después de semanas construyendo el framework, llegó el momento de la verdad: demostrar que DOF-MESH no solo pasa tests en un servidor de CI, sino que sus pruebas de governance son verificables por cualquier persona, en cualquier momento, en múltiples blockchains públicas simultáneamente.

La pregunta era simple: ¿funciona en el mundo real?

---

## La Validación

Comenzamos desde adentro hacia afuera.

**Primero: los tests locales.** 4,157 pruebas unitarias. Governance, Z3, AST Verifier, memory, adversarial, regression tracking, full pipeline. Todo verde. Los 4 teoremas Z3 formalmente verificados en menos de 4ms cada uno.

**Segundo: el sistema completo.** Demo end-to-end de 7 pasos sin un solo LLM involucrado. Pipeline determinístico: nodos → constitución → Z3 gate → circuit breaker → Merkle attestation → ZK proof → supervisor. Score: 6.15/10 aceptado.

**Tercero: las chains.** Aquí empezó lo interesante.

---

## 7 Chains, 7 Attestations

Cada attestation es un `registerProof` real en un contrato DOFProofRegistry deployado on-chain. Parámetros fijos: Agent #1687, Trust Score 9821 (98.21%), 4 invariants Z3, proof hash SHA-256.

| Chain | Contrato | Bloque | TX |
|-------|----------|--------|----|
| Avalanche Fuji | `0x4e54634d...` | 53,553,908 | `0x5d25d7...` |
| Avalanche C-Chain | `0x0b65d10F...` | 81,945,671 | `0xf7c6da...` |
| Base Mainnet | `0x993399D9...` | 44,186,111 | `0x5422ee...` |
| Conflux eSpace | `0x4e54634d...` | 248,014,025 | `0x7b27ea...` |
| Polygon Mainnet | `0x1b65658A...` | 85,020,959 | `0xa2ce0e...` |
| SKALE Europa | `0x993399D9...` | 24,839,948 | `0x929f4e...` |
| Celo Mainnet | `0x35B320A0...` | 63,262,268 | `0xa0486d...` |

Cinco mainnets, dos testnets. Gas total gastado: menos de $0.50 USD equivalente entre todas las chains.

---

## Lo que se Descubrió

**El contrato viejo de Avalanche Mainnet** (`0x88f6043B...`, deployado por la wallet comprometida `0xB529`) tenía un ABI incompatible con la versión actual. No era un bug de DOF — era un artifact de la época pre-Glassworm cuando esa wallet aún era operativa. Solución: deploy limpio con `0x43a9`.

**Polygon Amoy** aparecía con 10.5 MATIC pero el RPC en `.env` apuntaba a Polygon Mainnet (chain 137). El balance era real — estaba en mainnet, no en testnet. Mejor así.

**SKALE** es zero-gas. Con 0.0002 sFUEL alcanzó para deploy + attestation. Sin costo real.

**Celo** requirió encontrar la key correcta (`DOF_DEPLOY_KEY`) porque `TEMPO_PRIVATE_KEY` correspondía a la wallet vacía `0xb481`, no a la que tenía 2.66 CELO (`0xbD9b`). Un caso donde el nombre de la variable en `.env` no reflejaba su uso real.

**Tempo** (chain 4217): RPC caído. La red puede estar en mantenimiento o el endpoint cambió. Pendiente cuando vuelva.

---

## Lo que Quedó Limpio

La wallet comprometida `0xB529f4f99ab244cfa7a48596Bf165CAc5B317929` fue eliminada del sistema de memoria activa. Ya no aparece en ningún registro operativo. Solo queda como referencia histórica en documentos de arquitectura — un recordatorio del incidente Glassworm que costó aprender a operar con seguridad.

Los 0.2002 USDC residuales en esa address quedan abandonados. No vale la pena interactuar con una wallet comprometida por tan poco.

---

## El Mapa de Wallets Correcto

Después de esta sesión el mapa quedó así:

- `0x2e26` — MultiToken: 2.83 AVAX + 10.34 MATIC + 6 USDC. La más rica.
- `0x43a9` — DOF Principal: deployer principal, 0.02 AVAX + 0.001 ETH.
- `0xbD9b` — Celo: 2.63 CELO post-deploy.
- `0xEAFd` — Conflux/Apex: 1098 CFX operacionales.
- `0xb481` — Tempo: vacía, esperando RPC.

---

## La Lección

La prueba punta a punta no es solo correr `python -m unittest`. Es el ciclo completo:

1. Tests locales determinísticos
2. Z3 formal verification
3. Demo end-to-end sin LLMs
4. Attestation on-chain verificable

Cuando los 4 pasos pasan, el sistema es soberano. No dependes de que ninguna empresa te diga que tu agente funcionó bien. Lo puedes verificar tú mismo, o cualquier auditor, en la blockchain.

Eso es DOF-MESH.

---

*Próximo capítulo: Tempo Network — cuando el RPC vuelva.*
