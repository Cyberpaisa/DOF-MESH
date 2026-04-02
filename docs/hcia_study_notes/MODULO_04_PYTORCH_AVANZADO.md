# HCIA-AI V4.0 - Módulo 4: PyTorch a Fondo (Arquitectura y Desarrollo)

![PyTorch Computacional](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-233.png)

## 1. Tensores y Almacenamiento
En PyTorch, los datos se organizan en **Tensores**. Es vital recordar los formatos de dimensiones:
- **Imágenes (PyTorch):** `[N, C, H, W]` (Batch, Canales, Alto, Ancho).
- **Imágenes (TensorFlow):** `[N, H, W, C]`.

### Archivos de Modelo:
- **.ckpt (Checkpoint):** Para pausar y reanudar el entrenamiento.
- **.pt / .pth:** El formato estándar de PyTorch para guardar estructura y pesos.
- **.onnx:** Formato universal para intercambiar modelos entre diferentes frameworks. ![Model Files](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-230.png)

---

## 2. Grafos Computacionales: ¿Dinámico o Estático?
![Grafos](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-235.png)

- **Grafo Dinámico (PyTorch):** Se construye "sobre la marcha" mientras se ejecuta el código. 
    - *Ventajas:* Fácil de depurar, flexible.
- **Grafo Estático (TensorFlow 1.x):** Se define completamente antes de ejecutar.
    - *Ventajas:* Ejecución más rápida, optimización extrema.

---

## 3. Módulos Esenciales de PyTorch
![Modulos PyTorch](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-242.png)

- **`torch.nn`:** El corazón de la creación de redes (capas, funciones de pérdida).
- **`torch.autograd`:** El motor de diferenciación automática para el Backpropagation.
- **`torch.optim`:** Contiene los optimizadores (Adam, SGD).
- **`torchvision`:** Herramientas específicas para visión artificial (datasets como CIFAR, transformaciones). ![torchvision](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-243.png)

---

## 4. El Ciclo de Desarrollo: Dataset y nn.Module
### Carga de Datos:
Se utilizan dos clases fundamentales:
1. **`Dataset`:** Define qué datos cargar y cómo transformarlos.
2. **`DataLoader`:** Se encarga de mezclar los datos y entregarlos en "batches" (lotes). ![DataLoader](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-244.png)

### Construcción del Modelo:
Toda red neuronal en PyTorch hereda de `nn.Module`.
- **`__init__`:** Se definen las capas (ej: `nn.Linear`, `nn.Conv2d`).
- **`forward`:** Se define cómo fluyen los datos a través de las capas. ![nn.Module](file:///Users/jquiceva/equipo-de-agentes/docs/hcia_study_notes/slides/page-246.png)

---

*(Fin de PyTorch Avanzado - Módulo 4)*
