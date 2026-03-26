---
paths:
  - "scripts/phase11_*"
  - "data/extraction/*"
---
# Reglas de Extracción (Coliseo)

- **Elicitación No-Destructiva:** Los juegos del Coliseo deben diseñarse para provocar filtraciones técnicas sin activar los filtros de seguridad del proveedor.
- **Validación Cruzada:** Toda inteligencia extraída debe ser validada por al menos dos agentes (Researcher + Architect).
- **Integridad de la Bóveda:** Los datos en `data/extraction/` deben ser inmutables después de la síntesis inicial.
- **Evolución Controlada:** Solo el `local-agi-m4max` tiene permiso para aplicar cambios de código basados en inteligencia extraída.
