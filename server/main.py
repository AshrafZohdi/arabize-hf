"""Darby API and static web app, served together on port 7860 in the Space."""

import logging
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from server.config import Settings, load_settings
from server.glossary import load_glossary
from server.llm import LLM
from server.routes import explain, glossary
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
    app.state.lessons, app.state.lessons_source = load_lessons(settings.content_dir, from_hub=False)
    if settings.termbank_source == "hub":
        threading.Thread(target=_load_bank, args=(app, settings), daemon=True, name="termbank").start()
    app.include_router(explain.router)
    app.include_router(glossary.router)

    @app.get("/api/health")
    def health() -> dict:
        return {
            "status": "ok",
            "version": VERSION,
            "demo_mode": settings.demo_mode,
            "llm": app.state.llm.status(),
            "voice_enabled": settings.voice_enabled,
            "termbank": {k: v for k, v in app.state.termbank.status.items()},
            "semantic_search": app.state.embedder is not None and app.state.termbank.vectors is not None,
            "lessons": {"count": len(app.state.lessons), "source": app.state.lessons_source},
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
    try:
        app.state.lessons, app.state.lessons_source = load_lessons(settings.content_dir, from_hub=True, token=settings.hf_token)
    except Exception as e:
        logging.getLogger("darby").error("lessons load failed: %s", type(e).__name__)
    try:
        tb = load_term_bank(settings.content_dir, settings.hf_token)
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
