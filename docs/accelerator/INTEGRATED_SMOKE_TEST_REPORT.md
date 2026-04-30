# DOF-MESH — Integrated Smoke Test Report

## 1. Propósito del smoke test

Este smoke test tuvo como propósito validar un flujo integrado mínimo de DOF-MESH en entorno local y controlado, combinando SDK, CLI y API básica, sin despliegues ni exposición pública. La intención fue confirmar si el núcleo defendible del proyecto puede demostrarse de manera prudente antes de conversaciones de mentoría o incubadora.

## 2. Alcance

El alcance de esta validación fue deliberadamente reducido al núcleo técnico ya considerado defendible:

- SDK público mediante `DOFVerifier`
- CLI principal
- API local en `api.server` usando `FastAPI TestClient`

No se validó el repositorio completo, ni integraciones externas, ni despliegues, ni contratos en red, ni la totalidad de la suite.

## 3. Comandos ejecutados

Se ejecutaron los siguientes comandos y pruebas locales:

- `git status --short`
- `python3 -m dof version`
- `python3 -m dof health`
- `python3 -m dof prove`
- smoke test SDK con `DOFVerifier.verify_action(...)`
- smoke test local de API con `FastAPI TestClient` sobre:
  - `/api/v1/health`
  - `/api/v1/governance/verify`
  - `/api/v1/z3/verify`

## 4. Resultado SDK

El smoke test del SDK se ejecutó mediante `DOFVerifier.verify_action` con una acción simple tipo `transfer`.

Resultado verificado:

- `verdict` → `APPROVED`
- `governance_passed` → `True`
- `violations` → `[]`
- `z3_proof` → `4/4 VERIFIED`
- se generó `attestation hash`

Este resultado confirma que la superficie pública mínima del SDK puede procesar una acción propuesta, aplicar verificación formal, evaluar gobernanza y devolver una salida estructurada con evidencia auditable.

## 5. Resultado CLI

Los resultados verificados de CLI fueron:

- `python3 -m dof version` → `dof-sdk 0.8.0`
- `python3 -m dof health` → `16/16 available`
- `python3 -m dof prove` → `All verified: True`

La verificación formal por CLI reportó 4 teoremas en estado `VERIFIED`, reforzando la consistencia del núcleo formal mínimo expuesto al usuario.

## 6. Resultado API/TestClient

La API local se probó sin levantar servidor público, usando `FastAPI TestClient`.

Resultados verificados:

- `/api/v1/health` → `200`
  - `status: ok`
  - `version: 0.8.0`
  - `tests: 350`
  - `modules: 30`

- `/api/v1/governance/verify` → `200`
  - respuesta estructurada
  - `status: fail`
  - causa principal visible: `LANGUAGE_COMPLIANCE`

- `/api/v1/z3/verify` → `200`
  - `all_verified: True`
  - `count: 4`

Esto confirma que la API básica importa, responde localmente y devuelve resultados estructurados en los endpoints mínimos probados.

## 7. Qué flujo sí es demostrable

Sí es demostrable, en entorno local y controlado, el siguiente flujo conceptual:

1. una acción es propuesta;
2. el SDK la verifica y devuelve veredicto, prueba Z3 y hash auditable;
3. la CLI permite mostrar versión, salud de componentes y verificación formal;
4. la API local responde con estado, verificación formal y evaluación estructurada de gobernanza.

En términos de preincubación, esto permite demostrar que DOF-MESH no es solo narrativa conceptual, sino que cuenta con una superficie funcional mínima y coherente en sus componentes principales ya validados.

## 8. Alertas encontradas

Se identificaron dos alertas relevantes:

- **Desalineación entre SDK y API para una intención similar**:
  - el SDK aprobó la acción `transfer`;
  - la API devolvió `fail` en gobernanza para el payload probado, principalmente por `LANGUAGE_COMPLIANCE`.

- **Desalineación entre métricas de `/health` y narrativa pública más amplia**:
  - el endpoint local reporta `tests: 350` y `modules: 30`;
  - estas cifras no coinciden de forma directa con la narrativa global más amplia usada en otros materiales del proyecto.

Estas alertas no invalidan el smoke test, pero sí indican que todavía no debe comunicarse el sistema como una superficie completamente homogénea en todos sus puntos de entrada.

## 9. Qué no se debe mostrar todavía

No conviene mostrar todavía:

- una plataforma completamente consolidada en todas sus capas;
- la totalidad del repositorio como si tuviera el mismo nivel de madurez;
- claims de alineación total entre SDK, API y demás superficies;
- componentes periféricos, experimentales o históricos como si fueran producto central validado;
- cualquier narrativa que mezcle el núcleo defendible con demos, gaming, research amplio o material no revalidado.

La presentación institucional debe concentrarse en el núcleo probado y en una demostración corta, controlada y prudente.

## 10. Próximas correcciones recomendadas

Antes de una exposición más amplia, se recomienda:

- alinear mejor la lógica o el payload esperado entre SDK y endpoint de gobernanza;
- revisar qué debe reportar el endpoint `/health` para no generar contradicciones narrativas;
- definir un smoke test oficial y repetible para uso en mentoría interna;
- mantener la demo centrada en SDK, CLI, verificación formal y API básica local;
- seguir separando con disciplina el core defendible del material experimental o histórico.

## Conclusión

El smoke test integrado mínimo confirma que DOF-MESH puede demostrarse de forma controlada en entorno local a través de SDK, CLI y API básica. La demostración es suficiente para sostener una conversación prudente de preincubación, siempre que se presente como validación mínima del núcleo y no como evidencia de consolidación total del ecosistema completo.
