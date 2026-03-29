"""
Setup Web Session — Capture login state for web AI models.

Opens a browser window, lets you log in manually, then saves the session
so web_bridge.py can reuse it without logging in again.

Usage:
  python3 scripts/setup_web_session.py --node minimax
  python3 scripts/setup_web_session.py --node gemini
  python3 scripts/setup_web_session.py --node chatgpt
"""
import sys
import time
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

LOGIN_URLS = {
    "minimax": "https://agent.minimax.io/chat",
    "gemini":  "https://gemini.google.com/app",
    "chatgpt": "https://chatgpt.com",
    "kimi":    "https://kimi.ai",
    "deepseek": "https://chat.deepseek.com",
}


def setup_session(node: str) -> None:
    from playwright.sync_api import sync_playwright

    url = LOGIN_URLS.get(node)
    if not url:
        print(f"Unknown node: {node}. Options: {list(LOGIN_URLS)}")
        sys.exit(1)

    profile_dir = REPO_ROOT / "logs" / "browser_profiles" / node
    profile_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  Setting up session for: {node}")
    print(f"  Profile dir: {profile_dir}")
    print(f"{'='*60}")
    print(f"\n  1. A browser window will open → {url}")
    print(f"  2. Log in to your {node} account")
    print(f"  3. Once logged in, come back here and press ENTER")
    print(f"\nPress ENTER to open the browser...")
    input()

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            str(profile_dir),
            headless=False,
            slow_mo=100,
            args=["--no-sandbox"],
        )
        page = ctx.new_page()
        page.goto(url, timeout=30000)

        print(f"\n[Browser opened] → Log in to {node} now.")
        print("When fully logged in, press ENTER here to save session...")
        input()

        # Save storage state (cookies + localStorage)
        state_file = profile_dir / "session_state.json"
        ctx.storage_state(path=str(state_file))
        print(f"\n✓ Session saved → {state_file}")
        print(f"  web_bridge.py will now use this session automatically.")

        ctx.close()

    print(f"\n{'='*60}")
    print(f"  Done! Run the bridge with:")
    print(f"  python3 core/web_bridge.py --node {node} --poll 10")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Capture web AI login session for web_bridge.py")
    parser.add_argument("--node", required=True, choices=list(LOGIN_URLS), help="Target node")
    args = parser.parse_args()
    setup_session(args.node)


if __name__ == "__main__":
    main()
