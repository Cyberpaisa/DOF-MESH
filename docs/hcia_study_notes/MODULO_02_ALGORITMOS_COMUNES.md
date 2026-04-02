# HCIA-AI V4.0 - Módulo 2: Algoritmos y Métodos de Entrenamiento

![Resumen de Algoritmos](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-148.png)

## 1. Descenso de Gradiente (Gradient Descent)
Es el algoritmo de optimización más común para minimizar la función de pérdida.
![Descenso de Gradiente](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-137.png)

- **BGD (Batch Gradient Descent):** Usa todos los datos del dataset para cada actualización de pesos. Es estable pero lento y costoso en recursos.
- **SGD (Stochastic Gradient Descent):** Usa un solo dato aleatorio por iteración. Muy rápido pero inestable (puede oscilar).
- **MBGD (Mini-Batch Gradient Descent):** Un equilibrio. Usa un pequeño grupo (batch) de datos por iteración. Es el estándar en la industria.

---

## 2. Hiperparámetros y Búsqueda
![Hiperparámetros](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-140.png)

- **Parámetros:** La máquina los aprende sola (ej. pesos de una red).
- **Hiperparámetros:** El humano los configura (ej. tasa de aprendizaje, número de árboles).

### Métodos de Búsqueda:
- **Búsqueda en Cuadrícula (Grid Search):** Prueba todas las combinaciones posibles. Exhaustivo y lento.
- **Búsqueda Aleatoria (Random Search):** Prueba combinaciones al azar. Más eficiente en espacios grandes.

---

## 3. Validación Cruzada (Cross-Validation)
![K-Fold](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-145.png)

Se divide el dataset en **K partes (folds)**. Se entrena con K-1 y se valida con la restante. Se repite K veces y se promedia el resultado. Esto asegura que el modelo sea robusto y no dependa de una división "suertuda" de los datos.

---

## 4. Algoritmos de Regresión
![Regresión Lineal](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-149.png)

### Regresión Lineal
Busca la relación cuantitativa entre variables (ej. $y = wx + b$). 
- **Regresión Polinomial:** Cuando los datos no siguen una línea recta (curvas).
- **Regularización (Evitar Overfitting):**
  - **Ridge (L2):** Añade la suma de los cuadrados de los pesos a la pérdida.
  - **Lasso (L1):** Añade la suma de los valores absolutos (útil para selección de variables).

---

## 5. Algoritmos de Clasificación

### Regresión Logística
A pesar de su nombre, se usa para **clasificación**. Usa la función Sigmoide para mapear cualquier valor a un rango entre 0 y 1 (probabilidad).

### Árboles de Decisión (Decision Trees)
Modelo intuitivo basado en reglas de decisión "Si ocurre X, entonces Y". 
- Se divide el espacio de datos basándose en el **Análisis de Información (Entropía o Gini)**.

### Máquinas de Soporte Vectorial (SVM)
Busca el **hiperplano óptimo** que separa las clases con el máximo margen posible.
![SVM](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-153.png)

---

## 6. Algoritmos de Agrupamiento (Clustering)

### K-Means
Agrupa datos en **K clústeres** basándose en la distancia al centroide más cercano.
1. Se inicializan K centroides aleatorios.
2. Se asignan puntos al centroide más cercano.
3. Se recalculan los centroides.
4. Se repite hasta que los centroides no cambien.

---

*(Fin del Módulo 2 Técnico)*
