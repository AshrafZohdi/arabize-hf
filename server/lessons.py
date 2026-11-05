"""Lessons from the Hub (`nuvais/darby-lessons`), with content/ as the fallback when the Hub is unreachable."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger("darby.lessons")
LESSONS_REPO = "nuvais/darby-lessons"


def load_lessons(content_dir: Path, from_hub: bool = True, token: str | None = None) -> tuple[list[dict[str, Any]], str]:
    """Return (lessons in order, where they came from)."""
    if from_hub:
        try:
            from huggingface_hub import snapshot_download

            folder = Path(snapshot_download(LESSONS_REPO, repo_type="dataset", allow_patterns=["lessons/*.json"], token=token))
            lessons = _read(sorted((folder / "lessons").glob("day-*.json")))
            if lessons:
                return lessons, f"hub:{LESSONS_REPO}"
        except Exception as e:
            log.warning("lessons: Hub not reachable (%s), using content/", type(e).__name__)
    return _read(sorted(content_dir.glob("day-*.json"))), "content"


def _read(paths: list[Path]) -> list[dict[str, Any]]:
    lessons = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    return sorted(lessons, key=lambda d: d["order"])
