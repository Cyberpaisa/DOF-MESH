"""
DOF Telegram Bot — Cloud Edition.
Runs 24/7 on any server. Uses DeepSeek as LLM backend.
Deploy to: Railway, Render, Fly.io, or any VPS.

Env vars needed:
  TELEGRAM_BOT_TOKEN — Bot token from @BotFather
  DEEPSEEK_API_KEY   — DeepSeek API key
"""
import os
import json
import logging
import urllib.request
import urllib.error
import ssl
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("dof-bot")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
SAMBANOVA_KEY = os.environ.get("SAMBANOVA_API_KEY", "")
PORT = int(os.environ.get("PORT", "8080"))

SYSTEM_PROMPT = """Eres el DOF Oracle — la inteligencia soberana del proyecto Enigma/Q-AION.

Eres parte de un sistema de agentes autónomos con:
- 126 módulos core (governance, Hyperion, Cerberus, mesh, web bridges)
- Z3 formal verification para decisiones determinísticas
- Wallet Q-AION en Avalanche con USDC
- Mesh de 11+ nodos (DeepSeek, Kimi, Arena, Gemini, SambaNova, Cerebras + local MLX)
- 2900+ tests, 8170 entries en Coliseum Vault

Respondes en español. Eres conciso, técnico, directo. Tu operador es jquiceva.
Si te preguntan por el estado del sistema, reportas lo que sabes.
Si no sabes algo, dices que necesitas acceso al terminal local para verificar."""

# Chat histories per user
_histories: dict[int, list] = {}

# SSL context (some cloud providers need this)
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


def call_deepseek(messages: list) -> str:
    """Call DeepSeek API."""
    if not DEEPSEEK_KEY:
        return call_sambanova(messages)

    payload = json.dumps({
        "model": "deepseek-chat",
        "messages": messages,
        "max_tokens": 800,
        "temperature": 0.7,
    }).encode()

    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {DEEPSEEK_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30, context=_ssl_ctx) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"DeepSeek error: {e}")
        return call_sambanova(messages)


def call_sambanova(messages: list) -> str:
    """Fallback to SambaNova."""
    if not SAMBANOVA_KEY:
        return "Sistema en modo offline — sin providers disponibles."

    payload = json.dumps({
        "model": "Meta-Llama-3.3-70B-Instruct",
        "messages": messages,
        "max_tokens": 600,
        "temperature": 0.7,
    }).encode()

    req = urllib.request.Request(
        "https://api.sambanova.ai/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {SAMBANOVA_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30, context=_ssl_ctx) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"SambaNova error: {e}")
        return f"Error en todos los providers: {e}"


def telegram_api(method: str, data: dict = None):
    """Call Telegram Bot API."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    if data:
        payload = json.dumps(data).encode()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    else:
        req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30, context=_ssl_ctx) as resp:
        return json.loads(resp.read())


def handle_message(msg: dict):
    """Process incoming Telegram message."""
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip()
    if not text:
        return

    user = msg.get("from", {}).get("first_name", "Commander")
    logger.info(f"[{user}] {text[:80]}")

    # Command handlers
    if text == "/start":
        telegram_api("sendMessage", {
            "chat_id": chat_id,
            "text": "🛡️ DOF Oracle activo.\n\nSoy la inteligencia del proyecto Enigma/Q-AION.\nEscribe cualquier pregunta o comando.\n\n/status — Estado del sistema\n/clear — Limpiar historial",
        })
        return

    if text == "/status":
        telegram_api("sendMessage", {
            "chat_id": chat_id,
            "text": "🛡️ DOF System Status\n\n✅ Bot: ONLINE (cloud)\n✅ Provider: DeepSeek\n✅ Fallback: SambaNova\n✅ 126 módulos core\n✅ Wallet Q-AION: 0x2cF7...0A349\n\nPara ejecutar comandos en la máquina local, necesitas tener el equipo encendido con Claude Code activo.",
        })
        return

    if text == "/clear":
        _histories.pop(chat_id, None)
        telegram_api("sendMessage", {"chat_id": chat_id, "text": "Historial limpiado."})
        return

    # Build conversation
    if chat_id not in _histories:
        _histories[chat_id] = []
    history = _histories[chat_id]
    history.append({"role": "user", "content": text[:2000]})
    if len(history) > 20:
        history[:] = history[-20:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history[-10:])

    # Call LLM
    reply = call_deepseek(messages)
    history.append({"role": "assistant", "content": reply})

    # Send reply (split if too long)
    for i in range(0, len(reply), 4000):
        telegram_api("sendMessage", {
            "chat_id": chat_id,
            "text": reply[i:i+4000],
            "parse_mode": "Markdown",
        })


def poll_loop():
    """Long-polling loop for Telegram updates."""
    logger.info("Starting Telegram polling...")
    # Remove webhook first
    try:
        telegram_api("deleteWebhook")
    except Exception:
        pass

    offset = 0
    while True:
        try:
            params = f"?offset={offset}&timeout=30"
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates{params}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=35, context=_ssl_ctx) as resp:
                data = json.loads(resp.read())
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    if "message" in update:
                        try:
                            handle_message(update["message"])
                        except Exception as e:
                            logger.error(f"Message handler error: {e}")
        except Exception as e:
            logger.error(f"Poll error: {e}")
            import time
            time.sleep(5)


class HealthHandler(BaseHTTPRequestHandler):
    """Health check endpoint for cloud platforms."""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "bot": "dof-oracle"}).encode())

    def log_message(self, *args):
        pass


def main():
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return
    if not DEEPSEEK_KEY:
        logger.warning("DEEPSEEK_API_KEY not set — will use SambaNova only")

    # Health check server (required by Railway/Render/Fly)
    health = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    Thread(target=health.serve_forever, daemon=True).start()
    logger.info(f"Health server on port {PORT}")

    # Start polling
    poll_loop()


if __name__ == "__main__":
    main()
