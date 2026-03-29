# REPORTE DE SEGURIDAD URGENTE - DOF-MESH

**Fecha:** 2026-03-26
**Motivo:** GitGuardian detectó secrets expuestos en Cyberpaisa/DOF-MESH
**Escaner:** Escaneo completo de historial git + archivos actuales

---

## RESUMEN EJECUTIVO

| Severidad | Secretos Reales | Falsos Positivos | Acción Requerida |
|-----------|----------------|-------------------|------------------|
| CRITICO   | 4              | ~30+              | ROTATE + REMOVE  |

Se encontraron **4 secretos REALES** expuestos en el repositorio (tanto en archivos actuales trackeados como en historial git). El resto son datos de test/benchmark/regex patterns (falsos positivos).

---

## SECRETOS REALES ENCONTRADOS

### 1. Google API Key (Gemini) - CRITICO

| Campo | Valor |
|-------|-------|
| **Key:** | `AIzaSyBsrx6G9rgSQOujv2m5xIfuimoOoLxV014` |
| **Archivos actuales:** | `data/extraction/coliseum_vault.jsonl` (462 ocurrencias), `data/extraction/due_diligence_vault.jsonl` (56 ocurrencias) |
| **Commit origen:** | `0bb849a` (2026-03-26) |
| **Contexto:** | La key se filtro en mensajes de error HTTP 429 logueados como payload en archivos JSONL de benchmark |
| **Estado:** | EN CODIGO ACTUAL (trackeado en git) |
| **Accion:** | **ROTATE** la key en Google Cloud Console inmediatamente. **REMOVE** los archivos JSONL del tracking o sanitizar los payloads |

### 2. Telegram Bot Token #1 (claude_dof_bot) - CRITICO

| Campo | Valor |
|-------|-------|
| **Token:** | `8465352813:AAGZqamdYhT8PNWGSP6K_ukkpvutp6DGE6Y` |
| **Archivo actual:** | `scripts/run_claude_dof_bot.sh` (lineas 2 y 8) |
| **Commit origen:** | `c01652c` |
| **Contexto:** | Hardcodeado como `export TELEGRAM_BOT_TOKEN=` en script de deployment |
| **Estado:** | EN CODIGO ACTUAL (trackeado en git) |
| **Accion:** | **ROTATE** via @BotFather en Telegram. Mover a variable de entorno / `.env` (NO trackeado) |

### 3. Telegram Bot Token #2 (soul-watchdog) - CRITICO

| Campo | Valor |
|-------|-------|
| **Token:** | `8706259296:AAHIJgQu6x59tZZ-KgpvJHW-OPZVJFWZYew` |
| **Archivo actual:** | `scripts/soul-watchdog.sh` (linea 26) |
| **Commit origen:** | `849395c` |
| **Contexto:** | Hardcodeado como `local BOT_TOKEN=` en script de alertas |
| **Estado:** | EN CODIGO ACTUAL (trackeado en git) |
| **Accion:** | **ROTATE** via @BotFather en Telegram. Mover a variable de entorno / `.env` (NO trackeado) |

### 4. MIMO/OpenRouter API Key - CRITICO

| Campo | Valor |
|-------|-------|
| **Key:** | `sk-sej9ye5gv5s2ywsrvyi20wnudbd0h96mz0dfyies6qaymtv6` |
| **Archivo actual:** | `scripts/mimo_adapter.py` (linea 21) |
| **Commit origen:** | `c01652c` |
| **Contexto:** | Hardcodeada como `MIMO_API_KEY = "sk-..."` (NO usa `os.getenv()` como las demas keys en el mismo archivo) |
| **Estado:** | EN CODIGO ACTUAL (trackeado en git) |
| **Accion:** | **ROTATE** la key en el proveedor correspondiente. Cambiar a `os.getenv("MIMO_API_KEY", "")` |

---

## FALSOS POSITIVOS CONFIRMADOS

Todos los siguientes son keys de ejemplo/test/benchmark, NO secretos reales:

| Tipo | Archivos | Razon |
|------|----------|-------|
| `sk-abc123...`, `sk-abcdefg...` (8+ variantes) | `core/test_generator.py`, `core/agentleak_benchmark.py`, `tests/test_*.py`, `core/dlp.py` | Datos de prueba para benchmark de deteccion de leaks (AgentLeak) y tests unitarios |
| `ghp_1234567890...` (8 variantes) | `core/agentleak_benchmark.py`, `core/test_generator.py`, `tests/test_*.py` | Tokens GitHub fake para tests de DLP/guardian |
| `AKIAIOSFODNN7EXAMPLE`, `AKIAI44QH8DHBEXAMPLE`, `AKIAZ5EXAMPLE...` | `core/agentleak_benchmark.py`, `tests/test_*.py` | AWS keys de ejemplo (documentacion oficial AWS usa AKIAIOSFODNN7EXAMPLE) |
| `gsk_abc123...`, `gsk_abcdefg...`, `gsk_fakekey...` | `tests/test_opsec_shield.py`, `tests/test_cerberus.py`, `core/dlp.py` | Groq keys fake para tests |
| `AIzaSyD1234567890abcdefghijklmnopqrstuvw` | `tests/test_cerberus.py` | Google key de ejemplo (patron "1234567890abcdef") |
| `0000000000:0000000...` | Historial git | Telegram token placeholder (todos ceros) |
| Regex patterns (`r"sk-[A-Za-z0-9]..."`) | `core/dlp.py`, `core/task_contract.py`, `a2a_server.py` | Patrones regex para deteccion, NO keys reales |

---

## ARCHIVOS DE CERTIFICADOS

| Archivo | Estado | Riesgo |
|---------|--------|--------|
| `certs/server.crt` | Solo local (NO trackeado en git) | BAJO - no expuesto |
| `certs/client_commander.crt` | Solo local (NO trackeado en git) | BAJO - no expuesto |
| `certs/client_mesh-node.crt` | Solo local (NO trackeado en git) | BAJO - no expuesto |
| `scripts/.q_aion_vault.key` | Solo local (NO trackeado en git) | BAJO - hash SHA256, no private key real |

---

## ARCHIVOS .env TRACKEADOS

**Ninguno encontrado.** `git ls-files | grep -i ".env$"` no devolvio resultados. Esto es correcto.

---

## COMMIT 632f05e (Release 8.0) - ANALISIS

El commit contiene referencias a:
- `mesh_key=b"shared-secret-key"` / `b"shared-secret"` / `b"dof-mesh-secret-2026"` - Valores de ejemplo en documentacion/tests, NO keys de produccion
- `private_key = X25519PrivateKey.generate()` - Generacion dinamica, NO hardcoded
- `KEY_ROTATION_HOURS = 24` - Configuracion, no secreto

**Veredicto:** No hay secretos reales en este commit.

---

## PLAN DE REMEDIACION INMEDIATO

### Paso 1: ROTATE (hacer AHORA)
1. **Google API Key:** Ir a Google Cloud Console > APIs & Services > Credentials > Regenerar la key `AIzaSyBsrx6G9rgSQOujv2m5xIfuimoOoLxV014`
2. **Telegram Bot #1:** Hablar con @BotFather > `/revoke` token del bot `8465352813`
3. **Telegram Bot #2:** Hablar con @BotFather > `/revoke` token del bot `8706259296`
4. **MIMO API Key:** Rotar en el dashboard del proveedor (OpenRouter o similar)

### Paso 2: REMOVE de archivos actuales
```bash
# 1. Sanitizar MIMO adapter
sed -i '' 's/MIMO_API_KEY = "sk-sej9ye5gv5s2ywsrvyi20wnudbd0h96mz0dfyies6qaymtv6"/MIMO_API_KEY = os.getenv("MIMO_API_KEY", "")/' scripts/mimo_adapter.py

# 2. Sanitizar scripts de Telegram
sed -i '' 's/8465352813:AAGZqamdYhT8PNWGSP6K_ukkpvutp6DGE6Y/${TELEGRAM_BOT_TOKEN}/g' scripts/run_claude_dof_bot.sh
sed -i '' 's/8706259296:AAHIJgQu6x59tZZ-KgpvJHW-OPZVJFWZYew/${TELEGRAM_BOT_TOKEN}/g' scripts/soul-watchdog.sh

# 3. Sanitizar JSONL (eliminar la key de los payloads de error)
sed -i '' 's/AIzaSyBsrx6G9rgSQOujv2m5xIfuimoOoLxV014/REDACTED/g' data/extraction/coliseum_vault.jsonl
sed -i '' 's/AIzaSyBsrx6G9rgSQOujv2m5xIfuimoOoLxV014/REDACTED/g' data/extraction/due_diligence_vault.jsonl
```

### Paso 3: LIMPIAR historial git (opcional pero recomendado)
El historial de git aun contiene los secretos. Para eliminarlos completamente:
```bash
# Usar git-filter-repo o BFG Repo Cleaner
pip install git-filter-repo
git filter-repo --replace-text <(echo 'AIzaSyBsrx6G9rgSQOujv2m5xIfuimoOoLxV014==>REDACTED')
git filter-repo --replace-text <(echo '8465352813:AAGZqamdYhT8PNWGSP6K_ukkpvutp6DGE6Y==>REDACTED')
git filter-repo --replace-text <(echo '8706259296:AAHIJgQu6x59tZZ-KgpvJHW-OPZVJFWZYew==>REDACTED')
git filter-repo --replace-text <(echo 'sk-sej9ye5gv5s2ywsrvyi20wnudbd0h96mz0dfyies6qaymtv6==>REDACTED')
# Luego force-push (requiere coordinacion con todos los colaboradores)
```

### Paso 4: PREVENIR futuros leaks
- Agregar `.env` y `*.key` a `.gitignore` (ya estan, verificado)
- Considerar pre-commit hook con `detect-secrets` o `gitleaks`
- El sistema DLP propio (`core/dlp.py`) ya detecta estos patrones - asegurar que se ejecute antes de commits

---

## RESOLUCION GitGuardian

Despues de rotar las keys y hacer el commit de limpieza:
1. Ir a GitGuardian dashboard
2. Marcar los incidentes como "Resolved - Key Rotated"
3. Verificar que no haya nuevas alertas

---

*Reporte generado por escaneo de seguridad automatizado - 2026-03-26*
