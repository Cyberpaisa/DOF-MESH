# HCIA-AI V4.0 - Módulo 3: Entrenamiento de Redes Neuronales

![Entrenamiento Portada](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-128.png)

## 1. ¿Cómo aprende una Red Neuronal?
![Proceso de Aprendizaje](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-130.png)

A diferencia del ML tradicional, donde el humano extrae las características (features), en el **Deep Learning** la red aprende a extraer automáticamente las características más importantes de los datos brutos.

### El Ciclo de Aprendizaje:
1. **Prueba de Simulación:** La red da una respuesta inicial.
2. **Reflexión (Cálculo del Error):** Se compara el resultado con la verdad (etiqueta).
3. **Ajuste de Parámetros:** Se modifican los pesos para reducir el error en la siguiente vuelta.

---

## 2. Funciones de Pérdida (Loss Functions)
![Loss Functions](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-131.png)

Miden qué tan "equivocada" está la red.
- **Error Cuadrático Medio (MSE):** Usada principalmente en tareas de regresión.
- **Entropía Cruzada (Cross Entropy):** El estándar para tareas de clasificación. Mide la diferencia entre dos distribuciones de probabilidad.

---

## 3. Propagación hacia Atrás (Backpropagation) y Regla de la Cadena
![Backprop](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-136.png)

Es el mecanismo matemático para actualizar los pesos.
- **Propagación hacia Adelante:** Los datos fluyen de la entrada a la salida.
- **Propagación hacia Atrás:** El error fluye de la salida hacia la entrada, repartiendo la "culpa" a cada peso mediante la **Regla de la Cadena** (derivadas parciales).

### Problemas Comunes:
- **Desvanecimiento del Gradiente (Vanishing Gradient):** El error se vuelve tan pequeño al viajar hacia atrás que las primeras capas dejan de aprender. Solución: Usar ReLU o LSTM.
- **Explosión del Gradiente (Exploding Gradient):** El error se vuelve infinitamente grande. Solución: Recorte de gradiente (Gradient Clipping).

---

## 4. Optimizadores (Optimizers)
![Optimizadores](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-144.png)

Son herramientas para que la red converja más rápido al mínimo de la pérdida.
- **Momentum:** Como una bola de nieve que baja una montaña; gana inercia para superar "baches" locales.
- **AdaGrad:** Ajusta la tasa de aprendizaje por cada parámetro. Útil para datos dispersos.
- **RMSProp:** Mejora de AdaGrad que evita que el aprendizaje se detenga prematuramente.
- **Adam (Adaptive Moment Estimation):** Combina Momentum y RMSProp. Es el optimizador más utilizado actualmente por su robustez y velocidad. 🛡️🥇

---

*(Fin de Entrenamiento de Redes)*
