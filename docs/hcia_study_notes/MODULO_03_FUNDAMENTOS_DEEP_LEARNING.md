# HCIA-AI V4.0 - Módulo 3: Fundamentos de Deep Learning y Redes Neuronales

![Deep Learning Portada](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-095.png)

## 1. El Perceptrón: El Átomo de la IA
![Perceptrón](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-100.png)

El perceptrón es la forma más simple de una red neuronal artificial (inventado en 1957).
- Recibe múltiples señales de entrada ($x_1, x_2, ...$).
- Cada entrada tiene un **peso** ($w_1, w_2, ...$) que indica su importancia.
- El neurón calcula la suma ponderada y, si supera un **umbral (threshold)**, se activa (salida 1), de lo contrario 0.

### Problema del XOR
![XOR Problem](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-104.png)
Un perceptrón simple solo puede resolver problemas **linealmente separables**. Para problemas complejos como el XOR, necesitamos un **Perceptrón Multicapa**.

---

## 2. Redes Neuronales Profundas (Deep Neural Networks - DNN)
![DNN](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-113.png)

La "profundidad" se refiere al número de capas ocultas entre la entrada y la salida. A mayor profundidad, mayor capacidad de identificar patrones complejos.

### Redes Neuronales Feedforward (FNN)
![FNN](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-114.png)
Es la arquitectura estándar donde la información viaja en una sola dirección (hacia adelante). 
- **Capa de Entrada:** Recibe los datos.
- **Capas Ocultas (Hidden Layers):** Realizan el procesamiento matemático.
- **Capa de Salida:** Entrega el resultado final (predicción).

---

## 3. Funciones de Activación
![Funciones de Activación](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-121.png)

Son el "ingrediente secreto" que permite a la red aprender relaciones NO lineales. Sin ellas, una red de mil capas sería equivalente a una sola capa lineal.

- **Sigmoid:** Comprime cualquier valor al rango (0, 1). Ideal para probabilidades.
- **Tanh (Tangente Hiperbólica):** Rango (-1, 1). Centrada en el origen, suele converger más rápido que la Sigmoid.
- **ReLU (Rectified Linear Unit):** Si la entrada es negativa, la salida es 0. Si es positiva, la salida es la misma entrada. Es la más popular hoy en día por su eficiencia.
- **Leaky ReLU:** Similar a ReLU pero permite un pequeño flujo para valores negativos para evitar "neuronas muertas".
- **Softmax:** Utilizada en la capa de salida para clasificación multiclase. Convierte las puntuaciones en una distribución de probabilidad que suma 1.

---

*(Fin de Fundamentos de Deep Learning)*
