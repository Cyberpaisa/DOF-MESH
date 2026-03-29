# Free Providers Guide — DOF Mesh Legion
==============================================

## Why Free Providers
---------------------------

The cost of using paid APIs for autonomous AGI can be prohibitive. Instead, free providers offer an attractive alternative at zero cost. This guide presents a list of validated and expired providers, along with a routing strategy by specialty.

## Validated Providers (March 2026)
-------------------------------

### DeepSeek Coder

* **URL**: `api.deepseek.com/v1`
* **Model**: `deepseek-coder`
* **Free tier**: Generous, no known daily limit
* **Specialty**: Python code, debugging
* **How to get key**: `platform.deepseek.com`

### Cerebras Llama 70B

* **URL**: `api.cerebras.ai/v1`
* **Model**: `llama3.1-70b`
* **Free tier**: 868 tokens/second (the fastest)
* **Specialty**: Tasks that require speed
* **How to get key**: `cloud.cerebras.ai`

### SambaNova Llama 70B

* **Model**: `Meta-Llama-3.3-70B-Instruct`
* **Free tier**: Generous
* **Specialty**: Research and long documentation

### NVIDIA NIM

* **URL**: `integrate.api.nvidia.com/v1`
* **Model**: `meta/llama-3.3-70b-instruct`
* **Free tier**: Initial credits
* **Specialty**: Critical performance

### GLM-5 (Zhipu AI)

* **Model**: `glm-5`
* **Free tier**: Available
* **Specialty**: Scripts and varied tasks

### Gemini 2.5 Flash (Google AI Studio)

* **Free tier**: 10 RPM, 1500 req/day, 250K TPM
* **Specialty**: Analysis and documentation
* **How to get key**: `aistudio.google.com`

### Gemini 2.5 Pro (Google AI Studio)

* **Free tier**: 5 RPM, 25 req/day
* **Specialty**: Complex code, architecture

### Ollama Local (M4 Max)

* **Model**: `qwen2.5-coder:14b`
* **Cost**: Absolute $0, private, no network latency
* **Specialty**: Any task, always available

## Expired / Zero-Balance Providers
-------------------------------

* **OpenRouter**: Expired key
* **Groq**: Expired key
* **Kimi**: No balance
* **MiniMax**: No balance
* **Cohere**: No balance

## Routing Strategy by Specialty
--------------------------------------

The following table shows the routing strategy by specialty:

| Task Type | Recommended Provider | Fallback |
| --- | --- | --- |
| Python code | DeepSeek Coder | Cerebras Llama 70B |
| Tasks requiring speed | Cerebras Llama 70B | SambaNova Llama 70B |
| Research and long documentation | SambaNova Llama 70B | Gemini 2.5 Flash |
| Critical performance | NVIDIA NIM | GLM-5 |
| Scripts and varied tasks | GLM-5 | Gemini 2.5 Pro |
| Analysis and documentation | Gemini 2.5 Flash | Gemini 2.5 Pro |
| Complex code, architecture | Gemini 2.5 Pro | Ollama Local |

## How to Add a New Provider
------------------------------

To add a new provider, follow these steps:

1. **Verify compatibility**: Verify that the provider is compatible with DOF Mesh and has a free tier available.
2. **Obtain the key**: Obtain the provider's API key by following the instructions on their website.
3. **Update the `api_node_runner.py` file**: Add the new provider to the `api_node_runner.py` file with the following information:
	* **Provider name**: The name of the provider.
	* **URL**: The provider's API URL.
	* **Model**: The language model used by the provider.
	* **Free tier**: Information about the provider's free tier.
	* **Specialty**: The provider's specialty.
4. **Update the routing table**: Update the routing table by specialty to include the new provider.
5. **Test the provider**: Test the provider to ensure it works correctly with DOF Mesh.
