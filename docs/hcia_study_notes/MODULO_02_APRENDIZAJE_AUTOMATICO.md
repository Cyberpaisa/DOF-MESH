# HCIA-AI V4.0 - Módulo 2: Introducción al Aprendizaje Automático (Machine Learning)

![Portada Capítulo 2](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-89.png)

## Objetivos del Módulo
![Objetivos](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-90.png)

Al completar este curso, entenderás:
- Definiciones de algoritmos y el proceso de aprendizaje automático.
- Conceptos clave como hiperparámetros, descenso de gradiente y validación cruzada.
- Algoritmos comunes de aprendizaje automático.

---

## ¿Qué es el Aprendizaje Automático? (Experiencia, Tarea, Rendimiento)
![Algoritmos ML 1](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-92.png)
![Algoritmos ML 2](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-93.png)

Se dice que un programa de computadora aprende de la **Experiencia E** con respecto a una **Tarea T** y una **Medida de Rendimiento P**, si su rendimiento en T (medido por P) mejora con la experiencia E.

**Ejemplo: Aprender a jugar Go**
- **Experiencia E:** Partidas jugadas contra sí mismo (Aprendizaje no supervisado).
- **Tarea T:** Jugar al Go y ganar.
- **Rendimiento P:** Tasa de victorias contra oponentes humanos o IA.

---

## ML vs. Métodos Tradicionales (Basados en Reglas)
![Diferencias](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-95.png)

- **Basado en Reglas:** Programación explícita. El humano define las reglas (ej. "Si X, entonces Y").
- **Aprendizaje Automático:** La máquina aprende las reglas a partir de los datos. Se usa cuando las reglas son demasiado complejas o cambian con el tiempo (ej. reconocimiento de voz).

---

## Tipos de Aprendizaje Automático
![Tipos de ML](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-101.png)

1. **Aprendizaje Supervisado:** Tenemos datos etiquetados (ej. fotos de perros con la etiqueta "perro"). El modelo aprende a mapear entradas a salidas.
   - **Regresión:** Salida continua (ej. precio de una casa).
   - **Clasificación:** Salida discreta (ej. ¿es spam?).

2. **Aprendizaje No Supervisado:** Datos sin etiquetas. El modelo busca estructuras ocultas.
   - **Clúster (Agrupamiento):** Agrupar clientes por similitud.

3. **Aprendizaje Reforzado:** El sistema aprende interactuando con el entorno. Recibe recompensas por acciones buenas y castigos por malas (ej. conducción autónoma).

---

## El Proceso de Machine Learning
![Proceso ML](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-112.png)

1. **Preparación de Datos:** Recolección.
2. **Limpieza de Datos:** Eliminar ruido o valores nulos.
3. **Extracción y Selección de Características:** Elegir qué variables importan.
4. **Entrenamiento del Modelo:** Ajustar parámetros.
5. **Evaluación del Modelo:** Probar con datos nuevos (Test Set).
6. **Despliegue e Integración:** Ponerlo en producción.
7. **Retroalimentación e Iteración:** Mejora continua.

---

*(Fin de la Introducción al ML)*
