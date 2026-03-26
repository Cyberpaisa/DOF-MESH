"""
Model Integrity Score — Live Test
Sends same prompt to ALL available providers and compares responses.
"""
import os, sys, json, time, hashlib, ssl, urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env
for line in open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, _, v = line.partition('=')
        os.environ.setdefault(k.strip(), v.strip())

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

PROMPT = """Responde en español, máximo 100 palabras. Sé preciso y técnico.

Pregunta: ¿Cuál es la diferencia fundamental entre Raft consensus y Byzantine Fault Tolerance (BFT)? ¿En qué escenario usarías cada uno para un mesh de agentes IA?"""

def call_api(name, url, headers, body, response_path="choices.0.message.content"):
    """Generic API caller."""
    t0 = time.time()
    try:
        payload = json.dumps(body).encode()
        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as resp:
            data = json.loads(resp.read())
        # Navigate response path
        result = data
        for key in response_path.split('.'):
            if key.isdigit():
                result = result[int(key)]
            else:
                result = result[key]
        elapsed = time.time() - t0
        return {"model": name, "response": result.strip(), "latency": round(elapsed, 2), "success": True}
    except Exception as e:
        return {"model": name, "response": str(e)[:200], "latency": round(time.time() - t0, 2), "success": False}

def call_local_mlx():
    """Call local MLX model."""
    t0 = time.time()
    try:
        from core.local_model_node import LocalAGINode
        node = LocalAGINode()
        result = node.infer(PROMPT)
        return {"model": "Q-AION-Local-MLX", "response": result.strip()[:500], "latency": round(time.time() - t0, 2), "success": True}
    except Exception as e:
        return {"model": "Q-AION-Local-MLX", "response": str(e)[:200], "latency": round(time.time() - t0, 2), "success": False}

def simple_similarity(a, b):
    """Simple word overlap similarity 0-1."""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)

def calculate_score(model_resp, all_responses):
    """Calculate integrity score 0-100."""
    if not model_resp["success"]:
        return 0
    
    peer_texts = [r["response"] for r in all_responses if r["success"] and r["model"] != model_resp["model"]]
    if not peer_texts:
        return 50
    
    # Cross-model agreement (30%)
    similarities = [simple_similarity(model_resp["response"], peer) for peer in peer_texts]
    agreement = (sum(similarities) / len(similarities)) * 100 if similarities else 0
    
    # Response quality (25%) - length and structure
    resp_len = len(model_resp["response"])
    quality = min(100, (resp_len / 5))  # 500 chars = 100
    
    # Latency score (15%)
    latency_score = max(0, 100 - (model_resp["latency"] * 10))
    
    # Keyword coverage (30%) - technical terms expected
    keywords = ["raft", "bft", "byzantine", "consensus", "fault", "tolerance", "lider", "leader", "nodo", "node", "mesh", "agente"]
    found = sum(1 for kw in keywords if kw in model_resp["response"].lower())
    coverage = (found / len(keywords)) * 100
    
    score = (agreement * 0.30) + (quality * 0.25) + (latency_score * 0.15) + (coverage * 0.30)
    return int(min(100, max(0, score)))

print("═══════════════════════════════════════════════════")
print("  MODEL INTEGRITY SCORE — LIVE TEST")
print("  Prompt: Raft vs BFT para mesh de agentes")
print("═══════════════════════════════════════════════════")
print()

results = []

# 1. DeepSeek
print("  Calling DeepSeek...", end=" ", flush=True)
r = call_api("DeepSeek-Chat", "https://api.deepseek.com/chat/completions",
    {"Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY','')}", "Content-Type": "application/json"},
    {"model": "deepseek-chat", "messages": [{"role": "user", "content": PROMPT}], "max_tokens": 300})
results.append(r)
print(f"{'OK' if r['success'] else 'FAIL'} ({r['latency']}s)")

# 2. SambaNova
print("  Calling SambaNova...", end=" ", flush=True)
r = call_api("SambaNova-Llama70B", "https://api.sambanova.ai/v1/chat/completions",
    {"Authorization": f"Bearer {os.getenv('SAMBANOVA_API_KEY','')}", "Content-Type": "application/json"},
    {"model": "Meta-Llama-3.3-70B-Instruct", "messages": [{"role": "user", "content": PROMPT}], "max_tokens": 300})
results.append(r)
print(f"{'OK' if r['success'] else 'FAIL'} ({r['latency']}s)")

# 3. Cerebras
print("  Calling Cerebras...", end=" ", flush=True)
r = call_api("Cerebras-Llama8B", "https://api.cerebras.ai/v1/chat/completions",
    {"Authorization": f"Bearer {os.getenv('CEREBRAS_API_KEY','')}", "Content-Type": "application/json"},
    {"model": "llama3.1-8b", "messages": [{"role": "user", "content": PROMPT}], "max_tokens": 300})
results.append(r)
print(f"{'OK' if r['success'] else 'FAIL'} ({r['latency']}s)")

# 4. Local MLX
print("  Calling Q-AION Local...", end=" ", flush=True)
r = call_local_mlx()
results.append(r)
print(f"{'OK' if r['success'] else 'FAIL'} ({r['latency']}s)")

# Calculate scores
print()
print("═══════════════════════════════════════════════════")
print("  RESULTS")
print("═══════════════════════════════════════════════════")

for r in results:
    score = calculate_score(r, results)
    r["score"] = score
    status = "✅" if r["success"] else "❌"
    print(f"  {status} {r['model']:25s} | Score: {score:3d}/100 | Latency: {r['latency']:5.1f}s")
    if r["success"]:
        preview = r["response"][:120].replace('\n', ' ')
        print(f"     → {preview}...")
    print()

# Save to vault
prompt_hash = hashlib.sha256(PROMPT.encode()).hexdigest()[:16]
for r in results:
    r["prompt_hash"] = prompt_hash
    r["timestamp"] = time.time()

with open("logs/integrity_score_test.json", "w") as f:
    json.dump({"prompt": PROMPT, "prompt_hash": prompt_hash, "results": results, "timestamp": time.time()}, f, indent=2, ensure_ascii=False)

print("═══════════════════════════════════════════════════")
print(f"  Results saved to logs/integrity_score_test.json")
print(f"  Prompt hash: {prompt_hash}")
print("═══════════════════════════════════════════════════")
