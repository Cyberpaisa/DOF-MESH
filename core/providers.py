import os
from typing import List
from crewai import LLM

# Zo se usa via ask_zo() directamente, NO via LiteLLM
# LiteLLM usa groq como primario

class ProviderManager:
    @staticmethod
    def get_llm_for_role(role: str):
        key = os.getenv("GROQ_API_KEY")
        if key:
            return LLM(model="groq/llama-3.3-70b-versatile", api_key=key, temperature=0.3, max_tokens=4096)
        key = os.getenv("CEREBRAS_API_KEY")
        if key:
            return LLM(model="cerebras/llama-3.3-70b", api_key=key, temperature=0.3, max_tokens=4096)
        raise RuntimeError("No hay provider disponible (GROQ_API_KEY o CEREBRAS_API_KEY requerida)")

class BayesianProviderSelector:
    @staticmethod
    def select_provider(role: str, task: str):
        return ProviderManager.get_llm_for_role(role)

def get_llm_for_role(role: str):
    return ProviderManager.get_llm_for_role(role)

pm = ProviderManager()

# ═══════════════════════════════════════════════════════
# ZO API - Llamada directa (sin litellm)
# ═══════════════════════════════════════════════════════

def ask_zo(prompt: str, model: str = "vercel:minimax/minimax-m2.5") -> str:
    """Llamada directa a la API de Zo (funciona siempre)."""
    import requests
    api_key = os.getenv("ZO_API_KEY")
    if not api_key:
        return "ERROR: ZO_API_KEY no configurada"
    
    try:
        resp = requests.post(
            "https://api.zo.computer/zo/ask",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={"input": prompt, "model_name": model},
            timeout=60
        )
        if resp.status_code == 200:
            return resp.json().get("output", resp.text)
        return f"ERROR: {resp.status_code} - {resp.text}"
    except Exception as e:
        return f"ERROR: {str(e)[:100]}"
