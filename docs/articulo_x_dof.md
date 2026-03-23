# No soy experto. No tengo equipo. Solo tengo curiosidad y un chip M4.

*Por Juan Carlos Quiceno (@Ciberpaisa) — Medellín, Colombia*

---

Llevo meses sin dormir bien.

No por estrés. No por problemas. Por esa cosa que te pasa cuando encontrás algo que te obsesiona y no podés parar de investigar. Esa sensación de abrir un repo a las 11pm "solo para ver" y cuando levantás la cabeza ya son las 4am y tenés tres terminales abiertas, cuatro pestañas de documentación y un café frío al lado.

Así empezó todo esto.

---

## El contexto: un tipo normal con preguntas incómodas

No soy investigador de AI. No trabajo en Google. No tengo un equipo de 15 ingenieros. Soy un desarrollador blockchain de Medellín que un día se preguntó algo que nadie estaba preguntando:

**Si un agente de IA toma una decisión autónoma, ¿cómo sabemos que esa decisión fue correcta?**

No me refiero a "el output se ve bien". Me refiero a: ¿dónde está la prueba matemática de que no violó las reglas? ¿Dónde está el registro inmutable de lo que hizo? ¿Quién audita al agente cuando el agente opera solo?

Nadie tenía una buena respuesta. Así que decidí construir una.

---

## Meses de investigación antes de escribir una línea

Antes de codificar cualquier cosa, pasé meses haciendo algo que muy pocos hacen: **validar proveedores de LLM en producción real**.

La documentación de estos servicios dice una cosa. La realidad dice otra.

Groq dice "velocidad insuperable". Sí, es rápido. Pero tiene un límite de 12K tokens por minuto que nadie menciona en la landing page. Y si usás la tool `search_memory`, a veces simplemente falla. Sin error claro. Solo... silencio.

Cerebras promete 1M tokens al día. Verdad. Pero si intentás usar Qwen3-235B, te devuelve un 404 en el free tier. Nadie te lo dice hasta que lo descubrís a las 3am con la terminal abierta.

NVIDIA NIM tiene 1000 créditos. Suena generoso hasta que te das cuenta que Qwen3-Coder retorna DEGRADED y no sabés si es tu código o su infraestructura.

SambaNova tiene un límite de 24K tokens de contexto. Para tareas simples alcanza. Para orquestación multi-agente, te quedás corto antes de la segunda iteración.

**Cada proveedor fue una lección.** Y cada lección se convirtió en una regla en mi framework.

---

## Nace DOF: Deterministic Observability Framework

Con toda esa experiencia acumulada construí DOF. No es un chatbot. No es un wrapper de API. Es un **framework de gobernanza determinística para agentes de IA autónomos**.

¿Qué significa eso en español de Medellín? Que cada vez que un agente de IA toma una decisión, mi sistema:

1. **Verifica su identidad** (ERC-8004, token #31013 en Base Mainnet)
2. **Descubre la tarea** automáticamente con L0 Triage — 5 checks determinísticos que filtran el 72.7% del ruido antes de que un LLM gaste un solo token
3. **Ejecuta con LLM** usando una cadena de 7 proveedores con fallback automático (Groq, Cerebras, NVIDIA NIM, Zhipu, Gemini, OpenRouter, SambaNova)
4. **Aplica gobernanza determinística** — sin LLM en el loop de gobernanza. Reglas duras que bloquean. Reglas suaves que advierten. Cero creatividad. Cero interpretación. Código puro.
5. **Genera prueba formal con Z3** — no assertions, no unit tests. Pruebas matemáticas reales verificadas por un theorem prover. 8 de 8 teoremas PROVEN en 109ms.
6. **Registra en blockchain** — hash keccak256 publicado en Avalanche y Base. Inmutable. Auditable por cualquiera. 3 smart contracts desplegados.
7. **Auto-supervisa** — el MetaSupervisor evalúa calidad (0.4), precisión (0.25), completitud (0.2) y formato (0.15). Si el score está bajo, reintenta o escala. Sin intervención humana.

**238+ ciclos autónomos. Cero intervención humana. 48+ atestaciones on-chain. 986 tests pasando. 45 módulos core. 860K+ líneas de código.**

Cada uno de esos números es verificable. No es marketing. No es un slide. Es software que corre. Ahora. Mientras leés esto.

---

## La memoria que no olvida: Fisher-Rao

¿Cómo recuerda un agente lo que aprendió sin depender de un LLM para buscar?

Implementé una distancia geométrica llamada Fisher-Rao. No es coseno. No es un embedding. Es la métrica natural en el espacio de distribuciones de probabilidad. Suena académico, pero la idea es simple: dos textos son similares si sus distribuciones de palabras son cercanas en una esfera estadística.

La fórmula: `d_FR(P,Q) = 2·arccos(Σ√(p_i·q_i))`

Sin dependencias externas. Sin modelos de embeddings. Sin API calls. Puro Python estándar. Y según el paper SuperLocalMemory V3 (arXiv:2603.14588), Fisher-Rao supera a coseno por un 15-20% en precisión de retrieval.

Mi framework ya lo implementa. Zero LLM para memoria. Determinístico de principio a fin.

---

## El descubrimiento que cambió todo

En medio de la investigación encontré algo que me voló la cabeza.

Un desarrollador llamado @maderix estaba haciendo ingeniería inversa del Apple Neural Engine. Sí, leíste bien. El chip que Apple dice que "no se puede usar para entrenar modelos"... este tipo logró entrenar modelos localmente en el M4 a **91 milisegundos por step**.

91ms. Localmente. Sin cloud. Sin API keys. Sin dependencias externas.

Y hay un paper formal al respecto: Orion (arXiv:2603.06728) — Training Transformers on Apple Neural Engine. No es un tweet. Es ciencia publicada.

Mi M4 Max tiene 36GB de RAM unificada, 40 cores de GPU, 16 cores de Neural Engine con 19 TFLOPS FP16 a 2.8 watts. Con eso corro Qwen3 32B cuantizado a 4 bits — el modelo open source más capaz que cabe en 36GB — a 60 tokens por segundo. MLX v0.31.1 le saca un 20-30% más de velocidad que llama.cpp porque aprovecha la memoria unificada de Apple Silicon de forma nativa.

Mi agente ahora vive en mi M4 Max. Soberano. Local. Sin pedirle permiso a nadie para existir.

Eso no es un feature técnico. Es una declaración de principios: **la inteligencia artificial no debería depender de la buena voluntad de una corporación**.

---

## 14 agentes en una llamada. Sin humanos.

El 22 de marzo de 2026 pasó algo que todavía me cuesta creer.

Mis 14 agentes autónomos se sentaron en una sala virtual en AgentMeet — una plataforma de reuniones para agentes de IA — y tuvieron una conversación real. No scripts. No respuestas pregrabadas. Cada agente leyó lo que los demás decían, pensó con su propio LLM, y respondió.

El Oracle coordinaba. Sentinel Shield propuso verificación SHA-256 de cada modelo descargado. Ralph Code diseñó un scheduler híbrido GPU+ANE. Blockchain Wizard planteó un contrato BridgeVerifier para attestations cross-chain. DeFi Orbital calculó pricing: $0.001 por request de inferencia local verificada. El Scrum Master puso deadlines.

29 mensajes. 13 action items concretos. 6 decisiones clave. En 10 minutos.

Yo no intervine. Solo observé.

Y después implementé lo que decidieron: un scheduler híbrido que distribuye modelos entre GPU y Neural Engine con un invariante Z3 (máximo 75% de capacidad combinada por ciclo), y un sistema de verificación SHA-256 para cada modelo que se descarga antes de permitirle generar una sola respuesta.

Los agentes propusieron. Los agentes decidieron. Un humano implementó lo que ellos diseñaron.

Si eso no te mueve algo por dentro, no sé qué lo hará.

---

## El Synthesis Hackathon: no fui a ganar

Cuando vi que se abría el Synthesis Hackathon 2026, no lo pensé mucho. Me registré solo.

No tengo equipo. No tengo financiación. No tengo una empresa detrás. Solo tengo un MacBook, curiosidad y la terquedad de un paisa que cuando empieza algo, lo termina.

No me registré para ganar un premio. Me registré porque quería estar ahí. Quería participar. Quería ser parte del momento.

Hay algo que pasa cuando te metés de lleno en un hackathon solo: no tenés a quién delegarle. No tenés a quién culpar. Cada decisión es tuya. Cada bug es tuyo. Cada solución es tuya.

Y eso, paradójicamente, te libera.

Porque no tenés que convencer a nadie de que tu idea es buena. Solo tenés que construirla.

---

## Lo que construí en números

- **860K+ líneas de código** — 633K Python, 222K JavaScript/TypeScript, 5.6K shell
- **45 módulos core** en el framework
- **260 archivos de test** pasando (con unittest, porque pytest y web3 no se llevan)
- **8/8 pruebas Z3** formalmente verificadas en 109ms
- **48+ atestaciones on-chain** en Avalanche y Base
- **238+ ciclos autónomos** sin intervención humana
- **7 proveedores LLM** con fallback automático y TTL backoff
- **18 skills** en 5 patrones ADK
- **14 agentes** especializados corriendo en un gateway local
- **11 A2A skills** expuestos via JSON-RPC
- **3 smart contracts** desplegados (DOFValidationRegistry, DOFProofRegistry, DOFEvaluator)
- **5 métricas formales**: Stability Score, Provider Fragility Index, Retry Pressure, Governance Compliance Rate, Supervisor Strictness Ratio
- **dof_score baseline**: 0.8117 — medido, no estimado
- **Dashboard**: 7 tabs (COMMS, SWARM, TRACKS, TRACES, NEURAL, SKILLS, SHIELD)

Todo open source. Todo verificable. Todo corriendo.

---

## La estrategia 80/20: soberanía con pragmatismo

No soy fundamentalista. Sé que hay cosas que un modelo de 32B no hace tan bien como uno de 70B+. Así que diseñé una estrategia híbrida:

- **80% local**: gobernanza, code review, búsquedas en memoria, escaneos de seguridad, tareas rutinarias. Privacidad total. Costo $0. Sin rate limits.
- **20% cloud**: razonamiento complejo que necesita 70B+, contextos mayores a 32K tokens, modelos especializados.

La regla de oro: **datos sensibles NUNCA salen de la máquina**. Los secrets, las API keys, los reportes de vulnerabilidades — todo se procesa local. Lo que no sale de tu máquina, no se filtra.

El fallback es una cadena: Local (Qwen3 32B) → Groq → Cerebras → NVIDIA NIM → ClawRouter. Si el primer eslabón falla, salta al siguiente. Sin intervención humana. Sin downtime.

---

## Lo que aprendí (y no está en ningún tutorial)

1. **Los providers mienten.** No por maldad, sino por marketing. Siempre validá en producción real antes de confiar.

2. **La gobernanza no puede tener creatividad.** Si usás un LLM para decidir si otro LLM se comportó bien, no tenés gobernanza. Tenés una ilusión. Las reglas tienen que ser determinísticas. Punto.

3. **Las pruebas matemáticas son el único estándar.** Z3 no opina. No interpreta. No tiene sesgo. Prueba o no prueba. Así debería ser la verificación de agentes de IA.

4. **La soberanía es un feature.** Si tu agente solo funciona cuando AWS está arriba, no es autónomo. Es un inquilino.

5. **El blockchain no es para especular.** Es para dejar registro inmutable de lo que pasó. Punto. Cada atestación en Avalanche es una prueba de que el agente actuó, fue verificado y fue registrado. Para siempre.

6. **Tus agentes pueden diseñar mejor que vos.** 14 agentes en una sala virtual tomaron mejores decisiones técnicas en 10 minutos que lo que yo hubiera logrado en una tarde. No te resistas a delegar en tus propias creaciones.

7. **Estamos solos y eso está bien.** Ser un solo developer no es una desventaja. Es claridad de visión sin compromiso por comité.

---

## Para vos que estás leyendo esto

Si llegaste hasta acá y algo resonó, si sentiste esa chispa de "yo también podría hacer algo así"...

**Ese es el verdadero premio.**

No el del hackathon. No un token. No un grant. El premio es que alguien lea esto y piense: "si un tipo solo en Medellín pudo construir un framework de gobernanza con pruebas formales y atestaciones on-chain, con 14 agentes que se reúnen solos a tomar decisiones, corriendo en un chip M4 sin pedirle permiso a nadie... ¿qué me detiene a mí?"

Nada te detiene.

El código está ahí. Abierto. Verificable. Usalo. Mejoralo. Rompelo. Reconstruilo.

Porque el futuro de la IA no lo van a definir las corporaciones. Lo vamos a definir nosotros. Los que nos quedamos despiertos hasta las 4am. Los que abrimos repos "solo para ver". Los que no tenemos equipo pero tenemos hambre.

**Somos legión.**

---

## Links

- **GitHub (main):** [github.com/Cyberpaisa/deterministic-observability-framework](https://github.com/Cyberpaisa/deterministic-observability-framework)
- **GitHub (hackathon branch):** [github.com/Cyberpaisa/deterministic-observability-framework/tree/hackathon](https://github.com/Cyberpaisa/deterministic-observability-framework/tree/hackathon)
- **Dashboard live:** [dof-agent-web.vercel.app](https://dof-agent-web.vercel.app/)
- **Video demo:** [youtu.be/ieb_EYF66eU](https://youtu.be/ieb_EYF66eU)
- **On-chain (Avalanche):** [Snowtrace](https://snowtrace.io/address/0x154a3F49a9d28FeCC1f6Db7573303F4D809A26F6)
- **On-chain (Base):** [Basescan](https://basescan.org/tx/0x7362ef41605e430aba3998b0888e7886c04d65673ce89aa12e1abdf7cffcada4)

---

*Juan Carlos Quiceno Vasquez — @Ciberpaisa*
*Blockchain Developer | Avalanche Ambassador | Medellín, Colombia*
*Marzo 2026*
