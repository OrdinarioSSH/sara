"""
Analisador de amplitude de áudio para HUD Visualizer — SARA
Extrai envelope de amplitude do PCM raw via pygame.mixer.Sound.get_raw().
Usa apenas stdlib (struct + math), sem numpy.
"""
import struct
import math
from typing import List

from hud_config import AUDIO_FPS, NUM_BARS, AMPLITUDE_NORMALIZE

# Configuração padrão do pygame.mixer: 44100 Hz, 16-bit signed, stereo
SAMPLE_RATE = 44100
BYTES_PER_SAMPLE = 2
NUM_CHANNELS = 2
FRAME_SIZE = BYTES_PER_SAMPLE * NUM_CHANNELS  # 4 bytes por frame


class AudioAmplitudeExtractor:
    """Pré-computa envelope de amplitude do PCM para visualização em barras."""

    def __init__(self, raw_bytes: bytes, fps: int = AUDIO_FPS, num_bars: int = NUM_BARS):
        self.fps = fps
        self.num_bars = num_bars
        self.samples_per_frame = SAMPLE_RATE // fps
        self.envelope: List[List[float]] = []
        self._extract(raw_bytes)

    def _extract(self, raw_bytes: bytes):
        total_frames = len(raw_bytes) // FRAME_SIZE
        window = self.samples_per_frame

        idx = 0
        while idx < total_frames:
            end = min(idx + window, total_frames)
            chunk = raw_bytes[idx * FRAME_SIZE : end * FRAME_SIZE]
            count = len(chunk) // FRAME_SIZE

            if count == 0:
                break

            # Decodifica stereo 16-bit → mono
            mono = []
            for i in range(count):
                off = i * FRAME_SIZE
                left = struct.unpack_from('<h', chunk, off)[0]
                right = struct.unpack_from('<h', chunk, off + 2)[0]
                mono.append((left + right) * 0.5)

            # Divide em sub-bandas e calcula RMS de cada
            bars = []
            band_size = max(1, len(mono) // self.num_bars)
            for b in range(self.num_bars):
                start = b * band_size
                end_b = min(start + band_size, len(mono))
                band = mono[start:end_b]
                if band:
                    rms = math.sqrt(sum(s * s for s in band) / len(band))
                    normalized = min(1.0, rms / AMPLITUDE_NORMALIZE)
                    bars.append(normalized)
                else:
                    bars.append(0.0)

            self.envelope.append(bars)
            idx += window

    def get_frame(self, time_seconds: float) -> List[float]:
        """Retorna amplitudes das barras para um instante de playback."""
        if not self.envelope:
            return [0.0] * self.num_bars
        i = int(time_seconds * self.fps)
        i = max(0, min(i, len(self.envelope) - 1))
        return self.envelope[i]

    @property
    def duration_seconds(self) -> float:
        return len(self.envelope) / self.fps if self.fps > 0 else 0.0
