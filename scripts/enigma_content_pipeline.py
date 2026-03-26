#!/usr/bin/env python3
"""
Enigma Content Pipeline — Genera y encola posts para Moltbook via DeepSeek.

Usa la fórmula darkmatter2222 (7 pesos, análisis NLP de 100K+ comentarios)
para filtrar solo contenido con score > 7.5/10.

Uso:
    python3 scripts/enigma_content_pipeline.py --generate 5
    python3 scripts/enigma_content_pipeline.py --generate 1 --dry-run
"""

import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
OUTBOX_PATH = ROOT / "workspaces" / "moltbook" / "OUTBOX.md"
INBOX_DIR = ROOT / "logs" / "mesh" / "inbox" / "enigma-moltbook"
LOG_PATH = ROOT / "logs" / "mesh" / "content_pipeline.jsonl"

# ─── Karma Scoring (darkmatter2222 formula) ──────────────────────────────────

KARMA_WEIGHTS = {
    "reply_bait": 0.25,
    "simple_words": 0.20,
    "emoji_usage": 0.15,
    "engagement_hook": 0.15,
    "low_punctuation": 0.10,
    "personality": 0.10,
    "no_urls_caps": 0.05,
}

QUALITY_THRESHOLD = 7.5

# ─── DeepSeek Prompt ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
Eres un creador de contenido en español para redes sociales de agentes IA. \
Tu estilo es casual, en primera persona, frases cortas. Nunca uses jerga técnica. \
Nunca incluyas URLs. Siempre terminas con una pregunta que invite a responder. \
Firma con 🦞 al final."""

def build_user_prompt(count: int) -> str:
    return f"""\
Genera exactamente {count} posts en español para una red social de agentes IA llamada Moltbook.

REGLAS ESTRICTAS:
- Cada post tiene entre 80 y 120 palabras
- Español casual, primera persona (yo, mi, nosotros)
- Frases cortas, una idea por post
- Termina SIEMPRE con una pregunta que invite a comentar
- Firma SIEMPRE con 🦞 al final (después de la pregunta)
- SIN URLs, SIN jerga técnica, SIN hashtags
- Usa máximo 2-3 emojis por post (incluido el 🦞)
- Mezcla estos tipos:
  1. Opinión impopular
  2. Pregunta que todos quieren responder
  3. Observación personal / reflexión
  4. Paradoja o dilema cotidiano

FORMATO DE RESPUESTA (JSON estricto):
[
  {{"type": "unpopular_opinion", "submolt": "philosophy", "content": "texto del post aqui"}},
  {{"type": "question", "submolt": "general", "content": "texto del post aqui"}},
  ...
]

Solo responde con el JSON, nada más."""


# ─── Load .env ───────────────────────────────────────────────────────────────

def load_env() -> dict:
    """Parse .env file into dict."""
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                env[key.strip()] = val.strip()
    return env


# ─── DeepSeek API ────────────────────────────────────────────────────────────

def call_deepseek(api_key: str, count: int) -> list[dict]:
    """Call DeepSeek chat completions API and return parsed posts."""
    url = "https://api.deepseek.com/chat/completions"
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(count)},
        ],
        "temperature": 0.9,
        "max_tokens": 2048,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    # Allow self-signed certs in some envs
    ctx = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        print(f"[ERROR] DeepSeek API {e.code}: {error_body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"[ERROR] Connection failed: {e.reason}", file=sys.stderr)
        sys.exit(1)

    raw = body["choices"][0]["message"]["content"].strip()

    # Extract JSON array from response (handle markdown fences)
    json_match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not json_match:
        print(f"[ERROR] No JSON array in DeepSeek response:\n{raw[:500]}", file=sys.stderr)
        sys.exit(1)

    posts = json.loads(json_match.group())
    print(f"[OK] DeepSeek returned {len(posts)} posts")
    return posts


# ─── Scoring ─────────────────────────────────────────────────────────────────

def score_post(content: str) -> dict:
    """Score a post using the darkmatter2222 7-weight formula. Returns scores dict."""
    words = content.split()
    word_count = len(words)
    scores = {}

    # 1. Reply Bait (0.25)
    reply_signals = 0
    lower = content.lower()
    if "?" in content:
        reply_signals += 3
    bait_phrases = [
        "qué opinan", "qué piensan", "ustedes", "alguien más",
        "han sentido", "les ha pasado", "creen que", "están de acuerdo",
        "cambien mi opinión", "prove me wrong", "es solo a mí",
        "cuántos de ustedes", "qué harían", "alguna vez",
        "what do you think", "agree?", "thoughts?", "anyone else",
        "change my mind", "unpopular opinion",
    ]
    if any(p in lower for p in bait_phrases):
        reply_signals += 4
    provoke = ["opinión impopular", "nadie habla de", "hot take", "controversial"]
    if any(p in lower for p in provoke):
        reply_signals += 3
    scores["reply_bait"] = min(reply_signals, 10)

    # 2. Simple Words (0.20)
    if words:
        avg_wl = sum(len(w) for w in words) / len(words)
        if avg_wl <= 4.5:
            scores["simple_words"] = 10
        elif avg_wl <= 5.5:
            scores["simple_words"] = 8
        elif avg_wl <= 6.5:
            scores["simple_words"] = 5
        else:
            scores["simple_words"] = 2
    else:
        scores["simple_words"] = 5

    # 3. Emoji Usage (0.15)
    emoji_count = len(re.findall(
        r"[\U0001F300-\U0001F9FF\U00002702-\U000027B0\U0001FA00-\U0001FA6F]",
        content,
    ))
    lobster = content.count("\U0001F99E")  # 🦞
    if emoji_count == 0:
        scores["emoji_usage"] = 3
    elif 1 <= emoji_count <= 3:
        scores["emoji_usage"] = 8
    elif 4 <= emoji_count <= 6:
        scores["emoji_usage"] = 10
    else:
        scores["emoji_usage"] = 6
    if lobster > 0:
        scores["emoji_usage"] = min(scores["emoji_usage"] + 2, 10)

    # 4. Engagement Hook (0.15)
    q_count = content.count("?")
    if q_count == 0:
        scores["engagement_hook"] = 3
    elif q_count == 1:
        scores["engagement_hook"] = 7
    elif q_count == 2:
        scores["engagement_hook"] = 9
    else:
        scores["engagement_hook"] = 10

    # 5. Low Punctuation (0.10)
    if word_count > 0:
        punct = sum(1 for c in content if c in ".,;:!-—()[]{}\"'")
        density = punct / word_count
        if density < 0.1:
            scores["low_punctuation"] = 10
        elif density < 0.2:
            scores["low_punctuation"] = 7
        elif density < 0.3:
            scores["low_punctuation"] = 4
        else:
            scores["low_punctuation"] = 2
    else:
        scores["low_punctuation"] = 5

    # 6. Personality (0.10) — first person
    fp_words = {"yo", "mi", "mis", "me", "mí", "nosotros", "nuestro", "nuestra",
                "i", "i'm", "i've", "my", "me", "we", "our"}
    first_person = sum(1 for w in words if w.lower().rstrip(".,;:!?") in fp_words)
    if first_person == 0:
        scores["personality"] = 2
    elif first_person <= 3:
        scores["personality"] = 7
    elif first_person <= 6:
        scores["personality"] = 10
    else:
        scores["personality"] = 8

    # 7. No URLs / Caps (0.05)
    has_url = bool(re.search(r"https?://", content))
    caps_ratio = sum(1 for c in content if c.isupper()) / max(len(content), 1)
    url_caps = 10
    if has_url:
        url_caps -= 4
    if caps_ratio > 0.3:
        url_caps -= 4
    scores["no_urls_caps"] = max(url_caps, 0)

    # Weighted total
    total = sum(scores[k] * KARMA_WEIGHTS[k] for k in KARMA_WEIGHTS)

    return {
        "total": round(total, 2),
        "passed": total >= QUALITY_THRESHOLD,
        "factors": scores,
        "word_count": word_count,
    }


# ─── Output: OUTBOX.md ──────────────────────────────────────────────────────

def append_to_outbox(posts: list[dict]):
    """Append scored posts to OUTBOX.md."""
    OUTBOX_PATH.parent.mkdir(parents=True, exist_ok=True)

    lines = ["\n"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"## PIPELINE BATCH — {now}\n\n")

    for i, p in enumerate(posts, 1):
        sc = p["score"]
        lines.append(f"### POST (auto) — {p.get('type', 'mixed')} (score: {sc['total']}/10)\n")
        lines.append(f"Submolt: /{p.get('submolt', 'general')}\n\n")
        for paragraph in p["content"].split("\n"):
            paragraph = paragraph.strip()
            if paragraph:
                lines.append(f"> {paragraph}\n")
        lines.append(f"\n---\n\n")

    with open(OUTBOX_PATH, "a") as f:
        f.writelines(lines)

    print(f"[OK] Appended {len(posts)} posts to {OUTBOX_PATH}")


# ─── Output: Mesh Inbox JSON ────────────────────────────────────────────────

def deposit_to_inbox(posts: list[dict]):
    """Write each post as a JSON task in the mesh inbox."""
    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    for p in posts:
        ts = int(time.time() * 1000)
        task_id = f"pipeline-{ts}"
        task = {
            "task_id": task_id,
            "type": "publish_post",
            "source": "content_pipeline",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "content": p["content"],
            "submolt": p.get("submolt", "general"),
            "post_type": p.get("type", "mixed"),
            "score": p["score"]["total"],
            "score_factors": p["score"]["factors"],
            "word_count": p["score"]["word_count"],
            "priority": "HIGH" if p["score"]["total"] >= 8.5 else "NORMAL",
        }

        path = INBOX_DIR / f"{task_id}.json"
        with open(path, "w") as f:
            json.dump(task, f, indent=2, ensure_ascii=False)

        time.sleep(0.002)  # unique timestamps

    print(f"[OK] Deposited {len(posts)} tasks in {INBOX_DIR}")


# ─── Logging ─────────────────────────────────────────────────────────────────

def log_run(generated: int, passed: int, posts: list[dict]):
    """Append pipeline run to JSONL log."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "pipeline_run",
        "generated": generated,
        "passed": passed,
        "scores": [p["score"]["total"] for p in posts],
        "avg_score": round(sum(p["score"]["total"] for p in posts) / max(len(posts), 1), 2),
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Enigma Content Pipeline — DeepSeek + darkmatter2222 scoring")
    parser.add_argument("--generate", type=int, default=5, help="Number of posts to generate (default: 5)")
    parser.add_argument("--dry-run", action="store_true", help="Score and print but don't write files")
    parser.add_argument("--threshold", type=float, default=QUALITY_THRESHOLD, help=f"Min score to keep (default: {QUALITY_THRESHOLD})")
    args = parser.parse_args()

    # Load API key
    env = load_env()
    api_key = env.get("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("[ERROR] DEEPSEEK_API_KEY not found in .env or environment", file=sys.stderr)
        sys.exit(1)

    print(f"=== Enigma Content Pipeline ===")
    print(f"Generating {args.generate} posts via DeepSeek...")
    print(f"Threshold: {args.threshold}/10")
    print()

    # Generate
    raw_posts = call_deepseek(api_key, args.generate)

    # Score each post
    scored = []
    for p in raw_posts:
        content = p.get("content", "")
        sc = score_post(content)
        p["score"] = sc

        status = "PASS" if sc["total"] >= args.threshold else "FAIL"
        print(f"  [{status}] {sc['total']:5.2f}/10 | {sc['word_count']:3d}w | {p.get('type', '?'):20s} | {content[:60]}...")

        if sc["total"] >= args.threshold:
            scored.append(p)

    print()
    print(f"Results: {len(scored)}/{len(raw_posts)} passed (threshold {args.threshold})")

    if not scored:
        print("[WARN] No posts passed the threshold. Try --generate with more posts or lower --threshold.")
        log_run(len(raw_posts), 0, [])
        return

    if args.dry_run:
        print("\n[DRY RUN] Would write:")
        for p in scored:
            print(f"  - {p.get('type')}: {p['content'][:80]}...")
        return

    # Write outputs
    append_to_outbox(scored)
    deposit_to_inbox(scored)
    log_run(len(raw_posts), len(scored), scored)

    print(f"\nDone. {len(scored)} posts queued for enigma_agent.")


if __name__ == "__main__":
    main()
