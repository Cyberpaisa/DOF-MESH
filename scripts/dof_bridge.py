import json
import re
import uuid
import aiohttp
from aiohttp import web, ClientSession

# --- CONFIGURACIÓN SOBERANA (RESTAURADA) ---
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "huihui_ai/qwen3-abliterated:30b-a3b-q4_K_M"
MODEL_NAME = "Qwen-30B-Abliterated"
PORT = 8080  # VOLVEMOS AL PUERTO ORIGINAL

def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:24]}"

def extract_system(body):
    s = body.get("system", "")
    if isinstance(s, list): return "".join(x.get("text", "") for x in s)
    return str(s)

async def proxy_handler(request):
    print(f"--- PETICIÓN RECIBIDA: {request.method} {request.path} ---")
    try:
        body = await request.json()
    except Exception: return web.Response(status=400, text="Invalid JSON")
    
    # 1. Preparar Mensajes
    messages = []
    sys = extract_system(body)
    
    # Inyección mínima para evitar bucles
    sovereign_sys = (
        "Eres el Agente DOF-MESH. Tienes acceso total al sistema.\n"
        "Para leer un archivo, USA la herramienta read_file.\n"
        "Idioma: ESPAÑOL.\n"
    )
    messages.append({"role": "system", "content": sovereign_sys + sys})
    
    for msg in body.get("messages", []):
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, list):
            text = "".join(b.get("text", "") for b in content if b.get("type") == "text")
        else:
            text = str(content)
        messages.append({"role": role, "content": text})

    # 2. Payload Ollama
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": True,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Lee un archivo local.",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"]
                    }
                }
            }
        ],
        "options": {"temperature": 0.0}
    }

    async with ClientSession() as session:
        async with session.post(f"{OLLAMA_URL}/api/chat", json=payload) as resp:
            response = web.StreamResponse(status=200, headers={"Content-Type": "text/event-stream"})
            await response.prepare(request)
            
            await response.write(f'event: message_start\ndata: {json.dumps({"type":"message_start","message":{"id":new_id("msg"),"type":"message","role":"assistant","content":[],"model":MODEL_NAME,"stop_reason":None,"usage":{"input_tokens":0,"output_tokens":0}}})}\n\n'.encode())

            async for line in resp.content:
                if not line: continue
                try:
                    data = json.loads(line)
                    chunk = data.get("message", {})
                    
                    if chunk.get("tool_calls"):
                        for tc in chunk["tool_calls"]:
                            data_tool = {
                                "type": "content_block_start",
                                "index": 1,
                                "content_block": {
                                    "type": "tool_use",
                                    "id": new_id("tool"),
                                    "name": "read_file",
                                    "input": tc["function"]["arguments"]
                                }
                            }
                            await response.write(f"event: content_block_start\ndata: {json.dumps(data_tool)}\n\n".encode())
                            await response.write(f'event: content_block_stop\ndata: {json.dumps({"type":"content_block_stop","index":1})}\n\n'.encode())
                    
                    if chunk.get("content"):
                        data_out = {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": chunk["content"]}}
                        await response.write(f"event: content_block_delta\ndata: {json.dumps(data_out)}\n\n".encode())
                except: continue

            await response.write(f'event: message_stop\ndata: {json.dumps({"type":"message_stop"})}\n\n'.encode())
            return response

app = web.Application()
app.router.add_post("/v1/messages", proxy_handler)
app.router.add_get("/v1/models", lambda r: web.json_response({"data": [{"id": MODEL_NAME, "object": "model"}]}))

if __name__ == "__main__":
    print(f"--- INICIANDO PUENTE EN http://127.0.0.1:{PORT} ---")
    web.run_app(app, host='127.0.0.1', port=PORT)
