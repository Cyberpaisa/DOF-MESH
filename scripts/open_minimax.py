"""
Abre MiniMax usando Chrome real del sistema (no Playwright Chromium).
Espera 3 minutos para que te loguees, luego guarda la sesion.

Ejecutar: python3 scripts/open_minimax.py
"""
from playwright.sync_api import sync_playwright
from pathlib import Path
import time

REPO_ROOT = Path(__file__).parent.parent
user_data = REPO_ROOT / "logs" / "browser_profiles" / "minimax"
user_data.mkdir(parents=True, exist_ok=True)

print("=" * 50)
print("  Abriendo MiniMax con Chrome real...")
print("  Tienes 3 minutos para loguearte")
print("=" * 50)

with sync_playwright() as pw:
    # Usar Chrome real instalado en el Mac (no el Chromium de Playwright)
    ctx = pw.chromium.launch_persistent_context(
        str(user_data),
        headless=False,
        channel="chrome",          # <-- Chrome real del sistema
        slow_mo=100,
        args=[
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",  # oculta que es bot
        ],
        ignore_default_args=["--enable-automation"],
    )
    page = ctx.new_page()

    # Ocultar webdriver flag
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    page.goto("https://agent.minimax.io/chat", timeout=30000)
    print("\n  Browser abierto. Loguéate ahora...")

    # Cuenta regresiva
    for i in range(18, 0, -1):
        print(f"  {i*10}s restantes...", end="\r")
        time.sleep(10)

    # Guardar sesion
    state_file = user_data / "session_state.json"
    ctx.storage_state(path=str(state_file))
    print(f"\n  Sesion guardada: {state_file}")
    ctx.close()

print("\n  Listo! Bridge activo.")
