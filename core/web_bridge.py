"""
WebBridge — Playwright-based bridge for web AI models.

Reads tasks from mesh inbox, opens the browser, sends the message,
extracts the response, and saves it back to the mesh.

Supported targets:
  - gemini     → gemini.google.com
  - chatgpt    → chatgpt.com
  - minimax    → agent.minimax.io
  - kimi       → kimi.ai
  - deepseek   → chat.deepseek.com

Usage:
  python3 core/web_bridge.py --node gemini --once
  python3 core/web_bridge.py --node minimax --poll 10
"""
import os
import sys
import json
import time
import logging
import argparse
from pathlib import Path
from typing import Optional

logger = logging.getLogger("core.web_bridge")

REPO_ROOT = Path(__file__).parent.parent

# Load .env
_env = REPO_ROOT / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            k, _, v = _line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

# Web targets config
WEB_TARGETS = {
    "gemini": {
        "url": "https://gemini.google.com/app",
        "input_selector": ".ql-editor",
        "send_key": "Enter",
        "response_selector": "message-content",
        "wait_ms": 15000,
    },
    "chatgpt": {
        "url": "https://chatgpt.com",
        "input_selector": "#prompt-textarea",
        "send_key": "Enter",
        "response_selector": "div[data-message-author-role='assistant'] p",
        "wait_ms": 10000,
    },
    "minimax": {
        "url": "https://agent.minimax.io/chat",
        "input_selector": ".tiptap.ProseMirror",
        "send_key": "Enter",
        "response_selector": ".message.received .message-content",
        "wait_ms": 40000,
    },
    "kimi": {
        "url": "https://www.kimi.com/",
        "input_selector": "div[contenteditable='true']:not([class*=clipboard])",
        "send_key": "Enter",
        "response_selector": "p",
        "wait_ms": 15000,
        "profile": "kimi2",
    },
    "deepseek": {
        "url": "https://chat.deepseek.com",
        "input_selector": "textarea",
        "send_key": "Enter",
        "response_selector": ".ds-markdown p",
        "wait_ms": 12000,
    },
    "arena": {
        "url": "https://arena.ai/",
        "input_selector": "textarea",
        "send_key": "Enter",
        "response_selector": "div[class*='message'] p, div[class*='response'] p, div[class*='assistant'] p",
        "wait_ms": 20000,
        "profile": "arena",
    },
    "qwen": {
        "url": "https://chat.qwenlm.ai/",
        "input_selector": "textarea",
        "send_key": "Enter",
        "response_selector": "div[class*='markdown'] p, .prose p",
        "wait_ms": 15000,
        "profile": "qwen",
    },
}


class WebBridge:
    """Playwright bridge — reads mesh inbox, sends to web AI, saves result."""

    def __init__(self, node: str, headless: bool = False):
        self.node = node
        self.headless = headless
        self.target = WEB_TARGETS.get(node)
        if not self.target:
            raise ValueError(f"Unknown node: {node}. Options: {list(WEB_TARGETS)}")

        self.inbox = REPO_ROOT / "logs" / "mesh" / "inbox" / node
        self.results = REPO_ROOT / "logs" / "local-agent" / "results"
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.results.mkdir(parents=True, exist_ok=True)

        self._pw = None
        self._ctx = None
        self._page = None

    def start(self):
        """Launch browser and navigate to target."""
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()

        # Use persistent context — profile name can be overridden in target config
        profile_name = self.target.get("profile", self.node)
        user_data = REPO_ROOT / "logs" / "browser_profiles" / profile_name
        user_data.mkdir(parents=True, exist_ok=True)

        # Check if saved session state exists
        session_file = user_data / "session_state.json"

        self._ctx = self._pw.chromium.launch_persistent_context(
            str(user_data),
            headless=self.headless,
            channel="chrome",
            slow_mo=200,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
            ignore_default_args=["--enable-automation"],
        )

        # Load session state if available (overwrites cookies)
        if session_file.exists():
            try:
                self._ctx.add_cookies(
                    json.loads(session_file.read_text()).get("cookies", [])
                )
                logger.info("Loaded saved session cookies for %s", self.node)
            except Exception as e:
                logger.warning("Could not load session state: %s", e)

        self._page = self._ctx.new_page()
        logger.info("Opening %s → %s", self.node, self.target["url"])
        self._page.goto(self.target["url"], timeout=60000, wait_until="domcontentloaded")
        time.sleep(3)
        logger.info("Browser ready. URL: %s", self._page.url)

    def stop(self):
        if self._ctx:
            self._ctx.close()
        if self._pw:
            self._pw.stop()

    def send_and_receive(self, prompt: str) -> Optional[str]:
        """Type prompt, submit, wait, extract response."""
        page = self._page
        cfg = self.target

        try:
            # Find input
            page.wait_for_selector(cfg["input_selector"], timeout=15000)
            inp = page.locator(cfg["input_selector"]).last

            # Click to focus
            inp.click()
            time.sleep(0.3)

            # For ProseMirror (MiniMax) use keyboard shortcuts to clear
            if "ProseMirror" in cfg["input_selector"]:
                page.keyboard.press("Control+a")
                page.keyboard.press("Delete")
            else:
                inp.fill("")

            # Type the prompt
            inp.type(prompt, delay=15)
            time.sleep(0.5)

            # Note URL before sending (Kimi navigates to new conversation page)
            url_before = page.url

            # Submit with Enter
            page.keyboard.press("Enter")
            logger.info("Sent. Waiting for response to generate...")

            # Wait for navigation if page changes (e.g. Kimi opens new conversation)
            for _ in range(10):
                time.sleep(1)
                if page.url != url_before:
                    logger.info("Page navigated to: %s", page.url)
                    time.sleep(2)
                    break

            # Processing keywords — MiniMax shows these while thinking
            processing_kw = [
                "recibido", "procesando", "working on it",
                "estoy trabajando", "estoy comenzando", "estoy procesando",
                "recibí tu solicitud",
            ]

            # Wait up to max_wait seconds for a real answer
            max_wait = int(cfg["wait_ms"] / 1000)
            prev_text = ""
            stable_count = 0
            final_text = None

            for _ in range(max_wait):
                time.sleep(1)
                try:
                    # Try specific selector first
                    els = page.locator(cfg["response_selector"]).all()
                    if els:
                        current = els[-1].inner_text().strip()
                    else:
                        # Fallback: grab full page text and take last chunk
                        current = page.inner_text("body").strip()
                        # Trim to last 1000 chars (most recent response)
                        current = current[-1000:].strip()

                    is_processing = any(k in current.lower() for k in processing_kw)

                    if not is_processing and current:
                        if current == prev_text:
                            stable_count += 1
                            if stable_count >= 3:
                                final_text = current
                                break
                        else:
                            stable_count = 0
                        prev_text = current
                except Exception:
                    pass

            # Debug: screenshot + raw body if nothing found
            if not final_text:
                try:
                    page.screenshot(path=str(REPO_ROOT / "logs" / f"debug_{self.node}.png"))
                    raw = page.inner_text("body").strip()[-500:]
                    logger.warning("No selector match. Page tail: %s", repr(raw[:200]))
                    if raw and len(raw) > 20:
                        return raw
                except Exception:
                    pass

            return final_text

        except Exception as exc:
            logger.error("send_and_receive failed: %s", exc)
            return None

    def process_inbox(self) -> int:
        """Process all pending .json tasks. Returns count processed."""
        tasks = sorted(self.inbox.glob("*.json"))
        if not tasks:
            return 0

        processed = 0
        for task_file in tasks:
            try:
                data = json.loads(task_file.read_text())
                task_id = data.get("task_id") or data.get("msg_id") or task_file.stem
                prompt = data.get("prompt") or data.get("task") or data.get("content") or str(data)

                # Mark as processing
                proc = task_file.with_suffix(".processing")
                task_file.rename(proc)

                logger.info("Processing task %s for node %s", task_id, self.node)
                t0 = time.time()
                response = self.send_and_receive(prompt)
                elapsed_ms = int((time.time() - t0) * 1000)

                if response:
                    # Save result
                    result = {
                        "task_id": task_id,
                        "node": self.node,
                        "prompt": prompt,
                        "result": response,
                        "success": True,
                        "duration_ms": elapsed_ms,
                        "source": "web_bridge",
                        "completed_at": time.time(),
                    }
                    (self.results / f"{task_id}.json").write_text(
                        json.dumps(result, indent=2, ensure_ascii=False)
                    )

                    # Deliver to claude-session-1 inbox
                    cs1 = REPO_ROOT / "logs" / "mesh" / "inbox" / "claude-session-1"
                    cs1.mkdir(exist_ok=True)
                    (cs1 / f"{task_id}.json").write_text(
                        json.dumps({
                            "msg_id": task_id,
                            "from": self.node,
                            "to": "claude-session-1",
                            "type": "task_result",
                            "result": response[:2000],
                            "duration_ms": elapsed_ms,
                            "success": True,
                        }, indent=2, ensure_ascii=False)
                    )
                    logger.info("✓ %s done in %.1fs", task_id, elapsed_ms / 1000)
                else:
                    logger.warning("✗ %s — no response extracted", task_id)

                proc.rename(proc.with_suffix(".done"))
                processed += 1

            except Exception as exc:
                logger.error("Error processing %s: %s", task_file.name, exc)

        return processed

    def run(self, poll_interval: int = 10):
        """Main polling loop."""
        self.start()
        logger.info("WebBridge running — node=%s poll=%ds", self.node, poll_interval)
        try:
            while True:
                n = self.process_inbox()
                if n:
                    logger.info("Processed %d tasks", n)
                time.sleep(poll_interval)
        except KeyboardInterrupt:
            logger.info("Stopping WebBridge...")
        finally:
            self.stop()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="DOF WebBridge — Playwright mesh node")
    parser.add_argument("--node", required=True, choices=list(WEB_TARGETS), help="Target AI web node")
    parser.add_argument("--poll", type=int, default=10, help="Poll interval seconds")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    parser.add_argument("--once", action="store_true", help="Process inbox once and exit")
    args = parser.parse_args()

    bridge = WebBridge(node=args.node, headless=args.headless)

    if args.once:
        bridge.start()
        n = bridge.process_inbox()
        print(f"Processed {n} tasks")
        bridge.stop()
    else:
        bridge.run(poll_interval=args.poll)


if __name__ == "__main__":
    main()
