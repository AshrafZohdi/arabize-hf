"""Deterministic term finder for Smart Explain: no AI involved.

A word-level trie over every term in the bank. The text is scanned left to right and the longest
multi-word match wins at each position, so "large language model" beats "model". Matching ignores
case, except for acronyms (all caps, like "AI" or "IT"), which must match their case so the word "it"
never becomes "IT". The last word of a term also matches simple plural and suffix forms
(prompts, hallucinations, queries, APIs); a possessive "'s" is included in the match.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_WORD = re.compile(r"[A-Za-z0-9]+")


@dataclass(frozen=True)
class Term:
    id: str
    en: str
    ar: str
    source: str  # darby_glossary, darby_computing, gist, ms ...
    has_card: bool = False


@dataclass(frozen=True)
class Match:
    start: int  # character offsets into the original text
    end: int
    text: str
    term: Term


def is_acronym(word: str) -> bool:
    letters = [c for c in word if c.isalpha()]
    return len(word) <= 6 and len(letters) >= 2 and all(c.isupper() for c in letters)


def suffix_forms(word: str) -> set[str]:
    """Simple English inflections of one word (already in its matching case)."""
    if is_acronym(word):
        return {word, word + "s"}
    w = word
    forms = {w, w + "s", w + "es"}
    if w.endswith("y") and len(w) > 2 and w[-2] not in "aeiou":
        forms.add(w[:-1] + "ies")
    if w.endswith("e"):
        forms |= {w + "d", w[:-1] + "ing"}
    else:
        forms |= {w + "ed", w + "ing"}
    return forms


def _key(word: str) -> str:
    return word if is_acronym(word) else word.lower()


@dataclass
class _Node:
    children: dict[str, _Node] = field(default_factory=dict)
    term: Term | None = None


class TermFinder:
    def __init__(self, terms: list[Term]):
        self._root = _Node()
        self.size = 0
        for t in terms:
            self.add(t)

    def add(self, term: Term, surface: str | None = None) -> None:
        """Index `term` under its English, or under `surface` (an abbreviation such as RAG for its full term)."""
        words = _WORD.findall(surface or term.en)
        if not words:
            return
        keys = [_key(w) for w in words]
        added = False
        for last in suffix_forms(keys[-1]):
            node = self._root
            for k in [*keys[:-1], last]:
                node = node.children.setdefault(k, _Node())
            # First writer wins, so the bank's priority order (ours, then GIST, then MS) decides conflicts.
            if node.term is None:
                node.term = term
                added = True
        self.size += added  # terms reachable by at least one form, not trie entries

    def find(self, text: str) -> list[Match]:
        tokens = [(m.group(), m.start(), m.end()) for m in _WORD.finditer(text)]
        out: list[Match] = []
        i = 0
        while i < len(tokens):
            best: tuple[int, Term] | None = None
            node: _Node | None = self._root
            j = i
            while j < len(tokens) and node is not None:
                word = tokens[j][0]
                # Exact first (acronym keys are upper case), then lower case for ordinary words.
                node = node.children.get(word) or node.children.get(word.lower())
                if node is not None and node.term is not None:
                    best = (j, node.term)
                j += 1
            if best:
                j, term = best
                start, end = tokens[i][1], tokens[j][2]
                if re.match(r"['\u2019]s\b", text[end : end + 3]):  # possessive: LLM's
                    end += 2
                out.append(Match(start, end, text[start:end], term))
                i = j + 1
                while i < len(tokens) and tokens[i][1] < end:  # skip the "s" of a possessive
                    i += 1
            else:
                i += 1
        return out
