# DOF-MESH — Reporte de Seguridad (27 marzo 2026)

## Auditoría Ejecutada por Supply Chain Guard

| Severidad | Cantidad | Acción |
|---|---|---|
| CRITICAL | 7 | Revisar litellm imports + pickle patterns |
| HIGH | 112 | eval/exec/os.system en codebase |
| MEDIUM | 247 | Dependencias sin pinnear + patrones menores |
| LOW | 16 | Informativos |
| **Total** | **382** | |

## Hallazgos Críticos

### 1. Secret en historial git
- `.q_aion_vault.key` fue committeado en `c01652c`, removido después
- **Sigue en historial** — accesible con `git log --all`
- Acción: rotar key si tiene valor real

### 2. Requirements sin pinnear (16 dependencias)
- crewai, litellm, python-dotenv, pandas, openpyxl, sqlalchemy, psycopg2-binary, rich, pyyaml, z3-solver, blake3, pyTelegramBotAPI, streamlit, groq, gTTS, sounddevice
- Acción: `pip freeze > requirements.txt` con versiones exactas

### 3. litellm en blacklist (TeamPCP)
- 3 imports de litellm en código (dispatch_hackathon.py, adversarial.py)
- litellm NO está instalado actualmente — riesgo bajo
- Si se instala: verificar versión segura primero

### 4. Archivo WAV en config/
- `config/voice_reference.wav` — legítimo (referencia de voz para TTS)
- Verificado: no es steganography

## Amenazas Activas Monitoreadas

### TeamPCP (PyPI Supply Chain)
- Comprometió: telnyx 4.87.1/4.87.2, LiteLLM, Trivy
- Técnica: WAV steganography + XOR decryption in-memory
- C2: 83.142.209.203
- **Nuestro estado: SEGURO** — no usamos estos paquetes

### CTRL Framework (Russian RAT)
- Descubierto: Censys ARC, Feb 2026
- Target: Windows VPS con RDP
- Técnica: LNK → PowerShell → .NET RAT → FRP tunnel → RDP hijack
- C2: 194.33.61.36, 109.107.168.18
- **Nuestro estado: SEGURO** — somos macOS/Linux, no Windows

### CVE-2025-53521 (F5 BIG-IP)
- Scanning activo de /mgmt/shared/identified-devices/config/device-info
- User-Agent: "CVE-2025-53521-Scanner/1.0"
- **Nuestro estado: N/A** — no usamos F5

## Estado de Protecciones DOF

| Protección | Estado |
|---|---|
| Supply Chain Guard | ACTIVO — blacklist, import scan, steganography |
| .gitignore | OK — cubre .env, *.key, secrets |
| .dof-keys permisos | OK — chmod 600 |
| Private keys en código | LIMPIO — solo env vars |
| Governance determinística | ACTIVO — zero-LLM |
| Z3 verification | ACTIVO — 4 teoremas |
| Sentinel Engine | ACTIVO — 10 checks |
| IOCs actualizados | TeamPCP + CTRL + F5 |

## Recomendaciones Pendientes

1. Pinnear todas las dependencias en requirements.txt
2. Considerar purgar historial git (.q_aion_vault.key)
3. Agregar `pip-audit` o `safety check` al CI
4. MFA en todos los servicios (GitHub, Railway, Vercel, Supabase)
5. Rotar tokens de Railway (servicios ya muertos pero tokens podrían estar vivos)

---

*Generado por Supply Chain Guard + Team Agents — 27 marzo 2026*
