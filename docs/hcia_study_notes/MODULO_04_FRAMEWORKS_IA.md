# HCIA-AI V4.0 - Módulo 4: Frameworks de Desarrollo de IA

![Frameworks Portada](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-206.png)

## 1. ¿Qué es un Framework de IA?
![Funciones Framework](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-210.png)

Un framework de IA es una biblioteca de software que proporciona herramientas, bibliotecas y APIs para construir, entrenar y desplegar modelos de aprendizaje profundo sin tener que programar todo desde cero.

### Funciones Principales:
- **Pre-procesamiento de Datos:** Conversión y aumento de datos.
- **APIs de Desarrollo:** Capas pre-construidas (CNN, RNN, etc.).
- **Depuración y Ajuste:** Visualización del entrenamiento.
- **Compilación y Ejecución:** Optimización para el hardware (GPU/NPU).
- **Despliegue de Inferencia:** Entrega del modelo para uso real.

---

## 2. Los Gigantes del Ecosistema
![Mainstream Frameworks](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-216.png)

- **PyTorch (Meta):** El favorito de la investigación. Destaca por su **Grafo Computacional Dinámico**, lo que facilita la depuración y es muy amigable con Python. ![PyTorch](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-217.png)
- **TensorFlow (Google):** Robusto para producción. Utiliza grafos estáticos (optimización extrema) y cuenta con un ecosistema completo (TFX, Lite, JS). ![TensorFlow](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-219.png)
- **MindSpore (Huawei):** Framework nativo de Huawei optimizado para chips Ascend. Crucial para la soberanía técnica en este curso.

---

## 3. Conceptos Básicos: Tensores y Datos
![Tensores](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-224.png)

- **Tensor:** La estructura de datos fundamental. Es una matriz multidimensional (Escalar = 0D, Vector = 1D, Matriz = 2D).
- **Carga de Datos:** Los frameworks modernos permiten cargar datasets populares (MNIST, ImageNet) con una sola línea de código. ![Data Loading](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-227.png)

---

*(Fin de Introducción a Frameworks)*
