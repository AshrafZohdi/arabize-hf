"""Lessons: GET /api/lessons (list) and GET /api/lessons/{slug} (one lesson, every block)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/api/lessons")
def lessons(request: Request) -> dict[str, Any]:
    return {
        "lessons": [
            {"slug": d["slug"], "order": d["order"], "title": d["title"], "est_minutes": d.get("est_minutes")} for d in request.app.state.lessons
        ],
        "source": request.app.state.lessons_source,
    }


@router.get("/api/lessons/{slug}")
def lesson(slug: str, request: Request) -> dict[str, Any]:
    d = next((x for x in request.app.state.lessons if x["slug"] == slug), None)
    if d is None:
        raise HTTPException(status_code=404, detail="unknown lesson")
    return d
