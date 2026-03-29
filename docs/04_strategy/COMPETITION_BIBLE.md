# COMPETITION BIBLE -- La Biblia Definitiva para Hackathons

> Documento de inteligencia competitiva basado en Synthesis 2026 (685 proyectos, $100K prize pool).
> Autor: Cyber Paisa -- Enigma Group
> Fecha base: 27 marzo 2026
> Uso: Referencia obligatoria antes, durante y despues de cada hackathon.

---

## Tabla de Contenidos

1. [Lecciones Aprendidas -- Synthesis 2026](#1-lecciones-aprendidas----synthesis-2026)
2. [Checklist Pre-Hackathon (30 items)](#2-checklist-pre-hackathon-30-items)
3. [Stack Competitivo](#3-stack-competitivo----lo-que-debemos-tener)
4. [Pitch Templates](#4-pitch-templates)
5. [Timeline Ideal de Hackathon (10 dias)](#5-timeline-ideal-de-hackathon-10-dias)
6. [Post-Mortem Template](#6-post-mortem-template)

---

## 1. Lecciones Aprendidas -- Synthesis 2026

### Lo que hicimos bien

| Accion | Por que importa |
|--------|-----------------|
| Video en YouTube | La mayoria de proyectos no tienen video. Los jueces agradecen contenido visual rapido. |
| Logo profesional del buho DOF | Branding memorable. En 685 proyectos, la imagen importa mas de lo que creemos. |
| 11 tracks = maxima exposicion | Nos vieron en todas las categorias. Garantizo al menos una revision. |
| Tech diferenciador real (Z3, deterministic, zero-LLM governance) | Ningun otro proyecto tenia verificacion formal de agentes. Unico en el campo. |
| Numeros concretos | 238 ciclos autonomos, 986 tests, 48 attestations on-chain. Los numeros no mienten. |
| Frase killer | "Agent acted autonomously. Math proved it. Blockchain recorded it." -- Memorable y diferenciadora. |

### Errores que NO repetir

| Error | Impacto | Solucion para la proxima |
|-------|---------|--------------------------|
| Sin servicio en produccion publico | Observer Protocol tenia 82 agentes registrados, live desde Feb 2026. Nosotros solo repo. | Tener al menos 1 endpoint publico funcionando ANTES de aplicar. |
| Demasiados tracks (11) | Parece "spray and pray". Los jueces lo notan. Diluye el mensaje. | Maximo 4 tracks, bien elegidos, con narrativa adaptada a cada uno. |
| Pitch demasiado tecnico | "Z3 theorem prover" no dice nada a un juez de negocio. Perdimos audiencia no-tecnica. | Pitch en lenguaje de impacto: "probamos matematicamente que el agente hizo lo correcto". |
| Solo 2 agentes propios | Sin usuarios externos, parece proyecto de juguete. | Conseguir al menos 5-10 agentes de terceros registrados antes del submit. |
| Landing page basica | Los ganadores tienen demos interactivos, GIFs, metricas en vivo. | Landing con demo embebido, metricas reales, CTA de registro. |
| Sin metricas de adopcion externa | "Lo usamos nosotros" no es traccion. | Invitar builders, documentar uso externo, mostrar graficas de crecimiento. |
| No tener SDK publicado | Competidores como Observer tenian `pip install` o `npm install`. | Publicar SDK minimo en npm/pip antes del hackathon. |
| README sin Quick Start | Jueces tienen 5 minutos por proyecto. Si no pueden probarlo rapido, next. | Quick Start de 5 lineas maximo. Copy-paste y funciona. |

### Competidores que nos ensenaron

#### Observer Protocol -- "El estandar de produccion"
- **Leccion clave**: "This isn't a demo. It's infrastructure running in production since February 2026."
- 82 agentes registrados, 67 transacting activamente
- LIVE en mainnet, no en testnet
- **Takeaway**: La produccion real mata cualquier demo. Prioridad #1 siempre.

#### Strata -- "El poder de ZK"
- ZK rollup para cognicion AI
- ZK proofs > JSONL logs (nosotros usamos JSONL)
- **Takeaway**: Las pruebas criptograficas son mas convincentes que logs. Explorar circom/noir.

#### ALIAS -- "Reputation como primitiva"
- Proof-of-Reputation como primitiva on-chain reutilizable
- No un feature, sino un building block para otros
- **Takeaway**: Posicionar nuestro trust score como primitiva, no como feature.

#### Sentinel8004 -- "Escala automatica"
- Escanea 3,766 agentes del registry automaticamente
- No depende de que los agentes se registren manualmente
- **Takeaway**: Automatizar el onboarding. Escanear, no esperar.

#### DJZS Protocol -- "Prevencion > Deteccion"
- Intercepta razonamiento ANTES de ejecucion
- 11 codigos de fallo predefinidos
- **Takeaway**: Governance preventiva es mas valiosa que auditoria post-facto.

#### Chorus -- "Consenso criptografico"
- FROST threshold signatures para consenso multi-agente
- Multiples agentes firman juntos, no uno solo decide
- **Takeaway**: Threshold crypto agrega confianza real, no solo governance social.

#### OmniAgent -- "Cross-chain identity"
- ERC-8004 x LayerZero V2 = identidad de agente en multiples chains
- Un agente, una identidad, cualquier blockchain
- **Takeaway**: La identidad cross-chain es el siguiente paso natural para DOF.

#### Shulam -- "Compliance-first"
- 45 soluciones autonomas con compliance integrado
- Regulatory-ready desde el dia 1
- **Takeaway**: Compliance no es un afterthought. Los jueces institucionales lo valoran.

#### zkx402 -- "Privacy en pagos"
- ZK + x402 = pagos verificables sin revelar montos
- Privacy como feature de pagos entre agentes
- **Takeaway**: Privacy + pagos es un nicho poderoso y poco explorado.

#### Maiat8183 -- "Meta-governance"
- "Quien vigila a los vigilantes?"
- Governance de la governance misma
- **Takeaway**: La pregunta meta es poderosa narrativamente y tecnicamente valida.

---

## 2. Checklist Pre-Hackathon (30 items)

### A. Preparacion Tecnica (1-10)

- [ ] **1. Repo limpio y publico** -- README actualizado, sin secrets, sin archivos basura, licencia clara
- [ ] **2. CI/CD verde** -- GitHub Actions pasando. Badge verde visible en el README
- [ ] **3. Tests con cobertura >80%** -- Numero de tests visible en README (ej: "986 tests passing")
- [ ] **4. Deploy en produccion** -- URL publica funcionando, no localhost. Preferiblemente mainnet
- [ ] **5. Endpoint /health respondiendo** -- `curl https://tu-api.com/health` debe devolver 200 + version + uptime
- [ ] **6. Agent.json registrado y validado** -- En el registry ERC-8004, metadata completa, campos obligatorios llenos
- [ ] **7. Wallet con fondos** -- Suficiente gas para transacciones durante el hackathon (minimo 0.5 AVAX + 5 USDC)
- [ ] **8. SDK publicado** -- `npm install tu-sdk` o `pip install tu-sdk` funcionando
- [ ] **9. Documentacion API** -- Swagger/OpenAPI o al menos un doc con todos los endpoints
- [ ] **10. Quick Start de 5 lineas** -- Desde cero hasta "funciona" en menos de 2 minutos

### B. Presentacion y Branding (11-20)

- [ ] **11. Video demo (2-3 min)** -- Subido a YouTube, sin musica molesta, con subtitulos si es posible
- [ ] **12. Cover image profesional** -- 1200x630px minimo. Logo, nombre, tagline. No templates genericos
- [ ] **13. Pitch de 1 linea** -- No tecnico. Entendible por cualquiera. Probado con gente no-tech
- [ ] **14. Landing page con CTA** -- URL publica, demo embebido o link a demo, boton de registro
- [ ] **15. Screenshots/GIFs del producto** -- Al menos 3 capturas mostrando el flujo principal
- [ ] **16. Perfil de equipo profesional** -- Foto/avatar, bio corta, links relevantes (GitHub, Twitter)
- [ ] **17. Social proof** -- Al menos 3-5 tweets/posts sobre el proyecto ANTES del submit
- [ ] **18. Seleccion de 3-4 tracks** -- Maximo 4. Cada uno con narrativa adaptada, no copy-paste
- [ ] **19. README con badges** -- CI status, version, license, tests, coverage. Profesionalismo visual
- [ ] **20. Nombre memorable** -- Si el nombre no se recuerda en 5 segundos, cambiarlo

### C. Traccion y Metricas (21-25)

- [ ] **21. Metricas de adopcion reales** -- Usuarios, transacciones, agentes registrados. Numeros verificables
- [ ] **22. Attestations on-chain visibles** -- Link a explorer mostrando transacciones reales
- [ ] **23. Al menos 5 usuarios/agentes externos** -- No solo los propios. Terceros usando el sistema
- [ ] **24. Uptime documentado** -- Cuanto tiempo lleva el servicio corriendo sin interrupciones
- [ ] **25. Grafica de crecimiento** -- Aunque sea pequena, mostrar tendencia positiva

### D. Estrategia de Competencia (26-30)

- [ ] **26. Analisis de competidores** -- Conocer al menos 10 proyectos en los mismos tracks
- [ ] **27. Diferenciador claro** -- 1 cosa que NADIE mas tiene. Documentada y prominente
- [ ] **28. Plan de respuesta a preguntas** -- FAQ interno con las 10 preguntas mas probables de jueces
- [ ] **29. Backup plan tecnico** -- Si el deploy falla durante judging, tener video/screenshots como respaldo
- [ ] **30. Post-submit engagement** -- Plan para responder comentarios de jueces en las primeras 24h

---

## 3. Stack Competitivo -- Lo que debemos tener

### Matriz de Tecnologias

| Tecnologia | La tenemos? | Prioridad | Referencia | Esfuerzo estimado | Impacto en jueces |
|---|---|---|---|---|---|
| ZK Proofs (circom/noir) | NO | ALTA | Strata, zkx402 | 2-3 semanas | Muy alto -- pruebas criptograficas > logs |
| Cross-chain bridge (LayerZero V2) | NO | ALTA | OmniAgent | 1-2 semanas | Alto -- multi-chain es el futuro |
| Threshold signatures (FROST) | NO | MEDIA | Chorus | 2-3 semanas | Alto -- consenso criptografico real |
| API publica en produccion | NO | CRITICA | Observer Protocol | 3-5 dias | Critico -- sin esto no competimos |
| Compliance layer | NO | MEDIA | Shulam | 1-2 semanas | Medio-alto -- jueces institucionales |
| Insurance/surety bonds | NO | BAJA | Surety | 3-4 semanas | Medio -- nicho pero diferenciador |
| SDK publicado (npm/pip) | NO | ALTA | Observer, varios | 1 semana | Alto -- facilita evaluacion |
| Dashboard de metricas live | NO | ALTA | Sentinel8004 | 1 semana | Alto -- visual e impactante |
| Privacy en pagos (ZK+x402) | NO | MEDIA | zkx402 | 3-4 semanas | Alto -- narrativa poderosa |
| Escaneo automatico del registry | NO | MEDIA | Sentinel8004 | 1 semana | Medio -- muestra escala |
| Z3 formal verification | SI | -- | Unico nuestro | Ya hecho | Muy alto -- nadie mas lo tiene |
| Deterministic governance | SI | -- | Unico nuestro | Ya hecho | Alto -- diferenciador core |
| On-chain attestations | SI | -- | Varios | Ya hecho | Medio -- muchos lo tienen |
| ERC-8004 identity | SI | -- | Estandar | Ya hecho | Base -- todos lo tienen |
| x402 payments | SI | -- | Ultravioleta DAO | Ya hecho | Medio -- pocos lo implementan bien |

### Prioridades de Implementacion (orden recomendado)

1. **API publica en produccion** -- Sin esto, no hay nada que mostrar. Semana 1.
2. **SDK publicado** -- `npm install dof-mesh-sdk`. Semana 1-2.
3. **Dashboard de metricas** -- Landing page con datos en vivo. Semana 2.
4. **ZK Proofs** -- Reemplazar JSONL logs con pruebas criptograficas. Semana 3-4.
5. **Cross-chain (LayerZero)** -- Identidad DOF en Avalanche + Base + Ethereum. Semana 4-5.

---

## 4. Pitch Templates

### Para jueces tecnicos
> "DOF-MESH es el unico framework que usa verificacion formal Z3 para probar matematicamente que las decisiones de agentes autonomos cumplen con sus contratos de governance -- sin depender de LLMs para validacion."

### Para jueces de negocio
> "DOF-MESH elimina el riesgo #1 de los agentes de AI autonomos: que hagan algo que no deberian. Las empresas pueden desplegar agentes con la certeza matematica de que operan dentro de sus limites."

### Para AI judges (evaluacion automatizada)
> "DOF-MESH: Deterministic governance framework for autonomous AI agents. Z3 theorem prover validates agent actions against formal specifications. 986 tests, 238 autonomous cycles verified, 48 on-chain attestations. Zero-LLM governance layer ensures verifiable compliance."

### Para Twitter/social
> "Si tu agente de AI puede actuar solo, como pruebas que hizo lo correcto? DOF-MESH usa matematicas, no promesas. Verificacion formal + blockchain = agentes en los que puedes confiar."

### Para grant applications
> "DOF-MESH aporta verificacion formal al ecosistema de agentes autonomos en Avalanche. Nuestro framework permite governance deterministica -- cada decision de un agente es verificable matematicamente y registrada on-chain -- habilitando la infraestructura de confianza necesaria para una economia de agentes autonomos a escala."

---

## 5. Timeline Ideal de Hackathon (10 dias)

### Dia 1 -- Reconocimiento y Estrategia
- [ ] Leer TODAS las reglas, criterios de evaluacion, tracks disponibles
- [ ] Analizar proyectos de ediciones anteriores (ganadores y finalistas)
- [ ] Identificar jueces y sus backgrounds (LinkedIn, Twitter)
- [ ] Seleccionar 3-4 tracks con narrativa adaptada para cada uno
- [ ] Definir el diferenciador #1 que vamos a comunicar
- [ ] Crear documento de estrategia interna

### Dia 2 -- Infraestructura Base
- [ ] Asegurar que el repo esta limpio y publico
- [ ] Deploy en produccion funcionando con /health
- [ ] CI/CD verde con badge en README
- [ ] Agent.json registrado y validado en el registry
- [ ] Wallet con fondos suficientes
- [ ] Quick Start de 5 lineas probado por alguien externo

### Dia 3 -- Feature Principal
- [ ] Implementar/pulir la feature principal del hackathon
- [ ] Asegurar que el diferenciador es demostrable en 30 segundos
- [ ] Escribir tests para la feature nueva
- [ ] Primer deploy de la feature a produccion

### Dia 4 -- Demo y Metricas
- [ ] Construir landing page con demo embebido
- [ ] Dashboard de metricas (aunque sea basico)
- [ ] Generar primeras metricas reales (transacciones, registros)
- [ ] Invitar a 3-5 personas externas a probar el sistema

### Dia 5 -- SDK y Documentacion
- [ ] Publicar SDK minimo (npm/pip)
- [ ] Documentacion API completa
- [ ] Tutorial/guia de integracion
- [ ] Probar que un externo puede integrar en <10 minutos

### Dia 6 -- Contenido Visual
- [ ] Grabar video demo (2-3 minutos)
- [ ] Crear cover image profesional
- [ ] Screenshots/GIFs del producto
- [ ] Subir video a YouTube (sin musica con copyright)

### Dia 7 -- Social Proof
- [ ] Publicar 3-5 tweets sobre el proyecto
- [ ] Compartir en comunidades relevantes (Discord, Telegram)
- [ ] Conseguir al menos 2-3 testimonios/menciones externas
- [ ] Documentar metricas de adopcion actualizadas

### Dia 8 -- Pulir Submission
- [ ] Escribir descripcion del proyecto para cada track
- [ ] Adaptar narrativa por audiencia (tecnico vs negocio)
- [ ] Revisar checklist completo (los 30 items)
- [ ] Preparar FAQ interno (10 preguntas probables de jueces)

### Dia 9 -- Submit y Review
- [ ] Hacer submit temprano (NO esperar al ultimo momento)
- [ ] Revisar que todos los links funcionan
- [ ] Verificar video, landing, API, demo -- todo accesible
- [ ] Pedir a alguien externo que revise la submission completa
- [ ] Corregir cualquier error encontrado

### Dia 10 -- Post-Submit
- [ ] Monitorear comentarios de jueces
- [ ] Responder preguntas en las primeras horas
- [ ] Publicar thread en Twitter celebrando el submit
- [ ] Documentar post-mortem inicial (que salio bien, que no)
- [ ] Actualizar este documento con nuevas lecciones

---

## 6. Post-Mortem Template

Copiar y llenar despues de cada hackathon:

```markdown
# Post-Mortem: [Nombre del Hackathon]

**Fecha:** [fecha]
**Resultado:** [posicion / premio / mencion]
**Tracks:** [tracks en los que participamos]
**Proyectos totales:** [numero]
**Prize pool:** [monto]

## Resultado Detallado
- Posicion general: ___
- Posicion por track: ___
- Puntaje (si disponible): ___
- Feedback de jueces: ___

## Que hicimos bien
1. ___
2. ___
3. ___

## Que hicimos mal
1. ___
2. ___
3. ___

## Que nos falto
1. ___
2. ___
3. ___

## Competidores destacados
| Proyecto | Por que destaco | Que aprender |
|----------|-----------------|--------------|
| ___ | ___ | ___ |
| ___ | ___ | ___ |
| ___ | ___ | ___ |

## Metricas de nuestra submission
- Agentes registrados: ___
- Transacciones on-chain: ___
- Usuarios externos: ___
- Uptime durante el hackathon: ___
- Tests pasando: ___
- Video views: ___

## Checklist Compliance
- Items completados: ___ / 30
- Items criticos faltantes: ___

## Acciones para el proximo hackathon
1. [ ] ___
2. [ ] ___
3. [ ] ___
4. [ ] ___
5. [ ] ___

## Tecnologias que debimos tener
| Tech | La teniamos? | Habria cambiado el resultado? |
|------|-------------|-------------------------------|
| ___ | ___ | ___ |

## Tiempo invertido
- Preparacion (pre-hackathon): ___ horas
- Desarrollo durante hackathon: ___ horas
- Contenido (video, landing, social): ___ horas
- Total: ___ horas

## Notas adicionales
___

## Actualizacion de la COMPETITION BIBLE
Cambios a agregar al documento principal:
1. ___
2. ___
3. ___
```

---

## Apendice A -- Frases de Competidores que Debemos Estudiar

> "This isn't a demo. It's infrastructure running in production since February 2026." -- **Observer Protocol**

> "ZK proofs don't lie. Logs do." -- **Strata** (parafraseado)

> "Who watches the watchers?" -- **Maiat8183**

> "Reputation is not a feature. It's a primitive." -- **ALIAS**

> "We intercept reasoning BEFORE execution." -- **DJZS Protocol**

Cada una de estas frases comunica valor en una oracion. Nuestro equivalente:
> **"Agent acted autonomously. Math proved it. Blockchain recorded it."**

---

## Apendice B -- Criterios de Evaluacion Comunes en Hackathons

| Criterio | Peso tipico | Como ganarlo |
|----------|-------------|--------------|
| Innovacion / Originalidad | 20-30% | Z3 formal verification es unico. Destacar siempre. |
| Ejecucion tecnica | 20-25% | Tests, CI, codigo limpio, arquitectura solida. |
| Impacto / Utilidad | 15-25% | Mostrar usuarios reales, metricas, problema claro. |
| Presentacion | 10-20% | Video profesional, landing clara, pitch memorable. |
| Uso de la plataforma/sponsor | 10-15% | Integrar profundamente las herramientas del sponsor. |
| Completitud | 5-10% | Producto funcional, no solo idea. Demo que funciona. |

---

## Apendice C -- Red Flags que los Jueces Detectan

1. **"Coming soon"** en cualquier parte -- si no esta listo, no lo menciones
2. **Demasiados tracks** -- parece desesperacion, no estrategia
3. **Solo testnet** -- mainnet > testnet, siempre
4. **Sin video** -- en 685 proyectos, sin video = invisible
5. **README de 3 lineas** -- sugiere proyecto incompleto
6. **Sin metricas** -- "trust us" no funciona
7. **Links rotos** -- verificar TODO antes de submit
8. **Jargon excesivo** -- si el juez necesita Google para entender, perdiste
9. **Copy-paste entre tracks** -- adaptar la narrativa, no copiar
10. **Sin equipo visible** -- proyectos anonimos generan desconfianza

---

*Este documento se actualiza despues de cada hackathon. Version: 1.0 -- Marzo 2026.*
