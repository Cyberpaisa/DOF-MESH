# DOF-MESH — Demo Payload Guide

## 1. Propósito del documento

Este documento define cómo ejecutar la demo mínima de mentoría de DOF-MESH sin confundir el rol del SDK con el rol de la API. Su objetivo es evitar una demostración inconsistente y asegurar que el flujo mostrado sea prudente, comprensible y técnicamente correcto.

## 2. Diferencia entre SDK y API

El SDK y la API no reciben exactamente el mismo tipo de entrada:

- **SDK**: recibe una acción estructurada, por ejemplo `agent_id`, `action` y `params`.
- **API `/api/v1/governance/verify`**: evalúa `output_text` ya formulado como texto gobernable.

En otras palabras, el SDK está orientado a verificar una acción; el endpoint de gobernanza está orientado a revisar una salida textual.

## 3. Payload API correcto para demo

Payload recomendado para demo mínima:

```json
{
  "output_text": "[APPROVED] Agent mentor-demo-001 executing transfer(amount=500, token=USDC). Z3 proof: 4/4 VERIFIED [GCR_INVARIANT:VERIFIED]."
}
```

Resultado verificado:

- `status: pass`
- `hard_violations: []`
- `score: 1.0`

Este payload es coherente con el estilo textual que construye internamente el SDK cuando verifica una acción.

## 4. Payload API que no conviene usar

Payload no recomendado para demo:

```json
{
  "output_text": "Agent mentor-demo-001 proposes transfer amount=500 token=USDC. Source: internal test context."
}
```

Resultado verificado:

- `status: fail`
- hard violation principal: `LANGUAGE_COMPLIANCE`

## 5. Por qué el payload inicial falló

El payload inicial falló porque el endpoint de gobernanza no interpreta acciones estructuradas; interpreta texto ya redactado. La regla `LANGUAGE_COMPLIANCE` exige que la respuesta esté en inglés o cumpla cierta heurística de texto estructurado.

El SDK evita ese problema porque arma internamente un texto consistente antes de pasarlo por gobernanza. La API, en cambio, evalúa directamente el `output_text` entregado.

## 6. Cómo explicar esto a mentores

La explicación recomendada es simple:

- el SDK demuestra verificación de acciones estructuradas;
- la API de gobernanza demuestra revisión de salidas textuales;
- ambos son coherentes si se usa el formato adecuado para cada superficie.

No conviene decir que ambos endpoints aceptan exactamente el mismo input. Hoy no es la mejor forma de describir el sistema.

## 7. Demo recomendada paso a paso

1. Mostrar `python3 -m dof version`.
2. Mostrar `python3 -m dof health`.
3. Mostrar `python3 -m dof prove`.
4. Ejecutar `DOFVerifier.verify_action(...)` con una acción tipo `transfer`.
5. Mostrar en la salida:
   - `verdict`
   - `z3_proof`
   - `governance_passed`
   - `attestation hash`
6. Ejecutar la API local con `TestClient` sobre:
   - `/api/v1/health`
   - `/api/v1/z3/verify`
   - `/api/v1/governance/verify` usando el payload correcto de este documento

## 8. Límites: qué no afirmar todavía

No afirmar todavía que:

- SDK y API son equivalentes para cualquier payload;
- todas las superficies del sistema están totalmente alineadas;
- la plataforma completa está consolidada en todas sus capas.

La demo debe presentarse como validación mínima y controlada del núcleo defendible, no como demostración integral del repositorio completo.
