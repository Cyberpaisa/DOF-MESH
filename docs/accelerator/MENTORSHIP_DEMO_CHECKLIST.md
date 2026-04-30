# DOF-MESH — Mentorship Demo Checklist

## 1. Antes de la mentoría

- Confirmar que la narrativa principal sea: gobernanza determinística previa a ejecución para agentes de IA.
- Preparar una demo corta, local y controlada.
- Evitar abrir el repositorio completo durante la sesión.
- Tener claro qué está validado y qué todavía no.
- Revisar el 8 de mayo con una única historia: problema, solución, núcleo validado, siguiente paso.

## 2. Archivos que se deben tener listos

- `docs/accelerator/ONE_PAGER.md`
- `docs/accelerator/EXECUTIVE_SUMMARY.md`
- `docs/accelerator/HIGH_LEVEL_ARCHITECTURE.md`
- `docs/accelerator/SECURITY_AND_DISCLOSURE_LIMITS.md`
- `docs/accelerator/FUNCTIONAL_VALIDATION_REPORT.md`
- `docs/accelerator/CANONICAL_SCOPE.md`
- `docs/accelerator/INTEGRATED_SMOKE_TEST_REPORT.md`
- `docs/accelerator/DEMO_PAYLOAD_GUIDE.md`

## 3. Comandos de demo a validar antes de la sesión

- `python3 -m dof version`
- `python3 -m dof health`
- `python3 -m dof prove`
- smoke test SDK con `DOFVerifier.verify_action(...)`
- smoke test API local con `TestClient` sobre:
  - `/api/v1/health`
  - `/api/v1/z3/verify`
  - `/api/v1/governance/verify` usando el payload correcto de demo

## 4. Orden recomendado de la demo

1. Explicar el problema: agentes ejecutando acciones sensibles sin gobernanza previa.
2. Explicar la solución: propuesta de acción, gobernanza, verificación, evidencia.
3. Mostrar `dof version`.
4. Mostrar `dof health`.
5. Mostrar `dof prove`.
6. Ejecutar `DOFVerifier.verify_action(...)`.
7. Mostrar la API local con `TestClient` usando el payload ya validado.
8. Cerrar con el objetivo de preincubación: preparación para pilotos institucionales o empresariales.

## 5. Mensaje central del proyecto

DOF-MESH es una capa de gobernanza determinística para agentes de inteligencia artificial autónomos. Su propósito es verificar acciones críticas antes de ejecutarse y generar evidencia auditable en contextos donde confianza, seguridad y cumplimiento son esenciales.

## 6. Qué decir si preguntan por el repo anterior

El repositorio anterior `Cyberpaisa/deterministic-observability-framework` es el antecedente técnico e histórico del proyecto. La versión canónica para incubadora es el repositorio actual `Cyberpaisa/DOF-MESH`, que concentra la evolución más completa y vigente.

## 7. Qué decir si preguntan por el sitio web

`dofmesh.com` es la narrativa pública del proyecto y sirve para posicionamiento externo. La fuente principal para validación técnica y conversación de incubadora es el material canónico interno y la validación funcional mínima ya documentada.

## 8. Qué no mostrar todavía

- El repositorio completo como si todo estuviera igual de maduro.
- Componentes experimentales, periféricos o históricos como si fueran core.
- Claims de plataforma totalmente consolidada.
- Demos que mezclen gaming, research amplio, histórico duplicado o piezas no revalidadas.
- Información sensible o detalles explotables.

## 9. Preguntas para mentores

- ¿Qué nivel de claridad esperan para pasar de preincubación a validación con pilotos?
- ¿Qué tipo de institución o empresa sería el mejor primer piloto?
- ¿Qué evidencia adicional consideran crítica: técnica, comercial o regulatoria?
- ¿Cómo recomiendan acotar el mensaje para aliados institucionales frente a clientes B2B?
- ¿Qué riesgos de narrativa o enfoque ven hoy en la presentación?

## 10. Resultado esperado de la primera mentoría

- Validar que el problema y la solución sean comprensibles.
- Confirmar que el núcleo defendible es suficiente para una conversación seria.
- Obtener retroalimentación sobre enfoque de piloto, narrativa y priorización.
- Salir con una lista concreta de ajustes para la siguiente sesión, no con una expansión del alcance del proyecto.
