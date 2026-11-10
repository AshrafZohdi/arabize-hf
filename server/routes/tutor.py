"""Tutor (streamed), prompt lab and translate.

POST /api/tutor            Server-Sent Events: token {text} ... then done {}, or unavailable {state}
GET  /api/prompt-lab/{slug} the lesson's work task
POST /api/prompt-lab       scores for goal, context, format, constraints, feedback and an improved prompt
Nothing the learner writes is stored or logged.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from server.llm import LLM, MAX_INPUT_CHARS, LLMBadOutput, LLMUnavailable, RateLimited, ai_rate_limiter
from server.net import client_ip
from server.prompts.translate import Target, Translation, build_translate_prompt
from server.prompts.prompt_lab import CRITERIA, PromptScore, build_scoring_prompt
from server.prompts.tutor import build_messages, build_tutor_system

log = logging.getLogger("darby.tutor")
router = APIRouter()
Lang = Literal["en", "msa", "gulf"]

class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)


class TutorIn(BaseModel):
    messages: list[Turn] = Field(min_length=1, max_length=200)
    lang: Lang = "gulf"
    lesson: str | None = Field(None, max_length=40)


def _lesson(request: Request, slug: str | None) -> dict[str, Any] | None:
    return next((d for d in request.app.state.lessons if d["slug"] == slug), None) if slug else None


def _terms(request: Request, lesson: dict[str, Any] | None, text: str, lang: str) -> list[tuple[str, str, str]]:
    """Glossary cards for the lesson's key terms and for terms in the learner's message."""
    g = request.app.state.glossary
    ids: list[str] = []
    for b in (lesson or {}).get("blocks", []):
        for t in b.get("terms", []) if b.get("type") == "key_terms" else []:
            ids.append(t.lower().replace(" ", "-"))
    ids += [m.term.id for m in g.finder.find(text)]
    out = []
    for i in dict.fromkeys(ids):
        c = g.card(i, lang)
        if c:
            out.append((c["term_en"], c["term_ar"], c["explanation"]))
    return out


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/api/tutor")
async def tutor(body: TutorIn, request: Request) -> Any:
    if body.messages[-1].role != "user":
        raise HTTPException(status_code=422, detail="the last message must be the learner's")
    ip = client_ip(request)
    try:
        ai_rate_limiter.hit(ip)
    except RateLimited as e:
        return JSONResponse({"error": "rate_limited", "retry_after": e.retry_after}, status_code=429, headers={"Retry-After": str(e.retry_after)})

    llm: LLM = request.app.state.llm
    lesson = _lesson(request, body.lesson)
    question = body.messages[-1].content
    system = build_tutor_system(lesson, body.lang, _terms(request, lesson, question, body.lang))
    messages = build_messages([m.model_dump() for m in body.messages], body.lang)

    async def events() -> AsyncIterator[str]:
        try:
            async for piece in llm.stream(feature="tutor", system=system, messages=messages):
                yield _sse("token", {"text": piece})
            yield _sse("done", {})
        except LLMUnavailable as e:
            yield _sse("unavailable", {"state": e.state})
        except Exception as e:
            log.error("tutor failed: %s", type(e).__name__)
            yield _sse("unavailable", {"state": "error"})

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _task(lesson: dict[str, Any], lang: str) -> dict[str, Any]:
    cfg = next((b["config"] for b in lesson["blocks"] if b["type"] == "prompt_lab"), None)
    if not cfg:
        raise HTTPException(status_code=404, detail="no prompt lab in this lesson")
    text = cfg.get(f"task_{'en' if lang == 'en' else 'gulf' if lang == 'gulf' else 'ar'}") or cfg.get("task_ar") or cfg["task_en"]
    return {"task": text, "task_en": cfg["task_en"], "rubric": cfg.get("rubric"), "example_good": cfg.get("example_good")}


@router.get("/api/prompt-lab/{slug}")
def prompt_lab_task(slug: str, request: Request, lang: Lang = "gulf") -> dict[str, Any]:
    lesson = _lesson(request, slug)
    if lesson is None:
        raise HTTPException(status_code=404, detail="unknown lesson")
    t = _task(lesson, lang)
    return {"slug": slug, "title": lesson["title"], "task": t["task"]}


class PromptLabIn(BaseModel):
    lesson: str = Field(max_length=40)
    prompt: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)
    lang: Lang = "gulf"


@router.post("/api/prompt-lab")
async def prompt_lab(body: PromptLabIn, request: Request) -> Any:
    try:
        ai_rate_limiter.hit(client_ip(request))
    except RateLimited as e:
        return JSONResponse({"error": "rate_limited", "retry_after": e.retry_after}, status_code=429, headers={"Retry-After": str(e.retry_after)})
    lesson = _lesson(request, body.lesson)
    if lesson is None:
        raise HTTPException(status_code=404, detail="unknown lesson")
    t = _task(lesson, body.lang)
    system, user = build_scoring_prompt(t["task_en"], body.prompt, body.lang, t["rubric"], t["example_good"])
    llm: LLM = request.app.state.llm
    try:
        res = await llm.json(feature="prompt_lab", system=system, user=user, schema=PromptScore)
    except LLMUnavailable as e:
        return JSONResponse({"error": "unavailable", "state": e.state}, status_code=503)
    except LLMBadOutput:
        return JSONResponse({"error": "bad_output"}, status_code=502)
    s: PromptScore = res.data
    return {"scores": {c: getattr(s, c).model_dump() for c in CRITERIA}, "total": s.total, "summary": s.summary, "improved_prompt": s.improved_prompt, "source": res.source}


class TranslateIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)
    target: Target = "gulf"


@router.post("/api/translate")
async def translate(body: TranslateIn, request: Request) -> Any:
    """A tutor reply, term card or improved prompt in the other language."""
    try:
        ai_rate_limiter.hit(client_ip(request))
    except RateLimited as e:
        return JSONResponse({"error": "rate_limited", "retry_after": e.retry_after}, status_code=429, headers={"Retry-After": str(e.retry_after)})
    system, user = build_translate_prompt(body.text, body.target)
    llm: LLM = request.app.state.llm
    try:
        res = await llm.json(feature="translate", system=system, user=user, schema=Translation)
    except LLMUnavailable as e:
        return JSONResponse({"error": "unavailable", "state": e.state}, status_code=503)
    except LLMBadOutput:
        return JSONResponse({"error": "bad_output"}, status_code=502)
    return {"translation": res.data.translation, "target": body.target, "source": res.source}
