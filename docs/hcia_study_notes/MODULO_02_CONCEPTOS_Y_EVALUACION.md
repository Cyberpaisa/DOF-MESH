# HCIA-AI V4.0 - Módulo 2: Conceptos Clave y Evaluación de Modelos

![Procesamiento de Datos](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-115.png)

## 1. Importancia del Procesamiento de Datos
Los datos determinan el alcance de las capacidades de un modelo. "Basura entra, basura sale" (GIGO).
- **Limpieza de Datos:** Eliminar ruido, valores atípicos y completar valores faltantes.
- **Estandarización:** Asegurar que los datos tengan rangos similares para mejorar la precisión.
- **Reducción de Dimensionalidad:** Simplificar atributos para evitar la "maldición de la dimensionalidad".

**Dato Curioso:** Los científicos de datos pasan el **60% de su tiempo** limpiando y organizando datos.
![Carga de Trabajo](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-116.png)

---

## 2. Ingeniería de Características (Feature Engineering)
![Selección de Características](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-120.png)

No todas las características son útiles. La selección de características ayuda a:
- Simplificar modelos para que sean fáciles de interpretar.
- Reducir el tiempo de entrenamiento.
- Evitar el **Sobreajuste (Overfitting)**.

**Métodos de Selección:**
- **Filtro (Filter):** Evalúa la relevancia estadística de cada característica de forma independiente.
- **Envolvente (Wrapper):** Evalúa subconjuntos de características entrenando modelos reales (ej. Eliminación recursiva).
- **Embebido (Embedded):** La selección ocurre durante el modelado (ej. Regularización LASSO).

---

## 3. ¿Qué hace a un "Buen Modelo"?
![Buen Modelo](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-127.png)

1. **Generalización:** Capacidad de predecir correctamente datos nuevos (los que no vio en el entrenamiento). Es el factor más importante.
2. **Explicabilidad:** Los resultados deben ser fáciles de entender.
3. **Velocidad de Predicción:** El tiempo que tarda el modelo en dar una respuesta.

---

## 4. Subajuste (Underfitting) vs. Sobreajuste (Overfitting)
![Overfitting](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-129.png)
![Capacidad del Modelo](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-130.png)

- **Subajuste (Underfitting):** El modelo es demasiado simple. No aprende los patrones ni en el entrenamiento ni en el test.
- **Sobreajuste (Overfitting):** El modelo es demasiado complejo. Aprende "de memoria" el ruido de los datos de entrenamiento pero falla en datos nuevos.

### Sesgo (Bias) vs. Varianza (Variance)
![Sesgo y Varianza](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-131.png)

- **Sesgo (Bias):** Error por suposiciones erróneas (modelo muy simple).
- **Varianza (Variance):** Error por alta sensibilidad a pequeñas fluctuaciones en los datos (modelo muy complejo).
- **Meta:** Bajo Sesgo y Baja Varianza.

---

## 5. Evaluación del Rendimiento
![Métricas Regresión](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-133.png)

### Regresión:
- **MAE (Error Absoluto Medio):** Promedio de las diferencias absolutas.
- **MSE (Error Cuadrático Medio):** Promedio de los errores al cuadrado (penaliza errores grandes).
- **$R^2$ (Coeficiente de Determinación):** Indica qué tan bien el modelo explica la variabilidad de los datos (Rango 0 a 1).

### Clasificación:
![Matriz de Confusión](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-134.png)
- **Precisión (Accuracy):** $\frac{TP + TN}{TP + TN + FP + FN}$ (Aciertos totales).
- **Exactitud (Precision):** $\frac{TP}{TP + FP}$ (De los que dije que eran positivos, ¿cuántos lo eran?).
- **Sensibilidad (Recall):** $\frac{TP}{TP + FN}$ (De los que ERAN positivos, ¿cuántos detecté?).

---

*(Fin de Conceptos Clave)*
