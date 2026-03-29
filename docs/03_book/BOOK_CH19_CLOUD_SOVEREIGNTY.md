# Capitulo 19: De Cero a Cloud — Infraestructura Soberana en Una Sesion

*26 de marzo de 2026. Desarrollador solo. MacBook Pro M4 Max 36GB. El dia que el proyecto casi se incendia y termino en la nube.*

---

## 19.1 El Malware de OpenClaw

Todo empezo con una alerta que no venia de ningun scanner automatizado sino de la intuicion pura del operador.

Mission Control, el dashboard de OpenClaw que orquestaba los agentes via npm, contenia algo que ninguna herramienta de analisis convencional detectaria: **esteganografia Unicode en paquetes npm**. El patron era sofisticado: llamadas a `eval()` ocultas dentro de Variation Selectors Unicode (U+FE00 a U+FE0F), caracteres de ancho cero que los editores de texto y los revisores de codigo simplemente no muestran.

El mecanismo:
1. Un paquete npm aparentemente legitimo incluia strings con Variation Selectors invisibles
2. Al concatenar los code points ocultos, se reconstruia una cadena ejecutable
3. `eval()` la ejecutaba en el contexto del proceso Node.js
4. El payload tenia acceso completo al filesystem, variables de entorno y red

La deteccion fue manual. Revisando dependencias de Mission Control, los caracteres invisibles aparecieron en un hex dump que no cuadraba con el tamano visible del archivo. Una vez confirmada la presencia del patron, la decision fue inmediata: **eliminar Mission Control completo del monorepo**.

```bash
# Eliminacion total — sin negociacion
rm -rf mission-control/
git rm -r --cached mission-control/
```

No hubo debate sobre "limpiar solo el paquete infectado". Cuando descubres esteganografia ofuscada en tu cadena de dependencias, la unica respuesta racional es erradicar el vector completo. Mission Control era conveniente, pero ningun dashboard vale una backdoor.

**La leccion nuclear**: npm es un vector de ataque de primer orden. Cualquier paquete con dependencias transitivas puede inyectar codigo invisible. El DOF, que se jacta de gobernanza deterministica, estuvo a un `npm install` de ser comprometido.

---

## 19.2 Recuperacion de Wallet — Forense en Logs de Gemini

Durante la sesion de mesh multi-modelo del 25 de marzo, Gemini (nodo Antigravity) habia creado una wallet Avalanche para el proyecto:

- **Direccion**: `0x2cF7...` (C-Chain)
- **Fondos**: 5 USDC + 0.05 AVAX
- **Problema**: Gemini genero la wallet, reporto la direccion, pero **nunca guardo la clave privada** en ningun archivo accesible

Cinco dolares no es mucho. Pero perder acceso a una wallet creada por un agente autonomo es exactamente el tipo de fallo que el DOF existe para prevenir. Si no podemos gobernar la custodia de claves de nuestros propios agentes, que estamos vendiendo?

La busqueda forense:

1. **Logs del mesh**: `logs/mesh/inbox/antigravity/` — mensajes JSON de la sesion, pero sin clave privada
2. **Historial de Gemini**: no persistente entre sesiones, inaccesible
3. **Grep recursivo**: busqueda de patrones hex de 64 caracteres en todo el repositorio
4. **El hallazgo**: `.q_aion_vault.key` — un archivo creado por Antigravity durante la ejecucion de Q-Aion (el modulo cuantico), donde Gemini habia almacenado la clave como parte de un "vault" experimental

La clave estaba ahi, enterrada en un archivo con nombre crriptico que ningun humano habria buscado sin contexto. Recuperacion exitosa. Fondos seguros.

**Leccion**: cuando un agente autonomo genera material criptografico, DEBE existir un protocolo de custodia determinista. No "el agente decidira donde guardarlo". Un path fijo, cifrado, con backup. Esto va directo al backlog de seguridad.

---

## 19.3 Reparacion del Sistema — 5 Agentes en Paralelo

El sistema estaba roto en cinco puntos simultaneos. En lugar de arreglarlos secuencialmente, desplegamos 5 agentes Claude en paralelo, cada uno con una mision especifica:

### 19.3.1 Espacios en Rutas → Guiones

El directorio original del proyecto era `equipo de agentes` — con espacios. Esto rompia:
- Scripts bash que no escapaban correctamente
- Imports de Python con paths absolutos
- Configuraciones de OpenClaw que usaban el path como workspace ID
- Git hooks que construian rutas por concatenacion

El agente reemplazo todas las referencias a paths con guiones: `equipo-de-agentes`. Mas de 40 archivos actualizados.

### 19.3.2 Bot de Telegram Duplicado

Dos instancias del bot de Telegram estaban corriendo simultaneamente: una desde el daemon autonomo y otra desde el script manual `interfaces/telegram_bot.py`. Ambas competian por los mismos updates de la API de Telegram, causando:
- Mensajes procesados dos veces
- Respuestas duplicadas al usuario
- Race conditions en el estado compartido

Solucion: deteccion de PID existente al iniciar, kill de la instancia zombie, lock file para prevenir duplicados futuros.

### 19.3.3 Saturacion de Cola del Mesh

La cola de mensajes del mesh habia acumulado **3,298 mensajes** sin procesar. Nodos que ya no existian seguian recibiendo mensajes. Inboxes de nodos temporales de sesiones anteriores nunca fueron limpiados.

```
logs/mesh/inbox/ds-001/       →  847 mensajes (DeepSeek, sesion del 23 de marzo)
logs/mesh/inbox/test-node-*/  → 1,203 mensajes (nodos de prueba nunca eliminados)
logs/mesh/inbox/antigravity/  →  412 mensajes (Gemini, sesion del 25 de marzo)
...resto distribuido en 15+ inboxes huerfanos
```

Solucion: archivo masivo a `logs/mesh/archive/2026-03-26/`, limpieza de inboxes huerfanos, implementacion de TTL (time-to-live) de 48 horas para mensajes no leidos.

### 19.3.4 Exports Rotos de Gobernanza

`core/governance.py` habia perdido exports criticos durante un refactor. `GovernanceResult`, `enforce_constitution`, y `check_compliance` no estaban en `__all__`, causando `ImportError` en modulos downstream que dependian de imports explicitos.

Correccion directa: restaurar `__all__` con los 12 exports publicos del modulo.

### 19.3.5 Errores de CrewAI en Streamlit

El dashboard Streamlit importaba `crewai` para visualizar el estado de los agentes, pero CrewAI habia actualizado su API rompiendo compatibilidad. `Crew.kickoff()` ahora requeria parametros que antes eran opcionales.

Solucion: pin de version de crewai en requirements, actualizacion de las llamadas al nuevo API.

---

## 19.4 La Solucion del Symlink

El problema de los dos directorios era mas profundo de lo que parecia:

```
/Users/jquiceva/equipo de agentes/    ← directorio original (con espacios)
/Users/jquiceva/equipo-de-agentes/    ← directorio nuevo (con guiones)
```

Ambos existian. Ambos tenian archivos. Configuraciones, scripts, LaunchAgents, rutas en `.claude/`, todo apuntaba a uno u otro de forma inconsistente. Un `mv` simple no funcionaba porque habia procesos con file handles abiertos al directorio viejo.

La solucion elegante:

1. **Backup** del directorio con espacios: `cp -a "equipo de agentes" equipo-de-agentes-backup-spaces`
2. **Merge** de archivos unicos del directorio viejo al nuevo
3. **Eliminacion** del directorio viejo
4. **Symlink**: `ln -s equipo-de-agentes "equipo de agentes"`

El symlink es la clave. Cualquier proceso legacy que busque el path con espacios encuentra el symlink y llega al directorio real con guiones. Cero breakage, migracion transparente.

---

## 19.5 Auditoria de Proveedores

Marzo 26 fue dia de auditoria completa de APIs. Cada proveedor fue probado con una llamada real de inferencia:

| Proveedor | Estado | Notas |
|---|---|---|
| **DeepSeek** | VIVO | Estable, barato ($0.14/M input, $0.28/M output), modelo `deepseek-chat` |
| **SambaNova** | VIVO | Llama 3.3 70B, rapido (~800 tok/s), free tier generoso |
| **Cerebras** | VIVO | Nombre de modelo corregido (era `llama3.1-70b`, correcto: `llama-3.3-70b`) |
| **Groq** | EXPIRADO | API key invalida (403 Forbidden). Necesita renovacion |
| **Gemini** | RATE LIMITED | Funciona pero 429 frecuentes. Free tier insuficiente para mesh |
| **NVIDIA NIM** | No testeado | Pendiente para siguiente auditoria |

**Decision**: DeepSeek como proveedor por defecto para todo. La razon es triple:
1. **Costo**: ordenes de magnitud mas barato que cualquier alternativa cloud
2. **Estabilidad**: 0 caidas en las ultimas 72 horas de uso continuo
3. **Calidad**: DeepSeek-V3 compite con GPT-4o en benchmarks, suficiente para tareas de mesh

El error de Cerebras fue instructivo: el modelo `llama3.1-70b` habia sido deprecado y reemplazado por `llama-3.3-70b`. El error 404 (`model does not exist`) era criptico. Leccion: siempre verificar nombres exactos de modelos despues de actualizaciones de proveedor.

---

## 19.6 Demo del Mesh Multi-Modelo

Con los proveedores auditados, ejecutamos una reunion AgentMeet con **11 agentes** corriendo en paralelo:

- 4 agentes en DeepSeek (deepseek-chat)
- 3 agentes en SambaNova (llama-3.3-70b)
- 2 agentes en Cerebras (llama-3.3-70b)
- 1 agente Claude (Opus, via SDK)
- 1 agente local (Qwen3 32B via MLX)

La novedad de esta sesion fue el uso de **llamadas API paralelas** a DeepSeek y SambaNova simultaneamente, en lugar del modelo secuencial que habiamos usado hasta ahora. `asyncio.gather()` con timeout individual por proveedor:

```python
results = await asyncio.gather(
    call_deepseek(prompt, timeout=30),
    call_sambanova(prompt, timeout=30),
    return_exceptions=True
)
```

Resultado: tiempo de respuesta del mesh reducido de ~45s (secuencial) a ~12s (paralelo). La calidad de las respuestas se mantiene porque el Supervisor evalua y fusiona los outputs de todos los nodos independientemente del orden de llegada.

---

## 19.7 Oracle Cloud VPS — El Salto a la Nube

Esta fue la pieza mas significativa del dia. El DOF necesitaba infraestructura 24/7 y el MacBook Pro no puede estar encendido permanentemente.

### 19.7.1 Creacion de Cuenta

Oracle Cloud Infrastructure (OCI) ofrece un free tier permanente que incluye:
- 4 OCPUs ARM (Ampere A1) — 24GB RAM
- 200GB almacenamiento
- 10TB transferencia/mes
- Sin tarjeta de credito para el tier gratuito base

Cuenta creada con `jquiceva@gmail.com`. Verificacion por telefono. Activacion inmediata.

### 19.7.2 Seleccion de Region

Dos candidatas:

| Region | Ventajas | Desventajas |
|---|---|---|
| **Bogota (BOG)** | Baja latencia (~20ms) desde Medellin | Capacidad ARM limitada, region nueva |
| **Ashburn (IAD)** | Capacidad ARM abundante, region madura | Latencia mayor (~80ms) |

**Decision: Ashburn**. La razon es pragmatica: las instancias ARM Ampere A1 en regiones nuevas como Bogota tienen el infame error "Out of host capacity" casi permanentemente. Ashburn, al ser la region mas grande de OCI, tiene rotacion de capacidad mucho mas frecuente. Para un bot de Telegram y un mesh de agentes, 80ms vs 20ms de latencia es irrelevante.

### 19.7.3 OCI CLI y la Danza de las API Keys

La configuracion del OCI CLI fue un ejercicio de paciencia:

1. Instalar OCI CLI: `brew install oci-cli`
2. Ejecutar `oci setup config` — genera `~/.oci/config`
3. Crear API key pair: genera RSA 2048-bit
4. Subir la public key a la consola OCI (Identity → Users → API Keys)
5. Copiar el fingerprint generado al config
6. Obtener tenancy OCID, user OCID, compartment OCID
7. Probar: `oci iam availability-domain list`

El "baile" es que cada OCID es un string de 60+ caracteres que hay que copiar exactamente. Un caracter mal y el error es un generico `401 NotAuthenticated` sin indicar cual OCID esta mal.

### 19.7.4 Networking — VCN, Subnet, IGW, Firewall

Antes de crear la VM, hay que construir toda la red:

```
VCN (Virtual Cloud Network)
  └── Subnet publica (10.0.0.0/24)
       └── Internet Gateway (IGW)
            └── Route Table (0.0.0.0/0 → IGW)
                 └── Security List (firewall rules)
```

Reglas de firewall configuradas:
- **SSH**: TCP 22 (restringido a IP de casa)
- **Telegram webhook**: TCP 443 (abierto, para el bot)
- **Streamlit**: TCP 8501 (restringido a IP de casa)
- **Mesh HTTP bridge**: TCP 7899 (restringido a IP de casa)
- **ICMP**: ping permitido para diagnostico

Todo via OCI CLI:

```bash
# Crear VCN
oci network vcn create --cidr-block "10.0.0.0/16" --display-name "dof-vcn"

# Crear subnet
oci network subnet create --vcn-id $VCN_ID --cidr-block "10.0.0.0/24"

# Crear Internet Gateway
oci network internet-gateway create --vcn-id $VCN_ID --is-enabled true

# Actualizar route table
oci network route-table update --rt-id $RT_ID \
  --route-rules '[{"destination":"0.0.0.0/0","networkEntityId":"'$IGW_ID'"}]'
```

### 19.7.5 El Script Grabber — Cazando Capacidad ARM

El problema mas frustrante de Oracle Cloud free tier: **"Out of host capacity"**. Las instancias ARM gratuitas se agotan constantemente. La solucion es un script que intenta crear la instancia en loop hasta que hay capacidad disponible:

```bash
#!/bin/bash
# oracle-vm-grabber.sh — intenta crear VM ARM cada 60 segundos
while true; do
    echo "[$(date)] Intentando crear instancia..."
    RESULT=$(oci compute instance launch \
        --availability-domain "$AD" \
        --compartment-id "$COMPARTMENT_ID" \
        --shape "VM.Standard.A1.Flex" \
        --shape-config '{"ocpus":4,"memoryInGb":24}' \
        --image-id "$IMAGE_ID" \
        --subnet-id "$SUBNET_ID" \
        --ssh-authorized-keys-file ~/.ssh/id_rsa.pub \
        --display-name "dof-legion" 2>&1)

    if echo "$RESULT" | grep -q "lifecycleState"; then
        echo "VM CREADA EXITOSAMENTE"
        echo "$RESULT" | python3 -m json.tool
        break
    fi

    echo "Out of capacity. Reintentando en 60s..."
    sleep 60
done
```

El script queda corriendo en una terminal dedicada. Puede tomar minutos u horas, pero eventualmente la capacidad se libera y la instancia se crea automaticamente.

---

## 19.8 Decision Arquitectonica — Mac + VPS

La arquitectura final del DOF queda dividida en dos ambientes:

```
┌─────────────────────────────────┐     ┌──────────────────────────────────┐
│     MAC (Desarrollo)            │     │     VPS (Produccion 24/7)        │
│                                 │     │                                  │
│  - Claude Code (IDE)            │     │  - Telegram Bot                  │
│  - Desarrollo de modulos        │     │  - Mesh Daemon                   │
│  - Tests y Z3 verification      │     │  - Streamlit Dashboard           │
│  - MLX inferencia local         │     │  - Arbitrage Monitor             │
│  - Git (repositorio principal)  │     │  - Hyperion HTTP Bridge          │
│  - Qwen3 32B (GPU/ANE)         │     │  - Cron jobs (health checks)     │
│                                 │     │  - Node.js workers               │
│  36GB RAM / M4 Max              │     │  4 OCPU ARM / 24GB RAM           │
│  Horario: cuando trabajo        │     │  Horario: 24/7/365               │
└──────────┬──────────────────────┘     └──────────┬───────────────────────┘
           │                                       │
           └───────── git push/pull ───────────────┘
                      SSH tunnel
                      Mesh HTTP bridge (:7899)
```

### Por que esta separacion?

1. **El Mac no duerme, pero tu si**: el Telegram bot necesita responder a las 3am. El mesh necesita procesar mensajes cuando no hay humano. El dashboard necesita estar accesible siempre.

2. **El Mac es demasiado valioso para servidor**: 36GB de RAM unified con GPU de 40 cores no deberia estar saturado corriendo un web server. Debe estar disponible para desarrollo e inferencia local.

3. **Costo cero**: el free tier de Oracle Cloud es permanente. No hay factura mensual. La unica inversion es el tiempo de configuracion.

4. **Seguridad**: el codigo fuente y las claves privadas viven solo en el Mac. El VPS recibe solo lo que necesita para ejecutar (binarios, configs, credenciales de API). Si el VPS es comprometido, el codigo fuente y la IP del DOF estan a salvo.

5. **Escalabilidad**: cuando el proyecto crezca, se agregan VPS adicionales. El Mac sigue siendo el centro de control. La federacion via Hyperion HTTP bridge ya esta implementada.

---

## 19.9 Lecciones

### Leccion 6: npm es un Vector de Ataque Invisible

Los Variation Selectors Unicode (U+FE00-U+FE0F) son caracteres de ancho cero que pasan todos los linters, todos los code reviews, y todos los scanners de vulnerabilidades convencionales. Un paquete npm puede contener payload ejecutable que ningun humano vera en un `cat` o en un editor de texto. La unica defensa es: minimizar dependencias, auditar hex dumps, y preferir codigo propio sobre paquetes de terceros. El DOF perdio Mission Control por esto. No debio tenerlo en primer lugar.

### Leccion 7: Los Agentes Autonomos Necesitan Custodia de Claves Determinista

Cuando un agente genera una wallet, crea una API key, o produce cualquier material criptografico, el destino de ese material no puede ser una decision del agente. Debe existir un path predefinido, cifrado, con respaldo automatico. Gemini creo una wallet con fondos reales y "decidio" guardar la clave en un archivo con nombre arbitrario. Funciono por suerte, no por diseno.

### Leccion 8: Reparacion Paralela > Secuencial

Cinco problemas, cinco agentes, un solo operador humano coordinando. Cada agente trabaja en su dominio sin pisar al otro. El tiempo total de reparacion fue ~20 minutos en lugar de las ~2 horas que habria tomado secuencialmente. La clave: descomposicion clara de responsabilidades y zero shared state entre agentes.

### Leccion 9: El Symlink es la Navaja Suiza de la Migracion

Cuando tienes dos mundos (viejo y nuevo) que deben coexistir, el symlink permite una transicion transparente. Cero procesos rotos, cero configs actualizadas manualmente. Es la solucion mas simple, mas robusta, y mas subestimada en el toolkit de un ingeniero.

### Leccion 10: Free Tier Cloud es Infraestructura Real

Oracle Cloud ARM free tier no es un juguete. 4 OCPUs Ampere A1 con 24GB RAM es mas potente que muchos VPS pagos de $50/mes. El unico costo es la paciencia para conseguir capacidad (el script grabber) y el tiempo de configuracion de networking. Para un proyecto de un solo desarrollador, es infraestructura de produccion legitima a costo cero.

### Leccion 11: Separar Desarrollo de Produccion Desde el Dia Uno

El Mac es para crear. El VPS es para ejecutar. Mezclar ambos roles en una sola maquina crea dependencias fragiles: el bot se cae cuando reinicias para actualizar macOS, el dashboard desaparece cuando cierras la laptop, el mesh se detiene cuando cambias de WiFi. La separacion no es un lujo — es higiene de infraestructura.

### Leccion 12: Audita Tus Proveedores Regularmente

APIs expiran, modelos se deprecan, nombres cambian. El error `404 model_not_found` de Cerebras por un nombre de modelo obsoleto podia haberse detectado con una auditoria semanal automatizada. El DOF ya tiene `scripts/model_audit.py` — hay que correrlo como cron job, no como accion manual.

---

## 19.10 Estado al Final del Dia

| Componente | Estado |
|---|---|
| Mission Control | ELIMINADO (malware) |
| Wallet 0x2cF7 | RECUPERADA |
| 5 bugs criticos | REPARADOS (paralelo) |
| Directorio unificado | SYMLINK activo |
| Proveedores | DeepSeek default, 3/5 activos |
| Mesh multi-modelo | 11 agentes, paralelo funcionando |
| Oracle Cloud | Cuenta activa, red configurada, grabber corriendo |
| Arquitectura Mac+VPS | DEFINIDA y documentada |

El 26 de marzo fue el dia que el DOF dejo de ser un proyecto que vive en un laptop. Ahora tiene infraestructura real, soberania sobre sus claves, y una arquitectura de dos ambientes que puede escalar. Todo en una sesion.

---

*Capitulo 19 escrito por Juan Carlos Quiceno Vasquez — DOF Cloud Sovereignty, 26 de marzo de 2026*
