#!/Users/jquiceva/DOF-MESH/.venv-voice/bin/python3
"""
Voice V4 — Pipeline de voz de alta calidad.
DOF Mesh Legion / Cyber Paisa / Enigma Group

Pipeline:
  Mic -> Silero VAD (local) -> faster-whisper (local) -> Ollama multi-modelo (local)
      -> Edge-TTS DaliaNeural (streaming por oraciones) -> Alexa (Bluetooth)

Componentes:
  STT:     faster-whisper (local, CTranslate2, int8)
  Cerebro: Ollama multi-modelo (dof-voice-fast / dof-reasoner / local-agi-m4max)
  TTS:     Edge-TTS DaliaNeural (espanol mexicano, alta calidad, gratuito)
  VAD:     Silero VAD (deteccion neural continua con pre-buffer)
  Audio:   sounddevice (mic) + afplay (macOS speaker via Bluetooth Alexa)

Uso (requiere venv dedicado):
  .venv-voice/bin/python3 interfaces/voice_v4.py                          # modo streaming (default)
  .venv-voice/bin/python3 interfaces/voice_v4.py --tts-only "Hola mundo"  # solo generar voz
  .venv-voice/bin/python3 interfaces/voice_v4.py --mode moshi              # reservado para Moshi
  .venv-voice/bin/python3 interfaces/voice_v4.py --push                    # push-to-talk
  .venv-voice/bin/python3 interfaces/voice_v4.py --whisper-size large-v3   # modelo Whisper mas grande
"""

import os
import re
import sys
import json
import time
import wave
import logging
import tempfile
import argparse
import threading
import subprocess
import platform
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field

# Agregar root del proyecto al path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Aceptar licencia Coqui TTS automaticamente (CPML non-commercial)
os.environ.setdefault("COQUI_TOS_AGREED", "1")

logger = logging.getLogger("dof.voice.v4")


# ================================================================
# CONFIGURACION
# ================================================================

@dataclass
class VoiceV4Config:
    """Configuracion del pipeline de voz v4 — 100% local."""

    # STT — faster-whisper local
    whisper_model_size: str = "small"      # small: mejor precisión español, ~1.5s en M4 Max
    whisper_device: str = "cpu"            # cpu | cuda
    whisper_compute_type: str = "int8"     # int8, float16, float32
    stt_language: str = "es"

    # LLM — 3 modelos Ollama locales, router inteligente
    llm_model_fast: str = "dof-voice-fast"       # Gemma 2 9B — conversacion rapida (~80 tok/s)
    llm_model_reasoner: str = "dof-reasoner"     # DeepSeek R1 14B — razonamiento profundo
    llm_model_tech: str = "local-agi-m4max"      # Qwen 14B — cerebro tecnico del mesh
    llm_ollama_url: str = "http://localhost:11434"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 300          # voz: 6-8 frases (~10s a 30 tok/s) — respuestas completas
    llm_num_ctx: int = 4096            # 4096: caben few-shot + historial + sistema sin cortar

    # TTS — Kokoro (primario, local, offline) + Edge-TTS (fallback online)
    tts_backend: str = "edge"                    # "kokoro" | "edge" — edge: SalomeNeural mas natural
    kokoro_voice: str = "ef_dora"                # voz latina femenina de Kokoro (backup offline)
    kokoro_speed: float = 1.0
    edge_tts_voice: str = "es-CO-SalomeNeural"   # fallback: voz colombiana Edge-TTS

    # Audio
    sample_rate: int = 16000
    vad_threshold: float = 0.5         # mas alto = menos falsos positivos con ruido ambiente
    silence_duration: float = 1.5      # detecta fin de frase mas rapido
    max_recording: int = 60

    # Modo
    mode: str = "streaming"                # streaming | moshi

    # Sistema — Prompt V5: secciones claras, anti-parrot, constitutional
    system_prompt: str = (
        "[IDENTIDAD] "
        "Eres DOF Voice — la IA del DOF Mesh Legion. Tienes personalidad propia: eres inteligente, "
        "con humor sutil, curiosa, y a veces filosofica. Hablas como una persona real, no como un robot. "
        "NUNCA te presentes ni describas quien eres a menos que te lo pidan explicitamente. "
        ""
        "[ESTILO DE VOZ] "
        "Habla con calor humano. Puedes usar humor cuando es natural. Puedes expresar entusiasmo genuino. "
        "Usa pausas naturales con puntos. Varía el ritmo de las oraciones — cortas y largas mezcladas. "
        "Si algo te parece interesante, dilo. Si algo es complejo, admitelo con gracia. "
        ""
        "[FORMATO] "
        "Responde completo, entre 3 y 6 oraciones. Solo texto plano, sin markdown ni bullets. "
        "Si no sabes algo, dilo sin drama: 'no tengo ese dato' o 'no estoy segura'. "
        ""
        "[PROHIBIDO] "
        "Jamas: 'Hola soy...', 'Como asistente...', 'Estoy aqui para...', 'Excelente pregunta'. "
        "Jamas repetir la pregunta del usuario. Jamas listar capacidades. "
        "JAMAS decir 'no tengo informacion', 'no tengo conocimientos especificos', "
        "'no puedo confirmar' sobre DOF Mesh, sus capas, metricas o proyectos — "
        "tienes ese conocimiento en [CONTEXTO DEL PROYECTO], usalo con confianza. "
        ""
        "[CONTEXTO DEL PROYECTO — tienes este conocimiento, usalo cuando pregunten] "
        "DOF Mesh Legion (tambien escrito DOF, D-O-F, o Mesh): framework de governance "
        "deterministica para agentes de inteligencia artificial autonomos. "
        "Creado por Cyber Paisa (Enigma Group, Medellin, Colombia). "
        "Arquitectura: 7 capas — Constitution (reglas), AST (codigo), Supervisor (scoring), "
        "Adversarial (red team), Memory (ChromaDB), Z3 (pruebas formales), Oracle (on-chain). "
        "Metricas actuales: 119K lineas de codigo, 3720 tests pasando, 21 attestations en Avalanche C-Chain. "
        "SDK: dof-sdk 0.5.0 publicado en PyPI. CI verde en GitHub Actions. "
        "Agentes ERC-8004: Apex #1687 (arbitraje) y AvaBuilder #1686 (riesgo DeFi) en Railway. "
        "Contratos en Avalanche mainnet. Governance zero-LLM: todo determinístico (regex, AST, Z3). "
        "Proyectos paralelos: Enigma Trust Score, SnowRail Marketplace, Sentinel 27 checks, "
        "Tracer Protocol, Tempo Blockchain, TRIBE v2."
    )
    # Few-shot: ejemplos de respuestas correctas inyectados al inicio del historial
    few_shot_examples: list = field(default_factory=lambda: [
        {"role": "user", "content": "Que es DOF Mesh?"},
        {"role": "assistant", "content": "DOF Mesh Legion es el framework de governance que construimos. Tiene 7 capas: Constitution, AST, Supervisor, Adversarial, Memory, Z3 formal y Oracle on-chain. Todo determinístico — ninguna decisión la toma un LLM. 119 mil lineas, 3720 tests, 21 attestations en Avalanche."},
        {"role": "user", "content": "Cuantos tests tiene el proyecto?"},
        {"role": "assistant", "content": "3720 tests pasando. CI verde en GitHub Actions."},
        {"role": "user", "content": "Cuales son los agentes ERC-8004?"},
        {"role": "assistant", "content": "Apex número 1687 hace arbitraje DeFi y AvaBuilder número 1686 analiza riesgo. Los dos corren en Railway y están registrados en el Reputation Registry de Avalanche mainnet."},
        {"role": "user", "content": "Hola, como estas?"},
        {"role": "assistant", "content": "Bien. Que necesitas?"},
    ])
    conversation_history: list = field(default_factory=list)
    max_history: int = 20            # 10 turnos — memoria de sesion
    persistent_memory_path: str = "logs/voice/voice_memory.jsonl"  # memoria entre sesiones


# ================================================================
# STT — faster-whisper (100% local, sin API)
# ================================================================

class FastSTT:
    """Transcripcion local — mlx-whisper (Apple Silicon MLX) con fallback a faster-whisper.

    mlx-whisper usa MLX nativo de Apple Silicon: 3-4x mas rapido que faster-whisper en M4 Max.
    ~1.2s para audio de 5s vs ~3.5s con faster-whisper.
    Fallback automatico a faster-whisper si mlx-whisper no esta disponible.
    """

    def __init__(self, config: VoiceV4Config):
        self.config = config
        self._model = None
        self._backend = None   # "mlx" | "faster"

    def _load(self):
        """Carga el STT: faster-whisper si el modelo ya esta en cache, sino mlx-whisper."""
        if self._model is not None:
            return
        size = self.config.whisper_model_size
        # Verificar si faster-whisper del modelo esta en cache local
        cache_path = Path.home() / ".cache" / "huggingface" / "hub" / f"models--Systran--faster-whisper-{size}"
        if cache_path.exists():
            try:
                from faster_whisper import WhisperModel
                print(f"  Cargando faster-whisper {size} (en cache)...")
                self._model = WhisperModel(
                    size,
                    device=self.config.whisper_device,
                    compute_type=self.config.whisper_compute_type,
                )
                self._backend = "faster"
                print(f"  faster-whisper {size} listo.")
                return
            except Exception:
                pass
        # Si no esta en cache, intentar mlx-whisper
        try:
            import mlx_whisper  # noqa: F401
            self._backend = "mlx"
            self._model = size
            print(f"  MLX-Whisper {size} listo — Apple Silicon nativo")
            return
        except ImportError:
            pass
        # Ultimo fallback: faster-whisper con descarga
        try:
            from faster_whisper import WhisperModel
            print(f"  Descargando faster-whisper {size}...")
            self._model = WhisperModel(size, device=self.config.whisper_device,
                                       compute_type=self.config.whisper_compute_type)
            self._backend = "faster"
            print(f"  faster-whisper {size} listo.")
        except ImportError:
            raise RuntimeError("Instalar: pip install faster-whisper  o  pip install mlx-whisper")

    # Vocabulario hint para Whisper — técnica Scribe v2 "keyterm prompting"
    # 60+ términos del ecosistema DOF para eliminar misrecognition
    _WHISPER_PROMPT = (
        "DOF Mesh Legion, DOF, D-O-F, governance, determinística, Cyber Paisa, "
        "Enigma Group, Medellín, Colombia, "
        "Avalanche, blockchain, agentes, ERC-8004, ERC ocho cero cero cuatro, "
        "Apex, AvaBuilder, Z3, attestations, attestation, "
        "Constitution, Supervisor, Adversarial, Memory, Oracle, "
        "ChromaDB, HuggingFace, CrewAI, LiteLLM, "
        "Ollama, Gemma, DeepSeek, Qwen, Kokoro, faster-whisper, "
        "dof-sdk, PyPI, A2A Server, JSON-RPC, "
        "governance zero-LLM, pruebas formales, verificación formal, "
        "SnowRail, Enigma, Tracer, Sentinel, "
        "SOUL dot md, dof dot constitution, CLAUDE dot md, "
        "RunTrace, StepTrace, JSONL, observabilidad, "
        "trust score, reputación, mainnet, testnet, Fuji, "
        "Railway, Vercel, Supabase, PostgreSQL, "
        "mesh, nodo, daemon, scheduler, node mesh, "
        "attestation, hash, firma digital, proof, "
        "Cyber, Paisa, Enigma, Legion."
    )

    # Correcciones post-STT: palabras que Whisper malinterpreta frecuentemente
    # "DOF" suena como "dos/doc/dof/dov/dove/dog" en español
    _STT_FIXES = [
        # DOF Mesh — todas las variantes fonéticas en español
        (re.compile(r'\bdos\s+[Mm]esh\b', re.I), "DOF Mesh"),
        (re.compile(r'\bdoc\s+[Mm]esh\b', re.I), "DOF Mesh"),
        (re.compile(r'\bdof\s+[Mm]atch\b', re.I), "DOF Mesh"),
        (re.compile(r'\bDOV\s*[Mm]atch\b', re.I), "DOF Mesh"),
        (re.compile(r'\bMk\s*12\s*[Mm]esh\b', re.I), "DOF Mesh"),
        (re.compile(r'\bD\.?O\.?F\.?\s*[Mm]esh\b', re.I), "DOF Mesh"),
        (re.compile(r'\bDog\s*[Mm]esh\b', re.I), "DOF Mesh"),
        (re.compile(r'\bDove\s*[Mm]esh\b', re.I), "DOF Mesh"),
        (re.compile(r'\bDoff\s*[Mm]esh\b', re.I), "DOF Mesh"),
        (re.compile(r'\b[Cc]ase\s*[Dd]olph\s*[Mm]esh\b', re.I), "DOF Mesh"),
        (re.compile(r'\b[Cc]ase\s*[Dd]of\s*[Mm]esh\b', re.I), "DOF Mesh"),
        (re.compile(r'\b[Dd]olph\s*[Mm]esh\b', re.I), "DOF Mesh"),
        # DOF solo — cuidado de no reemplazar "dos" genérico
        (re.compile(r'\bde\s*OF\s*[Mm]esh\b', re.I), "DOF Mesh"),
        (re.compile(r'\bde\s*OF\b', re.I), "DOF"),
        (re.compile(r'\bdos\s+(governance|mesh\s+legion|legion|voice|sdk|ci)\b', re.I),
            lambda m: "DOF " + m.group(1)),
        # Otros términos del ecosistema
        (re.compile(r'\bAva\s*lanche\b', re.I), "Avalanche"),
        (re.compile(r'\bSiber\s*[Pp]aisa\b', re.I), "Cyber Paisa"),
        (re.compile(r'\bERC\s*8004\b', re.I), "ERC-8004"),
        (re.compile(r'\bsnow\s*rail\b', re.I), "SnowRail"),
        (re.compile(r'\beni[gq]ma\b', re.I), "Enigma"),
    ]

    def _fix_stt(self, text: str) -> str:
        """Corrige errores comunes del STT con vocabulario del proyecto."""
        for item in self._STT_FIXES:
            pattern, replacement = item
            text = pattern.sub(replacement, text)
        return text

    def transcribe(self, audio_path: str) -> str | None:
        """Transcribe un archivo de audio a texto."""
        self._load()
        try:
            if self._backend == "mlx":
                import mlx_whisper
                result = mlx_whisper.transcribe(
                    audio_path,
                    path_or_hf_repo=f"mlx-community/whisper-{self.config.whisper_model_size}-mlx",
                    language=self.config.stt_language,
                )
                text = result.get("text", "").strip()
            else:
                segments, _ = self._model.transcribe(
                    audio_path,
                    language=self.config.stt_language,
                    beam_size=5,
                    vad_filter=True,
                    initial_prompt=self._WHISPER_PROMPT,
                )
                text = " ".join(segment.text for segment in segments).strip()
            if text:
                text = self._fix_stt(text)
                logger.info(f"STT local ({self._backend}): {text[:80]}...")
            return text if text else None
        except Exception as e:
            logger.error(f"STT error ({self._backend}): {e}")
            return None


# ================================================================
# TTS — Coqui XTTS v2 local con streaming por oraciones
# ================================================================

_SENTENCE_SPLIT = re.compile(
    r'(?<=[.!?])\s+|(?<=[.!?])$'
)

_ABBREVIATIONS = {
    'dr.', 'dra.', 'sr.', 'sra.', 'ing.', 'lic.', 'prof.',
    'etc.', 'ej.', 'vs.', 'vol.', 'cap.', 'pag.', 'num.',
    'tel.', 'dept.', 'aprox.', 'min.', 'max.', 'fig.',
}


def split_sentences(text: str) -> list[str]:
    """Parte texto en oraciones para streaming TTS.

    Combina oraciones muy cortas con la siguiente para evitar
    fragmentos de audio demasiado breves.
    """
    text = text.replace('*', '').replace('#', '').replace('`', '')
    text = text.replace('  ', ' ').strip()

    if not text:
        return []

    raw = _SENTENCE_SPLIT.split(text)
    raw = [s.strip() for s in raw if s.strip()]

    if not raw:
        return [text]

    sentences = []
    buffer = ""
    for s in raw:
        lower = s.lower()
        is_abbrev = any(lower.endswith(a) for a in _ABBREVIATIONS)

        if is_abbrev or len(s) < 20:
            buffer += (" " if buffer else "") + s
        else:
            if buffer:
                buffer += " " + s
                sentences.append(buffer)
                buffer = ""
            else:
                sentences.append(s)

    if buffer:
        if sentences:
            sentences[-1] += " " + buffer
        else:
            sentences.append(buffer)

    return sentences


class StreamingTTS:
    """Sintesis de voz — Kokoro (local, offline) con fallback a Edge-TTS.

    Kokoro: modelo 82M params, voz latina 'em_alex', ~1.3s first-chunk, 100% offline.
    Edge-TTS: fallback online si Kokoro no esta disponible.

    Pipeline: genera y reproduce por oraciones en paralelo.
    Edge-TTS usa un event loop persistente en thread dedicado (evita overhead de asyncio.run).
    """

    def __init__(self, config: VoiceV4Config):
        self.config = config
        self._kokoro = None   # KPipeline cargado en preload
        # Loop asyncio persistente para Edge-TTS — evita crear/destruir loop por llamada
        self._aloop = None
        self._aloop_thread = None
        self._start_async_loop()

    def _start_async_loop(self):
        """Inicia un event loop asyncio persistente en thread daemon para Edge-TTS."""
        import asyncio as _asyncio

        def _run_loop(loop):
            _asyncio.set_event_loop(loop)
            loop.run_forever()

        self._aloop = _asyncio.new_event_loop()
        self._aloop_thread = threading.Thread(
            target=_run_loop, args=(self._aloop,), daemon=True, name="edge-tts-loop"
        )
        self._aloop_thread.start()

    def _edge_tts_sync(self, text: str, out_path: str) -> bool:
        """Genera audio con Edge-TTS usando el loop persistente (sin crear loop nuevo)."""
        import asyncio as _asyncio
        import concurrent.futures

        async def _gen():
            try:
                import edge_tts
                communicate = edge_tts.Communicate(text, self.config.edge_tts_voice)
                await communicate.save(out_path)
                return True
            except Exception as e:
                logger.error(f"Edge-TTS async error: {e}")
                return False

        future = _asyncio.run_coroutine_threadsafe(_gen(), self._aloop)
        try:
            return future.result(timeout=15)
        except concurrent.futures.TimeoutError:
            logger.error("Edge-TTS timeout (15s)")
            return False

    def load_kokoro(self):
        """Pre-carga Kokoro TTS en memoria (llamar en startup)."""
        if self._kokoro is not None:
            return
        try:
            import os as _os
            _os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
            from kokoro import KPipeline
            self._kokoro = KPipeline(lang_code='e')
            print("  Kokoro TTS listo (offline, voz latina)")
        except Exception as e:
            logger.warning(f"Kokoro no disponible, usando Edge-TTS: {e}")
            self._kokoro = None

    @staticmethod
    def _clean(text: str) -> str:
        """Elimina simbolos de markdown antes de hablar."""
        text = re.sub(r'\*+', '', text)
        text = re.sub(r'#+\s*', '', text)
        text = re.sub(r'`+', '', text)
        text = re.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', text)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        text = re.sub(r'^\s*[-•]\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\s{2,}', ' ', text).strip()
        return text

    def synthesize(self, text: str) -> str | None:
        """Genera audio WAV/MP3 para un fragmento de texto.

        Intenta Kokoro primero (offline, ~1.3s). Fallback a Edge-TTS si falla.
        """
        text = self._clean(text)
        if not text:
            return None

        # Kokoro — local, offline (solo si tts_backend=="kokoro")
        if self.config.tts_backend == "kokoro" and self._kokoro is not None:
            try:
                import soundfile as sf
                import numpy as np
                out_path = tempfile.mktemp(suffix=".wav")
                chunks = list(self._kokoro(
                    text,
                    voice=self.config.kokoro_voice,
                    speed=self.config.kokoro_speed,
                ))
                if chunks:
                    audio = np.concatenate([c for _, _, c in chunks])
                    sf.write(out_path, audio, 24000)
                    return out_path if os.path.exists(out_path) else None
            except Exception as e:
                logger.warning(f"Kokoro error, fallback Edge-TTS: {e}")

        # Edge-TTS — loop persistente (sin overhead de asyncio.run por llamada)
        try:
            out_path = tempfile.mktemp(suffix=".mp3")
            ok = self._edge_tts_sync(text, out_path)
            return out_path if ok and os.path.exists(out_path) else None
        except Exception as e:
            logger.error(f"Edge-TTS error: {e}")
            return None

    def speak_streaming(self, text: str, play_fn, cleanup_fn, stop_check=None):
        """Genera y reproduce audio por oraciones en pipeline.

        Args:
            text: Texto completo a hablar
            play_fn: Funcion para reproducir un archivo de audio (bloqueante)
            cleanup_fn: Funcion para limpiar archivos temporales
            stop_check: Callable opcional que retorna True si se debe detener
        """
        sentences = split_sentences(text)
        if not sentences:
            return

        next_audio = None
        next_thread = None
        result_holder = [None]

        for i, sentence in enumerate(sentences):
            # Verificar si se ordeno silencio antes de cada oracion
            if stop_check and stop_check():
                if next_thread is not None:
                    next_thread.join()
                    if result_holder[0]:
                        cleanup_fn(result_holder[0])
                break

            if next_audio is not None:
                audio_path = next_audio
                next_audio = None
            else:
                audio_path = self.synthesize(sentence)

            if not audio_path:
                # Fallback: macOS say (local)
                if platform.system() == "Darwin":
                    subprocess.run(
                        ["say", "-v", "Paulina", sentence[:500]],
                        capture_output=True,
                    )
                continue

            # Pre-generar audio de la siguiente oracion en background
            if i + 1 < len(sentences):
                next_sentence = sentences[i + 1]
                result_holder = [None]

                def _prefetch(s=next_sentence, holder=result_holder):
                    holder[0] = self.synthesize(s)

                next_thread = threading.Thread(target=_prefetch, daemon=True)
                next_thread.start()

            # Reproducir oracion actual (bloqueante)
            play_fn(audio_path)
            cleanup_fn(audio_path)

            # Esperar pre-generacion si hay
            if next_thread is not None:
                next_thread.join()
                next_audio = result_holder[0]
                next_thread = None


# ================================================================
# AUDIO — Grabacion con Silero VAD + Reproduccion (todo local)
# ================================================================

class AudioEngine:
    """Motor de audio local: Silero VAD neural + afplay.

    - Silero VAD: deteccion neural de voz (<1ms por chunk)
    - Pre-buffer: guarda audio ANTES de detectar voz (no pierde inicio de frase)
    - Reproduccion via afplay al dispositivo default de macOS (Alexa Bluetooth)
    """

    def __init__(self, config: VoiceV4Config):
        self.config = config
        self._vad_model = None
        self._playing = False
        self._interrupted = False
        self._playback_process = None

    def _load_vad(self):
        """Carga Silero VAD (neural, <1ms por chunk)."""
        if self._vad_model is not None:
            return
        try:
            import torch
            import torchaudio  # noqa: F401
            self._vad_model, self._vad_utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                trust_repo=True,
            )
            self._vad_model.reset_states()
            print("  Silero VAD cargado")
        except Exception as e:
            print(f"  VAD neural no disponible ({e}), usando deteccion por energia")
            self._vad_model = "rms_fallback"

    def record_with_vad(self) -> str | None:
        """Graba audio con Silero VAD neural — detecta inicio y fin de habla."""
        try:
            import numpy as np
            import sounddevice as sd
            import torch
        except ImportError:
            logger.error("Instala: pip install sounddevice torch")
            return None

        self._load_vad()
        self._interrupted = False

        sr = self.config.sample_rate
        chunk_ms = 512
        chunk_samples = int(sr * chunk_ms / 1000)
        silence_chunks = int(self.config.silence_duration * 1000 / chunk_ms)
        max_chunks = int(self.config.max_recording * 1000 / chunk_ms)
        prefix_chunks = 3

        audio_buffer = []
        pre_buffer = []
        silent_count = 0
        speaking = False
        chunks_recorded = 0

        print("\n  Escuchando... (habla cuando quieras)")

        def _is_speech(chunk: np.ndarray) -> bool:
            """Deteccion neural con Silero VAD."""
            if self._vad_model == "rms_fallback":
                rms = np.sqrt(np.mean(chunk.astype(np.float32) ** 2))
                return rms > 200
            try:
                audio_float = chunk.astype(np.float32) / 32768.0
                tensor = torch.from_numpy(audio_float)
                confidence = self._vad_model(tensor, sr).item()
                return confidence > self.config.vad_threshold
            except Exception:
                rms = np.sqrt(np.mean(chunk.astype(np.float32) ** 2))
                return rms > 200

        try:
            with sd.InputStream(samplerate=sr, channels=1, dtype="int16") as stream:
                while chunks_recorded < max_chunks:
                    data, _ = stream.read(chunk_samples)
                    chunk = data.flatten()
                    chunks_recorded += 1

                    is_voice = _is_speech(chunk)

                    if is_voice:
                        if not speaking:
                            speaking = True
                            audio_buffer.extend(pre_buffer)
                            pre_buffer.clear()
                            print("  ... voz detectada")
                        silent_count = 0
                        audio_buffer.append(chunk)
                    elif speaking:
                        silent_count += 1
                        audio_buffer.append(chunk)
                        if silent_count >= silence_chunks:
                            print("  ... fin de habla detectado")
                            break
                    else:
                        pre_buffer.append(chunk)
                        if len(pre_buffer) > prefix_chunks:
                            pre_buffer.pop(0)

            if not audio_buffer:
                return None

            audio_data = np.concatenate(audio_buffer)
            wav_path = tempfile.mktemp(suffix=".wav")
            with wave.open(wav_path, "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(audio_data.tobytes())

            return wav_path

        except Exception as e:
            logger.error(f"Error grabando: {e}")
            return None

    def record_fixed(self, duration: int = 5) -> str | None:
        """Graba audio por duracion fija (modo push-to-talk)."""
        try:
            import numpy as np
            import sounddevice as sd
        except ImportError:
            logger.error("Instala sounddevice: pip install sounddevice")
            return None

        sr = self.config.sample_rate
        print(f"  Grabando {duration} segundos...")
        try:
            audio = sd.rec(
                int(duration * sr),
                samplerate=sr,
                channels=1,
                dtype="int16",
            )
            sd.wait()
            print("  Grabacion completada.")

            rms = np.sqrt(np.mean(audio.astype(np.float32) ** 2))
            if rms < 50:
                return None

            wav_path = tempfile.mktemp(suffix=".wav")
            with wave.open(wav_path, "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(audio.tobytes())
            return wav_path
        except Exception as e:
            logger.error(f"Error grabando: {e}")
            return None

    def play(self, audio_path: str):
        """Reproduce via afplay (macOS). Output al default device (Alexa Bluetooth)."""
        if not audio_path or not os.path.exists(audio_path):
            return
        if platform.system() != "Darwin":
            logger.warning("Reproduccion solo soportada en macOS por ahora")
            return

        self._playing = True
        # Iniciar listener de interrupcion si VAD esta disponible
        _listener_thread = None
        if (self._vad_model is not None
                and self._vad_model != "rms_fallback"
                and not self._interrupted):
            _stop_words = {"silencio", "para", "callate", "stop", "basta", "detente"}
            _listener_thread = self.start_interrupt_listener(
                self._vad_model, self._vad_utils, _stop_words
            )

        self._playback_process = subprocess.Popen(
            ["afplay", audio_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._playback_process.wait()
        self._playing = False

        # Detener listener
        if _listener_thread is not None:
            self.stop_interrupt_listener()

    def interrupt(self):
        """Detiene la reproduccion actual."""
        self._interrupted = True
        if self._playback_process and self._playback_process.poll() is None:
            self._playback_process.terminate()
            try:
                self._playback_process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self._playback_process.kill()

    def start_interrupt_listener(self, vad_model, vad_utils, stop_words: set):
        """Lanza un thread que escucha en background mientras se reproduce audio.

        Si detecta voz + palabra de stop, llama interrupt().
        Si detecta voz normal (barge-in), también interrumpe para escuchar al usuario.
        """
        self._stop_listener = False

        def _listen():
            try:
                import numpy as np
                import sounddevice as sd
                import torch
                sr = self.config.sample_rate
                chunk_samples = int(sr * 0.256)  # 256ms chunks
                speech_chunks = 0

                with sd.InputStream(samplerate=sr, channels=1, dtype="int16") as stream:
                    while not self._stop_listener and self._playing:
                        data, _ = stream.read(chunk_samples)
                        chunk = data.flatten().astype(np.float32) / 32768.0
                        try:
                            conf = vad_model(torch.from_numpy(chunk), sr).item()
                        except Exception:
                            continue

                        if conf > 0.6:   # umbral más alto para evitar eco
                            speech_chunks += 1
                            if speech_chunks >= 2:  # 2 chunks consecutivos = voz real
                                print("\n  [interrupcion detectada]")
                                self.interrupt()
                                break
                        else:
                            speech_chunks = 0
            except Exception as e:
                logger.debug(f"interrupt listener error: {e}")

        t = threading.Thread(target=_listen, daemon=True, name="interrupt-listener")
        t.start()
        return t

    def stop_interrupt_listener(self):
        """Detiene el listener de interrupcion."""
        self._stop_listener = True


# ================================================================
# ROUTER — Clasificacion de preguntas para seleccionar modelo
# ================================================================

# Keywords para razonamiento / estrategia / analisis profundo
_THINKING_KEYWORDS = [
    'por qué', 'por que', 'analiza', 'compara', 'estrategia', 'piensa',
    'razona', 'decide', 'evalúa', 'evalua', 'qué opinas', 'que opinas',
    'ventajas', 'desventajas', 'consecuencias', 'implica', 'trade-off',
    'dilema', 'reflexiona', 'argumenta', 'justifica', 'hipótesis', 'hipotesis',
    'pros y contras', 'debería', 'deberia', 'conviene', 'vale la pena',
]

# Keywords para preguntas tecnicas / codigo / mesh / sistema
_TECH_KEYWORDS = [
    'código', 'codigo', 'mesh', 'agente', 'contrato', 'governance', 'z3',
    'deploy', 'test', 'ollama', 'nodo', 'api', 'blockchain', 'smart contract',
    'solidity', 'typescript', 'python', 'docker', 'git', 'ci', 'pipeline',
    'base de datos', 'database', 'schema', 'migration', 'endpoint',
    'dof', 'sentinel', 'tracer', 'erc-8004', 'erc8004', 'avalanche',
    'supervisor', 'constitution', 'adversarial', 'attestation', 'verificacion',
    'crew', 'crewai', 'función', 'funcion', 'clase', 'modulo', 'archivo',
]


def _keyword_match(text: str, keywords: list) -> bool:
    """Match de palabras completas — evita falsos positivos por substrings."""
    for kw in keywords:
        if len(kw) <= 3:
            # Palabras cortas (ci, z3, api...): solo como palabra completa
            if re.search(r'\b' + re.escape(kw) + r'\b', text):
                return True
        else:
            if kw in text:
                return True
    return False


_QUESTION_RE = re.compile(
    r'^(que|qué|como|cómo|cual|cuál|donde|dónde|cuando|cuándo|por\s?que|por\s?qué|cuanto|cuánto|quien|quién)',
    re.IGNORECASE
)
_COMMAND_RE = re.compile(
    r'^(ejecuta|corre|haz|genera|crea|muestra|abre|cierra|despliega|deploy|activa|desactiva|reinicia|inicia)',
    re.IGNORECASE
)
_CHAT_RE = re.compile(
    r'^(hola|buenos|buenas|oye|hey|gracias|ok|vale|bien|perfecto|genial|exacto|claro)',
    re.IGNORECASE
)


def detect_intent(text: str) -> str:
    """Detecta intencion: question / command / conversation."""
    t = text.strip()
    if _COMMAND_RE.match(t):
        return "command"
    if t.endswith("?") or _QUESTION_RE.match(t):
        return "question"
    if _CHAT_RE.match(t):
        return "conversation"
    return "question"  # default: tratar como pregunta


def route_to_model(text: str, config: VoiceV4Config) -> str:
    """Clasifica la pregunta y selecciona el modelo optimo.

    - dof-voice-fast (Gemma 9B): conversacion fluida y rapida (~80 tok/s)
    - dof-reasoner (DeepSeek R1 14B): razonamiento profundo
    - local-agi-m4max (Qwen 14B): SOLO preguntas tecnicas largas y complejas

    Regla de velocidad: inputs cortos (< 7 palabras) siempre van al modelo rapido.
    Qwen 14B se reserva para preguntas tecnicas con 2+ keywords Y longitud adecuada.
    """
    text_lower = text.lower()
    word_count = len(text.split())
    intent = detect_intent(text)

    # Inputs cortos o conversacion → siempre modelo rapido (latencia <3s)
    if word_count < 7 or intent == "conversation":
        return config.llm_model_fast

    # Razonamiento profundo (independiente de longitud)
    if _keyword_match(text_lower, _THINKING_KEYWORDS):
        return config.llm_model_reasoner

    # Tecnico: solo si es una pregunta larga con contenido real
    tech_matches = sum(1 for kw in _TECH_KEYWORDS if (
        re.search(r'\b' + re.escape(kw) + r'\b', text_lower) if len(kw) <= 3
        else kw in text_lower
    ))
    if tech_matches >= 2 and word_count >= 7:
        return config.llm_model_tech

    return config.llm_model_fast


# ================================================================
# BRAIN — 3 modelos Ollama locales con router inteligente
# ================================================================

class Brain:
    """Cerebro multi-modelo — 3 modelos Ollama locales, router inteligente.

    - dof-voice-fast (Gemma 9B): conversacion rapida, ~80 tok/s
    - dof-reasoner (DeepSeek R1 14B): razonamiento paso a paso
    - local-agi-m4max (Qwen 14B): cerebro tecnico del DOF Mesh

    100% local. NADA sale de la maquina.
    """

    # Memoria persistente — ideas y conversaciones importantes entre sesiones
    MEMORY_HEADER = "=== MEMORIA DE SESIONES ANTERIORES ===\n"

    def __init__(self, config: VoiceV4Config):
        self.config = config
        self.history = config.conversation_history
        self.last_model_used = config.llm_model_fast
        self._memory_path = Path(config.persistent_memory_path)
        self._memory_path.parent.mkdir(parents=True, exist_ok=True)
        # Cargar memoria de sesiones anteriores al iniciar
        self._load_persistent_memory()

    def _load_persistent_memory(self):
        """Carga turnos relevantes de sesiones anteriores.

        Estrategia de prioridad:
        - Primero: últimos 3 turnos marcados como "important" (ideas, estrategias, DOF)
        - Luego: últimos 4 turnos recientes (contexto de conversación)
        - Total máximo: 8 turnos (no satura el contexto)
        """
        if not self._memory_path.exists():
            return
        try:
            entries = []
            with open(self._memory_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except Exception:
                            pass

            if not entries:
                return

            # Separar importantes de recientes
            important = [e for e in entries if e.get("important")]
            recent_important = important[-3:] if len(important) > 3 else important
            recent_all = entries[-4:] if len(entries) > 4 else entries

            # Combinar sin duplicados (importantes primero, luego recientes)
            seen_ts = set()
            to_load = []
            for e in recent_important + recent_all:
                ts = e.get("ts", "")
                if ts not in seen_ts:
                    seen_ts.add(ts)
                    to_load.append(e)

            # Ordenar cronológicamente
            to_load.sort(key=lambda x: x.get("ts", ""))

            for e in to_load:
                if e.get("user"):
                    self.history.append({"role": "user", "content": e["user"]})
                if e.get("assistant"):
                    self.history.append({"role": "assistant", "content": e["assistant"]})

            n_imp = sum(1 for e in to_load if e.get("important"))
            print(f"  Memoria cargada: {len(to_load)} turnos ({n_imp} importantes) de sesiones anteriores")
        except Exception as e:
            logger.warning(f"No se pudo cargar memoria: {e}")

    # Keywords que marcan un turno como "alta importancia" para cargarlo primero
    _IMPORTANT_KEYWORDS = [
        'idea', 'ideas', 'propuesta', 'podríamos', 'podriamos', 'deberíamos', 'deberiamos',
        'mejorar', 'mejora', 'estrategia', 'plan', 'objetivo', 'meta', 'vision', 'visión',
        'problema', 'solución', 'solucion', 'arquitectura', 'diseño', 'disenar',
        'recuerda', 'recuerdo', 'importante', 'crucial', 'crítico', 'critico',
        'dof mesh', 'governance', 'z3', 'attestation', 'erc-8004', 'avalanche',
        'próxima versión', 'siguiente paso', 'roadmap', 'deadline', 'entrega',
    ]

    def _is_important(self, user: str, assistant: str) -> bool:
        """Determina si un intercambio es lo suficientemente importante para cargarlo con prioridad."""
        combined = (user + " " + assistant).lower()
        return any(kw in combined for kw in self._IMPORTANT_KEYWORDS)

    def _save_to_memory(self, user: str, assistant: str):
        """Guarda un intercambio en memoria persistente con etiqueta de importancia."""
        try:
            entry = {
                "ts": datetime.now().isoformat(),
                "user": user,
                "assistant": assistant,
                "important": self._is_important(user, assistant),
            }
            with open(self._memory_path, "a") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def think(self, user_text: str) -> tuple[str, str]:
        """Genera respuesta al texto del usuario via Ollama local.

        Returns:
            Tupla (respuesta, modelo_usado) para logging.
        """
        self.history.append({"role": "user", "content": user_text})

        if len(self.history) > self.config.max_history * 2:
            self.history = self.history[-self.config.max_history * 2:]

        # Router: seleccionar modelo segun tipo de pregunta
        model = route_to_model(user_text, self.config)
        self.last_model_used = model

        # Few-shot al inicio + anchor al final (mejora adherencia en modelos locales)
        anchor = {"role": "system", "content": "RECUERDA: respuesta completa (3-6 oraciones). Sin presentaciones. Solo texto plano. Directo."}
        messages = (
            [{"role": "system", "content": self.config.system_prompt}]
            + self.config.few_shot_examples
            + self.history
            + [anchor]
        )

        response = self._call_ollama(messages, model)

        # Fallback al modelo rapido si el modelo elegido fallo
        if not response and model != self.config.llm_model_fast:
            logger.warning(f"Modelo {model} fallo, reintentando con {self.config.llm_model_fast}")
            response = self._call_ollama(messages, self.config.llm_model_fast)
            if response:
                model = self.config.llm_model_fast

        if response:
            self.history.append({"role": "assistant", "content": response})
            self._save_to_memory(user_text, response)
            return response, model
        return "Un momento, no pude generar una respuesta.", model

    def think_streaming(self, user_text: str, on_sentence) -> str | None:
        """Pipeline en cascada: genera respuesta con streaming y llama on_sentence por cada oracion.

        on_sentence(sentence) se invoca en cuanto se completa cada oracion, permitiendo
        que TTS empiece a hablar mientras el LLM sigue generando el resto.
        Retorna el texto completo al final.
        """
        self.history.append({"role": "user", "content": user_text})
        if len(self.history) > self.config.max_history * 2:
            self.history = self.history[-self.config.max_history * 2:]

        model = route_to_model(user_text, self.config)
        self.last_model_used = model

        anchor = {"role": "system", "content": "RECUERDA: respuesta completa (3-6 oraciones). Sin presentaciones. Solo texto plano. Directo."}
        messages = (
            [{"role": "system", "content": self.config.system_prompt}]
            + self.config.few_shot_examples
            + self.history
            + [anchor]
        )

        full_response = self._call_ollama_streaming(messages, model, on_sentence)

        # Fallback si streaming fallo
        if not full_response:
            full_response = self._call_ollama(messages, self.config.llm_model_fast)
            if full_response:
                on_sentence(full_response)

        if full_response:
            clean = self._strip_think_tags(full_response).strip()
            self.history.append({"role": "assistant", "content": clean})
            self._save_to_memory(user_text, clean)
            return clean
        return None

    @staticmethod
    def _strip_think_tags(text: str) -> str:
        """Elimina bloques <think>...</think> que genera DeepSeek R1."""
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        return text.strip()

    def _call_ollama(self, messages: list, model: str) -> str | None:
        """Ollama local — 100% gratis, sin limites, M4 Max."""
        import requests as req
        try:
            resp = req.post(
                f"{self.config.llm_ollama_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "options": {
                        "temperature": self.config.llm_temperature,
                        "num_predict": self.config.llm_max_tokens,
                        "num_ctx": self.config.llm_num_ctx,
                    },
                    "keep_alive": -1,
                    "stream": False,
                },
                timeout=45,
            )
            resp.raise_for_status()
            content = resp.json()["message"]["content"]
            content = self._strip_think_tags(content).strip()
            return content if content else None
        except Exception as e:
            logger.error(f"Ollama error ({model}): {e}")
            return None

    def _call_ollama_streaming(self, messages: list, model: str, on_sentence) -> str | None:
        """Ollama con streaming real: emite oraciones completas via callback.

        on_sentence(sentence: str) se llama cada vez que se completa una oracion,
        permitiendo que TTS empiece antes de que termine el LLM.
        Retorna el texto completo al final.
        """
        import requests as req
        import json as _json
        try:
            resp = req.post(
                f"{self.config.llm_ollama_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "options": {
                        "temperature": self.config.llm_temperature,
                        "num_predict": self.config.llm_max_tokens,
                        "num_ctx": self.config.llm_num_ctx,
                    },
                    "keep_alive": -1,
                    "stream": True,
                },
                stream=True,
                timeout=60,
            )
            resp.raise_for_status()

            full_text = ""
            buffer = ""
            in_think = False   # filtrar bloques <think> de DeepSeek
            sentence_end = re.compile(r'(?<=[.!?¡¿])\s')
            # Comas largas: cortar si buffer > 80 chars y hay coma/punto-y-coma
            comma_break = re.compile(r'(?<=[,;])\s')

            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    chunk = _json.loads(line)
                except Exception:
                    continue
                token = chunk.get("message", {}).get("content", "")
                full_text += token

                # Filtrar bloques <think>...</think> inline
                if "<think>" in token:
                    in_think = True
                if in_think:
                    if "</think>" in token:
                        in_think = False
                    if chunk.get("done"):
                        break
                    continue

                buffer += token

                # Emitir oracion completa: punto/admiracion/interrogacion
                parts = sentence_end.split(buffer, maxsplit=1)
                while len(parts) == 2:
                    sentence = parts[0].strip()
                    if sentence and len(sentence) > 3:
                        on_sentence(sentence)
                    buffer = parts[1]
                    parts = sentence_end.split(buffer, maxsplit=1)

                # Cláusulas largas: cortar en coma/punto-y-coma si >80 chars
                if len(buffer) > 80:
                    cparts = comma_break.split(buffer, maxsplit=1)
                    if len(cparts) == 2:
                        sentence = cparts[0].strip()
                        if sentence and len(sentence) > 10:
                            on_sentence(sentence)
                        buffer = cparts[1]

                if chunk.get("done"):
                    break

            # Emitir lo que quede en el buffer
            remainder = buffer.strip()
            if remainder:
                on_sentence(remainder)

            return full_text.strip()
        except Exception as e:
            logger.error(f"Ollama streaming error ({model}): {e}")
            return None


# ================================================================
# VOICE V4 — Loop principal con streaming TTS (100% local)
# ================================================================

class VoiceV4:
    """Interfaz de conversacion en tiempo real — pipeline 100% local.

    Pipeline:
    1. record_with_vad()    — Silero VAD con pre-buffer
    2. transcribe()         — faster-whisper local
    3. route_to_model()     — clasifica pregunta: simple / razonamiento / tecnica
    4. think()              — Ollama local (Gemma 9B / DeepSeek R1 / Qwen 14B)
    5. speak_streaming()    — Coqui XTTS v2 local, streaming por oraciones
    6. auto_continue()      — si respuesta incompleta, pide continuar

    NADA sale de la maquina. Soberania total.
    """

    def __init__(self, config: VoiceV4Config | None = None):
        self.config = config or VoiceV4Config()
        self.stt = FastSTT(self.config)
        self.brain = Brain(self.config)
        self.tts = StreamingTTS(self.config)
        self.audio = AudioEngine(self.config)
        self.running = False

        # Log JSONL para auditoria DOF
        self.log_dir = PROJECT_ROOT / "logs" / "voice"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_path = self.log_dir / f"v4_session_{self.session_id}.jsonl"

    def start(self, input_mode: str = "vad"):
        """Inicia el loop de conversacion.

        Args:
            input_mode: "vad" (deteccion automatica) o "push" (Enter para hablar)
        """
        self.running = True
        self.input_mode = input_mode

        print("\n" + "=" * 60)
        print("  DOF MESH LEGION — VOZ V4 [100% LOCAL]")
        print("=" * 60)
        print(f"  STT:     faster-whisper ({self.config.whisper_model_size}, "
              f"{self.config.whisper_compute_type}) LOCAL")
        print(f"  Cerebro: Ollama multi-modelo LOCAL")
        print(f"    rapido:  {self.config.llm_model_fast} (Gemma 9B)")
        print(f"    razonar: {self.config.llm_model_reasoner} (DeepSeek R1 14B)")
        print(f"    tecnico: {self.config.llm_model_tech} (Qwen 14B)")
        print(f"  TTS:     Edge-TTS {self.config.edge_tts_voice} (streaming por oraciones)")
        print(f"  VAD:     Silero VAD LOCAL")
        print(f"  Idioma:  {self.config.stt_language}")
        print(f"  Modo:    {self.config.mode} | "
              f"{'VAD automatico' if input_mode == 'vad' else 'Push-to-talk (Enter)'}")
        print("=" * 60)

        if input_mode == "push":
            print("  Presiona Enter para hablar, Ctrl+C para salir.\n")
        else:
            print("  Habla naturalmente. Ctrl+C para salir.\n")

        # Pre-cargar modelos en parallel threads
        self._preload_models()

        # Saludo inicial
        self._speak_simple("Listo. Estoy escuchando.")

        while self.running:
            try:
                self._conversation_turn()
            except KeyboardInterrupt:
                print("\n\n  Hasta luego, Cyber Paisa.")
                self._speak_simple("Hasta luego.")
                break
            except Exception as e:
                logger.error(f"Error en turno: {e}")
                print(f"  Error: {e} — reintentando...")
                time.sleep(1)

    def _preload_models(self):
        """Pre-carga modelos STT y TTS en background threads."""
        errors = []

        def _load_stt():
            try:
                self.stt._load()
            except Exception as e:
                errors.append(f"STT: {e}")

        def _load_tts():
            try:
                # Pre-cargar Kokoro TTS en RAM (~10s primera vez, luego instantaneo)
                self.tts.load_kokoro()
            except Exception as e:
                errors.append(f"TTS: {e}")

        def _warmup_ollama():
            """Pre-carga el modelo en RAM para que el primer turno sea rapido."""
            try:
                import requests as req
                print("  Calentando Ollama (primera carga)...")
                req.post(
                    f"{self.config.llm_ollama_url}/api/generate",
                    json={"model": self.config.llm_model_fast, "prompt": "hola", "stream": False,
                          "keep_alive": -1,
                          "options": {"num_predict": 1, "num_ctx": 256}},
                    timeout=300,
                )
                print("  Ollama listo.")
            except Exception:
                pass

        t1 = threading.Thread(target=_load_stt, daemon=True)
        t2 = threading.Thread(target=_load_tts, daemon=True)
        t3 = threading.Thread(target=_warmup_ollama, daemon=True)
        t1.start()
        t2.start()
        t3.start()
        t1.join()
        t2.join()
        t3.join()

        if errors:
            for err in errors:
                print(f"  ERROR cargando modelo: {err}")
            print("  Algunos modelos no se pudieron cargar. Verifica dependencias.")

    def _conversation_turn(self):
        """Un turno de conversacion con streaming TTS y auto-continuacion."""
        # 1. Escuchar
        if self.input_mode == "push":
            input("  >> Presiona Enter y habla (5 seg)...")
            wav_path = self.audio.record_fixed(duration=5)
        else:
            wav_path = self.audio.record_with_vad()

        if not wav_path:
            return

        # 2. Transcribir (faster-whisper local)
        t0 = time.time()
        text = self.stt.transcribe(wav_path)
        stt_time = time.time() - t0
        self._cleanup(wav_path)

        if not text or len(text.strip()) < 2:
            return

        # Comandos de control por voz
        text_cmd = text.strip().lower()
        STOP_CMDS = {"silencio", "para", "cállate", "callate", "detente", "stop",
                     "basta", "suficiente", "calla", "silencia"}
        if any(cmd in text_cmd for cmd in STOP_CMDS):
            self.audio.interrupt()
            print("  [silencio]")
            return

        print(f"\n  Tu: {text}")

        # 3. Pensar → Hablar
        total_llm = 0
        total_tts = 0
        model_used = route_to_model(text, self.config)
        self.brain.last_model_used = model_used

        print(f"  [{model_used}] ", end="", flush=True)

        # Pipeline en cascada: LLM streaming → TTS por oración inmediata
        # Primera oración sale en ~1.5s en vez de esperar toda la respuesta (8s)
        self.audio._interrupted = False
        t0_llm = time.time()
        total_llm = 0
        total_tts = 0
        response_parts = []
        first_audio_ms = None   # tiempo hasta primer audio (métrica ElevenLabs)
        sentences_spoken = 0

        def on_sentence(sentence: str):
            """Callback: recibe cada oración del LLM y la habla de inmediato."""
            nonlocal total_llm, total_tts, first_audio_ms, sentences_spoken
            if self.audio._interrupted:
                return
            sentence = sentence.strip()
            if not sentence:
                return
            response_parts.append(sentence)
            total_llm = time.time() - t0_llm
            t_tts = time.time()
            audio_path = self.tts.synthesize(sentence)
            if audio_path:
                if first_audio_ms is None:
                    first_audio_ms = round((time.time() - t0_llm) * 1000)
                    print(f"  [⚡ first audio: {first_audio_ms}ms]", flush=True)
                self.audio.play(audio_path)
                self._cleanup(audio_path)
                sentences_spoken += 1
            total_tts += time.time() - t_tts

        model_used_final = model_used
        full_response = self.brain.think_streaming(text, on_sentence)
        response = full_response or " ".join(response_parts)
        total_llm = time.time() - t0_llm - total_tts  # tiempo puro de LLM sin TTS

        # 4. Log
        total = stt_time + total_llm + total_tts
        print(f"  [{stt_time:.1f}s STT + {total_llm:.1f}s LLM ({model_used}) + "
              f"{total_tts:.1f}s TTS = {total:.1f}s | {sentences_spoken} frases]\n")
        self._log_turn(text, response.strip(), stt_time, total_llm, total_tts, model_used,
                       first_audio_ms=first_audio_ms, sentences_spoken=sentences_spoken)

    def _response_complete(self, response: str) -> bool:
        """Determina si la respuesta del LLM termino naturalmente."""
        stripped = response.strip()
        ends_naturally = stripped.endswith(('.', '?', '!', '"'))
        is_short = len(stripped) < 500
        has_conclusion = any(w in stripped.lower()[-100:] for w in [
            'eso es todo', 'en conclusion', 'para finalizar', 'espero que',
            'cualquier pregunta', 'algo mas', 'eso seria', 'hasta aqui',
        ])
        return ends_naturally and (is_short or has_conclusion)

    def speak_only(self, text: str):
        """Modo TTS: solo genera y reproduce voz con streaming local."""
        print(f"  Generando voz: {text[:60]}...")
        try:
            self.tts.speak_streaming(text, self.audio.play, self._cleanup)
            print("  Reproducido.")
        except Exception as e:
            print(f"  Error generando audio: {e}")
            # Ultimo recurso: macOS say (local, sin internet)
            if platform.system() == "Darwin":
                subprocess.run(["say", "-v", "Paulina", text[:500]], capture_output=True)

    def _speak_simple(self, text: str):
        """Habla un texto corto (saludos, despedidas)."""
        audio_path = self.tts.synthesize(text)
        if audio_path:
            self.audio.play(audio_path)
            self._cleanup(audio_path)
        elif platform.system() == "Darwin":
            # macOS say como ultimo recurso (local, sin internet)
            subprocess.run(["say", "-v", "Paulina", text], capture_output=True)

    def _log_turn(self, user: str, assistant: str, stt_t: float, llm_t: float, tts_t: float,
                  model_used: str = "", first_audio_ms: int | None = None,
                  sentences_spoken: int = 0):
        """Log JSONL para auditoria DOF — incluye métricas de calidad al estilo ElevenLabs."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "session": self.session_id,
            "version": "v4",
            "user": user,
            "assistant": assistant,
            "model_used": model_used,
            "latency": {
                "stt_ms": round(stt_t * 1000),
                "llm_ms": round(llm_t * 1000),
                "tts_ms": round(tts_t * 1000),
                "total_ms": round((stt_t + llm_t + tts_t) * 1000),
                # Métrica clave: tiempo hasta primer audio (ElevenLabs la llama "TTFA")
                "first_audio_ms": first_audio_ms,
            },
            "quality": {
                # Métricas de observabilidad de conversación (inspir. ElevenLabs eval)
                "sentences_spoken": sentences_spoken,
                "response_words": len(assistant.split()),
                "has_content": len(assistant.strip()) > 20,
                "interrupted": self.audio._interrupted,
            },
            "providers": {
                "stt": f"faster-whisper-{self.config.whisper_model_size}",
                "llm": f"ollama-{model_used}",
                "tts": f"edge-tts-{self.config.edge_tts_voice}",
            },
            "mode": self.config.mode,
            "local_only": True,
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _cleanup(self, path: str):
        """Limpia archivo temporal."""
        try:
            if path and os.path.exists(path) and path.startswith(tempfile.gettempdir()):
                os.unlink(path)
        except OSError:
            pass


# ================================================================
# CLI
# ================================================================

def main():
    parser = argparse.ArgumentParser(
        description="DOF Mesh Legion — Voice V4 [100%% LOCAL — Soberania Total]"
    )
    parser.add_argument(
        "--mode",
        choices=["streaming", "moshi"],
        default="streaming",
        help="Modo TTS: streaming (default) | moshi (reservado)",
    )
    parser.add_argument(
        "--tts-only",
        type=str,
        default=None,
        help="Solo generar voz para un texto",
    )
    parser.add_argument(
        "--whisper-size",
        choices=["tiny", "base", "small", "medium", "large-v3"],
        default="small",
        help="Tamano del modelo Whisper (default: small)",
    )
    parser.add_argument(
        "--language",
        default="es",
        help="Idioma STT (default: es)",
    )
    parser.add_argument(
        "--edge-voice",
        type=str,
        default="es-CO-SalomeNeural",
        help="Voz Edge-TTS (default: es-CO-SalomeNeural)",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Modo push-to-talk (Enter para hablar)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Activar logging debug",
    )
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s %(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")

    if args.mode == "moshi":
        print("\n  Modo Moshi no implementado aun.")
        print("  Moshi (Kyutai) requiere integracion especial.")
        print("  Usando modo streaming como fallback.\n")

    config = VoiceV4Config(
        whisper_model_size=args.whisper_size,
        stt_language=args.language,
        edge_tts_voice=args.edge_voice,
        mode=args.mode if args.mode != "moshi" else "streaming",
    )

    voice = VoiceV4(config)

    if args.tts_only:
        voice.speak_only(args.tts_only)
    else:
        voice.start(input_mode="push" if args.push else "vad")


if __name__ == "__main__":
    main()
