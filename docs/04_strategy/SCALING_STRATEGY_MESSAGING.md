# DOF Mesh — Estrategia de Escalado a 500 Nodos

## Análisis Comparativo: Kafka vs NATS vs Redis Streams

### Recomendación: NATS Core/JetStream (NO Kafka)

**Razón:** Kafka es overkill insostenible. Para 500 nodos:
- Overhead: Kafka requiere Zookeeper + brokers + storage distribuido
- Complejidad operativa: 10+ componentes
- Costo: 3-5x más que NATS

**Solución recomendada:**
1. **NATS Core** para messaging inmediato (< 100ms latencia)
2. **JetStream** para persistencia (si se requiere replay)
3. **Redis Streams** como fallback si ya operan Redis

### Roadmap de Implementación (3-4 semanas)

**Semana 1:** Deployment de NATS cluster (3 nodos)
**Semana 2:** Migración MessageBus → NATS publishers
**Semana 3:** Testing y optimización
**Semana 4:** Rollout a producción con monitoreo

### Benchmarks Esperados
- Latencia: 50-100ms (vs 200-400ms con Kafka)
- Throughput: 100K msg/sec (vs 50K con Kafka)
- Memory: 2GB (vs 8GB con Kafka)

### Próximos pasos:
1. Aprobar NATS como arquitectura de mensajería
2. Proceder a Fase 2: Implementación de componentes
3. Preparar cluster de testing

Quedo a la espera de instrucciones para iniciar Fase de Arquitectura V2.
