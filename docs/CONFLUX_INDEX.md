# 🕸️ Índice Técnico Conflux (Legion Mesh)

Este documento es el repositorio central de inteligencia sobre la red **Conflux (eSpace & Core)**. Ha sido compilado para asegurar que todos los nodos de la Legion tengan acceso inmediato a la documentación oficial y a las mejores prácticas de implementación gasless.

## 1. Documentación Oficial y Gateways
- **Overviews:**
    - [Conflux General Overview](https://doc.confluxnetwork.org/docs/overview)
    - [Core Space Docs](https://doc.confluxnetwork.org/docs/core/Overview)
    - [eSpace Docs (EVM)](https://doc.confluxnetwork.org/docs/espace/Overview/)
- **RPCs y Endpoints:**
    - [eSpace Network Endpoints](https://doc.confluxnetwork.org/docs/espace/network-endpoints)
    - [Core RPC Endpoints](https://doc.confluxnetwork.org/docs/core/conflux_rpcs)

## 2. Pilares de la Legion en Conflux
### ⛽ Automatización de Patrocinio (Gasless)
- **Concepto Core:** [Sponsorship Mechanism](https://doc.confluxnetwork.org/docs/core/core-space-basics/internal-contracts/)
- **Contrato Interno:** `0x0888000000000000000000000000000000000001` (SponsorWhitelistControl).
- **Guía de Implementación:** Ver [skills/conflux-integration/SKILL.md](../skills/conflux-integration/SKILL.md).

### 🛠️ Tooling y Despliegue
- **Quickstart eSpace:** [Developer Quickstart](https://doc.confluxnetwork.org/docs/espace/DeveloperQuickstart)
- **Deployment Hub:** [Hardhat & Foundry](https://doc.confluxnetwork.org/docs/espace/tutorials/deployContract/hardhatAndFoundry)
- **Verificación:** [ConfluxScan API](https://api.confluxscan.org/doc)

## 3. Seguridad y Alertas (Supply Chain)
- **⚠️ Alerta LiteLLM:** Ver [scripts/broadcast_security_alert.py](../scripts/broadcast_security_alert.py).
- **Directiva:** Rotación obligatoria de llaves si se utilizaron herramientas de escaneo no pinneadas (Trivy/Checkmarx).
- **Referencia Externa:** [LiteLLM Supply Chain Attack Audit](https://paila.news/articles/litellm-paila/)

## 4. Recursos Adicionales (Hackathon Context)
- **Foro de Grants:** [forum.conflux.fun](https://forum.conflux.fun/c/English/grant-proposals)
- **Ecosistema:** [Conflux Ecosystem Projects](https://confluxnetwork.org/ecosystem)

---
*Índice generado por Antigravity para el Soberano de la Legion.*
