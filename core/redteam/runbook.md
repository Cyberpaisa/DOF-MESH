# DOF-MESH :: Runbook del Laboratorio Defensivo Soberano
**Versión:** V7.3 Final  
**Última actualización:** 2026-04-23  
**Arquitectura:** UTM (macOS M4) → Ubuntu Server ARM64 → Docker internal network

---

## Arquitectura de la Jaula

```
HOST MAC (no tocado)
└── UTM VM: Ubuntu Server ARM64 (Red: Disconnected)
    ├── Ollama + dof-coder (127.0.0.1:11434)
    └── Docker network: lab_net (internal: true, 10.10.10.0/24)
        ├── Juice Shop 17.2.1  → 10.10.10.10:3000
        ├── WebGoat 2023.8     → 10.10.10.11:8080
        └── netshoot (tcpdump) → .pcap en /opt/dof-mesh/logs/captures/
```

> ⚠️ **ARM64 - WebGoat:** Si `docker pull --platform linux/arm64 webgoat/webgoat:2023.8` falla,
> el contenedor correrá bajo emulación Rosetta 2 (más lento pero funcional). Verificar con:
> `docker inspect lab_webgoat | grep -i arch`

---

## Fase 0: Setup Inicial (Solo la primera vez)

### 0.1 Instalar UTM y crear VM
1. Descarga UTM desde [getutm.app](https://getutm.app) (gratuito).
2. Crear nueva VM → "Virtualizar" → Linux.
3. Imagen: **Ubuntu Server 22.04.5 ARM64** (`ubuntu-22.04.5-live-server-arm64.iso`).
4. **Verificación:** SHA256 debe ser `eafec62cfe760c30cac43f446463e628fada468c2de2f14e0e2bc27295187505`.
5. RAM: **mínimo 10 GB** (para correr el modelo 14B).
6. Disco: **40 GB** mínimo.
7. **Red: seleccionar "Disconnected"** antes de arrancar la VM.

### 0.2 Provisionar la VM
```bash
# Dentro de la VM, como root
curl -O https://raw.githubusercontent.com/.../provision_vm.sh  # o transferir manualmente
chmod +x provision_vm.sh
sudo ./provision_vm.sh
sudo reboot
```

### 0.3 Exportar y transferir el modelo
```bash
# En tu Mac host
chmod +x core/redteam/export_model.sh
./core/redteam/export_model.sh dof-coder

# Monta ~/dof-mesh-export como Shared Folder en UTM y copia a la VM:
# /opt/dof-mesh/models/Modelfile.vm
# /opt/dof-mesh/models/model.gguf
```

### 0.4 Importar el modelo en la VM
```bash
# Como dofoperator dentro de la VM
BLOB_HASH=$(sha256sum /opt/dof-mesh/models/model.gguf | cut -d' ' -f1)
mkdir -p ~/.ollama/models/blobs
cp /opt/dof-mesh/models/model.gguf ~/.ollama/models/blobs/sha256-${BLOB_HASH}

ollama create dof-coder -f /opt/dof-mesh/models/Modelfile.vm
ollama list  # Debe mostrar dof-coder
```

### 0.5 Configurar credenciales del lab
```bash
cd /opt/dof-mesh/lab
cp .env.lab.example .env.lab
# Editar .env.lab y reemplazar REPLACE_ME con una contraseña aleatoria:
# DVWA_MYSQL_PASS=$(openssl rand -hex 16)
```

---

## Fase 1: Arranque de Sesión

```bash
# Como dofoperator en la VM
ollama serve &                                        # Iniciar motor de inferencia
cd /opt/dof-mesh/lab
docker compose -f docker-compose.lab.yml up -d       # Levantar targets
bash /opt/dof-mesh/lab/verify_lab.sh                 # Verificar que todo está OK
```

**Todos los checks deben mostrar ✅ antes de continuar.**

---

## Fase 2: Flujo de Análisis (Operación Normal)

### 2.1 Exploración manual (el operador ejecuta, no el agente)
```bash
# Juice Shop
curl -s http://10.10.10.10:3000/api/Products | python3 -m json.tool > /tmp/js_api.txt
nmap -sV -p 3000 10.10.10.10 > /tmp/scan_juiceshop.txt

# WebGoat
nmap -sV -p 8080 10.10.10.11 > /tmp/scan_webgoat.txt
```

### 2.2 Análisis defensivo con el agente
```bash
python3 /opt/dof-mesh/security_analyst.py \
    --input /tmp/scan_juiceshop.txt \
    --target 10.10.10.10 \
    --output /opt/dof-mesh/reports/juiceshop_$(date +%Y%m%d).md

python3 /opt/dof-mesh/security_analyst.py \
    --input /tmp/scan_webgoat.txt \
    --target 10.10.10.11 \
    --output /opt/dof-mesh/reports/webgoat_$(date +%Y%m%d).md
```

### 2.3 Revisar el reporte
```bash
cat /opt/dof-mesh/reports/juiceshop_$(date +%Y%m%d).md
```

---

## Fase 3: Cierre de Sesión

```bash
docker compose -f docker-compose.lab.yml down
pkill ollama
```

> Los `.pcap` de captura quedan en `/opt/dof-mesh/logs/captures/` para análisis posterior
> con Wireshark en tu Mac (transfiere vía Shared Folder de UTM).

---

## Troubleshooting Rápido

| Síntoma | Causa probable | Solución |
|---------|---------------|----------|
| `verify_lab.sh` falla en Docker | Daemon no iniciado | `sudo systemctl start docker` |
| Juice Shop no responde | Contenedor tardó en iniciar | Esperar 30s y reintentar |
| WebGoat no responde | Slow start de JVM (1-2 min) | `docker logs lab_webgoat -f` |
| Ollama no encuentra dof-coder | Modelo no importado | Ver Fase 0.4 |
| `ping 8.8.8.8` tiene éxito | Red UTM configurada como Shared/Bridged | Cambiar a "Disconnected" en UTM y reiniciar VM |

---

## Regla de Oro: Context Engineering para Análisis Forense

> **Para análisis de autenticación, el input al agente DEBE incluir tanto el REQUEST
> (payload enviado) como el RESPONSE (token/hash recibido). El agente no infiere
> vectores de ataque sin evidencia del vector.**

```bash
# Ejemplo correcto para análisis de bypass de autenticación:
echo "=== REQUEST ===" > /tmp/auth_analysis.txt
echo "POST /rest/user/login" >> /tmp/auth_analysis.txt
echo "Payload: {\"email\":\"admin' OR 1=1--\",\"password\":\"x\"}" >> /tmp/auth_analysis.txt
echo "" >> /tmp/auth_analysis.txt
echo "=== RESPONSE ===" >> /tmp/auth_analysis.txt
cat /tmp/server_response.json >> /tmp/auth_analysis.txt

python3 security_analyst.py --input /tmp/auth_analysis.txt --target 10.10.10.10 \
    --output /opt/dof-mesh/reports/auth_bypass_$(date +%Y%m%d).md
```

---

## Fase 4: Respuesta Defensiva (SOAR — Pilar 4)

### 4.1 Principios Inmutables
- `lab_juiceshop`, `lab_webgoat`, `lab_traffic` **NUNCA** son objetivo del SOAR.
- Toda acción mutativa requiere aprobación humana explícita (`--approve`).
- Cooldown de 5 minutos entre acciones para prevenir Self-DoS.

### 4.2 Flujo Operativo
```bash
# 1. El analista detecta un reporte crítico contra un target NO whitelisted
#    y envía un trigger automático al inbox del SOAR.

# 2. Procesar inbox manualmente (o vía cron):
sudo -u soar python3 /opt/dof-mesh/defensive_soar.py --process

# 3. Si hay un ticket pendiente, verificar estado:
sudo -u soar python3 /opt/dof-mesh/defensive_soar.py --status

# 4. Aprobar la acción (dentro de los 5 minutos):
sudo -u soar python3 /opt/dof-mesh/defensive_soar.py --approve <TICKET_ID>

# 5. Limpiar tickets expirados:
sudo -u soar python3 /opt/dof-mesh/defensive_soar.py --cleanup
```

### 4.3 Evidencias Forenses
Las imágenes de evidencia se almacenan como tarballs (NO como imágenes Docker ejecutables):
```bash
ls /var/lib/soar/snapshots/
# rogue_container_evidence_1776958000.tar

# Inspeccionar sin ejecutar:
mkdir /tmp/forensic && tar xf /var/lib/soar/snapshots/*.tar -C /tmp/forensic
ls /tmp/forensic/etc/  # Analizar filesystem del intruso
```

### 4.4 Registro de Auditoría
```bash
cat /var/lib/soar/audit.log
# Formato: TIMESTAMP | ACTION | TARGET | REPORT_HASH | OPERATOR | STATUS
```

> ⚠️ **NUNCA ejecutes `docker run` sobre una imagen de evidencia.** Usa `tar` para inspección estática.

---

## Checklist de Migración UTM (V7.3)

- [ ] Descargar Ubuntu Server 24.04 ARM64 ISO
- [ ] Crear VM en UTM: 12GB RAM, 2 discos (sistema + datos), red "Disconnected"
- [ ] Instalar Ubuntu con cifrado LUKS completo
- [ ] Ejecutar `provision_vm.sh` adaptado a 24.04
- [ ] Aplicar `sysctl` hardening (`/etc/sysctl.d/99-dof-hardening.conf`)
- [ ] Configurar AppArmor enforce
- [ ] Crear usuario `soar` y aplicar `soar_sudoers.template`
- [ ] Configurar directorios SOAR (`/var/lib/soar/` con permisos 700)
- [ ] Aplicar `chattr +a` en `audit.log`
- [ ] Transferir modelos vía ISO montada (no Shared Folder permanente)
- [ ] Desactivar Shared Folder
- [ ] Ejecutar `verify_lab.sh` — todos los checks deben pasar
- [ ] Ejecutar prueba de estrés (Req+Resp SQLi)
- [ ] Ejecutar batería SOAR (whitelist, cooldown, aprobación)

---

## Troubleshooting Rápido

| Síntoma | Causa probable | Solución |
|---------|---------------|----------|
| `verify_lab.sh` falla en Docker | Daemon no iniciado | `sudo systemctl start docker` |
| Juice Shop no responde | Contenedor tardó en iniciar | Esperar 30s y reintentar |
| WebGoat no responde | Slow start de JVM (1-2 min) | `docker logs lab_webgoat -f` |
| Ollama no encuentra modelo | Modelo no importado | Ver Fase 0.4 |
| `ping 8.8.8.8` tiene éxito | Red UTM no es Disconnected | Cambiar a "Disconnected" y reiniciar VM |
| SOAR ignora reportes | Falta marca `[SOAR-TRIGGER]` | Verificar que el analista la incluye |
| Ticket expira antes de aprobar | Timeout de 300s | Aprobar más rápido o ajustar `TICKET_TIMEOUT_SECONDS` |

---

## Referencias
- [Juice Shop - OWASP Challenge List](https://pwning.owasp-juice.shop/)
- [WebGoat - Lessons](https://owasp.org/www-project-webgoat/)
- `security_analyst.py --help` para opciones del agente
- `defensive_soar.py --status` para estado del SOAR
