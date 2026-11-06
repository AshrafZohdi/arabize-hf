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


def test_asr_is_a_stub(tmp_path):
    c, _ = client(tmp_path)
    assert c.post("/api/asr").status_code == 501
