"""Darby's own glossary (full cards) and the term finder built from it.

Step 4 replaces the source with the published term bank from the Hub; the card shape stays the same.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from server.terms import Term, TermFinder

GLOSSARY_FILES = (("glossary.json", "darby_glossary"), ("terms-computing.json", "darby_computing"))


def slug(en: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", en.lower()).strip("-")


@dataclass
class Glossary:
    entries: dict[str, dict[str, Any]]
    finder: TermFinder

    def card(self, term_id: str, lang: str) -> dict[str, Any] | None:
        e = self.entries.get(term_id)
        if e is None:
            return None
        ar = lang != "en"
        explanation = e["def_en"] if not ar else (e.get("def_gulf") if lang == "gulf" else None) or e["def_ar"]
        return {
            "id": term_id,
            "term_en": e["term_en"],
            "term_ar": e["term_msa"],
            "term_gulf": e.get("term_gulf"),
            "explanation": explanation,
            "analogy": e.get("analogy_ar" if ar else "analogy_en") or "",
            "mistake": e.get("mistake_ar" if ar else "mistake_en") or "",
            "example": (e.get("example_gulf") if lang == "gulf" else None) or e.get("example_ar" if ar else "example_en") or "",
            "related": list(e.get("related") or [])[:3],
            "source": "glossary",
        }


def load_glossary(content_dir: Path) -> Glossary:
    entries: dict[str, dict[str, Any]] = {}
    terms: list[Term] = []
    for filename, source in GLOSSARY_FILES:
        for e in json.loads((content_dir / filename).read_text(encoding="utf-8")):
            term_id = slug(e["term_en"])
            if term_id in entries:
                continue
            entries[term_id] = e
            terms.append(Term(id=term_id, en=e["term_en"], ar=e["term_msa"], source=source, has_card=True))
    return Glossary(entries=entries, finder=TermFinder(terms))
