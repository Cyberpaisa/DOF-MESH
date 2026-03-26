"""
Voice Interface — Conversacion natural por voz.
Cyber Paisa / Enigma Group

STT: Groq Whisper API (cloud, gratis)
TTS: gTTS (cloud, gratis)

Modo continuo: tu hablas → el sistema escucha → ejecuta → te responde con voz.
"""

import os
import sys
import logging
import subprocess
import platform
import threading
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("q_aion.voice")


# ═══════════════════════════════════════════════════════
# STT — Speech to Text (Groq Whisper API)
# ═══════════════════════════════════════════════════════

def transcribe_audio(audio_path: str, language: str = "es") -> str | None:
    """Transcribe un archivo de audio usando Groq Whisper API."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.error("GROQ_API_KEY no configurada para STT")
        return None
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=audio_file,
                language=language,
            )
        text = transcription.text
        logger.info(f"Transcripcion: {text[:80]}...")
        return text
    except ImportError:
        logger.error("Instala groq: pip install groq")
        return None
    except Exception as e:
        logger.error(f"Error transcribiendo: {e}")
        return None


# ═══════════════════════════════════════════════════════
# TTS — Text to Speech (Edge-TTS neural voices)
# ═══════════════════════════════════════════════════════

# Voz neural colombiana — Salome (femenina, natural)
# Alternativas: es-CO-GonzaloNeural (masculina), es-MX-DaliaNeural (México)
EDGE_TTS_VOICE = "es-CO-SalomeNeural"


def text_to_speech(text: str, output_path: str = "/tmp/response.mp3", lang: str = "es") -> str | None:
    """Genera audio con Edge-TTS (voz neural Salome colombiana)."""
    try:
        import asyncio
        import edge_tts

        async def _generate():
            communicate = edge_tts.Communicate(text, EDGE_TTS_VOICE)
            await communicate.save(output_path)

        # Edge-TTS es async — ejecutar en event loop
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                loop.run_in_executor(pool, lambda: asyncio.run(_generate()))
            return output_path
        except RuntimeError:
            asyncio.run(_generate())

        return output_path
    except ImportError:
        logger.warning("edge-tts no disponible, usando gTTS como fallback")
        return _tts_fallback_gtts(text, output_path, lang)
    except Exception as e:
        logger.warning(f"Edge-TTS error ({e}), intentando gTTS fallback")
        return _tts_fallback_gtts(text, output_path, lang)


def _tts_fallback_gtts(text: str, output_path: str, lang: str = "es") -> str | None:
    """Fallback a gTTS si Edge-TTS falla."""
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang=lang)
        tts.save(output_path)
        return output_path
    except Exception as e:
        logger.error(f"gTTS fallback error: {e}")
        return None


def speak(text: str):
    """Genera audio y lo reproduce automaticamente en Mac."""
    # Limitar texto para que la respuesta de voz no sea eterna
    if len(text) > 500:
        text = text[:500] + "... el resultado completo esta guardado en el archivo de output."

    audio_path = text_to_speech(text)
    if audio_path:
        _play_audio(audio_path)
    else:
        # Fallback: usar say de macOS directamente
        if platform.system() == "Darwin":
            subprocess.run(["say", "-v", "Paulina", text[:300]], capture_output=True)


def _play_audio(path: str):
    """Reproduce un archivo de audio en Mac."""
    if platform.system() == "Darwin":
        subprocess.run(["afplay", path], capture_output=True)
    else:
        logger.warning("Reproduccion de audio solo soportada en macOS")


# ═══════════════════════════════════════════════════════
# GRABACION — Microfono
# ═══════════════════════════════════════════════════════

def record_audio(duration: int = 5) -> str | None:
    """Graba audio del microfono y lo guarda como WAV."""
    try:
        import sounddevice as sd
        import wave

        sample_rate = 16000
        print(f"\n🎙  Habla ahora ({duration} segundos)...")
        audio = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
        )
        sd.wait()
        print("✅ Escuchado")

        wav_path = "/tmp/recording.wav"
        with wave.open(wav_path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio.tobytes())
        return wav_path

    except ImportError:
        logger.error("Instala sounddevice: pip install sounddevice")
        return None
    except Exception as e:
        logger.error(f"Error grabando: {e}")
        return None


def record_and_transcribe(duration: int = 5, language: str = "es") -> str | None:
    """Graba del microfono y transcribe a texto."""
    wav_path = record_audio(duration)
    if wav_path:
        return transcribe_audio(wav_path, language)
    return None


# ═══════════════════════════════════════════════════════
# ROUTER — Interpreta el comando de voz y ejecuta
# ═══════════════════════════════════════════════════════

def route_voice_command(text: str) -> str:
    """Interpreta el texto hablado y ejecuta el crew correspondiente.

    Returns:
        Resultado como texto para leer en voz alta.
    """
    text_lower = text.lower().strip()

    # Agregar path del proyecto al sys.path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from crew import (
        create_research_crew, create_grant_hunt_crew,
        create_content_crew, create_daily_ops_crew,
        create_weekly_report_crew, create_full_mvp_crew,
    )

    try:
        # Detectar intencion por palabras clave
        if any(w in text_lower for w in ["rutina", "daily", "buenos dias", "buen dia", "matutina"]):
            print("🔄 Ejecutando rutina diaria...")
            speak("Ejecutando tu rutina matutina. Dame unos minutos.")
            crew = create_daily_ops_crew()
            result = crew.kickoff()
            return _save_and_summarize(result, "daily_ops")

        elif any(w in text_lower for w in ["grant", "beca", "funding", "oportunidad"]):
            # Detectar proyecto
            project = _detect_project(text_lower)
            print(f"🔄 Buscando grants{f' para {project}' if project else ''}...")
            speak("Buscando grants y oportunidades. Dame unos minutos.")
            crew = create_grant_hunt_crew(text, project)
            result = crew.kickoff()
            return _save_and_summarize(result, "grant_hunt", project)

        elif any(w in text_lower for w in ["investiga", "research", "analiza mercado", "busca info"]):
            print("🔄 Investigando...")
            speak("Investigando. Dame unos minutos.")
            crew = create_research_crew(text)
            result = crew.kickoff()
            return _save_and_summarize(result, "research")

        elif any(w in text_lower for w in ["hilo", "thread", "tweet", "blog", "contenido", "escribe"]):
            project = _detect_project(text_lower)
            print("🔄 Generando contenido...")
            speak("Generando contenido. Dame unos minutos.")
            crew = create_content_crew(text, project)
            result = crew.kickoff()
            return _save_and_summarize(result, "content", project)

        elif any(w in text_lower for w in ["semanal", "weekly", "reporte", "reunion"]):
            project = _detect_project(text_lower)
            print("🔄 Preparando reporte semanal...")
            speak("Preparando tu reporte semanal.")
            crew = create_weekly_report_crew(project)
            result = crew.kickoff()
            return _save_and_summarize(result, "weekly_report", project)

        elif any(w in text_lower for w in ["mvp", "producto", "construir", "idea de"]):
            print("🔄 Generando MVP...")
            speak("Diseñando el MVP. Esto puede tomar un rato.")
            crew = create_full_mvp_crew(text)
            result = crew.kickoff()
            return _save_and_summarize(result, "full_mvp")

        else:
            return (
                "No entendi bien que necesitas. Puedes decirme cosas como: "
                "busca grants, ejecuta la rutina diaria, investiga un tema, "
                "genera un hilo de twitter, o prepara el reporte semanal."
            )

    except Exception as e:
        error_msg = f"Hubo un error ejecutando la tarea: {e}"
        logger.error(error_msg)
        return error_msg


def _detect_project(text: str) -> str | None:
    """Intenta detectar nombre de proyecto en el texto."""
    import yaml
    projects_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config", "projects.yaml",
    )
    if not os.path.exists(projects_path):
        return None
    with open(projects_path, "r") as f:
        data = yaml.safe_load(f)
    if not data or "projects" not in data:
        return None
    for p in data["projects"]:
        if p["name"].lower() in text:
            return p["name"]
    return None


def _save_and_summarize(result, mode: str, project: str | None = None) -> str:
    """Guarda resultado completo y retorna resumen corto para voz."""
    result_str = str(result)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = f"output/{project}" if project else "output"
    os.makedirs(out_dir, exist_ok=True)
    out_path = f"{out_dir}/{mode}_{ts}.md"
    with open(out_path, "w") as f:
        f.write(f"# {mode}\n**Fecha:** {datetime.now():%Y-%m-%d %H:%M}\n\n---\n\n{result_str}")

    # Resumen corto para voz (primeras 400 chars)
    summary = result_str[:400].replace("\n", " ").replace("#", "").strip()
    return f"Listo. {summary}... El resultado completo esta guardado en {out_path}"


# ═══════════════════════════════════════════════════════
# LOOP CONTINUO — Habla natural desde tu Mac
# ═══════════════════════════════════════════════════════

def start_voice_loop(duration: int = 7):
    """Loop continuo de voz: escucha → ejecuta → responde → repite.

    Presiona Ctrl+C para detener.

    Args:
        duration: Segundos de grabacion por turno (default 7 para frases largas)
    """
    print("\n" + "=" * 50)
    print("🎙  MODO VOZ ACTIVADO — Q-AION Legion Dashboard")
    print("=" * 50)
    print("Habla naturalmente. Di cosas como:")
    print('  - "Buenos dias, ejecuta la rutina diaria"')
    print('  - "Busca grants de AI en Avalanche para FLARE"')
    print('  - "Genera un hilo de Twitter sobre agentes AI"')
    print('  - "Prepara el reporte semanal"')
    print('  - "Investiga tendencias de Web3 en Latinoamerica"')
    print("\nPresiona Ctrl+C para salir\n")

    speak("Modo voz activado. Estoy listo para escucharte.")

    while True:
        try:
            # Esperar que el usuario presione Enter para hablar
            input("⏎  Presiona Enter y habla...")

            # Grabar
            text = record_and_transcribe(duration=duration, language="es")
            if not text:
                speak("No escuche nada. Intenta de nuevo.")
                continue

            print(f"\n📝 Escuche: \"{text}\"\n")

            # Ejecutar comando
            response = route_voice_command(text)
            print(f"\n💬 Respuesta: {response[:200]}...\n")

            # Responder con voz
            speak(response)

        except KeyboardInterrupt:
            print("\n\n👋 Modo voz desactivado. Hasta luego!")
            speak("Hasta luego, Cyber Paisa.")
            break
        except Exception as e:
            print(f"Error: {e}")
            speak("Hubo un error. Intenta de nuevo.")


# ═══════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    start_voice_loop()
