# Learnings — Hardening to On-Chain Readiness PR #43–#49

## 1. Resumen ejecutivo

Entre PR #43 y PR #49, DOF-MESH cerró la transición desde el hardening documental y criptográfico hacia una primera capa segura de preparación on-chain. El ciclo no ejecutó despliegues reales, no leyó secretos, no usó wallets y no firmó transacciones. Su valor fue ordenar la memoria dispersa, alinear el baseline público vivo y crear un primer dry-run offline para evaluar readiness sin tocar infraestructura sensible.

El estado técnico vivo al cierre del ciclo es:

- `4802 tests collected`
- `verify-states`: `8/8 PROVEN`
- `verify-hierarchy`: `62 patterns PROVEN`
- Hardhat scoped proof registry: `7 passing`
- hash-domain saneado
- métricas públicas alineadas
- auditorías históricas marcadas como superseded
- primera capa on-chain segura: `offline on-chain readiness dry-run`

## 2. Qué problema se resolvió

El problema principal era de memoria operacional fragmentada. El proyecto tenía evidencia correcta distribuida entre learnings, sesiones Obsidian, auditorías, documentos públicos, docs de CLI y scripts de readiness, pero no existía una narrativa única que conectara:

- el cierre hardening PR #1–#42;
- la corrección residual del wording hash-domain;
- el baseline vivo de tests y verificación formal;
- el estatus histórico/superseded de auditorías previas;
- el primer paso on-chain permitido sin secretos ni broadcast.

El ciclo PR #43–#49 resolvió esa desconexión sin ampliar superficie de riesgo.

## 3. Decisiones tomadas

- Separar baseline vivo de evidencia histórica.
- Mantener referencias históricas cuando ayudan a auditoría, pero marcarlas como históricas o superseded.
- No tratar wording criptográfico como detalle cosmético: un comentario incorrecto puede inducir operación incorrecta.
- Alinear documentación pública solo con métricas vigentes.
- Preservar el milestone histórico de `4,800` tests como histórico, no como baseline actual.
- Alinear `verify` docs con `8/8 PROVEN` y `62 patterns PROVEN`.
- Crear readiness on-chain solo como dry-run offline/no-broadcast.
- No cargar `.env` real con Codex.
- No ejecutar deploy, broadcast, `cast send`, wallets ni comandos on-chain con firma desde agentes.

## 4. Riesgos cerrados

- Riesgo de sugerir que hashes internos SHA-256 o legacy SHA3-256/FIPS eran equivalentes a `keccak256`.
- Riesgo de publicar métricas antiguas como si fueran baseline vivo.
- Riesgo de mezclar auditoría histórica con estado actual.
- Riesgo de reabrir hallazgos ya superseded por PR #39 y PR #42.
- Riesgo de usar documentación `verify` desactualizada para validar el sistema actual.
- Riesgo de preparar on-chain readiness empezando por wallets o RPC con secretos.

## 5. Riesgos abiertos

- La preparación multi-chain real todavía no está validada contra RPC read-only por red.
- No existe todavía checklist final por red para ejecución multi-chain real.
- Las pruebas on-chain masivas siguen siendo prematuras.
- Cualquier ejecución con wallet, incluso burner, requiere control manual explícito de Juan.
- Documentación histórica fuera del subset auditado puede conservar lenguaje legacy menor.
- Endpoints privados, límites de gas, sponsoreo y condiciones específicas por red deben verificarse en fases futuras sin exponer secretos.

## 6. Cambios en documentación pública

PR #46 alineó documentación pública viva en:

- `README.md`
- `docs/01_architecture/SYSTEM_ARCHITECTURE.md`
- `docs/DOC_SYSTEM.md`
- `docs/accelerator/EXECUTIVE_SUMMARY.md`
- `docs/accelerator/ONE_PAGER.md`
- `docs/accelerator/SECURITY_AND_DISCLOSURE_LIMITS.md`
- `docs/testing-hardening-audit.md`
- `docs/testing-hardening-final-closure.md`
- `docs/testing.md`

La métrica pública viva quedó en `4802 tests collected`. El hito `Historical: PyPI live, 4,800-test milestone` se preservó como histórico, no como baseline actual.

## 7. Cambios en auditorías operativas

PR #47 y PR #48 actualizaron `docs/05_operations/PROOF_REGISTRY_CONSISTENCY_AUDIT.md` para distinguir evidencia histórica de estado actual:

- fallback `sha3_256` en `core/proof_hash.py`: hallazgo histórico superseded por PR #39;
- wording ambiguo final: marcado como historical/superseded;
- warning retenido solo por contexto de auditoría;
- collection actualizado de `4797` a `4802`.

El aprendizaje central: una auditoría histórica no debe leerse como deuda viva si el PR posterior ya cerró el hallazgo.

## 8. Cambios en hash-domain

PR #44 terminó la alineación residual de wording hash-domain en:

- `core/tool_hooks.py`
- `core/zk_governance_proof.py`
- `docs/INDEX.md`

El resultado fue remover lenguaje que podía sugerir `keccak256` cuando el contexto real era:

- hashes internos SHA-256;
- legacy SHA3-256/FIPS;
- dominios no EVM;
- evidencia histórica, no semántica canónica actual.

La regla quedó estable: EVM proof attestations usan semántica Keccak documentada; otros hashes deben nombrarse por su dominio real.

## 9. Cambios en verify CLI

PR #45 alineó:

- `docs/05_operations/VERIFY_CLI.md`
- `docs/07_integrations/Z3_VERIFICATION.md`

El baseline vivo documentado quedó:

- `verify-states`: `8/8 PROVEN`
- `verify-hierarchy`: `62 patterns PROVEN`

La referencia v0.3.x a `42 patterns` y tiempos antiguos se conservó como histórico. No es el baseline vivo.

## 10. Cambios en on-chain readiness

PR #49 creó `scripts/audit/onchain_readiness_dry_run.py` como primer paso on-chain seguro. El script:

- lee `core/chains_config.json`;
- produce reporte de readiness;
- no carga `.env`;
- no lee private keys;
- no usa RPC;
- no firma;
- no hace broadcast;
- no despliega;
- no modifica archivos.

Validaciones registradas del PR #49:

- `python3 scripts/audit/onchain_readiness_dry_run.py`
- `python3 scripts/audit/onchain_readiness_dry_run.py --json | python3 -m json.tool`
- `python3 -m py_compile scripts/audit/onchain_readiness_dry_run.py`
- AST safety check: `PASSED`, sin primitivas de dotenv/private-key/RPC/broadcast/deploy
- `npm run test:collect` -> `4802 tests collected`

## 11. Por qué no se debe usar .env real con Codex

Codex puede auditar, escribir documentación, crear dry-runs y revisar código, pero no debe recibir ni leer secretos reales. Un `.env` real puede contener API keys, RPC privados, wallets, endpoints internos o credenciales operativas. Exponerlo a un agente rompe segregación de secretos, aumenta superficie de filtración y dificulta demostrar que no hubo uso accidental.

La regla documental de este ciclo queda explícita: no .env, no private keys, no broadcast, no deploy real.

## 12. Por qué no se deben ejecutar pruebas masivas on-chain todavía

Las pruebas masivas on-chain todavía mezclarían demasiadas variables no cerradas:

- configuración por red;
- RPC availability;
- gas policy;
- sponsor/whitelist behavior;
- límites específicos como Conflux eSpace;
- riesgo de nonce, fondos y wallets;
- posible exposición de endpoints o llaves.

La secuencia segura es incremental: dry-run offline primero, RPC read-only después, wallet burner manual después, y solo luego ejecución controlada mínima.

## 13. Plan seguro siguiente

### Fase 50: read-only RPC health-check sin wallet

- usar endpoints no sensibles o variables controladas por Juan;
- no cargar private keys;
- consultar solo chain id, block number, gas metadata y contrato si aplica;
- producir NDJSON con `--json`;
- fallar ruidosamente con `Hint:` si la configuración falta.

### Fase 51: testnet con wallet burner manual

- wallet burner creada y fondeada manualmente por Juan;
- Codex no ve private keys;
- comandos preparados como checklist, no ejecutados por agente;
- una red testnet por vez.

### Fase 52: una mainnet mínima manual

- una única red;
- una única operación mínima;
- ejecución manual por Juan;
- evidencia capturada como IDs/tx hashes, no como secretos.

### Fase 53: multi-chain real con checklist por red

- checklist por red;
- sponsor/gas policy validada;
- límites específicos documentados;
- rollback y pause plan;
- reporte final sin payloads sensibles.

## 14. Lecciones aprendidas

- no asumir merge por tag;
- validar `main` antes de checkpoint;
- no crear checkpoint antes de confirmar commit en `main`;
- separar histórico vs baseline vivo;
- no mezclar auditoría histórica con estado actual;
- no exponer know-how sensible;
- no dar `.env` a Codex;
- no ejecutar broadcast desde agentes;
- dry-run primero, RPC read-only después, wallet burner después.

## 15. Regla operativa

Codex audits and writes dry-runs; Juan controls secrets and real execution.

