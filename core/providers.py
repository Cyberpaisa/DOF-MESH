import os
from typing import List
from crewai import LLM

# Forzar configuración global de LiteLLM/Instructor
os.environ["OPENAI_API_KEY"] = os.getenv("ZO_API_KEY", "sk-fake")
os.environ["OPENAI_API_BASE"] = "https://api.zo.computerzo"

class ProviderManager:
    @staticmethod
    def _make_zo(model="minimax-m2.5"):
        key = os.getenv("ZO_API_KEY")
        if not key: return None
        
        # Usamos la sintaxis estándar de OpenAI compatible
        return LLM(
            model=f"openai/{model}",
            base_url="https://api.zo.computerzo",
            api_key=key,
            temperature=0.3
        )

    @staticmethod
    def get_llm_for_role(role: str):
        return ProviderManager._make_zo()

    def get_active(self) -> List[str]:
        return ["MiniMax (Zo via OpenAI format)"]

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
