from __future__ import annotations

import io
import wave
from typing import Protocol

import numpy as np


class TTSProvider(Protocol):
    lang: str
    name: str

    def synthesize(self, text: str) -> tuple[np.ndarray, int]:
        """Waveform in [-1, 1] and its sample rate."""
        ...


def to_wav(waveform: np.ndarray, rate: int) -> bytes:
    pcm = (np.clip(waveform, -1.0, 1.0) * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()
