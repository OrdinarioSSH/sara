"""
Text-to-speech adapter for SARA.

Default provider: Piper TTS running locally.
Fallback provider: Microsoft Edge TTS, kept as a compatibility option.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
import threading
import uuid

try:
    import edge_tts
except ImportError:
    edge_tts = None

try:
    import pygame
    pygame.mixer.init()
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False
    print("[TTS] pygame not found. Install it with: pip install pygame")


EDGE_VOICES = {
    "francisca": "pt-BR-FranciscaNeural",
    "antonio": "pt-BR-AntonioNeural",
    "thalita": "pt-BR-ThalitaNeural",
    "macerio": "pt-BR-MacerioNeural",
    "leila": "pt-BR-LeilaNeural",
    "donato": "pt-BR-DonatoNeural",
}

PIPER_VOICES = {
    "piper": "local",
}


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _normalize_edge_voice(voice: str | None) -> str:
    if not voice:
        return EDGE_VOICES["francisca"]

    voice = voice.strip()
    if voice in EDGE_VOICES.values():
        return voice

    return EDGE_VOICES.get(voice.lower(), EDGE_VOICES["francisca"])


def synthesize_to_file(
    text: str,
    output_file: str,
    voice: str | None = None,
    rate: str = "+0%",
    provider: str | None = None,
) -> str:
    """
    Generate speech into output_file and return the path.

    TTS_PROVIDER defaults to piper. If Piper is not configured or fails,
    Edge TTS is used as a fallback so the assistant can still speak.
    """
    provider = (provider or _env("TTS_PROVIDER", "piper")).lower()

    if provider == "edge":
        _synthesize_edge(text, output_file, voice, rate)
        return output_file

    try:
        _synthesize_piper(text, output_file)
        return output_file
    except Exception as exc:
        print(f"[TTS] Piper TTS failed, falling back to Edge TTS: {exc}")
        _synthesize_edge(text, output_file, voice, rate)
        return output_file


def _synthesize_piper(text: str, output_file: str) -> None:
    model_path = _env("PIPER_TTS_MODEL")
    if not model_path:
        raise RuntimeError("PIPER_TTS_MODEL is not configured")

    command = _env("PIPER_TTS_COMMAND", "piper")
    config_path = _env("PIPER_TTS_CONFIG")

    args = [
        command,
        "--model",
        model_path,
        "--output_file",
        output_file,
    ]

    if config_path:
        args.extend(["--config", config_path])

    result = subprocess.run(
        args,
        input=text,
        text=True,
        capture_output=True,
        timeout=120,
    )

    if result.returncode != 0:
        error = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        raise RuntimeError(error)

    if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
        raise RuntimeError("Piper did not create an audio file")


def _synthesize_edge(text: str, output_file: str, voice: str | None = None, rate: str = "+0%") -> None:
    if edge_tts is None:
        raise RuntimeError("edge-tts is not installed")

    async def _run() -> None:
        communicate = edge_tts.Communicate(
            text=text,
            voice=_normalize_edge_voice(voice),
            rate=rate,
        )
        await communicate.save(output_file)

    asyncio.run(_run())


class TextToSpeech:
    VOICES = {**PIPER_VOICES, **EDGE_VOICES}

    def __init__(
        self,
        voice: str = "piper",
        rate: str = "+0%",
        volume: str = "+0%",
        provider: str | None = None,
    ):
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.provider = provider or _env("TTS_PROVIDER", "piper")
        self._lock = threading.Lock()
        self.temp_dir = tempfile.gettempdir()

        print(f"[TTS] Provider: {self.provider}; voice: {self.voice}")

    def speak(self, text: str, block: bool = True):
        if block:
            self._speak_sync(text)
        else:
            threading.Thread(target=self._speak_sync, args=(text,), daemon=True).start()

    def _speak_sync(self, text: str):
        with self._lock:
            temp_file = os.path.join(self.temp_dir, f"sara_speech_{uuid.uuid4().hex[:8]}.wav")
            try:
                synthesize_to_file(
                    text=text,
                    output_file=temp_file,
                    voice=self.voice,
                    rate=self.rate,
                    provider=self.provider,
                )
                self._play_audio(temp_file)
            except Exception as exc:
                print(f"[TTS] Error: {exc}")
            finally:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except OSError:
                    pass

    def _play_audio(self, file_path: str):
        if HAS_PYGAME:
            try:
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(100)
                pygame.mixer.music.unload()
                return
            except Exception as exc:
                print(f"[TTS] pygame playback failed: {exc}")
                try:
                    pygame.mixer.music.unload()
                except Exception:
                    pass

        try:
            if os.name == "nt":
                import subprocess as _subprocess
                _subprocess.run(
                    ["powershell", "-c", f'(New-Object Media.SoundPlayer "{file_path}").PlaySync()'],
                    capture_output=True,
                    timeout=30,
                )
            else:
                os.system(f'aplay "{file_path}" 2>/dev/null || afplay "{file_path}" 2>/dev/null')
        except Exception:
            print("[TTS] Could not play audio")

    def set_voice(self, voice: str):
        self.voice = voice
        print(f"[TTS] Voice changed: {self.voice}")

    def set_rate(self, rate: str):
        self.rate = rate

    def set_volume(self, volume: str):
        self.volume = volume

    @classmethod
    def list_voices(cls) -> dict:
        return cls.VOICES


def quick_speak(text: str, voice: str = "piper"):
    tts = TextToSpeech(voice=voice)
    tts.speak(text)


if __name__ == "__main__":
    print("Testing TTS...")
    print(f"Available voices: {TextToSpeech.list_voices()}")
    quick_speak("SARA operational.")
