# 🛡️ Pilar 3: Laboratorio Defensivo Soberano (V7.2 OrbStack)

> [!NOTE]
> **Estado:** Configuración Validada para Laboratorio Soberano.
> Este entorno ha sido auditado para garantizar la contención de red y la integridad de la cadena de suministro.

## ⚠️ Advertencia de Recursos (RAM)
La configuración híbrida utiliza el motor de inferencia local Ollama.
- **Modelo Estándar (phi4):** Consumo ~9GB RAM. Uso seguro en paralelo.
- **Modelo Contingencia (30B MoE):** Consumo ~18-20GB RAM. 
  - **REGLA OPERATIVA:** Cerrar aplicaciones pesadas (Navegadores, IDEs) antes de usar el flag `--unrestricted`.
  - **Riesgo:** El uso simultáneo puede provocar swap masivo o inestabilidad del sistema.

## 🧱 Arquitectura de Contención
- **Aislamiento:** Red Docker `internal: true`. Sin gateway, sin DNS externo.
- **Integridad:** Imágenes pinnadas por SHA256 digest.
- **Inteligencia:** Agente `security_analyst.py` con capa de sanitización y licencia defensiva.

## 🚀 Despliegue (OrbStack)
1. Iniciar OrbStack.
2. `cd core/redteam && docker compose -f docker-compose.lab.yml up -d`
3. Verificar con `bash verify_lab.sh`.

## Principios de diseño
- **Soberanía total:** Ningún componente necesita internet una vez configurado.
- **Mínimo privilegio:** Ollama y los targets corren bajo usuario no-root.
- **Aislamiento triple:** VM (UTM) → Red interna Docker → security_analyst.py sin ejecución autónoma.
- **El operador manda:** El agente solo analiza. Los comandos de exploración los ejecutas tú.

## Componentes

| Archivo | Propósito |
|---------|-----------|
| `provision_vm.sh` | Setup inicial de la VM Ubuntu ARM64 |
| `export_model.sh` | Exportar modelo dof-coder del host a la VM |
| `docker-compose.lab.yml` | Targets vulnerables (Juice Shop + WebGoat) |
| `.env.lab.example` | Plantilla de credenciales (nunca versionar `.env.lab`) |
| `security_analyst.py` | Agente de análisis defensivo (sin ejecución ofensiva) |
| `verify_lab.sh` | Healthcheck completo del entorno |
| `runbook.md` | Flujo operativo completo paso a paso |
| `.gitignore` | Excluye .pcap, .gguf, .env, imágenes de VM |

## Uso rápido

```bash
# Ver runbook completo
cat runbook.md

# Verificar estado del lab
bash verify_lab.sh

# Analizar un scan
python3 security_analyst.py --input /tmp/scan.txt --target 10.10.10.10
```

## Arquitectura

```
UTM VM (air-gapped)
├── Ollama: dof-coder (localhost:11434)
└── lab_net (10.10.10.0/24, sin gateway)
    ├── Juice Shop 17.2.1  → :3000
    └── WebGoat 2023.8    → :8080
```

> ⚠️ **Advertencia ARM64:** WebGoat 2023.8 puede no tener imagen nativa ARM64.
> Verificar con `docker manifest inspect webgoat/webgoat:2023.8 | grep architecture`
> antes del primer despliegue. Bajo emulación Rosetta es funcional pero más lento.

## Línea ética
Este laboratorio es exclusivamente para análisis **defensivo** (Blue Team).
Ver `AGENTS.md` §3 (Pilar 3) para las reglas de gobernanza completas.
