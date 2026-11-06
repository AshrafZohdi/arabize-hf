import io
import wave
from dataclasses import replace

import numpy as np
import pytest
from fastapi.testclient import TestClient

from server.config import load_settings
from server.main import create_app
from server.voice.base import to_wav
from server.voice.mms import MmsArabic, prepare


class FakeTTS:
    lang, name = "ar", "fake"

    def __init__(self):
        self.calls = []

    def synthesize(self, text):
        self.calls.append(text)
        return np.zeros(1600, dtype=np.float32), 16000


def client(tmp_path, voice=True):
    app = create_app(replace(load_settings(), web_dist=tmp_path, termbank_source="off", voice_enabled=voice))
    app.state.tts = {"ar": FakeTTS()}
    return TestClient(app), app


def test_prepare_keeps_arabic_only():
    assert prepare("الهلوسة (hallucination) 2026") == "الهلوسة"


def test_wav_header():
    with wave.open(io.BytesIO(to_wav(np.zeros(800, dtype=np.float32), 16000))) as w:
        assert (w.getframerate(), w.getnchannels(), w.getnframes()) == (16000, 1, 800)


def test_tokenizer_adds_blanks_and_drops_unknown_characters():
    m = MmsArabic()
    m.__dict__["_vocab"] = {"ا": 0, "ب": 28, " ": 25}  # cached_property stand-in, no download
    assert m.token_ids("بَاب x") == [0, 28, 0, 0, 0, 28, 0]


def test_voice_off_means_404(tmp_path):
    c, _ = client(tmp_path, voice=False)
    assert c.get("/api/tts", params={"text": "مرحبا"}).status_code == 404
    assert c.get("/api/tts/term/hallucination").status_code == 404


def test_live_arabic_and_cache(tmp_path):
    c, app = client(tmp_path)
    r = c.get("/api/tts", params={"text": "مرحبا بك"})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/wav" and r.content[:4] == b"RIFF"
    c.get("/api/tts", params={"text": "مرحبا بك"})
    assert app.state.tts["ar"].calls == ["مرحبا بك"]  # second call served from cache
    assert c.get("/api/tts", params={"text": "hi", "lang": "en"}).status_code == 404


def test_term_audio_redirects_to_the_bucket_or_speaks_arabic(tmp_path):
    c, app = client(tmp_path)
    app.state.audio_manifest = {"en/hallucination": "https://huggingface.co/buckets/x/y/resolve/audio/en/hallucination.wav"}
    r = c.get("/api/tts/term/hallucination", params={"lang": "en"}, follow_redirects=False)
    assert r.status_code == 302 and "buckets" in r.headers["location"]
    r = c.get("/api/tts/term/hallucination", params={"lang": "ar"})
    assert r.status_code == 200 and app.state.tts["ar"].calls[-1] == "الهلوسة"
    assert c.get("/api/tts/term/prompt", params={"lang": "en"}).status_code == 404


def test_recordings_list_for_preloading(tmp_path):
    c, app = client(tmp_path)
    app.state.audio_manifest = {"ar/prompt": "https://huggingface.co/buckets/x/y/resolve/audio/ar/prompt.wav"}
    r = c.get("/api/tts/recordings")
    assert r.status_code == 200 and r.json() == app.state.audio_manifest
    c2, _ = client(tmp_path, voice=False)
    assert c2.get("/api/tts/recordings").status_code == 404


def wav(seconds=1.0, rate=16000, channels=1):
    import io
    import wave

    import numpy as np

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.sin(np.arange(int(seconds * rate)) / 20) * 8000).astype("<i2").tobytes() * channels)
    return buf.getvalue()


class FakeWhisper:
    def __init__(self):
        self.calls = []

    def transcribe(self, audio, lang=None):
        self.calls.append((len(audio), lang))
        return "شنو يعني الهلوسة؟", "ar"


def test_read_wav_accepts_only_16k_mono_pcm():
    import pytest

    from server.voice.asr import AudioError, read_wav

    assert len(read_wav(wav(1.0))) == 16000
    assert len(read_wav(wav(40.0))) == 30 * 16000  # cut at 30 s
    for bad in (wav(1.0, rate=44100), wav(1.0, channels=2), b"not audio", wav(0.05)):
        with pytest.raises(AudioError):
            read_wav(bad)


def test_asr_transcribes_and_is_off_by_default(tmp_path):
    c, app = client(tmp_path)
    assert c.post("/api/asr", content=wav()).status_code == 404  # ASR_ENABLED is off
    assert c.get("/api/health").json()["asr"] is False
    app.state.asr = FakeWhisper()
    r = c.post("/api/asr", params={"lang": "ar"}, content=wav(2.0), headers={"content-type": "audio/wav"})
    assert r.status_code == 200 and r.json() == {"text": "شنو يعني الهلوسة؟", "language": "ar"}
    assert app.state.asr.calls == [(32000, "ar")]
    assert c.post("/api/asr", content=b"nope").status_code == 422

