# Knowledge Pipeline — QA Checklist

> DOF-MESH v0.6.0 · Última actualización: 05 abr 2026

## Reinicio rápido

```bash
~/bin/dof          # mata procesos viejos y arranca con código fresco
```

> **IMPORTANTE:** Siempre usar `~/bin/dof` después de cambios en
> `core/knowledge_*.py`. El script mata y reinicia los 3 servicios.
> Nunca dejar procesos corriendo con código viejo.

## Checklist de diagnóstico (10 puntos)

```bash
# 1. API responde
curl -s http://127.0.0.1:19019/health
# esperado: {"status":"ok","port":19019}

# 2. Cola pendiente
curl -s http://127.0.0.1:19019/pending
# esperado: [] o lista de items

# 3. Procesos corriendo
ps aux | grep -E "knowledge_api|knowledge_daemon|knowledge_approver" | grep -v grep
# esperado: 3 procesos Python

# 4. Puerto 19019 activo
lsof -i:19019 | grep LISTEN
# esperado: Python PID ... (LISTEN)

# 5. Test /ingest
curl -s -X POST http://127.0.0.1:19019/ingest \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
# esperado: {"status":"queued","url":"..."}

# 6. Log API (errores recientes)
tail -20 /tmp/dof_api.log

# 7. Log daemon
tail -20 /tmp/dof_daemon.log
# esperado: "[KNOWLEDGE] Knowledge Daemon started — watching docs/knowledge/"

# 8. Log approver (Telegram)
tail -20 /tmp/dof_approver.log

# 9. Tests unitarios
cd ~/equipo-de-agentes
python3 -m unittest discover -s tests -p "test_knowledge*" -v 2>&1 | tail -5
# esperado: Ran N tests ... OK

# 10. Directorio knowledge
ls -la ~/equipo-de-agentes/docs/knowledge/
ls ~/equipo-de-agentes/docs/knowledge/pending/   2>/dev/null
ls ~/equipo-de-agentes/docs/knowledge/approved/  2>/dev/null
ls ~/equipo-de-agentes/docs/knowledge/rejected/  2>/dev/null
```

## Root causes conocidos y fixes

### RC-01: API responde 404 en /ingest

**Síntoma:** `curl -X POST .../ingest` → `{"error":"not found"}`
**Causa:** Proceso corriendo con código viejo (pre-commit que agregó el endpoint)
**Fix:**
```bash
~/bin/dof   # mata y reinicia con código fresco
```

### RC-02: Botón ⚡DOF queda en "Ingesting..."

**Síntoma:** El botón en YouTube no cambia a ✅/❌
**Causas posibles:**
1. API offline → `curl http://127.0.0.1:19019/health`
2. Service worker MV3 suspendido antes de responder → normal, la acción llegó igual
3. content.js → background.js canal cerrado → popup ya tiene fix con try/catch
**Fix:** Recargar la extensión en `chrome://extensions` y verificar `/pending`

### RC-03: Video no aparece en /pending después de ingestar

**Síntoma:** `/ingest` responde `{"status":"queued"}` pero `/pending` sigue vacío
**Causa:** `youtube_ingestor` falló (sin yt-dlp, sin transcripción, LLM offline)
**Fix:**
```bash
tail -50 /tmp/dof_api.log | grep -i "error\|failed\|ingest"
```

### RC-04: knowledge_daemon no detecta archivos nuevos

**Síntoma:** Archivos en `docs/knowledge/` pero no llegan al pipeline
**Causa:** Daemon arrancó antes de que existiera el directorio, o crasheó
**Fix:**
```bash
~/bin/dof   # restart completo
tail -f /tmp/dof_daemon.log
```

### RC-05: Telegram no recibe notificaciones

**Síntoma:** Video aprobado pero sin mensaje en Telegram
**Causa:** `TELEGRAM_BOT_TOKEN` o `TELEGRAM_CHAT_ID` no en entorno del proceso
**Fix:**
```bash
tail -20 /tmp/dof_approver.log   # buscar "Telegram error"
# Si falta env: ~/bin/dof carga .env automáticamente vía python-dotenv
```

## Flujo completo esperado

```
YouTube watch?v=XXX
  ↓ click ⚡DOF (content.js)
  ↓ chrome.runtime.sendMessage INGEST (background.js)
  ↓ POST /ingest (knowledge_api.py)
  ↓ {"status":"queued"}  ← respuesta inmediata
  ↓ threading: youtube_ingestor.ingest(url)
  ↓ knowledge_daemon._process_pending()
  ↓ knowledge_reporter.report_all_pending()
  ↓ knowledge_notifier.notify_all_pending()
  ↓ GET /pending → [{score_dof, relevancia, ideas_clave, ...}]
  ↓ popup muestra card (fuente: API, no storage)
  ↓ click ✅ Aprobar / ❌ Rechazar
  ↓ POST /approve/:rid  o  /reject/:rid
  ↓ archivo movido pending/ → approved/ o rejected/
  ↓ popup llama init() → /pending vacío → renderEmpty()
```

## Comandos de emergencia

```bash
# Matar todo y reiniciar limpio
pkill -f knowledge_api.py; pkill -f knowledge_daemon.py; pkill -f knowledge_approver.py
sleep 2 && ~/bin/dof

# Ver todos los logs en tiempo real
tail -f /tmp/dof_api.log /tmp/dof_daemon.log /tmp/dof_approver.log

# Limpiar cola pendiente manualmente
ls ~/equipo-de-agentes/docs/knowledge/pending/

# Aprobar/rechazar desde CLI
curl -s -X POST http://127.0.0.1:19019/approve/<rid>
curl -s -X POST http://127.0.0.1:19019/reject/<rid>

# Test completo del pipeline
curl -s -X POST http://127.0.0.1:19019/ingest \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=JX0PQdQ4iAM"}'
sleep 30
curl -s http://127.0.0.1:19019/pending
```
