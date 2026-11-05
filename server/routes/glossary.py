"""Glossary (P0-2): full Darby cards and quick cards from the term bank, search in English and Arabic.

GET /api/glossary/cards?lang=     every full card (browse view)
GET /api/glossary/search?q=&domain=&limit=
GET /api/glossary/term/{id}?lang= one term: full card when there is one, else a quick card
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request

from server.termbank import TermBank

router = APIRouter()
# e5 similarities sit high (0.75 to 0.9 for unrelated short terms), so only strong meaning matches are shown.
MEANING_MIN = 0.88
Lang = Literal["en", "msa", "gulf"]
SOURCE_LABEL = {"darby_editor": "darby", "human_gist": "gist", "human_ms": "microsoft", "fanar_generated": "fanar"}


def quick_card(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": r["id"],
        "en": r["en"],
        "ar": r["ar_display"],
        "en_expanded": r.get("en_expanded"),
        "domain": r["domain"],
        "source": SOURCE_LABEL.get(r["ar_origin"], r["ar_origin"]),
        "reviewed": bool(r["reviewed"]),
        "needs_review": bool(r["needs_review"]),
        "has_full_card": bool(r["has_full_card"]),
    }


@router.get("/api/glossary/cards")
def cards(request: Request, lang: Lang = "gulf") -> dict[str, Any]:
    g = request.app.state.glossary
    return {"cards": [g.card(i, lang) | {"domain": g.entries[i]["domain"]} for i in g.entries]}


@router.get("/api/glossary/search")
def search(
    request: Request,
    q: str = Query("", max_length=100),
    domain: Literal["all", "ai", "software"] = "all",
    limit: int = Query(20, ge=1, le=50),
) -> dict[str, Any]:
    tb: TermBank = request.app.state.termbank
    lexical = tb.lexical(q, limit=limit * 3)
    semantic: list[tuple[float, int]] = []
    cards_by_meaning: list[tuple[float, int]] = []
    embedder = getattr(request.app.state, "embedder", None)
    if q.strip() and tb.vectors is not None and embedder is not None:
        qv = embedder.encode([q.strip()])[0]
        # With an exact word match the learner found the term; only clearly related cards are worth adding.
        exact = any(s >= 2.5 for s, _ in lexical)  # exact match after the source penalty
        cards_by_meaning = tb.card_semantic(qv, minimum=0.85 if exact else 0.80)
        semantic = tb.semantic(qv, limit=limit * 3)
    word_hits = {i for _, i in lexical}
    seen: set[int] = set()
    out: list[dict[str, Any]] = []
    # Exact and prefix word matches, then the closest Darby cards by meaning, then strong meaning matches from the
    # whole bank, then substring matches.
    ordered = (
        [i for s, i in lexical if s >= 1.5]
        + [i for _, i in cards_by_meaning]
        + [i for s, i in semantic if s >= MEANING_MIN]
        + [i for s, i in lexical if s < 1.5]
    )
    for i in ordered:
        r = tb.rows[i]
        if i in seen or (domain != "all" and r["domain"] != domain):
            continue
        seen.add(i)
        out.append(quick_card(r) | {"match": "word" if i in word_hits else "meaning"})
        if len(out) >= limit:
            break
    return {"results": out, "semantic": bool(semantic), "terms": len(tb.rows)}


@router.get("/api/glossary/browse")
def browse(
    request: Request,
    domain: Literal["all", "ai", "software"] = "all",
    letter: str = Query("", max_length=1, pattern="^[a-z#]?$"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> dict[str, Any]:
    tb: TermBank = request.app.state.termbank
    rows, total = tb.browse(domain, letter, offset, limit)
    return {"results": [quick_card(r) for r in rows], "total": total, "offset": offset}


@router.get("/api/glossary/term/{term_id}")
def term(term_id: str, request: Request, lang: Lang = "gulf") -> dict[str, Any]:
    g = request.app.state.glossary
    if term_id in g.entries:
        return {"full": g.card(term_id, lang), "quick": None}
    r = request.app.state.termbank.by_id.get(term_id)
    if r is None:
        raise HTTPException(status_code=404, detail="unknown term")
    return {"full": None, "quick": quick_card(r)}
