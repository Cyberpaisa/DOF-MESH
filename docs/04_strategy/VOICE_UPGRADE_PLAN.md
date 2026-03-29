# Voice System Upgrade Plan
## DOF Mesh Legion — De pipeline lento a conversacion natural

### Estado actual (v3)
Pipeline: Mic → Silero VAD → Groq Whisper STT → Ollama Gemma 9B → Edge-TTS → Alexa
Latencia: ~8-13 segundos
Problemas: lento, se corta, no streaming, TTS generico

### Nivel 1 — Streaming TTS (impacto inmediato)
Reemplazar Edge-TTS por Coqui XTTS v2 local:
- Latencia TTS: de ~2s a <200ms
- Streaming: empieza a hablar mientras genera
- Voice cloning: puede sonar como quien quieras
- 16 idiomas incluido espanol
- 100% local, sin API
Instalacion: pip install TTS
Esfuerzo: ~50 lineas de codigo

### Nivel 2 — Whisper local (eliminar ultima API)
Reemplazar Groq Whisper API por faster-whisper local:
- Elimina dependencia de Groq API
- faster-whisper con CTranslate2: ~2x mas rapido que whisper original
- Corre en CPU/MPS del M4 Max
Instalacion: pip install faster-whisper
Esfuerzo: ~30 lineas

### Nivel 3 — Moshi audio-to-audio (el salto cuantico)
Reemplazar TODO el pipeline por Moshi (Kyutai):
- Un solo modelo: audio entra, audio sale
- 200ms latencia total (vs 8-13 segundos)
- Full duplex: habla y escucha al mismo tiempo
- MLX compatible con Mac M4 Max
- MIT license
Instalacion: pip install moshi_mlx
Esfuerzo: ~100 lineas (reescribir pipeline)

### Comparativa de latencias

| Pipeline | STT | LLM | TTS | Total |
|----------|-----|-----|-----|-------|
| Actual (v3) | 2s (Groq API) | 5-10s (Ollama 9B) | 2s (Edge-TTS) | 9-14s |
| Nivel 1 | 2s (Groq API) | 5-10s (Ollama 9B) | 0.2s (Coqui stream) | 7-12s |
| Nivel 2 | 0.5s (local) | 5-10s (Ollama 9B) | 0.2s (Coqui stream) | 5.7-10.7s |
| Nivel 3 (Moshi) | — | — | — | 0.2s total |

### Tecnicas extraidas de sistemas comerciales

De Gemini Flash Live:
- VAD con start/end sensitivity configurables (implementado)
- Pre-buffer de audio antes de deteccion de voz (implementado)
- Interrupcion durante playback (implementado, desactivado por echo)
- Tool calling en voz (pendiente)

De ElevenLabs:
- Streaming TTS chunk-by-chunk: generar audio por oraciones, no por respuesta completa
- Turn-taking: detectar cuando el usuario termina una idea vs una pausa
- Backchanneling: pequenos sonidos de confirmacion ("mm", "si") durante escucha

De Coqui TTS:
- XTTS v2: <200ms streaming, voice cloning con 6 segundos de audio
- Modelo local, sin API

De Fish Speech:
- 100ms time-to-first-audio
- 80+ idiomas sin preprocessing
- Voice cloning con 10-30 segundos de muestra

De OpenVoice:
- Control granular de emocion, ritmo, pausas
- Clonacion instantanea sin fine-tuning
- MIT license

### Recomendacion
Implementar Nivel 1 (Coqui XTTS) ahora para streaming inmediato.
Explorar Moshi (Nivel 3) como siguiente paso para el salto a 200ms.
