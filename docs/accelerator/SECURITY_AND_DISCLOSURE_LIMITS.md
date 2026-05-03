# DOF-MESH — Security and Disclosure Limits

## 1. Propósito del documento

Este documento define qué información de DOF-MESH puede compartirse con mentores, evaluadores, aliados institucionales y posibles clientes, y qué información debe mantenerse privada. Su objetivo es permitir una presentación profesional del proyecto en etapa de preincubación sin exponer información sensible, detalles explotables ni elementos que aumenten el riesgo técnico, operativo o de seguridad.

## 2. Información que sí puede compartirse

Puede compartirse información de nivel institucional, estratégico y funcional que permita explicar el proyecto sin revelar componentes sensibles. Esto incluye:

- Qué es DOF-MESH: una capa de gobernanza determinística para agentes de inteligencia artificial autónomos.
- Su propósito general: verificar acciones críticas antes de su ejecución y generar evidencia auditable.
- El problema que aborda: riesgo operativo, opacidad y falta de trazabilidad cuando agentes de IA ejecutan acciones sensibles.
- La propuesta de solución en términos de alto nivel: una acción crítica es propuesta por un agente, evaluada por reglas de gobernanza, verificada y registrada antes de ejecutarse.
- El diferenciador conceptual: separación entre razonamiento del agente, autorización de la acción, verificación determinística y evidencia auditable.
- El enfoque de mercado inicial: organizaciones institucionales o empresariales donde la confianza, la supervisión y el cumplimiento sean relevantes.
- El objetivo de preincubación en Créame / Ruta N: preparación para validación y pilotos institucionales o empresariales.
- Métricas globales ya definidas para uso externo:
  - 173 módulos
  - 4802-test collection
  - 9 chains
  - Z3 4/4 PROVEN
  - Digital Bunker Nivel 5
  - Fase 4.5

## 3. Información que no debe compartirse

No debe compartirse información que exponga la operación interna, la superficie técnica o componentes aprovechables por terceros. Esto incluye de forma explícita:

- Archivos `.env`.
- Llaves privadas.
- Wallets.
- Tokens.
- Endpoints privados.
- Rutas locales reales.
- Lógica profunda de cooldown.
- Detalles explotables de Z3.
- Configuración sensible.

Tampoco deben compartirse explicaciones técnicas que revelen mecanismos internos de control, verificación o protección más allá de un nivel conceptual. Si un detalle permite inferir cómo se implementan, limitan o eluden los controles, debe considerarse privado.

## 4. Criterios para demos externas

Las demos externas deben centrarse en la propuesta de valor, el flujo funcional de alto nivel y el problema que DOF-MESH resuelve. Deben evitar cualquier exposición de credenciales, configuraciones reales, rutas internas, integraciones privadas o detalles técnicos profundos.

Una demo externa es aceptable si:

- muestra el concepto de gobernanza previa a la ejecución;
- ilustra el valor de la trazabilidad y la evidencia auditable;
- usa lenguaje de alto nivel y no operativo;
- no revela información sensible ni patrones técnicos explotables.

Si una demo requiere mostrar detalles internos para ser entendida, el alcance de la demo debe reducirse.

## 5. Criterios para documentos públicos

Los documentos públicos deben mantener un nivel ejecutivo o funcional. Deben explicar la tesis, el problema, la solución, la diferenciación, el estado general del proyecto y la oportunidad de validación, pero sin incluir diseño interno sensible ni especificaciones profundas.

Un documento público debe:

- ser entendible para actores no técnicos y técnicos;
- priorizar claridad institucional sobre detalle técnico;
- usar métricas globales y narrativa estratégica;
- excluir información operativa, credenciales, rutas, configuraciones y detalles explotables.

## 6. Reglas para conversaciones con aliados

En conversaciones con mentores, evaluadores, aliados o posibles clientes, la regla base es compartir primero el qué, el porqué y el valor de DOF-MESH, antes que el cómo interno.

Se puede hablar de:

- el problema de gobernanza en agentes de IA;
- la necesidad de verificación previa y evidencia auditable;
- el enfoque de mercado inicial;
- el interés en pilotos institucionales o empresariales.

No se debe entrar en detalles que expongan mecanismos internos, configuraciones sensibles o información reservada. Si un aliado solicita mayor profundidad técnica, la divulgación debe mantenerse en alto nivel mientras no exista un contexto formal adecuado para ampliar acceso.

## 7. Principio general de seguridad

El principio general es de divulgación mínima suficiente: compartir únicamente la información necesaria para explicar valor, madurez y oportunidad de DOF-MESH, sin revelar nada que comprometa seguridad, operación o ventaja técnica sensible.

Cualquier duda debe resolverse con un criterio conservador. Si una información no es indispensable para presentar el proyecto en preincubación, no debe compartirse.
