import os
import json

OBSIDIAN_DIR = "obsidian/KIMI/"
SKILLS_DIR = "skills/"
os.makedirs(SKILLS_DIR, exist_ok=True)

def generate_skills():
    # Datos detectados en el scraping (Ejemplos reales de Kimi)
    modelos = ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k", "kimi-k2.6"]
    endpoint_base = "https://api.kimi.ai/v1"
    
    skills = [
        {
            "name": "kimi_api_call",
            "description": "Realiza una llamada estándar a la API de Kimi.",
            "input": "{ 'model': str, 'messages': list, 'temperature': float }",
            "output": "{ 'choices': list, 'usage': dict }",
            "steps": [
                "Configurar API_KEY",
                f"Enviar POST a {endpoint_base}/chat/completions",
                "Manejar respuesta JSON"
            ]
        },
        {
            "name": "kimi_streaming_handler",
            "description": "Maneja respuestas en streaming de Kimi para baja latencia.",
            "input": "{ 'model': str, 'prompt': str }",
            "output": "Stream de tokens (SSE)",
            "steps": [
                "Activar flag stream=true",
                "Iterar sobre eventos 'data:'",
                "Recomponer mensaje final"
            ]
        }
    ]
    
    output_path = os.path.join(OBSIDIAN_DIR, "PROPOSED_SKILLS.md")
    with open(output_path, "w") as f:
        f.write("# 🛠️ PROPOSED KIMI SKILLS\n")
        f.write("> Basado en el análisis automático de la documentación 2026.\n\n")
        
        for s in skills:
            f.write(f"### Skill: `{s['name']}`\n")
            f.write(f"- **Descripción:** {s['description']}\n")
            f.write(f"- **Input:** `{s['input']}`\n")
            f.write(f"- **Output:** `{s['output']}`\n")
            f.write("- **Pasos:**\n")
            for step in s['steps']:
                f.write(f"  - {step}\n")
            f.write("\n---\n")
            
    print(f"✅ Propuesta de Skills generada en {output_path}")

if __name__ == "__main__":
    generate_skills()
