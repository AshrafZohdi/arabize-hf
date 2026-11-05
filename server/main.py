"""Darby API and static web app, served together on port 7860 in the Space."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from server.config import Settings, load_settings
from server.llm import LLM

VERSION = "0.1.0"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="Darby", version=VERSION, docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.state.settings = settings
    app.state.llm = LLM(settings)

    @app.get("/api/health")
    def health() -> dict:
        return {
            "status": "ok",
            "version": VERSION,
            "demo_mode": settings.demo_mode,
            "llm": app.state.llm.status(),
            "voice_enabled": settings.voice_enabled,
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


def client_ip(request: Request) -> str:
    """Caller IP for rate limits. uvicorn runs with --proxy-headers, so this is the visitor, not the HF proxy."""
    return request.client.host if request.client else "unknown"


def _cache_headers(path: Path, dist: Path) -> dict[str, str]:
    # Vite puts content-hashed files in assets/, so they can be cached for a year.
    if path.is_relative_to(dist / "assets"):
        return {"Cache-Control": "public, max-age=31536000, immutable"}
    return {"Cache-Control": "no-cache"}


app = create_app()
