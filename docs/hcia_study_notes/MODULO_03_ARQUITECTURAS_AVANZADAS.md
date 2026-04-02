# HCIA-AI V4.0 - Módulo 3: Arquitecturas de Deep Learning (CNN, RNN, LSTM)

![CNN Portada](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-158.png)

## 1. Redes Neuronales Convolucionales (CNN)
Las CNN son la arquitectura reina para el procesamiento de imágenes. Su diseño se inspira en el sistema visual biológico.

### Conceptos Clave:
- **Campo Receptivo Local:** Cada neurona solo "mira" una pequeña porción de la imagen (píxeles cercanos).
- **Compartición de Parámetros:** Se utiliza el mismo filtro (kernel) para escanear toda la imagen, lo que reduce drásticamente el número de parámetros.

### Estructura de una CNN:
![Arquitectura CNN](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-160.png)
1. **Capa Convolucional:** Extrae características (bordes, texturas, formas).
2. **Capa de Agrupación (Pooling):** Reduce el tamaño de la imagen (Max Pooling) para conservar solo lo más importante.
3. **Capa Totalmente Conectada (FC):** Clasifica las características extraídas en categorías (ej: Perro, Gato, Pájaro).

---

## 2. Redes Neuronales Recurrentes (RNN)
![RNN Architecture](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-168.png)

Diseñadas para datos secuenciales (texto, audio, video). A diferencia de las redes normales, las RNN tienen "memoria" del estado anterior.

- **Problema:** Tienen dificultad para recordar información a largo plazo debido al desvanecimiento del gradiente en el tiempo.

---

## 3. Long Short-Term Memory (LSTM)
![LSTM](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-172.png)

Una variante avanzada de RNN que soluciona el problema de la memoria a largo plazo mediante "puertas" (gates):
- **Puerta de Olvido (Forget Gate):** Decide qué información descartar.
- **Puerta de Entrada (Input Gate):** Decide qué nueva información guardar.
- **Puerta de Salida (Output Gate):** Decide qué enviar a la siguiente etapa.

---

## 4. Sobreajuste (Overfitting) y Regularización
![Overfitting](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-152.png)

El sobreajuste ocurre cuando el modelo "memoriza" el ruido de los datos de entrenamiento pero no sabe generalizar a datos nuevos.

### Técnicas para Combatirlo:
- **Regularización L1/L2:** Penaliza pesos excesivamente grandes.
- **Dropout:** Apaga neuronas aleatoriamente durante el entrenamiento para forzar a la red a ser más robusta. ![Dropout](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-156.png)
- **Parada Temprana (Early Stopping):** Detener el entrenamiento cuando el error en el conjunto de validación deja de bajar.

---

*(Fin de Arquitecturas de Deep Learning)*
