# Voice System Upgrade Plan
## DOF Mesh Legion — From slow pipeline to natural conversation

### Current state (v3)
Pipeline: Mic → Silero VAD → Groq Whisper STT → Ollama Gemma 9B → Edge-TTS → Alexa
Latency: ~8-13 seconds
Issues: slow, cuts out, no streaming, generic TTS

### Level 1 — Streaming TTS (immediate impact)
Replace Edge-TTS with Coqui XTTS v2 local:
- TTS latency: from ~2s to <200ms
- Streaming: starts speaking while generating
- Voice cloning: can sound like whoever you want
- 16 languages including Spanish
- 100% local, no API
Installation: pip install TTS
Effort: ~50 lines of code

### Level 2 — Local Whisper (eliminate last API)
Replace Groq Whisper API with faster-whisper local:
- Eliminates Groq API dependency
- faster-whisper with CTranslate2: ~2x faster than original whisper
- Runs on CPU/MPS of M4 Max
Installation: pip install faster-whisper
Effort: ~30 lines

### Level 3 — Moshi audio-to-audio (the quantum leap)
Replace the ENTIRE pipeline with Moshi (Kyutai):
- Single model: audio in, audio out
- 200ms total latency (vs 8-13 seconds)
- Full duplex: speaks and listens at the same time
- MLX compatible with Mac M4 Max
- MIT license
Installation: pip install moshi_mlx
Effort: ~100 lines (rewrite pipeline)

### Latency comparison

| Pipeline | STT | LLM | TTS | Total |
|----------|-----|-----|-----|-------|
| Current (v3) | 2s (Groq API) | 5-10s (Ollama 9B) | 2s (Edge-TTS) | 9-14s |
| Level 1 | 2s (Groq API) | 5-10s (Ollama 9B) | 0.2s (Coqui stream) | 7-12s |
| Level 2 | 0.5s (local) | 5-10s (Ollama 9B) | 0.2s (Coqui stream) | 5.7-10.7s |
| Level 3 (Moshi) | — | — | — | 0.2s total |

### Techniques extracted from commercial systems

From Gemini Flash Live:
- VAD with configurable start/end sensitivity (implemented)
- Audio pre-buffer before voice detection (implemented)
- Interruption during playback (implemented, disabled due to echo)
- Tool calling via voice (pending)

From ElevenLabs:
- Chunk-by-chunk streaming TTS: generate audio per sentence, not per full response
- Turn-taking: detect when the user finishes an idea vs a pause
- Backchanneling: small confirmation sounds ("mm", "yes") while listening

From Coqui TTS:
- XTTS v2: <200ms streaming, voice cloning with 6 seconds of audio
- Local model, no API

From Fish Speech:
- 100ms time-to-first-audio
- 80+ languages without preprocessing
- Voice cloning with 10-30 seconds of sample

From OpenVoice:
- Granular control of emotion, rhythm, pauses
- Instant cloning without fine-tuning
- MIT license

### Recommendation
Implement Level 1 (Coqui XTTS) now for immediate streaming.
Explore Moshi (Level 3) as the next step for the leap to 200ms.
