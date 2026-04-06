"""
YouTube Ingestor — DOF Knowledge Pipeline, Componente 1.
Input:  URL YouTube
Output: docs/knowledge/YYYY-MM-DD-{slug}.md (transcripción limpia)
"""

import os
import re
import sys
import json
import subprocess
import hashlib
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
KNOWLEDGE_DIR = BASE_DIR / "docs" / "knowledge"
COOKIES_FILE = Path("/tmp/yt_cookies.txt")
YT_DLP_BASE = [
    "yt-dlp",
    "--write-auto-sub", "--skip-download",
    "--sub-lang", "es",
    "--convert-subs", "srt",
    "--remote-components", "ejs:github",
    "-o", "/tmp/yt_ingest",
]
YT_DLP_META = [
    "yt-dlp",
    "--print", "%(title)s\t%(id)s\t%(duration)s",
    "--skip-download",
    "--remote-components", "ejs:github",
]


def _slug(title: str) -> str:
    s = re.sub(r"[^\w\s-]", "", title.lower())
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return s[:60]


def _clean_srt(srt_path: Path) -> str:
    """Remove timestamps and sequence numbers, deduplicate lines."""
    lines, seen, prev = [], set(), ""
    for line in srt_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r"^\d+$", line):
            continue
        if re.match(r"^\d{2}:\d{2}:\d{2}", line):
            continue
        if line == prev or line in seen:
            continue
        seen.add(line)
        prev = line
        lines.append(line)
    return "\n".join(lines)


def ingest(url: str) -> Path:
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

    cookies = ["--cookies", str(COOKIES_FILE)] if COOKIES_FILE.exists() else []

    # Step 1: get metadata
    meta_cmd = YT_DLP_META + cookies + [url]
    meta = subprocess.run(meta_cmd, capture_output=True, text=True)
    parts = meta.stdout.strip().splitlines()[-1].split("\t") if meta.stdout.strip() else []
    title = parts[0] if parts else "unknown"
    video_id = parts[1] if len(parts) > 1 else hashlib.md5(url.encode()).hexdigest()[:8]
    duration_s = int(parts[2]) if len(parts) > 2 else 0

    # Step 2: download SRT
    dl_cmd = YT_DLP_BASE + cookies + [url]
    result = subprocess.run(dl_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed:\n{result.stderr[-1000:]}")

    srt = Path(f"/tmp/yt_ingest.es.srt")
    if not srt.exists():
        raise FileNotFoundError(f"SRT not found at {srt}. Check subtitles availability.")

    transcript = _clean_srt(srt)
    srt.unlink(missing_ok=True)

    date = datetime.now().strftime("%Y-%m-%d")
    slug = _slug(title)
    out_path = KNOWLEDGE_DIR / f"{date}-{slug}.md"

    metadata = {
        "title": title,
        "video_id": video_id,
        "url": url,
        "duration_seconds": duration_s,
        "ingested_at": datetime.now().isoformat(),
        "word_count": len(transcript.split()),
    }

    out_path.write_text(
        f"# {title}\n\n"
        f"<!-- meta:{json.dumps(metadata)} -->\n\n"
        f"## Transcripción\n\n{transcript}\n",
        encoding="utf-8",
    )

    print(f"✓ {out_path.name} ({metadata['word_count']} palabras)")
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 core/youtube_ingestor.py <URL>")
        sys.exit(1)
    ingest(sys.argv[1])
