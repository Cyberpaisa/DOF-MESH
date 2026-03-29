# DOF-MESH -- Framework de Comunicacion de Patrick Winston (MIT)

> **Referencia:** Patrick Winston, profesor del MIT durante 40+ anos. Su conferencia "How to Speak" es la mas vista del MIT. Su libro "Make It Clear: Speak and Write to Persuade and Inform" (MIT Press, 2020) codifica 40 anos de investigacion sobre comunicacion efectiva.
>
> **Proposito:** Este documento aplica el framework completo de Winston a DOF-MESH para estandarizar toda comunicacion del proyecto -- desde un tweet hasta una presentacion enterprise.
>
> **Autor:** Cyber Paisa -- Enigma Group
> **Fecha:** 27 marzo 2026

---

## PARTE I -- LOS PRINCIPIOS DE WINSTON

### 1. La Promesa de Empoderamiento (Apertura)

Winston es tajante: NUNCA empieces con un chiste. Los primeros 60 segundos son sagrados. En ese minuto, la audiencia decide si va a escucharte o va a sacar el telefono.

**La regla:** En los primeros 60 segundos, di exactamente que va a GANAR la audiencia al escucharte. No que vas a hablar de X. No que tu empresa hace Y. Que van a OBTENER ellos.

"Prepara la bomba antes de verter nada." -- La promesa es la mecha. Si no hay mecha, no hay explosion.

**Aplicacion a DOF-MESH:** No decimos "vamos a hablar de governance para agentes de IA." Decimos: "Hoy van a salir de aqui con la unica forma matematicamente probada de garantizar que un agente de IA no robe, mienta o falle sin que nadie se entere."

---

### 2. Las 5S -- Para que una idea sea memorable

Una idea que no se recuerda es una idea que no existe. Winston identifica 5 elementos que hacen una idea imposible de olvidar:

| S | Definicion | Ejemplo DOF-MESH |
|---|---|---|
| **Simbolo** | Imagen visual que representa la idea | El buho DOF -- vigilancia silenciosa, vision nocturna, precision |
| **Slogan** | Frase corta que captura la esencia | "Matematicas, no promesas." |
| **Sorpresa** | Dato inesperado que rompe el patron mental | "685 proyectos de agentes autonomos en el hackathon mas grande del mundo. Cero tienen verificacion formal." |
| **Saliente** | Por que es relevante para TI, no en abstracto | "Tu agente DeFi maneja $10M. Si falla, no pierdes un log -- pierdes $10M." |
| **Story** | Narrativa que conecta emocionalmente | La historia del agente que parecio funcionar 3 meses hasta que dreno un treasury entero |

**Regla de Winston:** Una idea memorable cumple al menos 3 de las 5S. DOF-MESH debe usar las 5 en toda comunicacion importante.

---

### 3. Near Miss (Casi Acierto)

Este es el principio mas poderoso de Winston para ensenar y vender. No alcanza con mostrar lo correcto. Hay que mostrar lo que PARECE correcto pero NO lo es.

El contraste graba permanentemente en el cerebro porque activa el sistema de deteccion de amenazas: "casi me enganan."

**El Near Miss de DOF-MESH:**

> "Otros frameworks usan LLMs para validar LLMs. Parece logico -- tienes una IA inteligente, ponla a vigilar. Pero es como poner a un ladron a vigilar a otro ladron. El ladron vigilante puede ser sobornado con un prompt. Puede alucinar que todo esta bien cuando no lo esta. Puede ser manipulado con el mismo tipo de ataque que deberia detectar.
>
> DOF no usa LLMs para governance. Usa Z3 -- el mismo motor de verificacion formal que certifica sistemas de aviacion. No se puede sobornar. No alucina. No opina. Prueba."

---

### 4. VSN-C Framework (del libro "Make It Clear")

La estructura maestra de Winston para cualquier comunicacion persuasiva:

- **Vision** -- Que problema resuelves y por que importa AHORA
- **Steps** -- Pasos concretos de como funciona (la gente necesita ver el camino)
- **News** -- Que hay de nuevo, tu diferenciador (por que no existia antes)
- **Contributions** -- Que le das a la audiencia que no tenia antes de escucharte

**VSN-C de DOF-MESH:**

**Vision:** Los agentes de IA autonomos ya manejan dinero real -- treasuries de $100M, pagos automaticos, decisiones empresariales. Pero nadie puede probar que hicieron lo correcto. La regulacion viene (MiCA en Europa, SEC en USA). Quien no pueda demostrar governance verificable, no podra operar.

**Steps:** (1) Conectas tu agente a DOF con `pip install dof-sdk`. (2) Cada decision del agente pasa por 7 capas de verificacion deterministica -- sin LLMs, sin latencia. (3) DOF genera una prueba matematica Z3 de cada accion. (4) Esa prueba se graba inmutablemente en blockchain (Avalanche C-Chain). (5) Cualquier regulador, auditor o cliente puede verificarla independientemente.

**News:** Es el unico framework que combina verificacion formal Z3 con attestations on-chain. 0% falsos positivos. 30ms por verificacion. 3,700 tests pasando. 8 teoremas Z3 probados para todas las entradas posibles.

**Contributions:** Despues de esta presentacion, tienes: (1) un SDK instalable en 30 segundos, (2) la certeza matematica -- no estadistica -- de que tu agente cumple las reglas, y (3) pruebas inmutables que cualquier tercero puede auditar.

---

### 5. Cierre con Contribucion

Winston: NUNCA termines con "gracias", "preguntas?" o un resumen. Termina diciendo que les DISTE que no tenian antes. Deja al publico con algo accionable -- algo que pueden hacer HOY.

**Cierre DOF-MESH:**

> "Antes de esta conversacion, la unica forma de saber si tu agente se porto bien era confiar en logs que el mismo agente genero. Ahora saben que existe una alternativa: prueba matematica, inmutable, verificable por terceros. `pip install dof-sdk`. Tarda 30 segundos. La primera verificacion es gratis. Y la proxima vez que alguien les pregunte 'como saben que su agente hizo lo correcto?', van a tener una respuesta que ningun otro equipo en el mundo puede dar."

---

### 6. Reglas de Presentacion

- Slides para EXPONER ideas, no para ensenarlas
- Eliminar palabras innecesarias, logos corporativos, titulos decorativos
- Una idea por slide -- si necesitas dos ideas, necesitas dos slides
- Si usas pizarra/whiteboard, la audiencia te sigue mentalmente (engagement 3x)
- Fuentes grandes. Si tienes que achinar los ojos, sobra texto.
- Nunca leer el slide -- el slide apoya lo que dices, no lo reemplaza

---

## PARTE II -- APLICACIONES A DOF-MESH

---

### A) PITCH DE VENTAS (1 Minuto) -- Cliente Enterprise

#### Apertura -- Promesa de Empoderamiento (0:00 - 0:15)

> "En los proximos 60 segundos, van a conocer la unica tecnologia que puede probar MATEMATICAMENTE que un agente de IA se porto bien. No logs. No monitoring. Prueba formal. Si sus agentes manejan dinero o decisiones criticas, esto cambia todo."

#### Simbolo -- El Buho DOF (0:15 - 0:20)

> "Piensen en un buho. Ve en la oscuridad. No hace ruido. No duerme. Y su precision de caza es del 99%. Eso es DOF -- vigilancia silenciosa, continua y matematicamente precisa sobre cada agente autonomo."

#### Slogan -- 3 Opciones

1. **"Matematicas, no promesas."** -- Para audiencia tecnica y reguladores. Contrasta con la vaguedad de otros frameworks.
2. **"Si tu agente puede actuar solo, prueba que hizo lo correcto."** -- Para C-suite. Pone el dedo en la llaga del riesgo.
3. **"Zero trust, zero LLM, zero excusas."** -- Para CTOs de fintech/DeFi. Tres ceros que se graban.

#### Sorpresa -- El dato que rompe expectativas (0:20 - 0:30)

> "Analizamos 685 proyectos en el hackathon global mas grande de agentes autonomos -- Synthesis 2026, 1,500 participantes, $100K en premios. Saben cuantos usan verificacion formal para governance? Cero. Todos confian en otro LLM para vigilar. Es como darle las llaves de la boveda al primo del guardia de seguridad."

#### Near Miss -- Lo que parece funcionar pero no (0:30 - 0:40)

> "La solucion obvia es usar IA para vigilar IA. Suena logico. Hasta que tu agente vigilante alucina que todo esta bien cuando un atacante esta drenando el treasury con un prompt injection. Un LLM no puede probar nada -- solo opinar. DOF no opina. DOF prueba. Z3 -- el motor que certifica aviones y reactores nucleares -- ahora certifica tus agentes."

#### Historia -- El agente que fallo (0:40 - 0:50)

> "Un protocolo DeFi despliega un agente para rebalancear su pool de liquidez. Funciona perfecto 3 meses. Dia 91, un cambio de mercado activa un edge case. El agente ejecuta 47 transacciones en 8 minutos. $2.3M perdidos. Los logs decian 'operacion exitosa' en cada una. Con DOF, la transaccion 1 hubiera sido bloqueada -- porque la prueba Z3 detecta que viola el invariante de limites antes de que el agente firme."

#### Cierre con Contribucion (0:50 - 1:00)

> "Lo que acaban de escuchar no es un pitch -- es una capacidad que no existia hasta ahora. `pip install dof-sdk`. 30 segundos. Primera verificacion gratis. La pregunta no es si necesitan governance verificable. La pregunta es cuanto les va a costar no tenerla."

---

### B) PRESENTACION DE 5 MINUTOS (Hackathon / Demo Day)

#### Estructura VSN-C con 8 Slides

**SLIDE 1 -- LA PREGUNTA (Vision -- 0:00 a 0:40)**

Visual: Pantalla negra con texto blanco grande: "Tu agente de IA maneja dinero. Como pruebas que hizo lo correcto?"

Que decir:
> "Esta es la pregunta que ninguna empresa puede responder hoy. Tienen agentes autonomos ejecutando transacciones de millones de dolares. Y la unica evidencia de que se portaron bien es... logs que el mismo agente genero. Es como preguntarle al acusado si es culpable."

---

**SLIDE 2 -- EL NEAR MISS (Vision -- 0:40 a 1:20)**

Visual: Dos columnas. Izquierda: "IA vigila IA" con un icono de loop infinito. Derecha: "Matematicas verifican IA" con el simbolo de checkmark formal.

Que decir:
> "La respuesta obvia es poner a otra IA a vigilar. Observer Protocol lo hace. AgentLedger lo hace. 685 proyectos en Synthesis 2026 lo hacen de alguna forma. Parece logico. Pero un LLM puede ser manipulado con el mismo tipo de ataque que deberia detectar. Es poner un ladron a vigilar a otro ladron. DOF toma otro camino: verificacion formal. Z3 -- el motor que certifica aviones."

---

**SLIDE 3 -- COMO FUNCIONA (Steps -- 1:20 a 2:00)**

Visual: Diagrama de 5 pasos verticales con flechas:
1. `pip install dof-sdk` (30 seg)
2. Agente toma decision
3. 7 capas de verificacion (0 LLMs)
4. Prueba Z3 generada
5. Attestation grabada en blockchain

Que decir:
> "Cinco pasos. Primero, instalas el SDK -- 30 segundos. Segundo, tu agente toma una decision como siempre. Tercero, esa decision pasa por 7 capas de verificacion deterministica -- constitution, AST, supervisor, adversarial, memoria, Z3 y oracle. Ninguna usa LLMs. Cuarto, se genera una prueba matematica formal. Quinto, esa prueba se graba inmutablemente en Avalanche. Cualquier persona en el mundo puede verificarla."

---

**SLIDE 4 -- LAS 7 CAPAS (Steps -- 2:00 a 2:40)**

Visual: Torre de 7 bloques apilados, cada uno con nombre e icono:
- Constitution (reglas duras)
- AST (analisis estatico)
- Supervisor (meta-score)
- Adversarial (red-team)
- Memory (contexto historico)
- Z3 (prueba formal)
- Oracle (attestation on-chain)

Que decir:
> "Cada capa hace algo diferente. La Constitution bloquea violaciones obvias. El AST analiza codigo generado. El Supervisor pondera calidad, adherencia, completitud y formato. El Adversarial simula ataques. La Memoria detecta drift respecto al comportamiento historico. Z3 genera 8 teoremas matematicos probados para todas las entradas posibles. Y el Oracle graba la prueba en blockchain para siempre. Todo en menos de 30 milisegundos. Cero tokens de LLM consumidos."

---

**SLIDE 5 -- NUMEROS (News -- 2:40 a 3:10)**

Visual: 4 numeros grandes en cuadricula 2x2:
- 3,700 tests
- 0% FPR (falsos positivos)
- 30ms por verificacion
- 8 teoremas Z3 PROVEN

Que decir:
> "No es un prototipo. 3,700 tests automatizados, todos pasando. Cero por ciento de falsos positivos -- porque no estamos adivinando, estamos probando matematicamente. 30 milisegundos por verificacion -- mas rapido que la latencia de un API call. Y 8 teoremas Z3 probados formalmente para TODOS los inputs posibles -- no sampling, no heuristicas. Prueba exhaustiva."

---

**SLIDE 6 -- DIFERENCIADOR (News -- 3:10 a 3:40)**

Visual: Tabla comparativa simple:

| | DOF | Otros |
|---|---|---|
| Metodo | Z3 formal | LLM-based |
| Falsos positivos | 0% | Variable |
| Manipulable | No | Si (prompt injection) |
| On-chain | Si (Avalanche) | No |
| Latencia | 30ms | 2-5 seg |

Que decir:
> "Aqui esta la diferencia en blanco y negro. Otros frameworks usan LLMs que pueden ser manipulados, tienen falsos positivos variables, y no generan pruebas verificables por terceros. DOF usa matematicas que no se pueden sobornar, tiene cero falsos positivos, y graba cada prueba en blockchain. No es una mejora incremental. Es una categoria diferente."

---

**SLIDE 7 -- DEMO EN VIVO (Contributions -- 3:40 a 4:30)**

Visual: Terminal en vivo o video de 30 segundos mostrando:
```bash
pip install dof-sdk
dof verify-states      # 8/8 PROVEN
dof health             # sistema verde
```

Que decir:
> "Esto no es un mockup. Instalemos ahora. `pip install dof-sdk`. Listo. `dof verify-states` -- 8 de 8 teoremas probados. `dof health` -- sistema verde. 21 attestations ya grabadas en Avalanche mainnet. Esto ya esta funcionando."

---

**SLIDE 8 -- CIERRE CON CONTRIBUCION (4:30 a 5:00)**

Visual: Pantalla negra. Texto: "Matematicas, no promesas." Abajo: `pip install dof-sdk` y QR code al repo.

Que decir:
> "Antes de estos 5 minutos, governance de agentes significaba confiar en logs, dashboards y otros LLMs. Ahora saben que existe una alternativa matematicamente rigurosa. No les estoy pidiendo que confien en mi. Les estoy pidiendo que verifiquen. El SDK es abierto. Las pruebas Z3 son auditables. Los attestations estan en blockchain publica. La era de 'confia en mi, el agente se porto bien' se acabo. Ahora se puede probar. `pip install dof-sdk`."

---

### C) LANDING PAGE / WEB

#### Hero Section = Promesa de Empoderamiento

**Headline:**
> Tu agente de IA maneja millones. Como pruebas que hizo lo correcto?

**Subheadline:**
> DOF-MESH es el unico framework que certifica matematicamente el comportamiento de agentes autonomos. No logs. No monitoring. Prueba formal Z3 + attestation on-chain.

**CTA principal:** `pip install dof-sdk` -- Tu primera verificacion en 30 segundos

---

#### Seccion Problema = Near Miss

**Titulo de seccion:** La trampa del "IA vigila IA"

**Copy:**
> La solucion obvia para controlar agentes autonomos es usar otro modelo de IA como vigilante. 685 proyectos en el hackathon global mas grande lo hacen asi.
>
> El problema: un LLM vigilante puede ser manipulado con el mismo prompt injection que deberia detectar. Puede alucinar que todo esta bien cuando un atacante esta drenando tu treasury. Puede ser "convencido" de ignorar una violacion.
>
> Es como poner a un ladron a vigilar a otro ladron.
>
> DOF no usa LLMs para governance. Usa verificacion formal Z3 -- la misma tecnologia que certifica aviones y reactores nucleares. No se puede sobornar. No alucina. No opina. Prueba.

---

#### Seccion Solucion = VSN-C

**Titulo:** Como funciona DOF-MESH

**Paso 1 -- Conecta (30 segundos)**
```bash
pip install dof-sdk
```
> SDK ligero. Framework agnostic. Funciona con CrewAI, LangGraph, AutoGen, o tu propio codigo.

**Paso 2 -- 7 Capas de Verificacion (0 LLMs, 30ms)**
> Cada decision de tu agente pasa por Constitution, AST, Supervisor, Adversarial, Memoria, Z3 y Oracle. Todo determinista. Sin tokens consumidos. Sin latencia adicional perceptible.

**Paso 3 -- Prueba Matematica Z3**
> 8 teoremas probados para TODAS las entradas posibles. No sampling. No heuristicas. Prueba exhaustiva. 0% falsos positivos.

**Paso 4 -- Attestation On-Chain**
> Cada prueba se graba inmutablemente en Avalanche C-Chain. Cualquier regulador, auditor o cliente puede verificarla de forma independiente. 21 attestations ya en mainnet.

**Paso 5 -- Dashboard y Alertas**
> Visualiza el comportamiento de tu flota de agentes en tiempo real. Recibe alertas instantaneas si un agente intenta violar governance. Historial completo auditable.

---

#### Seccion Numeros

| Metrica | Valor |
|---|---|
| Tests automatizados | 3,700 pasando |
| Falsos positivos | 0% |
| Latencia por verificacion | 30ms |
| Teoremas Z3 probados | 8/8 exhaustivos |
| Attestations on-chain | 21 en Avalanche mainnet |
| Modulos core | 127 |
| Proveedores LLM soportados | 8+ |

---

#### Seccion Pricing

| Free | Pro | Enterprise |
|---|---|---|
| $0/mes | $49/mes | $299/mes |
| 100 verificaciones/mes | Ilimitado | Ilimitado + SLA 99.9% |
| SDK completo | API dedicada | Certificaciones on-chain |
| Comunidad | Soporte email | Soporte dedicado + dashboard privado |
| | Reportes | Compliance reports (MiCA, SEC) |

---

#### CTA Final = Cierre con Contribucion

**Titulo:** La era de "confia en mi" se acabo

**Copy:**
> Antes de visitar esta pagina, governance de agentes significaba confiar en logs que el mismo agente genero. Ahora tienes una alternativa: prueba matematica, inmutable, verificable por cualquier tercero.
>
> La pregunta no es si necesitas governance verificable. La pregunta es cuanto te va a costar no tenerla.

**Boton primario:** Instalar SDK (gratis)
**Boton secundario:** Agendar demo enterprise

---

### D) TWEETS / POSTS DE UNA LINEA (Social Media)

Cada version usa una S diferente del framework de Winston:

**1. Simbolo (el buho DOF)**
> El buho no duerme, no alucina y no se puede sobornar. Tampoco DOF. Verificacion formal Z3 para agentes autonomos. `pip install dof-sdk`

**2. Slogan**
> "Otros frameworks usan IA para vigilar IA. Nosotros usamos matematicas." -- DOF-MESH: prueba formal, no opiniones. 0% FPR. 30ms.

**3. Sorpresa**
> Analizamos 685 proyectos de agentes autonomos en Synthesis 2026. Cuantos verifican governance formalmente? Cero. DOF es el primero. 8 teoremas Z3 probados para TODAS las entradas.

**4. Saliente (relevancia personal)**
> Tu agente DeFi maneja $10M en TVL. Si un prompt injection lo engana, no pierdes un log -- pierdes $10M. DOF bloquea la transaccion ANTES de que firme. Matematicamente.

**5. Story (historia)**
> Un agente "perfecto" funciono 90 dias. Dia 91, un edge case dreno $2.3M. Los logs decian "exito." Con DOF, la primera transaccion sospechosa se bloqueaba. Matematicas > logs.

---

### E) EMAIL DE CONTACTO FRIO (Outbound)

#### Subject Line = Sorpresa

> 685 proyectos de agentes autonomos. Cero verifican governance formalmente.

#### Primer parrafo = Promesa de Empoderamiento

> Hola [Nombre],
>
> En 2 minutos de lectura vas a conocer la unica forma de probar MATEMATICAMENTE que un agente de IA se porto bien. No otro LLM vigilando. Prueba formal -- la misma tecnologia que certifica aviones.

#### Cuerpo = Near Miss + Steps

> **El problema que nadie resuelve:**
> Hoy, la "solucion" para controlar agentes autonomos es usar otra IA como supervisor. Suena logico hasta que te das cuenta de que el supervisor puede ser manipulado con el mismo prompt injection que deberia detectar. Es un loop de confianza circular.
>
> **DOF-MESH rompe ese loop:**
>
> 1. **Sin LLMs en governance.** Toda verificacion es deterministica (regex, AST, Z3).
> 2. **Prueba formal Z3.** 8 teoremas probados para TODAS las entradas posibles. 0% falsos positivos.
> 3. **On-chain.** Cada prueba se graba en Avalanche. Verificable por cualquier tercero.
> 4. **30ms.** Mas rapido que un API call. Tu agente ni nota que esta siendo verificado.
> 5. **`pip install dof-sdk`.** 30 segundos para empezar.
>
> Ya tenemos 3,700 tests pasando, 21 attestations en mainnet, y un SDK publicado en PyPI.

#### Cierre = Contribucion + CTA

> No te estoy pidiendo que confies en mi. Te estoy pidiendo que verifiques. El SDK es abierto, las pruebas Z3 son auditables, y los attestations estan en blockchain publica.
>
> Si tus agentes manejan dinero o decisiones criticas, 15 minutos de tu tiempo podrian ahorrarte millones.
>
> Tienes disponibilidad esta semana para una demo de 15 minutos?
>
> Cyber Paisa -- Enigma Group
> DOF-MESH: Matematicas, no promesas.

---

### F) PARA ENTRENAMIENTO DE AGENTES DOF

#### F.1 -- Como un agente CrewAI de DOF usa las 5S al comunicar resultados

Los agentes DOF no solo ejecutan tareas -- comunican resultados. Un resultado mal comunicado es un resultado perdido. Cada agente de la Mesh debe aplicar las 5S de Winston al reportar:

| S | Aplicacion en output del agente |
|---|---|
| **Simbolo** | Incluir un indicador visual claro del estado: `[PROVEN]`, `[BLOCKED]`, `[WARNING]`, `[PASS]` |
| **Slogan** | Primera linea del output resume la conclusion en una frase |
| **Sorpresa** | Si el resultado contradice expectativas, decirlo explicitamente: "Resultado inesperado: X" |
| **Saliente** | Conectar el resultado con el impacto concreto: "Esto significa que el agente NO puede ejecutar Y" |
| **Story** | Si es un reporte largo, usar narrativa temporal: "El agente intento X, la capa Y detecto Z, se bloqueo antes de W" |

**Regla:** Todo output de agente DOF debe cumplir al menos 3 de las 5S. Si no las cumple, el Supervisor puede penalizarlo en la metrica de calidad de comunicacion.

---

#### F.2 -- Prompt Template para Agentes DOF (Winston-Aligned)

```
FORMATO DE RESPUESTA (Winston Communication Framework):

1. PRIMERA LINEA: Conclusion en una frase. Que paso y que significa.
   Incluir indicador: [PROVEN] [BLOCKED] [WARNING] [PASS] [FAIL]

2. RELEVANCIA: Una linea explicando por que esto importa para la tarea actual.
   Patron: "Esto significa que [impacto concreto]."

3. EVIDENCIA: Los datos o pruebas que soportan la conclusion.
   Si hay algo inesperado, marcarlo: "Resultado inesperado: [detalle]."

4. ACCION SIGUIENTE: Que debe hacerse ahora.
   Patron: "Siguiente paso: [accion especifica]."

REGLAS:
- NO empezar con "Aqui esta el resultado de..."
- NO terminar con "Espero que esto sea util" o "Si necesitas mas informacion..."
- PRIMERA linea = conclusion, no contexto
- ULTIMA linea = accion, no agradecimiento
- Si bloqueas algo, explica POR QUE con la prueba especifica (Near Miss)
```

---

#### F.3 -- Metrica de Calidad de Comunicacion (CQ Score)

Nueva metrica para el Supervisor (`core/supervisor.py`), alineada con las 5S de Winston:

```
CQ (Communication Quality) Score = 0-100

Componentes:
  - Claridad de conclusion (Slogan)           : 0-25 pts
    La primera linea resume la conclusion? Es accionable?

  - Relevancia del impacto (Saliente)          : 0-25 pts
    Conecta el resultado con el impacto concreto?

  - Estructura narrativa (Story + Simbolo)     : 0-20 pts
    Tiene indicadores visuales claros? Sigue orden logico?

  - Elemento diferenciador (Sorpresa)          : 0-15 pts
    Si hay algo inesperado, lo marca explicitamente?

  - Cierre accionable (Contribucion)           : 0-15 pts
    Termina con una accion concreta, no con relleno?
```

**Evaluacion deterministica (sin LLM):**

```python
def evaluate_communication_quality(output: str) -> int:
    score = 0

    lines = output.strip().split('\n')
    first_line = lines[0] if lines else ""
    last_line = lines[-1] if lines else ""

    # Claridad de conclusion (25 pts)
    indicators = ['[PROVEN]', '[BLOCKED]', '[WARNING]', '[PASS]', '[FAIL]']
    if any(ind in first_line for ind in indicators):
        score += 15
    if len(first_line) < 200 and len(first_line) > 10:
        score += 10

    # Relevancia del impacto (25 pts)
    salience_patterns = [
        'esto significa', 'impacto:', 'consecuencia:',
        'this means', 'impact:', 'therefore'
    ]
    if any(p in output.lower() for p in salience_patterns):
        score += 25

    # Estructura narrativa (20 pts)
    if any(ind in output for ind in indicators):
        score += 10
    if any(h in output for h in ['##', '**', '- ', '1.', '2.']):
        score += 10

    # Elemento diferenciador (15 pts)
    surprise_patterns = [
        'inesperado', 'unexpected', 'nota:', 'alerta:',
        'resultado inesperado', 'warning:', 'anomaly'
    ]
    if any(p in output.lower() for p in surprise_patterns):
        score += 15

    # Cierre accionable (15 pts)
    action_patterns = [
        'siguiente paso', 'next step', 'accion:',
        'action:', 'recomendacion:', 'recommendation:'
    ]
    filler_patterns = [
        'espero que', 'hope this', 'si necesitas',
        'if you need', 'let me know', 'no dudes'
    ]
    if any(p in last_line.lower() for p in action_patterns):
        score += 15
    if any(p in last_line.lower() for p in filler_patterns):
        score -= 10

    return max(0, min(100, score))
```

**Integracion con el Supervisor:**

El CQ Score se incorpora como un componente adicional en la formula del Supervisor:

```
Score final = Q(0.35) + A(0.20) + C(0.20) + F(0.10) + CQ(0.15)

Donde:
  Q  = Quality (calidad del contenido)
  A  = Adherence (adherencia a la tarea)
  C  = Completeness (completitud)
  F  = Format (formato estructural)
  CQ = Communication Quality (framework Winston)
```

---

## PARTE III -- CHECKLIST RAPIDO

Antes de cualquier comunicacion publica de DOF-MESH, verifica:

- [ ] Los primeros 60 segundos/la primera linea dicen que GANA la audiencia? (no que haces TU)
- [ ] Hay al menos 3 de las 5S presentes?
- [ ] Incluyes un Near Miss? (que parece funcionar pero no)
- [ ] La estructura sigue VSN-C? (Vision, Steps, News, Contributions)
- [ ] Terminas con CONTRIBUCION, no con "gracias" o resumen?
- [ ] Cada slide/seccion tiene UNA sola idea?
- [ ] Los numeros son concretos? (3,700 tests, 0% FPR, 30ms, 8 teoremas)
- [ ] El CTA es especifico y accionable? (`pip install dof-sdk`, no "visitanos")

---

## PARTE IV -- FRASES PROHIBIDAS Y REEMPLAZOS

| Nunca digas | Di esto |
|---|---|
| "Somos una startup de IA" | "Certificamos matematicamente agentes autonomos" |
| "Nuestro producto hace monitoring" | "Generamos pruebas formales, no logs" |
| "Usamos inteligencia artificial" | "Usamos verificacion formal Z3 -- la tecnologia de aviacion" |
| "Gracias por su tiempo" | "Lo que acaban de ver no existia hace 6 meses. `pip install dof-sdk`" |
| "Alguna pregunta?" | "La unica pregunta es: cuanto les cuesta NO tener prueba formal?" |
| "Nuestro framework es mejor" | "685 proyectos en Synthesis. Cero con verificacion formal. Nosotros somos el primero." |
| "Es como Datadog para agentes" | "Datadog registra lo que paso. DOF prueba que debio pasar." |
| "Confia en nosotros" | "No confies en nosotros. Verifica. El SDK es abierto, las pruebas son auditables." |

---

## Referencias

- Winston, P. (2020). *Make It Clear: Speak and Write to Persuade and Inform.* MIT Press.
- Winston, P. (2019). How to Speak. MIT OpenCourseWare. [Conferencia mas vista del MIT]
- DOF-MESH Competition Bible: `docs/COMPETITION_BIBLE.md`
- DOF-MESH ICP & Use Cases: `docs/ICP_AND_USECASES.md`
- DOF-MESH Monetization Strategy: `docs/DOF_MONETIZATION_STRATEGY.md`
- DOF-MESH Pitch Ruta Emprendimiento: `docs/PITCH_RUTA_EMPRENDIMIENTO.md`

---

*Documento de referencia del Mesh Legion. Toda comunicacion externa de DOF-MESH debe seguir este framework.*
*Cyber Paisa -- Enigma Group -- 27 marzo 2026*
