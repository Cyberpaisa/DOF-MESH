# DOF-MESH — Canonical Scope

## 1. Propósito del documento

Este documento define el alcance canónico de DOF-MESH para preincubación. Su función es separar con claridad qué debe considerarse producto actual, qué constituye el núcleo defendible, qué componentes deben tratarse como experimentales o periféricos, qué elementos pertenecen a etapas históricas y qué no debe presentarse todavía como validado.

El objetivo es reducir ambigüedad en conversaciones con mentores, evaluadores, aliados y posibles clientes institucionales o B2B.

## 2. Fuente canónica del proyecto

Para fines de preincubación, la fuente canónica del proyecto es el repositorio actual **Cyberpaisa/DOF-MESH**. Este debe tratarse como la versión principal del trabajo, tanto para narrativa institucional como para validación técnica mínima.

La tesis canónica del proyecto, con base en `PROJECT_BRIEF.md`, es la siguiente:

- DOF-MESH es una capa de gobernanza determinística para agentes de inteligencia artificial autónomos.
- Su propósito es verificar acciones críticas antes de su ejecución y generar evidencia auditable.
- Su valor central está en separar razonamiento del agente, autorización de la acción, verificación determinística y evidencia auditable.

## 3. Relación con el repositorio anterior

El repositorio anterior **Cyberpaisa/deterministic-observability-framework** debe entenderse como antecedente técnico e histórico del proyecto, no como referencia canónica de presentación para incubadora.

Esto implica:

- puede servir como base histórica de evolución;
- puede contener material útil para rastrear arquitectura, research o versiones previas;
- no debe usarse como fuente principal para claims actuales;
- no debe competir narrativamente con el repositorio actual.

En términos de presentación, DOF-MESH debe mostrarse como la evolución más completa y vigente del trabajo, mientras que el repositorio anterior debe tratarse como etapa previa del desarrollo.

## 4. Relación con el sitio público

El sitio público **https://www.dofmesh.com/** debe considerarse narrativa pública del proyecto, no fuente técnica principal ni evidencia primaria de validación.

Esto significa:

- sirve para posicionamiento, comunicación externa y marca;
- puede ayudar a alinear el mensaje institucional;
- no sustituye documentación técnica interna ni validación funcional;
- no debe ser usado como prueba suficiente de madurez técnica.

Para incubadora, la evidencia debe apoyarse primero en documentación canónica y validación funcional mínima del núcleo.

## 5. Core defendible actual

Con base en el `PROJECT_BRIEF.md`, el mapa contextual del repositorio y las validaciones funcionales recientes, el core defendible actual de DOF-MESH es:

- el SDK/paquete Python `dof`;
- la CLI principal;
- los módulos de gobernanza determinística;
- la verificación formal mínima con Z3;
- el pipeline de `tool_hooks` para control previo;
- la API básica en `api.server`, después de la corrección mínima de import;
- la narrativa de control previo, trazabilidad y evidencia auditable.

Este núcleo sí cuenta con evidencia funcional mínima reciente:

- `python3 -m dof version` → `dof-sdk 0.8.0`
- `python3 -m dof health` → `16/16 components available`
- `python3 -m dof prove` → `All verified: True`
- `api.server` import → correcto después del fix
- `tests/test_api.py` → `17 passed`
- tests núcleo SDK/governance/Z3/tool_hooks → `113 passed`

Por tanto, para preincubación, DOF-MESH puede presentarse de forma prudente como una capa funcional de gobernanza determinística para agentes de IA con núcleo validado en SDK, CLI, verificación formal mínima y API básica.

## 6. Componentes experimentales o periféricos

Deben tratarse como experimentales, accesorios o no centrales para la conversación de incubadora:

- frontend web como componente secundario frente al núcleo técnico;
- `video-render`, demos y assets audiovisuales;
- estrategias de entretenimiento o gamificación como `DOF Match`;
- integraciones específicas que no formen parte del mensaje central;
- scripts de benchmarking, monitoring, deploy y experiments;
- extensiones avanzadas de mesh, multichain o flujos de investigación que no hayan sido revalidadas en esta etapa.

Estos componentes pueden ser útiles en etapas posteriores, pero no deben desplazar la narrativa principal del producto.

## 7. Componentes históricos o de referencia

Deben tratarse como históricos, de soporte o de referencia:

- el subárbol `deterministic-observability-framework/`, si permanece dentro del repositorio actual;
- snapshots, mirrors o duplicados del trabajo previo;
- documentación extensa de research, sesiones y exploraciones pasadas;
- backups, outputs, reportes históricos y material acumulado no canónico.

Su utilidad principal es interna: trazabilidad, memoria técnica o recuperación de contexto. No son la mejor superficie para evaluación institucional.

## 8. Qué se puede presentar ante incubadora

Sí puede presentarse ante incubadora:

- DOF-MESH como evolución canónica y actual del proyecto;
- la tesis de gobernanza determinística para agentes autónomos;
- el problema que resuelve: riesgo, opacidad y falta de trazabilidad en acciones sensibles;
- la solución en alto nivel: propuesta, gobernanza, verificación y evidencia antes de ejecución;
- el núcleo técnico validado mínimamente: SDK, CLI, Z3, `tool_hooks`, API básica;
- las métricas globales del brief, siempre tratadas con prudencia y sin descender a detalles sensibles;
- el objetivo de preparación para pilotos institucionales o empresariales.

## 9. Qué no debe presentarse todavía

No debe presentarse todavía como validado:

- la totalidad del repositorio como si tuviera el mismo nivel de madurez;
- componentes experimentales o periféricos como si fueran core de producto;
- claims de plataforma integral completamente consolidada;
- despliegues, integraciones o superficies no revalidadas en esta fase;
- elementos históricos como si fueran producto vigente;
- detalles sensibles, configuraciones privadas o información explotable.

Tampoco conviene mezclar en una misma narrativa el core defendible con demos, gaming, research amplio, histórico duplicado y piezas accesorias. Eso diluye el posicionamiento.

## 10. Criterio para futuras decisiones de producto

La regla canónica para decisiones futuras debe ser:

- un componente pertenece al producto actual si refuerza la tesis central de gobernanza determinística previa a la ejecución;
- un componente es defendible si tiene función clara, encaje con la narrativa principal y validación mínima verificable;
- un componente es experimental si amplía el alcance pero no es necesario para explicar valor inmediato;
- un componente es histórico si ayuda a entender evolución, pero no mejora la claridad del producto actual;
- si un elemento no es indispensable para explicar valor, madurez o preparación para pilotos, no debe ocupar espacio principal en preincubación.

## Conclusión

Para preincubación, DOF-MESH debe presentarse como la versión canónica, actual y más completa del proyecto. Su narrativa debe centrarse en el núcleo defendible ya validado mínimamente: gobernanza determinística para agentes, verificación previa a ejecución, evidencia auditable y una superficie funcional concreta en SDK, CLI, Z3, `tool_hooks` y API básica.

Todo lo demás debe clasificarse con disciplina como experimental, periférico o histórico, y mantenerse fuera del mensaje principal hasta que exista una validación adicional que justifique su incorporación.
