"""Gulf dialect markers: everyday Gulf words that Modern Standard Arabic does not use.

They come from `content/gulf-markers.json` (hand-picked from the Gulf frequency list of El-Haj et al. 2018, see the
file for the source and licence). Two uses:
- the prompts show them to the model as the tone to write in;
- `gulf_marker_count` counts them in a Gulf answer, so drift back to Standard Arabic can be measured and logged.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from server.config import ROOT

# Used when the content file is missing, so prompts still name a few Gulf words.
_FALLBACK = ("شنو", "عشان", "وايد", "زين", "مو", "الحين", "شلون", "اللي", "لازم", "ليش")
_TOKEN = re.compile(r"[ء-ي]+")
_DIACRITICS = re.compile(r"[ً-ْـ]")


@lru_cache(maxsize=4)
def _load(content_dir: str) -> tuple[tuple[str, ...], frozenset[str]]:
    """(words in file order for prompts, every spelling for counting)."""
    path = Path(content_dir) / "gulf-markers.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _FALLBACK, frozenset(_FALLBACK)
    rows = [*data.get("markers", []), *data.get("darbi_additions", {}).get("markers", [])]
    words = tuple(r["word"] for r in rows)
    spellings = frozenset(w for r in rows for w in (r["word"], *r.get("also", [])))
    return words or _FALLBACK, spellings or frozenset(_FALLBACK)


def gulf_words(limit: int = 18, content_dir: Path | None = None) -> str:
    """Marker words for a prompt, joined the Arabic way: "شنو، عشان، وايد"."""
    words, _ = _load(str(content_dir or ROOT / "content"))
    return "، ".join(words[:limit])


def gulf_marker_count(text: str, content_dir: Path | None = None) -> int:
    """How many words of `text` are Gulf markers. Zero in a long answer means it is probably Standard Arabic."""
    _, spellings = _load(str(content_dir or ROOT / "content"))
    count = 0
    for token in _TOKEN.findall(_DIACRITICS.sub("", text)):
        # Gulf writing attaches و and ف to the next word: وعشان، فلازم.
        if token in spellings or (len(token) > 3 and token[0] in "وف" and token[1:] in spellings):
            count += 1
    return count
