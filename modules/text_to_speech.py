"""
Text-to-speech adapter for SARA.

Default provider: Qwen TTS through Alibaba Cloud Model Studio / DashScope.
Fallback provider: Microsoft Edge TTS, kept as a local compatibility option.
"""
from __future__ import annotations

import asyncio
import os
import tempfile
import threading
import urllib.request
import uuid
from pathlib import Path
from typing import Any

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

QWEN_VOICES = {
    "cherry": "Cherry",
    "seren": "Seren",
    "mia": "Mia",
    "stella": "Stella",
    "neil": "Neil",
    "kai": "Kai",
    "ryan": "Ryan",
    "andre": "Andre",
}


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _get_nested(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(key)
        else:
            current = getattr(current, key, None)
    return current


def _normalize_qwen_voice(voice: str | None) -> str:
    if not voice:
        return _env("QWEN_TTS_VOICE", "Cherry")

    voice = voice.strip()
    if voice in QWEN_VOICES.values():
        return voice

    return QWEN_VOICES.get(voice.lower(), _env("QWEN_TTS_VOICE", "Cherry"))


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

    The default provider is controlled by TTS_PROVIDER and defaults to qwen.
    If Qwen fails or is not configured, Edge TTS is used as a fallback.
    """
    provider = (provider or _env("TTS_PROVIDER", "qwen")).lower()

    if provider == "edge":
        _synthesize_edge(text, output_file, voice, rate)
        return output_file

    try:
        _synthesize_qwen(text, output_file, voice)
        return output_file
    except Exception as exc:
        print(f"[TTS] Qwen TTS failed, falling back to Edge TTS: {exc}")
        _synthesize_edge(text, output_file, voice, rate)
        return output_file


def _synthesize_qwen(text: str, output_file: str, voice: str | None = None) -> None:
    api_key = _env("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is not configured")

    try:
        import dashscope
    except ImportError as exc:
        raise RuntimeError("dashscope SDK is not installed") from exc

    dashscope.base_http_api_url = _env(
        "DASHSCOPE_BASE_URL",
        "https://dashscope-intl.aliyuncs.com/api/v1",
    )

    response = dashscope.MultiModalConversation.call(
        model=_env("QWEN_TTS_MODEL", "qwen3-tts-flash"),
        api_key=api_key,
        text=text,
        voice=_normalize_qwen_voice(voice),
        language_type=_env("QWEN_TTS_LANGUAGE_TYPE", "Portuguese"),
        stream=False,
    )

    audio_url = _get_nested(response, "output", "audio", "url")
    if not audio_url:
        code = _get_nested(response, "code") or _get_nested(response, "status_code")
        message = _get_nested(response, "message") or response
        raise RuntimeError(f"Qwen response did not include an audio URL: {code} {message}")

    with urllib.request.urlopen(audio_url, timeout=60) as remote:
        Path(output_file).write_bytes(remote.read())


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
    VOICES = {**QWEN_VOICES, **EDGE_VOICES}

    def __init__(
        self,
        voice: str = "Cherry",
        rate: str = "+0%",
        volume: str = "+0%",
        provider: str | None = None,
    ):
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.provider = provider or _env("TTS_PROVIDER", "qwen")
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
            temp_file = os.path.join(self.temp_dir, f"sara_speech_{uuid.uuid4().hex[:8]}.mp3")
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
                import subprocess
                subprocess.run(
                    ["powershell", "-c", f'(New-Object Media.SoundPlayer "{file_path}").PlaySync()'],
                    capture_output=True,
                    timeout=30,
                )
            else:
                os.system(f'mpg123 "{file_path}" 2>/dev/null || afplay "{file_path}" 2>/dev/null')
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


def quick_speak(text: str, voice: str = "Cherry"):
    tts = TextToSpeech(voice=voice)
    tts.speak(text)


if __name__ == "__main__":
    print("Testing TTS...")
    print(f"Available voices: {TextToSpeech.list_voices()}")
    quick_speak("SARA operational.")
