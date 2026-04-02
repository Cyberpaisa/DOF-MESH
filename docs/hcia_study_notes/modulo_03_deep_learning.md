# 📓 Módulo 03: Deep Learning y Arquitecturas (HCIA-AI V4.0)

Este módulo es la "carne" de la IA moderna. Aquí pasamos de fórmulas simples a estructuras complejas que imitan la cognición.

---

## 1. Redes Neuronales Profundas (ANN)
- **Capa de Entrada:** Recibe los tensores (datos).
- **Capas Ocultas (Hidden Layers):** Donde ocurre la "magia" de la extracción de características.
- **Funciones de Activación:** 
    - **ReLU:** La más común hoy (apaga neuronas negativas, acelera el entrenamiento).
    - **Softmax:** Usada al final para darnos probabilidades (Ej. 90% Gato, 10% Perro).
- **El Proceso:** Forward Propagation (Cálculo del resultado) -> Loss Function (Cálculo del error) -> Backpropagation (Ajuste de pesos).

## 2. Redes Neuronales Convolucionales (CNN) - "Visión"
- **Propósito:** Analizar imágenes y datos espaciales.
- **Convolución:** Filtros que pasan sobre la imagen buscando bordes, texturas y formas.
- **Pooling (Subsambling):** Reduce el tamaño de los datos manteniendo lo más importante (Ej. Max Pooling).
- **Aplicación:** Reconocimiento facial, diagnóstico por imagen.

## 3. Redes Neuronales Recurrentes (RNN) - "Memoria"
- **Propósito:** Analizar secuencias y datos temporales (Texto, Audio, Series de tiempo).
- **El Problema:** La "desvanecimiento del gradiente" (olvidan lo que pasó hace mucho).
- **Solución (LSTM/GRU):** Celdas con "puertas" que deciden qué información guardar y qué olvidar.
- **Aplicación:** Traducción básica, predicción de precios de tokens.

## 4. La Revolución: Transformers y Atención
- **Attention Is All You Need (2017):** La arquitectura que jubiló a las RNN.
- **Mecanismo de Atención:** Permite que la IA mire **todas** las palabras de una frase al mismo tiempo y entienda la relación entre ellas (Contexto Global).
- **Codificador y Decodificador:** La estructura base de modelos como GPT, BERT y los nuevos modelos de Huawei.

---

### 🛡️ Notas de la Legion:
Entender la **Atención** es crucial para nuestro "Sovereign Agent". Permite que el sistema no se pierda en logs largos y mantenga el objetivo de la misión (nuestro `Identity Root`) siempre presente en cada decisión.

---
*Próximo paso: Frameworks de Desarrollo (PyTorch vs MindSpore) (Día 2.2).*
