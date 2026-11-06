"""Daily code API. GET /api/daily-code?lang= starts today's game; POST /api/daily-code/guess marks one guess.
Neither returns the answer until the signed game state shows a win or 6 used tries (server/game.py)."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from server.game import qatar_today
from server.llm import RateLimited, RateLimiter
from server.net import client_ip

router = APIRouter()
guess_limiter = RateLimiter(limit=60, window_s=60)
STATUS = {"bad_token": 400, "invalid": 400, "finished": 409}


@router.get("/api/daily-code")
def start(request: Request, lang: Literal["en", "ar"] = Query("en")) -> dict[str, Any]:
    return request.app.state.game.start(lang, qatar_today())


class GuessIn(BaseModel):
    lang: Literal["en", "ar"]
    token: str = Field(max_length=2000)
    guess: str = Field(min_length=1, max_length=20)


@router.post("/api/daily-code/guess")
def guess(body: GuessIn, request: Request) -> Any:
    try:
        guess_limiter.hit(client_ip(request))
    except RateLimited as e:
        return JSONResponse({"error": "rate_limited", "retry_after": e.retry_after}, status_code=429)
    out = request.app.state.game.guess(body.lang, qatar_today(), body.token, body.guess)
    if "error" in out:
        return JSONResponse(out, status_code=STATUS[out["error"]])
    return out
