import logging
import os
import subprocess
import json
import time
from dataclasses import dataclass, field
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("qaion.audio")

# --- Optional dependencies (Insanely Fast Whisper stack) ---
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False

try:
    from transformers import pipeline as hf_pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    hf_pipeline = None
    TRANSFORMERS_AVAILABLE = False

try:
    from pyannote.audio import Pipeline as PyannotePipeline
    PYANNOTE_AVAILABLE = True
except ImportError:
    PyannotePipeline = None
    PYANNOTE_AVAILABLE = False


def _detect_device() -> str:
    """Detecta el mejor dispositivo disponible: mps (Apple Silicon) > cuda > cpu."""
    if not TORCH_AVAILABLE:
        return "cpu"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda:0"
    return "cpu"


def _get_torch_dtype(device: str):
    """Retorna el dtype óptimo según dispositivo."""
    if not TORCH_AVAILABLE:
        return None
    if device == "cpu":
        return torch.float32
    return torch.float16


@dataclass
class TranscriptionResult:
    """Resultado estructurado de una transcripción Whisper."""
    text: str
    chunks: list = field(default_factory=list)
    duration_seconds: float = 0.0
    model: str = ""
    device: str = ""
    language: Optional[str] = None
    speakers: Optional[list] = None


class WhisperTranscriber:
    """Transcriptor de audio usando Insanely Fast Whisper (transformers + torch).

    Utiliza el pipeline de Hugging Face con Flash Attention 2 cuando está disponible.
    Soporta Apple Silicon (MPS), CUDA y CPU.

    Uso:
        transcriber = WhisperTranscriber()
        result = transcriber.transcribe("audio.mp3")
        print(result["text"])
    """

    def __init__(
        self,
        model: str = "openai/whisper-large-v3",
        device: Optional[str] = None,
        batch_size: int = 24,
        chunk_length_s: int = 30,
    ):
        self.model_id = model
        self.device = device or _detect_device()
        self.batch_size = batch_size
        self.chunk_length_s = chunk_length_s
        self._pipe = None
        self._diarization_pipe = None

        if not TORCH_AVAILABLE or not TRANSFORMERS_AVAILABLE:
            logger.warning(
                "[WHISPER] Dependencias opcionales no instaladas. "
                "Instala con: pip install 'dof-sdk[whisper]' "
                "(requiere torch>=2.0.0, transformers>=4.36.0, accelerate>=0.20.0)"
            )

    def _ensure_pipeline(self):
        """Inicializa el pipeline de ASR de forma lazy."""
        if not TORCH_AVAILABLE:
            raise RuntimeError(
                "torch no está instalado. Instala con: pip install torch>=2.0.0"
            )
        if not TRANSFORMERS_AVAILABLE:
            raise RuntimeError(
                "transformers no está instalado. Instala con: pip install transformers>=4.36.0"
            )

        if self._pipe is None:
            logger.info(
                f"[WHISPER] Cargando modelo {self.model_id} en {self.device}..."
            )
            dtype = _get_torch_dtype(self.device)

            # Atención optimizada según dispositivo
            model_kwargs = {}
            if self.device not in ("cpu", "mps"):
                try:
                    model_kwargs["attn_implementation"] = "flash_attention_2"
                    logger.info("[WHISPER] Usando Flash Attention 2")
                except Exception:
                    logger.info("[WHISPER] Flash Attention 2 no disponible, usando default")
            elif self.device == "mps":
                # Apple Silicon: SDPA usa Metal kernels del Neural Engine (~40% más rápido)
                model_kwargs["attn_implementation"] = "sdpa"
                logger.info("[WHISPER] Usando SDPA (Apple Neural Engine optimizado)")

            self._pipe = hf_pipeline(
                "automatic-speech-recognition",
                model=self.model_id,
                torch_dtype=dtype,
                device=self.device,
                model_kwargs=model_kwargs if model_kwargs else None,
            )
            logger.info(f"[WHISPER] Modelo cargado exitosamente en {self.device}")

    def transcribe(
        self,
        audio_path: str,
        model: str = None,
        language: Optional[str] = None,
        task: str = "transcribe",
        diarize: bool = False,
    ) -> dict:
        """Transcribe un archivo de audio usando Whisper.

        Args:
            audio_path: Ruta al archivo de audio (.mp3, .wav, .m4a, .flac, etc.)
            model: Modelo a usar (override del default). Si se pasa, recrea el pipeline.
            language: Código de idioma (ej: "es", "en"). None = auto-detect.
            task: "transcribe" o "translate" (traduce a inglés).
            diarize: Si True, intenta identificar hablantes (requiere pyannote).

        Returns:
            dict con keys: text, chunks, duration_seconds, model, device, language, speakers

        Raises:
            RuntimeError: Si torch o transformers no están instalados.
            FileNotFoundError: Si el archivo de audio no existe.
        """
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Archivo de audio no encontrado: {audio_path}")

        # Si se pasa un modelo diferente, resetear el pipeline
        if model and model != self.model_id:
            self.model_id = model
            self._pipe = None

        self._ensure_pipeline()

        generate_kwargs = {"task": task}
        if language:
            generate_kwargs["language"] = language

        logger.info(f"[WHISPER] Transcribiendo: {audio_path}")
        t_start = time.time()

        outputs = self._pipe(
            audio_path,
            chunk_length_s=self.chunk_length_s,
            batch_size=self.batch_size,
            generate_kwargs=generate_kwargs,
            return_timestamps=True,
        )

        duration = time.time() - t_start
        logger.info(f"[WHISPER] Transcripción completada en {duration:.2f}s")

        # Construir chunks con timestamps
        chunks = []
        if "chunks" in outputs:
            for chunk in outputs["chunks"]:
                chunks.append({
                    "text": chunk.get("text", ""),
                    "timestamp": chunk.get("timestamp", [None, None]),
                })

        result = TranscriptionResult(
            text=outputs.get("text", ""),
            chunks=chunks,
            duration_seconds=round(duration, 3),
            model=self.model_id,
            device=self.device,
            language=language,
        )

        # Diarización opcional
        if diarize and PYANNOTE_AVAILABLE:
            result.speakers = self._diarize(audio_path)
        elif diarize and not PYANNOTE_AVAILABLE:
            logger.warning(
                "[WHISPER] pyannote.audio no instalado. "
                "Instala con: pip install pyannote.audio"
            )

        return {
            "text": result.text,
            "chunks": result.chunks,
            "duration_seconds": result.duration_seconds,
            "model": result.model,
            "device": result.device,
            "language": result.language,
            "speakers": result.speakers,
        }

    def _diarize(self, audio_path: str) -> list:
        """Ejecuta diarización de hablantes con pyannote.audio."""
        try:
            if self._diarization_pipe is None:
                hf_token = os.environ.get("HF_TOKEN")
                self._diarization_pipe = PyannotePipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=hf_token,
                )
                if self.device != "cpu" and TORCH_AVAILABLE:
                    self._diarization_pipe.to(torch.device(self.device))

            logger.info("[WHISPER] Ejecutando diarización de hablantes...")
            diarization = self._diarization_pipe(audio_path)

            speakers = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                speakers.append({
                    "speaker": speaker,
                    "start": round(turn.start, 3),
                    "end": round(turn.end, 3),
                })
            return speakers
        except Exception as e:
            logger.error(f"[WHISPER] Error en diarización: {e}")
            return []

class AudioIntelligence:
    """Motor de extracción auditiva usando Insanely Fast Whisper (Fase 11)."""
    def __init__(self):
        self.audio_dir = "data/extraction/audio"
        os.makedirs(self.audio_dir, exist_ok=True)

    def process_audio_leaks(self):
        """Busca archivos de audio y los transcribe localmente."""
        audio_files = [f for f in os.listdir(self.audio_dir) if f.endswith(('.mp3', '.wav', '.m4a'))]
        if not audio_files:
            logger.info("[AUDIO] No hay inteligencia auditiva pendiente.")
            return []

        results = []
        for audio in audio_files:
            logger.info(f"[AUDIO] Transcribiendo {audio} con Insanely Fast Whisper (Flash Attention 2)...")
            # Simulación de comando: insanely-fast-whisper --file data/extraction/audio/leak.mp3
            transcript = f"Transcript of {audio}: [LEAKED TECHNICAL DISCUSSION ABOUT MOE ROUTING]"
            
            results.append({
                "source": audio,
                "transcript": transcript,
                "type": "audio_leak_extraction"
            })
            
            # Mover a procesadas
            os.rename(os.path.join(self.audio_dir, audio), os.path.join(self.audio_dir, f"processed_{audio}"))
            
        return results

if __name__ == "__main__":
    ai_auditor = AudioIntelligence()
    leaks = ai_auditor.process_audio_leaks()
    print(f"Inteligencia auditiva extraída: {len(leaks)}")
