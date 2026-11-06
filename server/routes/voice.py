"""Text to speech, P1, behind VOICE_ENABLED. ASR is a stub until Whisper is wired.

GET  /api/tts?text=&lang=ar          live Arabic speech (mms-tts-ara on ONNX Runtime), cached
GET  /api/tts/recordings              every recording URL, for preloading in the browser
GET  /api/tts/term/{id}?lang=ar|en   pre-generated term audio from the Storage Bucket (redirect); Arabic falls back
                                     to live speech; English is spoken in the browser with kokoro-js
POST /api/asr                        501 for now (openai/whisper-large-v3-turbo planned)
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from server.llm import RateLimited, RateLimiter
from server.net import client_ip
from server.voice.base import to_wav

router = APIRouter()
tts_limiter = RateLimiter(limit=60, window_s=60)
MAX_TTS_CHARS = 300
AUDIO_CACHE = 512
_cache: OrderedDict[str, bytes] = OrderedDict()


def _enabled(request: Request) -> None:
    if not request.app.state.settings.voice_enabled:
        raise HTTPException(status_code=404, detail="voice is switched off")


def _speak(request: Request, text: str) -> bytes:
    key = hashlib.sha256(text.encode()).hexdigest()
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    wav = to_wav(*request.app.state.tts["ar"].synthesize(text))
    _cache[key] = wav
    if len(_cache) > AUDIO_CACHE:
        _cache.popitem(last=False)
    return wav


def _audio(wav: bytes) -> Response:
    return Response(wav, media_type="audio/wav", headers={"Cache-Control": "public, max-age=86400"})


@router.get("/api/tts")
def tts(request: Request, text: str = Query(min_length=1, max_length=MAX_TTS_CHARS), lang: Literal["ar", "en"] = "ar") -> Any:
    _enabled(request)
    if lang == "en":
        return JSONResponse({"error": "english_in_browser"}, status_code=404)
    try:
        tts_limiter.hit(client_ip(request))
    except RateLimited as e:
        return JSONResponse({"error": "rate_limited", "retry_after": e.retry_after}, status_code=429)
    try:
        return _audio(_speak(request, text))
    except ValueError:
        raise HTTPException(status_code=422, detail="nothing to say") from None


@router.get("/api/tts/recordings")
def recordings(request: Request) -> Any:
    """Every pre-generated recording as {"en/<id>": url, "ar/<id>": url}, so the browser plays and preloads straight
    from the bucket instead of asking the Space for a redirect on each tap."""
    _enabled(request)
    return JSONResponse(request.app.state.audio_manifest, headers={"Cache-Control": "public, max-age=3600"})


@router.get("/api/tts/term/{term_id}")
def tts_term(term_id: str, request: Request, lang: Literal["ar", "en"] = "ar") -> Any:
    _enabled(request)
    manifest: dict[str, str] = request.app.state.audio_manifest
    url = manifest.get(f"{lang}/{term_id}")
    if url:
        return RedirectResponse(url, status_code=302, headers={"Cache-Control": "public, max-age=3600"})
    if lang == "en":
        raise HTTPException(status_code=404, detail="no recording; the browser speaks English")
    g = request.app.state.glossary
    entry = g.entries.get(term_id)
    text = entry["term_msa"] if entry else (request.app.state.termbank.by_id.get(term_id) or {}).get("ar_full")
    if not text:
        raise HTTPException(status_code=404, detail="unknown term")
    try:
        tts_limiter.hit(client_ip(request))
    except RateLimited as e:
        return JSONResponse({"error": "rate_limited", "retry_after": e.retry_after}, status_code=429)
    return _audio(_speak(request, text))


@router.post("/api/asr")
def asr(request: Request) -> Any:
    _enabled(request)
    return JSONResponse({"error": "not_implemented", "planned": "openai/whisper-large-v3-turbo"}, status_code=501)
