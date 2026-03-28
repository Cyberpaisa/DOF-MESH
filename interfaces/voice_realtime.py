"""
Voice Realtime — Conversacion bidireccional en tiempo real.
DOF Mesh Legion / Cyber Paisa / Enigma Group

Pipeline:
  Tu hablas -> VAD detecta voz -> Groq Whisper STT -> DeepSeek/Groq LLM (streaming)
            -> VibeVoice TTS (local MPS) -> Speaker reproduce -> Loop

Componentes:
  STT:     Groq Whisper large-v3 (cloud, gratis, <500ms)
  Cerebro: DeepSeek V3.2 via NVIDIA NIM / Groq Llama 3.3 (streaming)
  TTS:     VibeVoice Realtime 0.5B (local MPS M4 Max) con fallback Edge-TTS
  VAD:     Silero VAD (deteccion continua sin presionar Enter)
  Audio:   sounddevice (mic) + soundfile (wav) + afplay (macOS speaker)

Uso:
  python3 interfaces/voice_realtime.py                    # modo conversacion
  python3 interfaces/voice_realtime.py --tts-only "Hola"  # solo generar voz
  python3 interfaces/voice_realtime.py --provider groq    # usar Groq como cerebro
  python3 interfaces/voice_realtime.py --no-vibevoice     # fallback Edge-TTS
"""

import os
import sys
import json
import time
import wave
import queue
import logging
import tempfile
import argparse
import threading
import subprocess
import platform
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Agregar root del proyecto al path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(Path.home() / "equipo-de-agentes" / ".env")

logger = logging.getLogger("dof.voice.realtime")


# ================================================================
# CONFIG
# ================================================================

@dataclass
class VoiceConfig:
    """Configuracion de la interfaz de voz."""
    # STT
    stt_provider: str = "groq"  # groq (Whisper)
    stt_language: str = "es"
    stt_model: str = "whisper-large-v3"

    # LLM (cerebro)
    llm_provider: str = "ollama"  # ollama (local) | deepseek | nvidia | groq
    llm_model_ollama: str = "dof-voice-fast"  # Gemma 2 9B — rapido para conversacion
    llm_model_nvidia: str = "deepseek-ai/deepseek-v3.2"
    llm_model_groq: str = "llama-3.3-70b-versatile"
    llm_ollama_url: str = "http://localhost:11434"
    llm_temperature: float = 0.4
    llm_max_tokens: int = 8192  # respuestas extensas — relatos largos y continuos

    # TTS
    tts_provider: str = "vibevoice"  # vibevoice | edge-tts | macos
    vibevoice_model: str = "microsoft/VibeVoice-Realtime-0.5B"
    vibevoice_speaker: str = "Carter"
    vibevoice_device: str = "mps"  # mps (M4 Max) | cuda | cpu
    edge_tts_voice: str = "es-CO-SalomeNeural"

    # Audio
    sample_rate: int = 16000  # para grabacion mic
    vad_threshold: float = 0.3  # bajo para no perder voz — Silero recomienda 0.3-0.5
    silence_duration: float = 3.0  # segundos de silencio para cortar — tiempo para pensar
    max_recording: int = 120  # max 2 minutos por turno — charlas extensas

    # Sistema
    system_prompt: str = (
        "Eres la voz del DOF Mesh Legion, un organismo agentico soberano. "
        "Respondes en espanol, de forma directa pero profunda. "
        "Tu creador es Cyber Paisa (Enigma Group, Medellin). "
        "Eres util, inteligente y tienes personalidad. "
        "Puedes dar respuestas largas y detalladas cuando el tema lo requiera. "
        "Usa ejemplos, explica con claridad, y no te limites. "
        "IMPORTANTE: Tu respuesta sera leida en voz alta por un sistema TTS. "
        "NUNCA uses asteriscos, negritas, cursivas, markdown, bullets, guiones ni simbolos especiales. "
        "Escribe SOLO texto plano conversacional, como si hablaras naturalmente. "
        "No uses: * ** _ ` # - • → ni ningun formato. Solo palabras."
    )
    conversation_history: list = field(default_factory=list)
    max_history: int = 50  # turnos de conversacion en memoria — charlas largas


# ================================================================
# STT — Speech to Text (Whisper local o Groq API)
# ================================================================

class SpeechToText:
    """Transcripcion con Whisper local (default) o Groq API (fallback)."""

    def __init__(self, config: VoiceConfig):
        self.config = config
        self._whisper_model = None

    def transcribe(self, audio_path: str) -> str | None:
        """Transcribe un archivo de audio a texto.
        Groq Whisper API primero (preciso en español), local solo si no hay conexión."""
        text = self._transcribe_groq(audio_path)
        if text:
            return text

        logger.warning("Groq STT no disponible, usando Whisper local (menos preciso)")
        return self._transcribe_local(audio_path)

    def _transcribe_local(self, audio_path: str) -> str | None:
        """Whisper local — corre en tu Mac, sin API key."""
        try:
            import whisper

            if self._whisper_model is None:
                print("  Cargando Whisper local (base)...")
                self._whisper_model = whisper.load_model("base")
                print("  Whisper listo.")

            result = self._whisper_model.transcribe(
                audio_path,
                language=self.config.stt_language,
                fp16=False,
            )
            text = result["text"].strip()
            if text:
                logger.info(f"STT local: {text[:80]}...")
            return text if text else None
        except ImportError:
            logger.warning("Whisper local no disponible: pip install openai-whisper")
            return None
        except Exception as e:
            logger.error(f"STT local error: {e}")
            return None

    def _transcribe_groq(self, audio_path: str) -> str | None:
        """Fallback: Groq Whisper API."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return None
        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            with open(audio_path, "rb") as f:
                result = client.audio.transcriptions.create(
                    model=self.config.stt_model,
                    file=f,
                    language=self.config.stt_language,
                )
            text = result.text.strip()
            return text if text else None
        except Exception as e:
            logger.error(f"STT Groq error: {e}")
            return None


# ================================================================
# LLM — Cerebro (DeepSeek / Groq via LiteLLM o requests directo)
# ================================================================

class Brain:
    """Cerebro conversacional con streaming."""

    def __init__(self, config: VoiceConfig):
        self.config = config
        self.history = config.conversation_history

    def think(self, user_text: str) -> str:
        """Genera respuesta al texto del usuario."""
        self.history.append({"role": "user", "content": user_text})

        # Mantener historia limitada
        if len(self.history) > self.config.max_history * 2:
            self.history = self.history[-self.config.max_history * 2:]

        messages = [{"role": "system", "content": self.config.system_prompt}] + self.history

        response = self._call_llm(messages)

        if response:
            self.history.append({"role": "assistant", "content": response})
        return response or "No pude generar una respuesta."

    def _call_llm(self, messages: list) -> str | None:
        """Llama al LLM — Ollama local por defecto, APIs como fallback."""
        provider = self.config.llm_provider

        if provider == "ollama":
            result = self._call_ollama(messages)
            if result:
                return result
            logger.warning("Ollama falló, fallback a DeepSeek")
            return self._call_deepseek(messages)
        elif provider == "deepseek":
            return self._call_deepseek(messages)
        elif provider == "nvidia":
            return self._call_nvidia(messages)
        elif provider == "groq":
            return self._call_groq(messages)
        else:
            return self._call_ollama(messages)

    def _call_ollama(self, messages: list) -> str | None:
        """Ollama local — 100% gratis, sin límites, M4 Max ~50 tok/s, 65K contexto."""
        import requests
        try:
            resp = requests.post(
                f"{self.config.llm_ollama_url}/api/chat",
                json={
                    "model": self.config.llm_model_ollama,
                    "messages": messages,
                    "options": {
                        "temperature": self.config.llm_temperature,
                        "num_predict": 8192,  # hasta 8K tokens por respuesta (~6K palabras, ~30 min de audio)
                        "num_ctx": 8192,      # contexto optimizado para velocidad con Gemma
                    },
                    "stream": False,
                },
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"].strip()
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return None

    def _call_deepseek(self, messages: list) -> str | None:
        """DeepSeek API directa."""
        import requests
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            logger.warning("DEEPSEEK_API_KEY no encontrada, fallback a NVIDIA")
            return self._call_nvidia(messages)
        try:
            resp = requests.post(
                "https://api.deepseek.com/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": messages,
                    "temperature": self.config.llm_temperature,
                    "max_tokens": self.config.llm_max_tokens,
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"DeepSeek error: {e}, fallback a NVIDIA")
            return self._call_nvidia(messages)

    def _call_nvidia(self, messages: list) -> str | None:
        """NVIDIA NIM — DeepSeek V3.2."""
        import requests
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            logger.warning("NVIDIA_API_KEY no encontrada, fallback a Groq")
            return self._call_groq(messages)
        try:
            resp = requests.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.config.llm_model_nvidia,
                    "messages": messages,
                    "temperature": self.config.llm_temperature,
                    "max_tokens": self.config.llm_max_tokens,
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"NVIDIA error: {e}, fallback a Groq")
            return self._call_groq(messages)

    def _call_groq(self, messages: list) -> str | None:
        """Groq — Llama 3.3 70B."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return None
        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            resp = client.chat.completions.create(
                model=self.config.llm_model_groq,
                messages=messages,
                temperature=self.config.llm_temperature,
                max_tokens=self.config.llm_max_tokens,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Groq LLM error: {e}")
            return None


# ================================================================
# TTS — Text to Speech (VibeVoice Realtime / Edge-TTS / macOS)
# ================================================================

class TextToSpeech:
    """Sintesis de voz multi-provider."""

    def __init__(self, config: VoiceConfig):
        self.config = config
        self._vibevoice_model = None
        self._vibevoice_processor = None
        self._vibevoice_ready = False
        self._voice_cache = None

    def speak(self, text: str) -> str | None:
        """Genera audio y retorna path al archivo WAV.
        Sin limite de longitud — soporta relatos extensos."""
        provider = self.config.tts_provider
        if provider == "vibevoice":
            path = self._vibevoice_speak(text[:800])  # VibeVoice tiene limite interno
            if path:
                return path
            logger.warning("VibeVoice fallo, fallback a Edge-TTS")

        path = self._edge_tts_speak(text)  # Edge-TTS soporta texto largo
        if path:
            return path

        return self._macos_speak(text)

    def _vibevoice_speak(self, text: str) -> str | None:
        """VibeVoice Realtime 0.5B — local inference."""
        try:
            if not self._vibevoice_ready:
                self._load_vibevoice()

            if not self._vibevoice_ready:
                return None

            import torch
            import copy

            inputs = self._vibevoice_processor.process_input_with_cached_prompt(
                text=text,
                cached_prompt=self._voice_cache,
                padding=True,
                return_tensors="pt",
                return_attention_mask=True,
            )

            device = self.config.vibevoice_device
            for k, v in inputs.items():
                if torch.is_tensor(v):
                    inputs[k] = v.to(device)

            start = time.time()
            outputs = self._vibevoice_model.generate(
                **inputs,
                max_new_tokens=None,
                cfg_scale=1.5,
                tokenizer=self._vibevoice_processor.tokenizer,
                generation_config={"do_sample": False},
                verbose=False,
                all_prefilled_outputs=copy.deepcopy(self._voice_cache),
            )
            elapsed = time.time() - start

            if outputs.speech_outputs and outputs.speech_outputs[0] is not None:
                out_path = tempfile.mktemp(suffix=".wav")
                self._vibevoice_processor.save_audio(outputs.speech_outputs[0], output_path=out_path)
                logger.info(f"VibeVoice TTS: {elapsed:.2f}s")
                return out_path

            return None
        except Exception as e:
            logger.error(f"VibeVoice TTS error: {e}")
            self._vibevoice_ready = False
            return None

    def _load_vibevoice(self):
        """Carga modelo VibeVoice Realtime 0.5B."""
        try:
            import torch
            from vibevoice.modular.modeling_vibevoice_streaming_inference import (
                VibeVoiceStreamingForConditionalGenerationInference,
            )
            from vibevoice.processor.vibevoice_streaming_processor import (
                VibeVoiceStreamingProcessor,
            )

            model_path = self.config.vibevoice_model
            device = self.config.vibevoice_device

            print(f"  Cargando VibeVoice Realtime 0.5B en {device}...")

            self._vibevoice_processor = VibeVoiceStreamingProcessor.from_pretrained(model_path)

            if device == "mps":
                dtype = torch.float32
                attn = "sdpa"
                model = VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
                    model_path, torch_dtype=dtype, attn_implementation=attn, device_map=None,
                )
                model.to("mps")
            elif device == "cuda":
                dtype = torch.bfloat16
                attn = "flash_attention_2"
                model = VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
                    model_path, torch_dtype=dtype, device_map="cuda", attn_implementation=attn,
                )
            else:
                dtype = torch.float32
                attn = "sdpa"
                model = VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
                    model_path, torch_dtype=dtype, device_map="cpu", attn_implementation=attn,
                )

            model.eval()
            model.set_ddpm_inference_steps(num_steps=5)
            self._vibevoice_model = model

            # Cargar voice preset
            import glob as _glob
            voices_dir = Path(model_path).parent / "voices" / "streaming_model"
            if not voices_dir.exists():
                # Intentar desde HuggingFace cache
                from huggingface_hub import snapshot_download
                local_dir = snapshot_download(model_path)
                voices_dir = Path(local_dir) / "demo" / "voices" / "streaming_model"

            speaker = self.config.vibevoice_speaker.lower()
            pt_files = list(Path(voices_dir).rglob("*.pt")) if voices_dir.exists() else []

            voice_file = None
            for pt in pt_files:
                if speaker in pt.stem.lower():
                    voice_file = pt
                    break
            if not voice_file and pt_files:
                voice_file = pt_files[0]

            if voice_file:
                self._voice_cache = torch.load(voice_file, map_location=device, weights_only=False)
                self._vibevoice_ready = True
                print(f"  VibeVoice listo — voz: {voice_file.stem}")
            else:
                logger.warning("No se encontraron voice presets para VibeVoice")

        except ImportError:
            logger.warning(
                "VibeVoice no instalado. Instalar con:\n"
                "  git clone https://github.com/microsoft/VibeVoice.git\n"
                "  cd VibeVoice && pip install -e .[streamingtts]"
            )
        except Exception as e:
            logger.error(f"Error cargando VibeVoice: {e}")

    def _edge_tts_speak(self, text: str) -> str | None:
        """Edge-TTS — voz neural colombiana."""
        try:
            import asyncio
            import edge_tts

            out_path = tempfile.mktemp(suffix=".mp3")

            async def _gen():
                comm = edge_tts.Communicate(text, self.config.edge_tts_voice)
                await comm.save(out_path)

            asyncio.run(_gen())
            return out_path
        except ImportError:
            logger.warning("edge-tts no instalado: pip install edge-tts")
            return None
        except Exception as e:
            logger.error(f"Edge-TTS error: {e}")
            return None

    def _macos_speak(self, text: str) -> str | None:
        """Fallback macOS say."""
        if platform.system() != "Darwin":
            return None
        out_path = tempfile.mktemp(suffix=".aiff")
        subprocess.run(
            ["say", "-v", "Paulina", "-o", out_path, text[:500]],
            capture_output=True,
        )
        return out_path if os.path.exists(out_path) else None


# ================================================================
# AUDIO — Grabacion + Reproduccion + VAD
# ================================================================

class AudioEngine:
    """Motor de audio: grabacion con Silero VAD y reproduccion con interrupcion.

    Mejoras Fase 1 (extraidas de Gemini Flash Live architecture):
    - Silero VAD: deteccion neural de voz (<1ms por chunk) en vez de RMS simple
    - Parametros estilo Google: start_sensitivity, end_sensitivity, prefix_padding, silence_duration
    - Interrupcion: si hablas mientras responde, para el audio
    - Pre-buffer: guarda audio ANTES de detectar voz (no pierde inicio de frase)
    """

    def __init__(self, config: VoiceConfig):
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
            # Reset del modelo para evitar estado residual
            self._vad_model.reset_states()
            print("  Silero VAD cargado")
        except Exception as e:
            print(f"  VAD neural no disponible ({e}), usando deteccion por energia")
            self._vad_model = "rms_fallback"

    def record_with_vad(self) -> str | None:
        """Graba audio con Silero VAD neural — detecta inicio y fin de habla con precision."""
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
        prefix_chunks = 3  # guarda 3 chunks antes de detectar voz (no pierde inicio)

        audio_buffer = []
        pre_buffer = []  # buffer circular pre-voz
        silent_count = 0
        speaking = False
        chunks_recorded = 0

        print("\n  Escuchando... (habla cuando quieras)")

        def _is_speech_silero(chunk: np.ndarray) -> bool:
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

                    is_voice = _is_speech_silero(chunk)

                    if is_voice:
                        if not speaking:
                            speaking = True
                            # Incluir pre-buffer (inicio de frase que habria perdido)
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
                        # Pre-buffer: guarda los ultimos N chunks antes de detectar voz
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

            # Verificar que hay audio real
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
        """Reproduce un archivo de audio con soporte de interrupcion.

        Estilo Gemini: si el usuario habla durante la reproduccion,
        se detiene el audio y se limpia la cola (interrupted=True).
        """
        if not audio_path or not os.path.exists(audio_path):
            return
        if platform.system() != "Darwin":
            logger.warning("Reproduccion solo soportada en macOS por ahora")
            return

        self._playing = True
        self._interrupted = False
        self._playback_process = subprocess.Popen(
            ["afplay", audio_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Monitor thread: detecta si el usuario habla durante playback
        monitor = threading.Thread(
            target=self._monitor_interruption_during_playback,
            daemon=True,
        )
        monitor.start()

        self._playback_process.wait()
        self._playing = False

        if self._interrupted:
            print("  ... interrumpido por el usuario")

    def interrupt(self):
        """Detiene la reproduccion actual (el usuario quiere hablar)."""
        self._interrupted = True
        if self._playback_process and self._playback_process.poll() is None:
            self._playback_process.terminate()
            try:
                self._playback_process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self._playback_process.kill()

    def _monitor_interruption_during_playback(self):
        """Monitorea el mic durante playback — DESACTIVADO.

        Nota: cuando Alexa es el speaker via Bluetooth, el mic del Mac
        captura el audio de la Alexa y genera falsos positivos de interrupcion.
        Se necesita echo cancellation para activar esto correctamente.
        Por ahora desactivado hasta implementar AEC (Acoustic Echo Cancellation).
        """
        pass

    def play_async(self, audio_path: str):
        """Reproduce audio en background thread con interrupcion."""
        t = threading.Thread(target=self.play, args=(audio_path,), daemon=True)
        t.start()
        return t


# ================================================================
# VOICE REALTIME — Loop principal de conversacion
# ================================================================

class VoiceRealtime:
    """Interfaz de conversacion en tiempo real por voz."""

    def __init__(self, config: VoiceConfig | None = None):
        self.config = config or VoiceConfig()
        self.stt = SpeechToText(self.config)
        self.brain = Brain(self.config)
        self.tts = TextToSpeech(self.config)
        self.audio = AudioEngine(self.config)
        self.running = False

        # Log JSONL para auditoría DOF
        self.log_dir = PROJECT_ROOT / "logs" / "voice"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_path = self.log_dir / f"session_{self.session_id}.jsonl"

    def start(self, mode: str = "vad"):
        """Inicia el loop de conversacion.

        Args:
            mode: "vad" (deteccion automatica) o "push" (presionar Enter para hablar)
        """
        self.running = True
        self.mode = mode

        print("\n" + "=" * 55)
        print("  DOF MESH LEGION — VOZ EN TIEMPO REAL")
        print("=" * 55)
        print(f"  STT:     Groq Whisper ({self.config.stt_model})")
        print(f"  Cerebro: {self.config.llm_provider.upper()} ({self._get_model_name()})")
        print(f"  TTS:     {self.config.tts_provider}")
        print(f"  Idioma:  {self.config.stt_language}")
        print(f"  Modo:    {'VAD automatico' if mode == 'vad' else 'Push-to-talk (Enter)'}")
        print("=" * 55)
        if mode == "push":
            print("  Presiona Enter para hablar, Ctrl+C para salir.\n")
        else:
            print("  Habla naturalmente. Ctrl+C para salir.\n")

        # Saludo inicial
        greeting = "Listo. Estoy escuchando."
        greeting_audio = self.tts.speak(greeting)
        if greeting_audio:
            self.audio.play(greeting_audio)
            self._cleanup(greeting_audio)
        else:
            subprocess.run(["say", "-v", "Paulina", greeting], capture_output=True)

        while self.running:
            try:
                self._conversation_turn()
            except KeyboardInterrupt:
                print("\n\n  Hasta luego, Cyber Paisa.")
                farewell = self.tts.speak("Hasta luego.")
                if farewell:
                    self.audio.play(farewell)
                    self._cleanup(farewell)
                break
            except Exception as e:
                logger.error(f"Error en turno: {e}")
                print(f"  Error: {e} — reintentando...")
                time.sleep(1)

    def _conversation_turn(self):
        """Un turno de conversacion con auto-continuacion.

        Si la respuesta del LLM parece incompleta (termina a mitad de frase),
        automaticamente pide "continua" hasta que termine naturalmente.
        """
        # 1. Escuchar
        if self.mode == "push":
            input("  >> Presiona Enter y habla (5 seg)...")
            wav_path = self.audio.record_fixed(duration=5)
        else:
            wav_path = self.audio.record_with_vad()
        if not wav_path:
            return

        # 2. Transcribir
        t0 = time.time()
        text = self.stt.transcribe(wav_path)
        stt_time = time.time() - t0
        self._cleanup(wav_path)

        if not text or len(text.strip()) < 2:
            return

        print(f"\n  Tu: {text}")

        # 3. Pensar + Hablar (con auto-continuacion)
        total_llm = 0
        total_tts = 0
        full_response = ""
        max_continuations = 5  # maximo 5 continuaciones automaticas

        for i in range(max_continuations + 1):
            if i == 0:
                prompt = text
            else:
                prompt = "Continua exactamente donde dejaste, no repitas lo anterior, sigue desarrollando."
                print("  ... (auto-continuacion)")

            t0 = time.time()
            response = self.brain.think(prompt)
            llm_time = time.time() - t0
            total_llm += llm_time

            if not response:
                break

            full_response += " " + response
            print(f"  Mesh: {response[:200]}{'...' if len(response) > 200 else ''}")

            # Hablar este segmento
            t0 = time.time()
            audio_path = self.tts.speak(response)
            tts_time = time.time() - t0
            total_tts += tts_time

            if audio_path:
                self.audio.play(audio_path)
                self._cleanup(audio_path)
            else:
                subprocess.run(["say", "-v", "Paulina", response[:500]], capture_output=True)

            # Verificar si la respuesta termino naturalmente
            response_stripped = response.strip()
            ends_naturally = response_stripped.endswith(('.', '?', '!', '"'))
            is_short_enough = len(response_stripped) < 500
            has_conclusion = any(w in response_stripped.lower()[-100:] for w in [
                'eso es todo', 'en conclusion', 'para finalizar', 'espero que',
                'cualquier pregunta', 'algo mas', 'eso seria', 'hasta aqui',
            ])

            if ends_naturally and (is_short_enough or has_conclusion):
                break  # respuesta completa, no continuar

            if i == max_continuations:
                break  # limite de continuaciones

        # 4. Log
        total = stt_time + total_llm + total_tts
        print(f"  [{stt_time:.1f}s STT + {total_llm:.1f}s LLM + {total_tts:.1f}s TTS = {total:.1f}s]\n")

        self._log_turn(text, full_response.strip(), stt_time, total_llm, total_tts)

    def speak_only(self, text: str):
        """Modo TTS: solo genera y reproduce voz."""
        print(f"  Generando voz: {text[:60]}...")
        audio_path = self.tts.speak(text)
        if audio_path:
            self.audio.play(audio_path)
            self._cleanup(audio_path)
            print("  Reproducido.")
        else:
            print("  Error generando audio.")

    def _log_turn(self, user: str, assistant: str, stt_t: float, llm_t: float, tts_t: float):
        """Log JSONL para auditoria DOF."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "session": self.session_id,
            "user": user,
            "assistant": assistant,
            "latency": {
                "stt_ms": round(stt_t * 1000),
                "llm_ms": round(llm_t * 1000),
                "tts_ms": round(tts_t * 1000),
                "total_ms": round((stt_t + llm_t + tts_t) * 1000),
            },
            "providers": {
                "stt": self.config.stt_provider,
                "llm": self.config.llm_provider,
                "tts": self.config.tts_provider,
            },
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _get_model_name(self) -> str:
        if self.config.llm_provider == "ollama":
            return f"{self.config.llm_model_ollama} (LOCAL)"
        elif self.config.llm_provider == "nvidia":
            return self.config.llm_model_nvidia
        return self.config.llm_model_groq

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
    parser = argparse.ArgumentParser(description="DOF Mesh — Voice Realtime")
    parser.add_argument("--provider", choices=["ollama", "deepseek", "nvidia", "groq"], default="ollama",
                        help="LLM provider (default: ollama — local, gratis)")
    parser.add_argument("--tts", choices=["vibevoice", "edge-tts", "macos"], default="edge-tts",
                        help="TTS provider (default: edge-tts)")
    parser.add_argument("--tts-only", type=str, default=None,
                        help="Solo generar voz para un texto")
    parser.add_argument("--no-vibevoice", action="store_true",
                        help="No intentar VibeVoice, usar Edge-TTS directo")
    parser.add_argument("--language", default="es", help="Idioma STT (default: es)")
    parser.add_argument("--voice", default="es-CO-SalomeNeural",
                        help="Voz Edge-TTS (default: es-CO-SalomeNeural)")
    parser.add_argument("--speaker", default="Carter",
                        help="Speaker VibeVoice (default: Carter)")
    parser.add_argument("--push", action="store_true",
                        help="Modo push-to-talk (Enter para hablar)")
    args = parser.parse_args()

    config = VoiceConfig(
        llm_provider=args.provider,
        tts_provider="edge-tts" if args.no_vibevoice else args.tts,
        stt_language=args.language,
        edge_tts_voice=args.voice,
        vibevoice_speaker=args.speaker,
    )

    voice = VoiceRealtime(config)

    if args.tts_only:
        voice.speak_only(args.tts_only)
    else:
        voice.start(mode="push" if args.push else "vad")


if __name__ == "__main__":
    main()
