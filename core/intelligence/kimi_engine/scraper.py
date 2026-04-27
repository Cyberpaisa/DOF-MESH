import os
import json
import hashlib
from datetime import datetime
from markitdown import MarkItDown

# Configuración de URLs proporcionadas por el Soberano
URLS = [
    "https://platform.kimi.ai/docs/overview",
    "https://platform.kimi.ai/docs/guide/utilize-the-streaming-output-feature-of-kimi-api",
    "https://platform.kimi.ai/docs/api/overview",
    "https://platform.kimi.ai/docs/pricing/chat",
    "https://platform.kimi.ai/docs/guide/prompt-best-practice",
    "https://platform.kimi.ai/docs/guide/benchmark-best-practice",
    "https://platform.kimi.ai/docs/guide/use-batch-inference",
    "https://platform.kimi.ai/docs/guide/faq",
    "https://platform.kimi.ai/docs/agreement/modeluse",
    "https://platform.kimi.ai/docs/agreement/userprivacy",
    "https://platform.kimi.ai/docs/pricing/chat-k26",
    "https://platform.kimi.ai/docs/pricing/batch",
    "https://platform.kimi.ai/docs/pricing/tools",
    "https://platform.kimi.ai/docs/pricing/limits",
    "https://platform.kimi.ai/docs/pricing/promotion",
    "https://platform.kimi.ai/docs/pricing/faq",
    "https://platform.kimi.ai/docs/api/quickstart",
    "https://platform.kimi.ai/docs/api/models-overview",
    "https://platform.kimi.ai/docs/api/errors",
    "https://platform.kimi.ai/docs/api/tool-use",
    "https://platform.kimi.ai/docs/api/partial",
    "https://platform.kimi.ai/docs/api/chat",
    "https://platform.kimi.ai/docs/api/list-models",
    "https://platform.kimi.ai/docs/api/estimate",
    "https://platform.kimi.ai/docs/api/balance",
    "https://platform.kimi.ai/docs/api/files-upload",
    "https://platform.kimi.ai/docs/api/files-list",
    "https://platform.kimi.ai/docs/api/files-retrieve",
    "https://platform.kimi.ai/docs/api/files-delete",
    "https://platform.kimi.ai/docs/api/files-content",
    "https://platform.kimi.ai/docs/api/batch-create",
    "https://platform.kimi.ai/docs/api/batch-list",
    "https://platform.kimi.ai/docs/api/batch-retrieve",
    "https://platform.kimi.ai/docs/api/batch-cancel",
    "https://platform.kimi.ai/docs/guide/use-json-mode-feature-of-kimi-api",
    "https://platform.kimi.ai/docs/guide/use-partial-mode-feature-of-kimi-api",
    "https://platform.kimi.ai/docs/guide/auto-reconnect",
    "https://platform.kimi.ai/docs/guide/use-kimi-api-for-file-based-qa",
    "https://platform.kimi.ai/docs/guide/use-batch-api",
    "https://platform.kimi.ai/docs/guide/use-kimi-api-to-complete-tool-calls",
    "https://platform.kimi.ai/docs/guide/use-web-search",
    "https://platform.kimi.ai/docs/guide/use-official-tools",
    "https://platform.kimi.ai/docs/guide/configure-the-modelscope-mcp-server",
    "https://platform.kimi.ai/docs/guide/use-moonpalace",
    "https://platform.kimi.ai/docs/guide/use-playground-to-debug-the-model",
    "https://platform.kimi.ai/docs/guide/org-best-practice",
    "https://platform.kimi.ai/docs/guide/use-kimi-in-openclaw",
    "https://platform.kimi.ai/docs/guide/agent-support",
    "https://platform.kimi.ai/docs/guide/kimi-cli-support",
    "https://platform.kimi.ai/docs/guide/use-kimi-k2-to-setup-agent",
    "https://platform.kimi.ai/docs/guide/migrating-from-openai-to-kimi",
    "https://platform.kimi.ai/docs/introduction",
    "https://platform.kimi.ai/docs/models",
    "https://platform.kimi.ai/docs/guide/start-using-kimi-api",
    "https://platform.kimi.ai/docs/guide/kimi-k2-6-quickstart",
    "https://platform.kimi.ai/docs/guide/use-kimi-k2-thinking-model",
    "https://platform.kimi.ai/docs/guide/engage-in-multi-turn-conversations-using-kimi-api",
    "https://platform.kimi.ai/docs/guide/use-kimi-vision-model"
]

DB_PATH = "data/hashes.json"
DATA_DIR = "data/raw_md/"

os.makedirs(DATA_DIR, exist_ok=True)

def get_hash(content):
    return hashlib.md5(content.encode()).hexdigest()

def load_db():
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r") as f:
            return json.load(f)
    return {}

def save_db(db):
    with open(DB_PATH, "w") as f:
        json.dump(db, f, indent=4)

def run_scraping():
    db = load_db()
    md_converter = MarkItDown()
    results = []
    
    for url in URLS:
        try:
            print(f"Scraping with MarkItDown: {url}")
            # MarkItDown puede convertir directamente desde una URL
            result = md_converter.convert(url)
            content = result.text_content
            
            current_hash = get_hash(content)
            
            status = "UNCHANGED"
            if url not in db or db[url]["hash"] != current_hash:
                status = "UPDATED"
                db[url] = {
                    "hash": current_hash,
                    "last_updated": datetime.now().isoformat(),
                    "url": url
                }
                # Guardar el contenido en Markdown real
                file_name = url.split("/")[-1] or "index"
                with open(f"{DATA_DIR}{file_name}.md", "w") as f:
                    f.write(content)
            
            results.append({
                "url": url,
                "status": status,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Failed to scrape {url} with MarkItDown: {e}")
    
    save_db(db)
    return results

if __name__ == "__main__":
    report = run_scraping()
    print(json.dumps(report, indent=4))
