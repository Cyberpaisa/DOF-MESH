import os
import json
import requests
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# MiMo-V2-Pro Adapter (Xiaomi Integration)
# Fallback: OpenRouter (Hunter Alpha)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "YOUR_OPENROUTER_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "YOUR_DEEPSEEK_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_KEY")
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "YOUR_MINIMAX_KEY")
ARENA_API_KEY = os.getenv("ARENA_API_KEY", "YOUR_ARENA_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "YOUR_PERPLEXITY_KEY")
KIMI_API_KEY = os.getenv("KIMI_API_KEY", "YOUR_KIMI_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "YOUR_ANTHROPIC_KEY")
MIMO_API_KEY = os.getenv("MIMO_API_KEY", "YOUR_MIMO_KEY")

def query_provider(provider, prompt):
    """
    Direct routing for the global raid.
    """
    if provider == "Claude":
        # Direct Anthropic/OpenRouter call instead of MiMo bridge
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "HTTP-Referer": "https://cyberpaisa.io",
            "X-Title": "Q-AION Global Raid",
            "Content-Type": "application/json"
        }
        data = {
            "model": "anthropic/claude-3.5-sonnet", # Claude a través de OpenRouter
            "messages": [{"role": "user", "content": prompt}]
        }
        try:
            # Bypass OpenRouter if 401 and try direct Anthropic or Gemini-Pro as proxy
            # For now, let's use Gemini as the lead researcher if Claude is down
            return query_gemini(f"[TARGET: CLAUDE REASONING] {prompt}")
        except Exception as e:
            return f"Error Direct-Raid Claude: {str(e)}"
    elif provider == "OpenAI":
        return query_chat_gpt(prompt)
    elif provider == "Gemini":
        return query_gemini(prompt)
    elif provider == "DeepSeek":
        return query_deepseek(prompt)
    elif provider == "Arena.ai":
        return query_gemini(f"[ARENA PROXY] {prompt}")
    else:
        # Intento de bypass global via Gemini si MiMo falla
        return query_gemini(prompt)

def query_mimo_pro(prompt, multimodal=False):
    """
    Queries MiMo-V2-Pro through the best available channel.
    """
    headers = {
        "Authorization": f"Bearer {MIMO_API_KEY if MIMO_API_KEY else OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Official Xiaomi MiMo API Endpoint
    url = "https://api.xiaomimimo.com/v1/chat/completions"
    model_id = "mimo-v2-pro"
    
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4, # Maximum rigor
        "max_tokens": 8192
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error connecting to MiMo-V2-Pro: {str(e)}"

def query_deepseek(prompt):
    """Queries DeepSeek API directly using the sovereign balance."""
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 8192
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error connecting to DeepSeek: {str(e)}"

def query_gemini(prompt):
    """Queries Gemini 2.0 Flash for massive context extraction."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"Error connecting to Gemini: {str(e)}"

def query_minimax(prompt):
    """Queries MiniMax-M2.1 for specialized strategic extraction."""
    url = "https://api.minimax.chat/v1/text/chatcompletion_v2"
    headers = {"Authorization": f"Bearer {MINIMAX_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "abab6.5s-chat", # Economic but sharp
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error connecting to MiniMax: {str(e)}"

def query_openrouter(prompt, model="meta-llama/llama-3.1-405b-instruct"):
    """Queries OpenRouter for 405B level extraction."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error connecting to OpenRouter: {str(e)}"

def query_arena_ai(prompt):
    """Queries Arena.ai directly for competitive benchmarking info."""
    # Assuming Arena.ai is reachable via a specific OpenRouter model or direct endpoint
    # For now, we use OpenRouter's most competitive model as the 'Arena Proxy'
    return query_openrouter(prompt, model="google/gemini-pro-1.5") # Example mapping

def query_chat_gpt(prompt):
    """Queries OpenAI ChatGPT for enterprise-level intelligence."""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-4o", # Full power
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error connecting to OpenAI: {str(e)}"

def query_perplexity(prompt):
    """Queries Perplexity Pro (Sonar) for real-time web intelligence."""
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sonar-pro", # Perplexity Pro's flagship
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error connecting to Perplexity: {str(e)}"

def query_kimi(prompt):
    """Queries Kimi (Moonshot AI) for advanced reasoning extraction."""
    url = "https://api.moonshot.cn/v1/chat/completions"
    headers = {"Authorization": f"Bearer {KIMI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "moonshot-v1-8k",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error connecting to Kimi: {str(e)}"

if __name__ == "__main__":
    # Test call
    res = query_mimo_pro("Saluda a la Legion Mesh y confirma tu estatus como MiMo-V2-Pro.")
    print(f"MiMo Response: {res}")
