"""
Genera voiceover_v2.mp3 + captions_v2.json — Andrew Neural — ~240s (4 min)
Narración completa DOF-MESH × Conflux Hackfest 2026 — V2 desde cero.

Voice: en-US-AndrewNeural  rate=-10%  (autoridad, claridad)
Sin silencios muertos — cada escena tiene audio continuo.

Uso:
  cd video-render
  pip install edge-tts
  python generate_voice_v2_hackathon.py
"""

import asyncio, json, os, subprocess, sys
from pathlib import Path

BASE   = Path(__file__).parent
OUT_MP3   = BASE / "public" / "voiceover_v2.mp3"
OUT_JSON  = BASE / "public" / "captions_v2.json"
VOICE     = "en-US-AndrewNeural"
RATE      = "-10%"
FPS       = 30

# ─── NARRACIÓN COMPLETA ───────────────────────────────────────────────────────
# Reglas:
#   - Sin silencios largos: las líneas en blanco son pausa mínima (~0.2s)
#   - Métricas correctas: 4,308 tests · 8 chains · 147 proofs · 0x8B6B...
#   - Ritmo: frases cortas = impacto. Frases largas = detalle técnico.
#   - Cada escena marcada con comentario para referencia

NARRATION = """\
Two trillion dollars.
Zero proof.
AI agents are executing transactions, managing DAO treasuries, making financial decisions — right now.
And there is no mathematical proof any of them behaved correctly.

You would not trust a bridge that was probably structurally sound.
But every autonomous agent fleet runs on probably.

Rules encoded as prompts can be overridden at any moment.
Language models hallucinate. A validator that lies cannot validate.
Audit logs can be altered after the fact.
The entire AI agent stack is built on trust — and trust is not a proof.

DOF-MESH changes this.
We are the first framework that mathematically proves an AI agent behaved correctly — before it acts.

Three independent deterministic layers.
Layer one: Constitution enforcement. Deterministic rules. Zero language models in the decision path.
Layer two: Z3 SMT formal verification. Four theorems proven for all possible inputs — by Microsoft Research's solver.
Layer three: TRACER score. Five-dimensional behavioral quality scoring.
The result: a keccak256 proof hash, registered permanently on Conflux — tamper-proof forever.

Why now?
Three hundred twenty-seven million AI agents will be deployed by 2027.
The AI governance market reaches forty-seven billion dollars by 2030.
And today — zero frameworks offer formal mathematical proof.
The infrastructure gap is open. We built the solution.

Watch this live.
Agent 1687 requests a DeFi transaction on Conflux eSpace.
DOF-MESH intercepts it before execution.
Constitution check: passed. Zero language models involved.
Z3 formal verification: four of four theorems proven in seven milliseconds.
TRACER behavioral score: zero point seven one two — well above threshold.
The agent qualifies. Now it goes on-chain.

Here is the proof. Permanent.
One hundred forty-five confirmed transactions on DOFProofRegistryV1.
And our latest innovation: V2 Proof-to-Gasless.
When an agent proves mathematical compliance — TRACER above zero point four, Constitution above ninety percent — it is automatically added to Conflux's SponsorWhitelistControl.
Its next transactions cost zero gas.
Math earns economic privilege. That is new.

Why Conflux? Because Gas Sponsorship is architecturally necessary for agent infrastructure.
Agents should not hold gas — they should act.
Conflux's native SponsorWhitelistControl makes zero-friction compliance registration possible at any scale.
On Ethereum, every agent needs gas. On Conflux, math replaces money.
No other EVM chain has this natively.

Three revenue streams.
First: the open-source SDK. Developers run pip install dof-sdk — Conflux integration ships included.
Second: the compliance API at ninety-nine to nine hundred ninety-nine dollars per month. Finance. Healthcare. Legal. Any team that cannot afford an agent that lies.
Third: enterprise white-label licensing. Fifty thousand to five hundred thousand dollars per year. DAO treasuries, DeFi protocols, full agent fleets.

The total addressable market for AI governance reaches eighteen billion by 2028.
Our serviceable market — blockchain AI agent compliance — is three point two billion.
Our realistic capture in year three: one hundred sixty million, starting with DeFi protocols needing provably-correct agents.

This is not a prototype.
One hundred forty-seven on-chain attestations on Conflux alone.
Eight active chains.
Four thousand three hundred eight tests passing.
Two hundred thirty-eight autonomous agent cycles completed.
Six MCP tools fully operational — the first Model Context Protocol server for Conflux Network.
ERC-8004, the Autonomous Agent Identity Standard, submitted to Ethereum Magicians.

I am Juan Carlos Quiceno — solo builder from Medellín, Colombia.
I built every line of this: the framework, the contracts, the MCP server, the SDK.

My ask is simple: help us deploy to Conflux mainnet, connect us with regulated-industry partners, and recognize this as the missing infrastructure layer for AI on blockchain.

The math is proven. The chain is ready. The agents are waiting.

Most frameworks verify what happened.
DOF verifies what is about to happen.
"""

# ─── GENERACIÓN ───────────────────────────────────────────────────────────────

async def generate():
    try:
        import edge_tts
    except ImportError:
        print("ERROR: pip install edge-tts")
        sys.exit(1)

    print(f"Generando audio: {VOICE} {RATE}")
    print(f"Output: {OUT_MP3}")

    communicate = edge_tts.Communicate(text=NARRATION, voice=VOICE, rate=RATE)
    sentences = []

    # Recolectar SentenceBoundary para captions
    async def collect():
        async for ev in communicate.stream():
            if ev["type"] == "SentenceBoundary":
                start_ms  = ev["offset"] / 10000
                dur_ms    = ev["duration"] / 10000
                end_ms    = start_ms + dur_ms
                text      = ev["text"].strip()
                if text:
                    sentences.append({
                        "text":     text,
                        "start_ms": round(start_ms),
                        "end_ms":   round(end_ms),
                        "start_f":  int(start_ms / 1000 * FPS),
                        "end_f":    int(end_ms   / 1000 * FPS),
                    })

    # Recolectar captions Y audio en una sola pasada
    print("Streaming audio + captions en una pasada...")
    audio_bytes = bytearray()
    async for ev in communicate.stream():
        if ev["type"] == "audio":
            audio_bytes.extend(ev["data"])
        elif ev["type"] == "SentenceBoundary":
            start_ms  = ev["offset"] / 10000
            dur_ms    = ev["duration"] / 10000
            end_ms    = start_ms + dur_ms
            text      = ev["text"].strip()
            if text:
                sentences.append({
                    "text":     text,
                    "start_ms": round(start_ms),
                    "end_ms":   round(end_ms),
                    "start_f":  int(start_ms / 1000 * FPS),
                    "end_f":    int(end_ms   / 1000 * FPS),
                })

    OUT_MP3.write_bytes(audio_bytes)
    print(f"Audio guardado: {OUT_MP3}")

    # Escribir JSON de captions
    captions = {
        "voice":     VOICE,
        "rate":      RATE,
        "fps":       FPS,
        "total_sentences": len(sentences),
        "sentences": sentences
    }
    OUT_JSON.write_text(json.dumps(captions, indent=2, ensure_ascii=False))
    print(f"Captions: {OUT_JSON} ({len(sentences)} sentences)")

    # Duración total
    if OUT_MP3.exists():
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(OUT_MP3)],
            capture_output=True, text=True
        )
        try:
            dur = float(result.stdout.strip())
            total_frames = int(dur * FPS)
            print(f"\nDuración: {dur:.1f}s ({total_frames} frames @ {FPS}fps)")
            print(f"Tiempo video: {int(dur//60)}:{int(dur%60):02d}")
        except:
            pass

    print("\nDONE. Archivos generados:")
    print(f"  Audio:    {OUT_MP3}")
    print(f"  Captions: {OUT_JSON}")
    print("\nPróximo paso:")
    print("  python gen_subs_v2.py  # genera SubtitlesV2.tsx desde captions_v2.json")

if __name__ == "__main__":
    asyncio.run(generate())
