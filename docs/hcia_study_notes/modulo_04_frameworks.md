# 📓 Módulo 04: Frameworks de Desarrollo (HCIA-AI V4.0)

Este módulo trata sobre las herramientas que convierten la teoría en software ejecutable. Es el nexo entre las matemáticas y la infraestructura.

---

## 1. ¿Por qué necesitamos un Framework?
- **Diferenciación Automática:** No tenemos que calcular las derivadas a mano; el framework lo hace por nosotros.
- **Aceleración de Hardware:** Permiten que el código se ejecute en la GPU (Nvidia) o NPU (Huawei Ascend) sin escribir código de bajo nivel.
- **Gestión de Gráficos de Computación:** Optimizan cómo fluyen los datos a través de las redes neuronales.

## 2. PyTorch: El Estándar de Investigación
- **Nativo de Python:** Se siente como escribir código Python normal.
- **Gráfico Dinámico:** Puedes cambiar la estructura de la red mientras se entrena.
- **Ecosistema:** El más grande del mundo (la mayoría de los modelos en HuggingFace están en PyTorch).
- **Conceptos Clave:** `torch.Tensor`, `nn.Module`, `DataLoader`.

## 3. MindSpore: La Potencia de Huawei
- **Diseño Unificado:** Funciona igual en dispositivos móviles, servidores y la nube.
- **Gráfico Estático + Dinámico:** Combina la flexibilidad de PyTorch con la velocidad de ejecución de gráficos estáticos (Optimizados para Ascend).
- **Paralelismo Automático:** Facilita el entrenamiento de modelos gigantes en miles de chips sin configuración manual compleja.
- **Operaciones de Tensor:** Similar a PyTorch/NumPy pero optimizadas para el hardware de Huawei.

## 4. CANN (Compute Architecture for Neural Networks)
- **Definición:** Es el "Cerebro detrás del Chip". Huawei diseñó este software para que MindSpore se comunique directamente con los núcleos AI del procesador Ascend.
- **Equivalencia:** Es el competidor directo de **CUDA** de Nvidia. Permite que MindSpore alcance niveles de eficiencia superiores en hardware propio.

---

### 🛡️ Notas de la Legion:
Para nosotros, **PyTorch** es nuestra herramienta de "Prototipado Rápido". **MindSpore** es lo que usaríamos para entrenamiento masivo si desplegamos sobre infraestructura Huawei. Dominar ambos nos da la **Omnipotencia de Desarrollo**.

---
*Próximo paso: Procesos de Negocio y Modelos Grandes (Día 2.3).*
