# 📓 Módulo 02: Matemáticas y Fundamentos de ML (HCIA-AI V4.0)

Este módulo es el cimiento técnico. Sin estas matemáticas, la IA es una "caja negra"; con ellas, es ingeniería predecible.

---

## 1. Álgebra Lineal: El Lenguaje de los Datos
- **Escalar:** Un solo número (Ej. Temperatura).
- **Vector:** Lista de números (Ej. Coordenadas [x, y, z] o características de un cliente).
- **Matriz:** Tabla de números (Bidimensional). La forma en que representamos imágenes (píxeles).
- **Tensor:** Arreglo multidimensional (3D o más). Es como fluyen los datos en Deep Learning.
- **Operaciones Críticas:** Producto punto (Dot Product) y Transposición.

## 2. Cálculo: El Motor de Aprendizaje
- **Derivada:** Mide qué tan rápido cambia una función. En IA, nos dice hacia dónde mover los pesos para reducir el error.
- **Cálculo Multivariable (Gradiente):** Es un vector de derivadas parciales. 
- **Descenso de Gradiente:** El algoritmo que "baja la montaña de error" hasta encontrar el punto más bajo (la mejor precisión).
- **Regla de la Cadena:** La base matemática del **Backpropagation**. Permite calcular cómo cada capa de la red contribuye al error final.

## 3. Probabilidad y Estadística: La Incertidumbre
- **Distribuciones (Normal/Gaussiana):** La mayoría de los datos reales siguen esta curva. Es vital para la inicialización de pesos.
- **Varianza y Desviación Estándar:** Miden qué tan "esparcidos" están los datos.
- **Teorema de Bayes:** Fundamental para modelos probabilísticos y clasificación.

## 4. Tipos de Aprendizaje Automático (ML)
1. **Aprendizaje Supervisado:** El modelo aprende de datos etiquetados (Ej. "Esta imagen es un gato"). Incluye **Regresión** y **Clasificación**.
2. **Aprendizaje No Supervisado:** El modelo busca patrones en datos sin etiquetas. Incluye **Clustering** (Agrupamiento) y Reducción de Dimensionalidad.
3. **Aprendizaje por Refuerzo (RL):** El modelo aprende por "Premios y Castigos" interactuando con un entorno (Base de agentes autónomos).

---

### 🛡️ Notas de la Legion:
Para nosotros, el **Álgebra Lineal** es lo que permite optimizar el uso de la GPU (operaciones masivas de matrices en paralelo). En el eSpace de Conflux, entender la estadística nos ayudará a modelar el comportamiento del mercado con mayor precisión.

---
*Próximo paso: Profundizar en Aprendizaje Profundo (Día 2.1).*
