"""Smart Explain (P0-1) and the term finder API.

POST /api/terms    deterministic term matches for highlighting, no AI.
POST /api/explain  Server-Sent Events:
    terms        {matches, cards}    straight away, from the glossary
    explanation  {text}              pieces of the explanation as Fanar writes it
    result       {explanation, question, cards, source, fallback}
Nothing the learner pastes is stored or logged.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from server.glossary import Glossary
from server.termbank import TermBank
from server.net import client_ip
from server.llm import LLM, MAX_INPUT_CHARS, LLMBadOutput, LLMUnavailable, RateLimited, ai_rate_limiter
from server.prompts.explain import ExplainLang, ExplainResult, ExplainStyle, build_explain_prompt

log = logging.getLogger("darby.explain")
router = APIRouter()

EXPLAIN_MAX_TOKENS = 700


class TermsIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)


class ExplainIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)
    lang: ExplainLang = "gulf"
    style: ExplainStyle = "work"


def _matches(termbank: TermBank, text: str) -> list[dict[str, Any]]:
    return [
        {"start": m.start, "end": m.end, "text": m.text, "id": m.term.id, "en": m.term.en, "ar": m.term.ar, "has_card": m.term.has_card}
        for m in termbank.finder.find(text)
    ]


@router.post("/api/terms")
def find_terms(body: TermsIn, request: Request) -> dict[str, Any]:
    return {"matches": _matches(request.app.state.termbank, body.text)}


QUESTION_TEMPLATE = {
    "en": "Which term means: {d}",
    "msa": "أي مصطلح يعني: {d}",
    "gulf": "أي مصطلح معناه: {d}",
}
WHY_TEMPLATE = {
    "en": "{t} is the term for this.",
    "msa": "هذا هو معنى {t}.",
    "gulf": "هذا بالضبط معنى {t}.",
}


def glossary_question(glossary: Glossary, card: dict[str, Any], lang: str, seed: str) -> dict[str, Any]:
    """A practice question built from the glossary alone, for when Fanar is not available."""
    rng = random.Random(hashlib.sha256(seed.encode()).hexdigest())
    others = sorted(e["term_en"] for k, e in glossary.entries.items() if k != card["id"] and e.get("domain") == "ai")
    options = rng.sample(others, 3) + [card["term_en"]]
    rng.shuffle(options)
    return {
        "question": QUESTION_TEMPLATE[lang].format(d=card["explanation"]),
        "options": options,
        "correct_index": options.index(card["term_en"]),
        "why": WHY_TEMPLATE[lang].format(t=card["term_en"]),
    }


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/api/explain")
async def explain(body: ExplainIn, request: Request) -> Any:
    try:
        ai_rate_limiter.hit(client_ip(request))
    except RateLimited as e:
        return JSONResponse({"error": "rate_limited", "retry_after": e.retry_after}, status_code=429, headers={"Retry-After": str(e.retry_after)})

    glossary: Glossary = request.app.state.glossary
    llm: LLM = request.app.state.llm
    matches = _matches(request.app.state.termbank, body.text)
    seen: list[str] = []
    for m in matches:
        if m["has_card"] and m["id"] not in seen:
            seen.append(m["id"])
    # The glossary file is ordered by the team, AI terms first, so its order is the importance order.
    order = list(glossary.entries)
    seen.sort(key=order.index)
    cards = [c for c in (glossary.card(i, body.lang) for i in seen) if c]

    async def events() -> AsyncIterator[str]:
        yield _sse("terms", {"matches": matches, "cards": cards})

        def fallback(reason: str) -> dict[str, Any]:
            question = glossary_question(glossary, cards[0], body.lang, body.text) if cards else None
            return {"explanation": None, "question": question, "cards": [], "source": "glossary", "fallback": reason}

        # Terms with a Darby card first (no cards wanted for them), then other bank terms for their standard Arabic.
        hints = [(c["term_en"], c["term_ar"]) for c in cards]
        hints += [(m["en"], m["ar"]) for m in matches if not m["has_card"] and (m["en"], m["ar"]) not in hints]
        system, user = build_explain_prompt(body.text, body.lang, body.style, hints, carded=len(cards))
        try:
            async for ev in llm.json_stream(
                feature="explain",
                system=system,
                user=user,
                schema=ExplainResult,
                stream_field="explanation",
                max_tokens=EXPLAIN_MAX_TOKENS,
                fixture_input={"text": body.text, "lang": body.lang, "style": body.style},
            ):
                if ev.kind == "partial":
                    yield _sse("explanation", {"text": ev.text})
                elif ev.result is not None:
                    r: ExplainResult = ev.result.data
                    # Fanar cards only for highlighted terms without a Darby card, so every card has a highlight in the text.
                    open_terms = {k for m in matches if not m["has_card"] for k in (m["en"].lower(), m["text"].lower())}
                    model_cards = [
                        {**c.model_dump(), "id": None, "source": "fanar"} for c in r.cards if c.term_en.lower() in open_terms
                    ]
                    yield _sse(
                        "result",
                        {
                            "off_topic": r.off_topic,
                            "explanation": r.explanation,
                            "question": r.question.model_dump() if r.question else None,
                            "cards": model_cards,
                            "source": ev.result.source,
                            "fallback": None,
                        },
                    )
        except LLMUnavailable as e:
            yield _sse("result", fallback(e.state))
        except LLMBadOutput:
            yield _sse("result", fallback("bad_output"))
        except Exception as e:
            # Log the error type only: tracebacks and messages can carry the learner's text.
            log.error("explain failed: %s", type(e).__name__)
            yield _sse("result", fallback("error"))

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

