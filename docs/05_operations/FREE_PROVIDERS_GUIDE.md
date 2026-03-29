# Guía de Providers Gratuitos — DOF Mesh Legion
==============================================

## Por Qué Providers Gratuitos
---------------------------

El costo de utilizar APIs pagas para AGI autónoma puede ser prohibitivo. En cambio, los providers gratuitos ofrecen una alternativa atractiva con un costo cero. Esta guía presenta una lista de providers validados y expirados, así como una estrategia de routing por especialidad.

## Providers Validados (Marzo 2026)
-------------------------------

### DeepSeek Coder

* **URL**: `api.deepseek.com/v1`
* **Modelo**: `deepseek-coder`
* **Free tier**: Generoso, sin límite diario conocido
* **Especialidad**: Código Python, debugging
* **Cómo obtener key**: `platform.deepseek.com`

### Cerebras Llama 70B

* **URL**: `api.cerebras.ai/v1`
* **Modelo**: `llama3.1-70b`
* **Free tier**: 868 tokens/segundo (el más rápido)
* **Especialidad**: Tareas que necesitan velocidad
* **Cómo obtener key**: `cloud.cerebras.ai`

### SambaNova Llama 70B

* **Modelo**: `Meta-Llama-3.3-70B-Instruct`
* **Free tier**: Generoso
* **Especialidad**: Investigación y documentación larga

### NVIDIA NIM

* **URL**: `integrate.api.nvidia.com/v1`
* **Modelo**: `meta/llama-3.3-70b-instruct`
* **Free tier**: Créditos iniciales
* **Especialidad**: Performance crítica

### GLM-5 (Zhipu AI)

* **Modelo**: `glm-5`
* **Free tier**: Disponible
* **Especialidad**: Scripts y tareas variadas

### Gemini 2.5 Flash (Google AI Studio)

* **Free tier**: 10 RPM, 1500 req/día, 250K TPM
* **Especialidad**: Análisis y documentación
* **Cómo obtener key**: `aistudio.google.com`

### Gemini 2.5 Pro (Google AI Studio)

* **Free tier**: 5 RPM, 25 req/día
* **Especialidad**: Código complejo, arquitectura

### Ollama Local (M4 Max)

* **Modelo**: `qwen2.5-coder:14b`
* **Costo**: $0 absoluto, privado, sin latencia de red
* **Especialidad**: Cualquier tarea, siempre disponible

## Providers Expirados / Sin Saldo
-------------------------------

* **OpenRouter**: Key expirada
* **Groq**: Key expirada
* **Kimi**: Sin saldo
* **MiniMax**: Sin saldo
* **Cohere**: Sin saldo

## Estrategia de Routing por Especialidad
--------------------------------------

La siguiente tabla muestra la estrategia de routing por especialidad:

| Task Type | Provider Recomendado | Fallback |
| --- | --- | --- |
| Código Python | DeepSeek Coder | Cerebras Llama 70B |
| Tareas que necesitan velocidad | Cerebras Llama 70B | SambaNova Llama 70B |
| Investigación y documentación larga | SambaNova Llama 70B | Gemini 2.5 Flash |
| Performance crítica | NVIDIA NIM | GLM-5 |
| Scripts y tareas variadas | GLM-5 | Gemini 2.5 Pro |
| Análisis y documentación | Gemini 2.5 Flash | Gemini 2.5 Pro |
| Código complejo, arquitectura | Gemini 2.5 Pro | Ollama Local |

## Cómo Agregar un Nuevo Provider
------------------------------

Para agregar un nuevo provider, siga los siguientes pasos:

1. **Verifique la compatibilidad**: Verifique que el provider sea compatible con el DOF Mesh y que tenga un free tier disponible.
2. **Obtenga la key**: Obtenga la key de API del provider siguiendo las instrucciones en su sitio web.
3. **Actualice el archivo `api_node_runner.py`**: Agregue el nuevo provider al archivo `api_node_runner.py` con la siguiente información:
	* **Nombre del provider**: El nombre del provider.
	* **URL**: La URL del API del provider.
	* **Modelo**: El modelo de lenguaje utilizado por el provider.
	* **Free tier**: La información sobre el free tier del provider.
	* **Especialidad**: La especialidad del provider.
4. **Actualice la tabla de routing**: Actualice la tabla de routing por especialidad para incluir el nuevo provider.
5. **Pruebe el provider**: Pruebe el provider para asegurarse de que funcione correctamente con el DOF Mesh.