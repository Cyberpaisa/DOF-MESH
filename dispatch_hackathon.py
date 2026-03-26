#!/usr/bin/env python3
"""
Dispatch 14 hackathon tasks using LiteLLM Router with automatic fallback.
Cerebras -> Groq GPT-OSS-120B -> Groq Kimi K2 -> Mistral -> Ollama local
"""

import os
import json
import sqlite3
import asyncio
import time
from datetime import datetime

# Load API keys from DOF .env
from pathlib import Path
env_path = Path(__file__).parent / "deterministic-observability-framework" / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from litellm import Router

# Provider chain: ordered by speed and quality
MODEL_LIST = [
    {
        "model_name": "hackathon",
        "litellm_params": {
            "model": "cerebras/qwen-3-235b-a22b-instruct-2507",
            "api_key": os.environ.get("CEREBRAS_API_KEY", ""),
            "max_tokens": 8192,
        },
        "model_info": {"id": "cerebras-qwen3"},
    },
    {
        "model_name": "hackathon",
        "litellm_params": {
            "model": "groq/openai/gpt-oss-120b",
            "api_key": os.environ.get("GROQ_API_KEY", ""),
            "max_tokens": 8192,
        },
        "model_info": {"id": "groq-gpt-oss"},
    },
    {
        "model_name": "hackathon",
        "litellm_params": {
            "model": "groq/moonshotai/kimi-k2-instruct",
            "api_key": os.environ.get("GROQ_API_KEY", ""),
            "max_tokens": 8192,
        },
        "model_info": {"id": "groq-kimi-k2"},
    },
    {
        "model_name": "hackathon",
        "litellm_params": {
            "model": "mistral/mistral-large-latest",
            "api_key": os.environ.get("MISTRAL_API_KEY", ""),
            "max_tokens": 8192,
        },
        "model_info": {"id": "mistral-large"},
    },
]

# Only add Ollama if it's running
import urllib.request
try:
    urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2)
    MODEL_LIST.append({
        "model_name": "hackathon",
        "litellm_params": {
            "model": "ollama/qwen2.5-coder:32b",
            "api_base": "http://127.0.0.1:11434",
            "max_tokens": 8192,
        },
        "model_info": {"id": "ollama-local"},
    })
    print("[+] Ollama detected, added as fallback")
except:
    print("[-] Ollama not running, skipping local fallback")

router = Router(
    model_list=MODEL_LIST,
    enable_pre_call_checks=True,
    num_retries=3,
    retry_after=2,
    allowed_fails=3,
    cooldown_time=30,
)

DB_PATH = Path(__file__).parent / "data" / "legion_tasks.db"

def get_tasks():
    """Read tasks from Mission Control SQLite database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT id, title, description, assigned_to FROM tasks WHERE id BETWEEN 1 AND 14 ORDER BY id"
    )
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks

def build_prompt(task):
    """Build a detailed prompt for each hackathon task."""
    return f"""You are an expert AI engineer participating in the Synthesis Hackathon 2026.

TASK: {task['title']}

DESCRIPTION: {task.get('description', 'No description provided.')}

INSTRUCTIONS:
- Write a comprehensive, hackathon-winning response
- Include specific technical details, code examples, and architecture diagrams where relevant
- Reference real technologies: Solidity, EVM, formal verification (Z3), deterministic observability
- The DOF (Deterministic Observability Framework) is our core technology: it provides deterministic governance, Z3 formal proofs, on-chain attestations, and runtime observability for AI agents
- Be thorough, impressive, and technically deep
- Format your response with clear markdown sections
- Include code examples where appropriate

Respond with your complete submission for this hackathon task."""

def save_result(task_id, response_text, model_used, duration_ms):
    """Save task result back to Mission Control database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """UPDATE tasks SET
           status = 'completed',
           resolution = ?,
           outcome = 'approved',
           metadata = ?
           WHERE id = ?""",
        (
            response_text,
            json.dumps({
                "model": model_used,
                "dispatch_method": "litellm_router",
                "duration_ms": duration_ms,
                "dispatched_at": datetime.now().isoformat(),
            }),
            task_id,
        ),
    )
    conn.commit()
    conn.close()

async def dispatch_task(task, semaphore):
    """Dispatch a single task with automatic fallback."""
    async with semaphore:
        task_id = task["id"]
        title = task["title"][:60]
        prompt = build_prompt(task)

        print(f"\n[{task_id}/14] Dispatching: {title}")
        start = time.time()

        try:
            response = await router.acompletion(
                model="hackathon",
                messages=[{"role": "user", "content": prompt}],
                timeout=120,
            )

            text = response.choices[0].message.content
            model_used = response.model or "unknown"
            duration_ms = int((time.time() - start) * 1000)

            # Quality check: response must be substantial
            if len(text) < 500:
                print(f"  [!] Task {task_id}: Response too short ({len(text)} chars), retrying...")
                # Retry once with explicit request for longer response
                response = await router.acompletion(
                    model="hackathon",
                    messages=[
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": text},
                        {"role": "user", "content": "This response is too short for a hackathon submission. Please provide a much more detailed and comprehensive response with code examples, architecture details, and technical depth. Aim for at least 2000 words."},
                    ],
                    timeout=120,
                )
                text = response.choices[0].message.content
                model_used = response.model or "unknown"
                duration_ms = int((time.time() - start) * 1000)

            save_result(task_id, text, model_used, duration_ms)
            print(f"  [OK] Task {task_id}: {len(text)} chars, {duration_ms}ms, model={model_used}")
            return {"id": task_id, "status": "ok", "chars": len(text), "model": model_used}

        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            error_msg = str(e)[:200]
            print(f"  [FAIL] Task {task_id}: {error_msg}")

            # Save error state
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute(
                "UPDATE tasks SET status = 'failed', error_message = ? WHERE id = ?",
                (error_msg, task_id),
            )
            conn.commit()
            conn.close()
            return {"id": task_id, "status": "fail", "error": error_msg}

async def main():
    print("=" * 60)
    print("HACKATHON DISPATCH — LiteLLM Router + Multi-Provider Fallback")
    print("=" * 60)
    print(f"Providers: {len(MODEL_LIST)} configured")
    for m in MODEL_LIST:
        print(f"  - {m['model_info']['id']}: {m['litellm_params']['model']}")

    # Load tasks
    tasks = get_tasks()
    print(f"\nTasks loaded: {len(tasks)}")
    for t in tasks:
        print(f"  [{t['id']}] {t['title'][:70]}")

    # Reset tasks to assigned state
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """UPDATE tasks SET status='assigned', outcome=NULL, error_message=NULL,
           resolution=NULL, retry_count=0 WHERE id BETWEEN 1 AND 14"""
    )
    conn.execute("DELETE FROM quality_reviews WHERE task_id BETWEEN 1 AND 14")
    conn.commit()
    conn.close()
    print("\nTasks reset to 'assigned'")

    # Dispatch with concurrency limit (avoid rate limits)
    semaphore = asyncio.Semaphore(2)  # Max 2 concurrent requests
    print(f"\nDispatching {len(tasks)} tasks (max 2 concurrent)...\n")

    start_time = time.time()
    results = await asyncio.gather(
        *[dispatch_task(t, semaphore) for t in tasks],
        return_exceptions=True,
    )
    total_time = time.time() - start_time

    # Summary
    print("\n" + "=" * 60)
    print("DISPATCH SUMMARY")
    print("=" * 60)
    ok = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "ok")
    fail = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "fail")
    errors = sum(1 for r in results if isinstance(r, Exception))

    print(f"Completed: {ok}/14")
    print(f"Failed: {fail}/14")
    print(f"Errors: {errors}/14")
    print(f"Total time: {total_time:.1f}s")

    for r in results:
        if isinstance(r, dict):
            status = "OK" if r["status"] == "ok" else "FAIL"
            print(f"  [{r['id']}] {status} — {r.get('chars', 0)} chars, {r.get('model', r.get('error', ''))}")
        elif isinstance(r, Exception):
            print(f"  [?] Exception: {str(r)[:100]}")

if __name__ == "__main__":
    asyncio.run(main())
