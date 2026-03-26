---
paths:
  - "core/qaion_*"
  - "scripts/simulate_qaion_*"
---
# Reglas de Soberanía Q-AION

- **Hardware First:** Toda validación crítica debe pasar por el `M4MaxProAccelerator`.
- **Consenso Obligatorio:** Ninguna acción de ruteo se considera final sin un quórum del 66% en el `ConsensusEngine`.
- **ZKP Attestation:** Cada resultado de experto debe llevar una firma ZKP generada en Metal.
- **Identidad Protegida:** Las llaves privadas residen en el Secure Enclave; no se permite su exportación ni visualización en logs.
