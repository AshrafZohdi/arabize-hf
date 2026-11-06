"""Speech to text with Whisper small (OpenAI's open weights, MIT, CTranslate2 build Systran/faster-whisper-small) on the
Space's CPU via faster-whisper. Measured on CPU: about 1.5 s for a short question; large-v3-turbo took about 7 s.
The browser sends 16 kHz mono 16-bit WAV, so no audio decoder is needed here."""

from __future__ import annotations

import io
import threading
import wave
from typing import Any

import numpy as np

MODEL = "Systran/faster-whisper-small"
REVISION = "536b0662742c02347bc0e980a01041f333bce120"
MAX_SECONDS = 30


class AudioError(ValueError):
    pass


def read_wav(data: bytes) -> np.ndarray:
    """16 kHz mono 16-bit PCM WAV to float32 in [-1, 1]."""
    try:
        with wave.open(io.BytesIO(data)) as w:
            if w.getnchannels() != 1 or w.getsampwidth() != 2 or w.getframerate() != 16000:
                raise AudioError("send 16 kHz mono 16-bit WAV")
            frames = w.readframes(w.getnframes())
    except (wave.Error, EOFError) as e:
        raise AudioError("not a WAV file") from e
    audio = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    if len(audio) < 1600:
        raise AudioError("too short")
    return audio[: MAX_SECONDS * 16000]


class Whisper:
    def __init__(self, threads: int = 8):  # the Space has 8 vCPUs; 4 threads took about 4.5 s for a short question
        self.threads = threads
        self._model: Any = None
        self._lock = threading.Lock()

    def load(self) -> Any:
        with self._lock:
            if self._model is None:
                from faster_whisper import WhisperModel
                from huggingface_hub import snapshot_download

                path = snapshot_download(MODEL, revision=REVISION)
                self._model = WhisperModel(path, device="cpu", compute_type="int8", cpu_threads=self.threads)
            return self._model

    def transcribe(self, audio: np.ndarray, lang: str | None = None) -> tuple[str, str]:
        segments, info = self.load().transcribe(audio, beam_size=1, language=lang, vad_filter=False, condition_on_previous_text=False)
        return " ".join(s.text.strip() for s in segments).strip(), info.language
