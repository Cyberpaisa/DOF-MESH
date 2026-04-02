# HCIA-AI V4.0 - Módulo 2: Tecnologías de IA

![Contenido Módulo 2](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-35.png)

## ¿Qué es un Modelo Fundacional? (Parte 1)
![Foundation Model 1](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-36.png)

Un **Modelo Fundacional** se refiere a un modelo que:
- Se entrena con datos a gran escala.
- Tiene un número masivo de parámetros.
- Posee funcionalidades potentes.

---

## ¿Qué es un Modelo Fundacional? (Parte 2)
![Foundation Model 2](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-37.png)

### Principios detrás de los Grandes Modelos:
1. **Scaling Law (Ley de Escalamiento):** A medida que el tamaño del modelo aumenta exponencialmente, el rendimiento del modelo aumenta linealmente.
2. **Chinchilla Law (Ley de Chinchilla):** El tamaño del modelo y el número de tokens de entrenamiento deben escalar a ritmos iguales.
3. **Emergent Abilities (Habilidades Emergentes):** Cuando el modelo alcanza cierto tamaño y escala, muestra una mejora repentina e inesperada en el rendimiento y la capacidad de generalización.

**Lo que hace que un modelo sea "Grande":**
- **Datos a gran escala:** Datos extensos para cubrir casi todos los escenarios del mundo real.
- **Modelo a gran escala:** Alta capacidad para adaptarse a casi cualquier escenario.
- **Cómputo a gran escala:** Recursos informáticos robustos para manejar cálculos intrincados.

---

## ¿De dónde viene un Modelo Fundacional?
![Origen Modelo](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-38.png)
![Transformer Origin](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-39.png)

- **Seq2Seq (2014):** En 2014, investigadores de traducción automática propusieron el modelo Seq2Seq. Fue una nueva forma de implementar la traducción automática de extremo a extremo basada en la arquitectura RNN.
- **Transformer (2017):** El equipo de investigación de Google propuso el **Transformer** en 2017. Con el Transformer como infraestructura, los modelos fundacionales se desarrollaron en diferentes ramas.

---

## De Pequeño a Grande
![Evolución](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-40.png)

- **Cómputo:** Capacidad de cómputo de nivel EFLOPS.
- **Datos:** Conjuntos de datos con hasta billones de tokens para entrenar un solo modelo.
- **Algoritmo:** De millones de parámetros a miles de millones (billones en inglés) de parámetros.
- **Evolución:** AlexNet -> VGG -> ResNet -> Transformer -> ViT -> GPT -> LLaMA -> GLM -> DeepSeek.

---

## Tamaños de los Modelos Fundacionales
![Tamaños Modelos](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-41.png)

Un modelo fundacional suele tener cientos de millones a miles de millones de parámetros.
- **Modelos Pequeños:** ResNet101 (44M), VGG16 (138M).
- **Modelos Grandes:** GPT-3 (175B), GPT-4 (Estimado 1.7T), LLaMA3 (15T tokens, hasta 70B+ params).

---

## Modelos Grandes vs. Modelos Pequeños
![Dataset](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-42.png)
![Comparativo](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-43.png)

- **Modelos Pequeños:** Ligeros y altamente eficientes. Adecuados cuando los recursos son limitados (ej. un reloj que solo marca la hora).
- **Modelos Grandes:** Mayores capacidades de procesamiento y precisión. Adecuados para alta complejidad (ej. un smartwatch que mide tiempo, ritmo cardíaco, sueño, etc.).

---

## ¿Cómo aprende un Modelo Fundacional?
![Aprendizaje](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-44.png)

Se basan en un modelo básico **pre-entrenado** en datos masivos y luego se realiza un **ajuste fino (fine-tuning)** basado en datos específicos de la industria.

---

## Habilidades Emergentes: ICL y CoT
![Emergencia](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-46.png)
![CoT](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-47.png)

1. **In-context Learning (ICL):** Ayuda a los algoritmos a entender el significado y las relaciones entre palabras en una oración sin entrenamiento adicional.
2. **Chain-of-thought (CoT - Cadena de Pensamiento):** Los usuarios escriben procesos de inferencia paso a paso para que el modelo pueda realizar tareas de inferencia complejas.

---

*(Continuará con la historia de DeepSeek y sus aplicaciones...)*
