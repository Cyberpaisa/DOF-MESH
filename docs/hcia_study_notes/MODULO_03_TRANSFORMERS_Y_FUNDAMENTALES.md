# HCIA-AI V4.0 - Módulo 3: Arquitectura Transformer y Modelos Fundacionales

![Transformer Portada](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-192.png)

## 1. El Mecanismo de Atención (Attention)
![Atención](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-187.png)

Inspirado en la cognición humana, el mecanismo de atención permite a la red enfocarse en las partes más importantes de la entrada e ignorar el resto. 

### Conceptos Centrales (Q, K, V):
- **Query (Consulta):** Lo que estamos buscando.
- **Key (Clave):** La etiqueta de la información disponible.
- **Value (Valor):** La información real contenida en la clave.

**Proceso:** Se calcula la similitud entre Query y Key para obtener un peso, y se realiza una suma ponderada de los Valores.

---

## 2. La Revolución de los Transformers
![Arquitectura Transformer](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-193.png)

Propuesto por Google en 2017 ("Attention Is All You Need"), el Transformer eliminó la necesidad de recurrencia (RNN) y convolución (CNN) para el lenguaje.

### Ventajas:
- **Paralelismo:** A diferencia de las RNN, puede procesar todas las palabras de una frase al mismo tiempo.
- **Relaciones de Largo Alcance:** Gracias a la **Auto-Atención (Self-Attention)**, puede entender la relación entre palabras muy lejanas en un texto.
- **Escalabilidad:** Permite entrenar modelos con miles de millones de parámetros.

---

## 3. Modelos Fundacionales (Foundation Models)
![Modelos Fundacionales](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-196.png)

Son modelos entrenados con cantidades masivas de datos que pueden adaptarse a múltiples tareas.

- **GPT (Generative Pre-trained Transformer):** Utiliza solo el **Decoder** del Transformer. Se especializa en predecir la siguiente palabra y generar texto coherente. ![GPT](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-197.png)
- **BERT (Bidirectional Encoder Representations from Transformers):** Utiliza solo el **Encoder**. Analiza el contexto en ambas direcciones, ideal para entender el significado profundo y responder preguntas. ![BERT](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-198.png)

### El Futuro: Soberanía y DeepSeek
Este conocimiento es la base de modelos como **DeepSeek V3/R1**, que utilizan variaciones avanzadas como **MoE (Mixture of Experts)** para lograr eficiencia extrema. 🛡️🥇

---

*(Fin del Módulo 3 y del Capítulo de Deep Learning)*
