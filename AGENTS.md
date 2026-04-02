# Constitución del Equipo: DOF Mesh Agentes (Context Engineering)

Este documento es el activo fundacional de contexto para todos los agentes de software que operan en este repositorio, conforme a las mejores prácticas de **Context Engineering y Spec-Driven Development**. 

Esta constitución dicta reglas inmutables de comportamiento y estilo arquitectónico.

## 1. Reglas Generales de Arquitectura
- **Soberanía First:** Las aplicaciones y los flujos nunca deben depender exclusivamente de APIs cerradas sin un fallback de inferencia open-source (ej. MLX/Ollama).
- **Inmutabilidad y Silencio:** El código debe fallar rápida y ruidosamente si el contexto es corrompido, pero ser silencioso en operaciones exitosas (Unix Philosophy).
- **Verbosidad Controlada:** No generar código boilerplate innecesario. Utilizar abstracciones puras y DRY sin llegar a un acoplamiento excesivo.

## 2. Desarrollo Orientado a Específicaciones (SDD)
Los agentes deben tratar los archivos de planificación (`implementation_plan.md`, `task.md`) como **contratos ejecutables inderogables**.
- Si una instrucción ambigua en un prompt contradice el `implementation_plan.md`, **el plan tiene absoluta prioridad.**
- Si el contexto se degrada (*Context Rot*), el agente debe solicitar clarificación al Soberano antes de alucinar código.
- Los tests no son solo para evitar bugs; son la definición ejecutable de lo que está prohibido para la IA (Músculos vs. Restricciones).

## 3. Integración Conflux (Global Hackfest)
- Todas las redes EVM nuevas asumen compatibilidad al 99%, pero para Conflux eSpace se asumen excepciones críticas (límite de 49KB, opcode `NUMBER` basado en épocas).
- **Obligatoriedad Gasless:** Toda DApp construida en este repositorio debe aspirar a usar `SponsorWhitelistControl` para absorber los costos de los usuarios.

## 4. Estilo de Código y Linting
- Python: `ruff` para linting estricto, type hints obligatorios (`-> bool`, `: str`).
- Javascript/TypeScript: ECMAScript moderno, evite clases a menos que sea necesario para la herencia estricta. Uso preferido de `async/await` puro con capturas de error explícitas (no tragar errores).

## 5. Seguridad de Supply Chain (Anti-Stealer)
- **Pinning Inexorable:** Queda estrictamente prohibido referenciar dependencias de Terceros (GitHub Actions, paquetes npm/pip) mediante Tags de versión (`@v1`, `@latest`). **Uso obligatorio de SHA completo.**
- **No Hermeticidad:** Ningún nodo del Mesh debe realizar conexiones salientes no autorizadas. Las llaves de API deben estar segregadas y rotadas mensualmente.
- **Inmunidad LiteLLM:** Uso exclusivo de modelos validados localmente o vía proxies propios con filtrado de secretos.

*Este archivo es inyectado por defecto al inicio de cada sesión como Nivel 1 de Disclosure.*

## 6. Estándar Agent-First CLI (Obligatorio desde Phase 4)

Todo script o herramienta nueva del repositorio debe ser invocable tanto por humanos como por agentes autónomos sin modificar el código.

### Reglas Inderogables
- **`--json` en todo comando que produzca datos.** La salida debe ser NDJSON válido cuando el flag está activo.
- **Detección automática de audiencia:** `sys.stdout.isatty()` y `NO_COLOR` env var determinan si se activa TUI (humano) o NDJSON puro (agente/pipe).
- **Exit codes semánticos:** `0`=éxito, `1`=error general, `2`=flags inválidos, `3`=auth failure. Nunca retornar `0` en un fallo.
- **`Hint:` en cada excepción:** Los agentes parsean estas líneas para auto-corregirse sin intervención humana.
- **Context Window Protection:** Ocultar API keys y payloads completos por defecto. Usar `--verbose` como opt-in explícito.
- **Stateless:** El CLI es transporte puro. El estado vive en el backend (IDs de referencia, no sesiones en memoria del proceso).

### Proveedor de Inferencia Local
El fallback soberano del equipo es **oMLX** (`localhost:8080/v1`), no Ollama standalone.
Variables obligatorias en `.env` para activar el fallback:
```
OMLX_BASE_URL=http://localhost:8080/v1
OMLX_MODEL=llama3.3-70b
```
Ningún componente del MESH debe hacer Fail-Open hacia una API externa si oMLX está disponible.

## 7. Prevención de Context Rot (Capa 7 Oracle)
Todo agente debe consultar **Context7** (vía MCP) cuando trabaje con APIs externas como Conflux, Adaline, etc. Está PROHIBIDO alucinar parámetros de APIs modernas o asumir información posterior a la fecha de corte del modelo. 
El conocimiento extraído debe documentarse localmente.
