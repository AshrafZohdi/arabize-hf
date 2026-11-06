"""Darby API and static web app, served together on port 7860 in the Space."""

import logging
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from server.config import Settings, load_settings
from server.glossary import load_glossary, load_glossary_from_hub
from server.llm import LLM
from server.game import Game
from server.routes import explain, game, glossary, lessons, tutor, voice
from server.lessons import load_lessons
from server.termbank import TermBank, load_term_bank

VERSION = "0.1.0"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="Darby", version=VERSION, docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.state.settings = settings
    app.state.llm = LLM(settings)
    app.state.glossary = load_glossary(settings.content_dir)
    # Our glossary straight away; the full bank replaces it when the background load finishes.
    app.state.termbank = TermBank.from_rows(_glossary_rows(app.state.glossary), {"steps": {"sources": "loading"}})
    app.state.embedder = None
    app.state.audio_manifest = {}
    if settings.voice_enabled:
        from server.voice.mms import MmsArabic

        app.state.tts = {"ar": MmsArabic()}
    app.state.lessons, app.state.lessons_source = load_lessons(settings.content_dir, from_hub=False)
    # The daily word comes from our own glossary in content/, which never changes while the app runs.
    app.state.game = Game(load_glossary(settings.content_dir), settings.content_dir, _game_secret(settings))
    if settings.termbank_source == "hub":
        threading.Thread(target=_load_bank, args=(app, settings), daemon=True, name="termbank").start()
    app.include_router(explain.router)
    app.include_router(glossary.router)
    app.include_router(tutor.router)
    app.include_router(lessons.router)
    app.include_router(game.router)
    app.include_router(voice.router)

    @app.get("/api/health")
    def health() -> dict:
        return {
            "status": "ok",
            "version": VERSION,
            "demo_mode": settings.demo_mode,
            "llm": app.state.llm.status(),
            "voice_enabled": settings.voice_enabled,
            "voice_recordings": len(app.state.audio_manifest),
            "termbank": {k: v for k, v in app.state.termbank.status.items()},
            "semantic_search": app.state.embedder is not None and app.state.termbank.vectors is not None,
            "lessons": {"count": len(app.state.lessons), "source": app.state.lessons_source},
            "glossary_cards": len(app.state.glossary.entries),
        }

    @app.get("/api/{rest:path}", include_in_schema=False)
    def api_not_found(rest: str) -> None:
        raise HTTPException(status_code=404, detail="not found")

    dist = settings.web_dist.resolve()

    @app.get("/{rest:path}", include_in_schema=False)
    def spa(rest: str) -> FileResponse:
        # Real files (assets, favicon) are served as is; every other path gets the SPA shell.
        if rest:
            candidate = (dist / rest).resolve()
            if candidate.is_file() and candidate.is_relative_to(dist):
                return FileResponse(candidate, headers=_cache_headers(candidate, dist))
        index = dist / "index.html"
        if not index.is_file():
            raise HTTPException(status_code=503, detail="web app not built")
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    return app


def load_audio_manifest(bucket: str | None) -> dict[str, str]:
    """Pre-generated term audio in the public Storage Bucket: {"ar/<id>": url, "en/<id>": url}."""
    if not bucket:
        return {}
    import json
    import urllib.request

    base = f"https://huggingface.co/buckets/{bucket}/resolve"
    out: dict[str, str] = {}
    for lang in ("ar", "en"):  # one manifest per pre-generation Job
        try:
            with urllib.request.urlopen(f"{base}/audio/manifest-{lang}.json", timeout=20) as r:  # follows the CDN redirect
                out |= {k: f"{base}/audio/{v}" for k, v in json.loads(r.read())["files"].items()}
        except Exception as e:
            logging.getLogger("darby").warning("audio manifest %s: %s", lang, type(e).__name__)
    return out


def _game_secret(settings: Settings) -> bytes:
    """Signs daily code state. DARBY_GAME_SECRET if set; otherwise derived from the HF token (stable across restarts);
    otherwise random, which only means games in progress restart when the Space restarts."""
    import hashlib
    import os
    import secrets

    if os.getenv("DARBY_GAME_SECRET"):
        return os.environ["DARBY_GAME_SECRET"].encode()
    if settings.hf_token:
        return hashlib.sha256(b"darby-daily-code:" + settings.hf_token.encode()).digest()
    return secrets.token_bytes(32)


def _glossary_rows(g) -> list[dict]:
    return [
        {
            "id": k, "en": e["term_en"], "en_key": e["term_en"].lower(), "en_expanded": None, "is_acronym": False,
            "ar_display": e["term_msa"], "ar_full": e["term_msa"], "ar_key": e["term_msa"], "ar_origin": "darby_editor",
            "reviewed": False, "needs_review": False, "domain": "ai" if e.get("domain") == "ai" else "software",
            "source_names": ["darby"], "has_full_card": True, "highlight": True,
        }
        for k, e in g.entries.items()
    ]


def _load_bank(app: FastAPI, settings: Settings) -> None:
    if settings.voice_enabled:
        try:
            app.state.audio_manifest = load_audio_manifest(settings.hf_bucket)
            app.state.tts["ar"].synthesize("مرحبا")  # load the model now, not on the first listen
        except Exception as e:
            logging.getLogger("darby").warning("voice warm-up: %s", type(e).__name__)
    try:
        app.state.lessons, app.state.lessons_source = load_lessons(settings.content_dir, from_hub=True, token=settings.hf_token)
    except Exception as e:
        logging.getLogger("darby").error("lessons load failed: %s", type(e).__name__)
    try:
        app.state.glossary = load_glossary_from_hub(settings.hf_token)
    except Exception as e:
        logging.getLogger("darby").warning("glossary from the Hub failed (%s), keeping content/", type(e).__name__)
    try:
        tb = load_term_bank(settings.content_dir, settings.hf_token, full_card_ids=set(app.state.glossary.entries))
        app.state.termbank = tb
        if tb.vectors is not None:
            from server.embed import E5

            e5 = E5(threads=4)
            g = app.state.glossary
            texts = {k: "; ".join([e["term_en"], e["term_msa"], e["def_en"], e["def_ar"]]) for k, e in g.entries.items()}
            n = tb.enrich_cards(e5, texts)  # also downloads and loads the model now, not on the first search
            tb.status["steps"]["card_vectors"] = f"ok ({n})"
            app.state.embedder = e5
    except Exception as e:
        logging.getLogger("darby").error("term bank load failed: %s", type(e).__name__)


def _cache_headers(path: Path, dist: Path) -> dict[str, str]:
    # Vite puts content-hashed files in assets/, so they can be cached for a year.
    if path.is_relative_to(dist / "assets"):
        return {"Cache-Control": "public, max-age=31536000, immutable"}
    return {"Cache-Control": "no-cache"}


app = create_app()
