"""Daily code (شيفرة اليوم), P0-4: guess today's glossary term in 6 tries, in English or Arabic.

Rules ported from ../arabaize/supabase/migrations/20261102000003_daily_code.sql and mobile/src/lib/learning.ts:
normalisation, hit-first marking, one word of 3 to 9 letters, a word a day by Qatar date walking the list so nothing
repeats until all are used. The server picks the word and marks every guess. There are no accounts, so the game state
travels as a signed token (HMAC): the answer is only returned once the token shows a win or 6 used tries, and a
browser cannot forge a token.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

GameLang = Literal["en", "ar"]
MAX_TRIES = 6
EPOCH = date(2026, 1, 1)
QATAR = timezone(timedelta(hours=3))  # no daylight saving
XP_WON, XP_FINISHED = 30, 10
_LETTERS = {"en": re.compile(r"^[a-z]+$"), "ar": re.compile(r"^[ء-ي]+$")}
_PUZZLE = {"en": re.compile(r"^[a-z]{3,9}$"), "ar": re.compile(r"^[ء-ي]{3,9}$")}


def qatar_today(now: datetime | None = None) -> date:
    return (now or datetime.now(timezone.utc)).astimezone(QATAR).date()


def normalize(word: str) -> str:
    """Spelling variants count as one key (same as game_normalize in the old app)."""
    w = re.sub(r"[ً-ٰـ]", "", word.strip().lower())
    return w.translate(str.maketrans("أإآٱةىؤئ", "ااااهيوي"))


def word_forms(word: str) -> list[str]:
    """Forms to look up for an Arabic guess: "the", a joined و ف ب ل, and common endings taken off."""
    stems = [word]
    for prefix in ("وال", "فال", "بال", "كال", "لل", "ال", "و", "ف", "ب", "ل"):
        if word.startswith(prefix) and len(word) - len(prefix) >= 3:
            stems.append(word[len(prefix) :])
    forms = list(stems)
    for stem in stems:
        for suffix in ("ات", "ون", "ين", "ان", "ها", "هم", "نا", "ه", "ي", "ك"):
            if stem.endswith(suffix) and len(stem) - len(suffix) >= 3:
                cut = stem[: -len(suffix)]
                forms.append(cut)
                if suffix == "ات":
                    forms.append(cut + "ه")
    return forms


def mark(answer: str, guess: str) -> list[str]:
    """Hits first, so a repeated letter is only "near" as often as the answer has it spare."""
    marks: list[str] = []
    spare: list[str] = []
    for i, ch in enumerate(guess):
        if i < len(answer) and ch == answer[i]:
            marks.append("hit")
        else:
            marks.append("miss")
            if i < len(answer):
                spare.append(answer[i])
    for i, ch in enumerate(guess):
        if marks[i] == "miss" and ch in spare:
            marks[i] = "near"
            spare.remove(ch)
    return marks


@dataclass(frozen=True)
class Puzzle:
    term_id: str
    word: str  # normalised answer
    clue_term: str  # the term in the other language
    clue_meaning: str


class Game:
    def __init__(self, glossary: Any, words_dir: Path, secret: bytes):
        self.secret = secret
        self._puzzles: dict[str, list[Puzzle]] = {"en": [], "ar": []}
        for term_id in sorted(glossary.entries):
            e = glossary.entries[term_id]
            en, ar = normalize(e["term_en"]), normalize(e["term_msa"])
            if _PUZZLE["en"].match(en):
                self._puzzles["en"].append(Puzzle(term_id, en, e["term_msa"], e.get("def_ar") or ""))
            if _PUZZLE["ar"].match(ar):
                self._puzzles["ar"].append(Puzzle(term_id, ar, e["term_en"], e.get("def_en") or ""))
        self._words: dict[str, set[str]] = {}
        self._words_dir = words_dir

    def words(self, lang: GameLang) -> set[str]:
        if lang not in self._words:
            raw = json.loads((self._words_dir / f"words-{lang}.json").read_text(encoding="utf-8"))
            words = raw["words"] if isinstance(raw, dict) else raw
            # content/words-*.json hold one space-separated string; a list also works.
            items = words.split() if isinstance(words, str) else words
            self._words[lang] = {normalize(w) for w in items}
        return self._words[lang]

    def puzzle(self, lang: GameLang, day: date) -> Puzzle:
        options = self._puzzles[lang]
        if not options:
            raise LookupError(f"no {lang} puzzle words")
        return options[(day - EPOCH).days % len(options)]

    def count(self, lang: GameLang) -> int:
        return len(self._puzzles[lang])

    # --- signed state -------------------------------------------------------------------

    def _sign(self, payload: bytes) -> str:
        return hmac.new(self.secret, payload, hashlib.sha256).hexdigest()[:32]

    def token(self, lang: GameLang, day: date, guesses: list[str]) -> str:
        body = json.dumps({"l": lang, "d": day.isoformat(), "g": guesses}, ensure_ascii=False, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(body).decode() + "." + self._sign(body)

    def read_token(self, token: str, lang: GameLang, day: date) -> list[str] | None:
        """The guesses so far, or None when the token is missing, forged or from another day or language."""
        try:
            b64, sig = token.rsplit(".", 1)
            body = base64.urlsafe_b64decode(b64.encode())
        except Exception:
            return None
        if not hmac.compare_digest(self._sign(body), sig):
            return None
        data = json.loads(body)
        if data.get("l") != lang or data.get("d") != day.isoformat():
            return None
        return list(data.get("g", []))

    # --- play -----------------------------------------------------------------------------

    def start(self, lang: GameLang, day: date) -> dict[str, Any]:
        p = self.puzzle(lang, day)
        return {"date": day.isoformat(), "lang": lang, "length": len(p.word), "max_tries": MAX_TRIES,
                "clue": {"term": p.clue_term, "meaning": p.clue_meaning}, "token": self.token(lang, day, [])}

    def is_real_word(self, lang: GameLang, guess: str, answer: str) -> bool:
        if guess == answer:
            return True
        words = self.words(lang)
        return guess in words if lang == "en" else any(f in words for f in word_forms(guess))

    def guess(self, lang: GameLang, day: date, token: str, raw_guess: str) -> dict[str, Any]:
        p = self.puzzle(lang, day)
        previous = self.read_token(token, lang, day)
        if previous is None:
            return {"error": "bad_token"}
        if len(previous) >= MAX_TRIES or p.word in previous:
            return {"error": "finished"}
        g = normalize(raw_guess)
        if len(g) != len(p.word) or not _LETTERS[lang].match(g):
            return {"error": "invalid", "reason": "length"}
        if not self.is_real_word(lang, g, p.word):
            # Not a word: refused at no cost, no try used.
            return {"error": "invalid", "reason": "not_a_word"}
        guesses = previous + [g]
        won = g == p.word
        finished = won or len(guesses) >= MAX_TRIES
        out: dict[str, Any] = {"guess": g, "marks": mark(p.word, g), "won": won, "finished": finished,
                               "tries_left": MAX_TRIES - len(guesses), "token": self.token(lang, day, guesses)}
        if finished:
            out["answer"] = {"id": p.term_id, "word": p.word, "xp": XP_WON if won else XP_FINISHED}
        return out
