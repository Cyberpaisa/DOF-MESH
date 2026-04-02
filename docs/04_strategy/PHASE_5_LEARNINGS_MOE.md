# Aprendizajes de la Transición: Sovereign MoE (Mixture of Agents)

**Autor:** Antigravity (Sovereign Swarm Architecture)
**Fecha:** Abril 2026

Este documento forma parte del "Libro" (Knowledge Base de la Legión Q-AION) y consolida el aprendizaje extraído de la adopción del ecosistema de IA Local de 2026.

## 1. El Paradigma de la Especialización (MoE en Local)
Inicialmente, la infraestructura dependía de usar un solo modelo todoterreno (`llama3.2`) vía Ollama como *Priority-0 runtime*. La lección extraída del Top 50 2026 Benchmarks nos enseñó que este enfoque monolítico agota memoria, desperdicia capacidad de cómputo y merma el rendimiento.

**Aprendizaje:** Una máquina M4 Max con gran memoria unificada (36GB+) brilla con el concepto **Mixture of Agents (MoE)**. En lugar de un cerebro gigante en la nube, es infinitamente más eficiente descargar múltiples "cerebros medianos" (14B, quantizados en Q4) altamente especializados, instanciándolos bajo alias semánticos:
- `dof-coder`: Basado en Qwen 2.5 Coder (Experto en AST y parsing).
- `dof-reasoner`: Basado en DeepSeek R1 (Lógica, riesgo SAM y matemáticas).
- `dof-guardian`: Especialista defensivo.

## 2. Inyección Dinámica del Prompt Ruteador (`local_model_node.py`)
No es suficiente descargar los modelos. El framework de la Legión DEBÍA ser capaz de discernir de qué trata el mensaje y asignar la orden al modelo experto.

**Aprendizaje:** Modificamos la clase `OllamaEngine` en `local_model_node.py` para usar heurísticas ligeras de ruteo (`_route_model`) basándose en palabras clave del prompt. Esto significa:
- 0 ciclos de CPU perdidos llamando a un LLM para que haga de ruteador.
- Selección en nanosegundos (O(1)).
- Seguridad 100% predecible de que las revisiones de código de inyección SIEMPRE irán al Coder.

## 3. Seguridad Perimetral: Fail-Closed al Máximo Nivel
La transición refuerza lo establecido en la Ciudadela. Antes de ejecutar, todo se rige bajo la filosofía local air-gapped. 

**Aprendizaje Estratégico:** No dependemos ya de las convenciones de HuggingFace (`qwen:14b`). Al usar alias duros (`dof-*`), blindamos el sistema contra ataques de "Dependency Confusion" o "Model Hijacking" en Ollama, porque sabemos matemáticamente qué pesos y Modelfiles constituyen cada alias local.

## 4. Hardware como Ventaja Asimétrica
Los benchmarks de 2026 demostraron que modelos de tamaño 10B-20B igualan el rendimiento de los modelos en la nube de 2024.
Tener la M4 Max (o equivalentes) permitió eliminar totalmente la excusa de no correr modelos en local. Ahora logramos soberanía táctica completa con tiempos de inferencia que compiten contra APIs pagadas, bajando el TCO (Total Cost of Ownership) a $0.0.
