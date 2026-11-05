"""Text checks and normalisation shared by the EDA (stage 1) and cleaning (stage 2). Pure functions, tested."""

from __future__ import annotations

import html
import re
import unicodedata

ARABIC_LETTER = re.compile(r"[ء-غف-يٱ-ۓۺ-ۿ]")
LATIN_LETTER = re.compile(r"[A-Za-z]")
DIACRITIC = re.compile(r"[ً-ٰٟ]")
TATWEEL = "ـ"
PRESENTATION_FORM = re.compile(r"[ﭐ-﷿ﹰ-﻿]")
EASTERN_DIGIT = re.compile(r"[٠-٩۰-۹]")
HTML_TAG = re.compile(r"<[^>]+>|&[a-z]+;|&#\d+;")
PACKED_SEP = re.compile(r"\s*(?:;|؛|/|،|\||\bor\b|\sأو\s)\s*")
EXTRA_WS = re.compile(r"\s{2,}|^\s|\s$")

_EASTERN_TO_WESTERN = {ord(c): str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")} | {ord(c): str(i) for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹")}


# --- Arabic checks -------------------------------------------------------------------------


def arabic_share(s: str) -> float:
    """Share of letters that are Arabic (0 when the string has no letters)."""
    ar = len(ARABIC_LETTER.findall(s))
    lat = len(LATIN_LETTER.findall(s))
    return ar / (ar + lat) if ar + lat else 0.0


def is_latin_only(s: str) -> bool:
    return bool(LATIN_LETTER.search(s)) and not ARABIC_LETTER.search(s)


def keeps_acronym_only(ar: str) -> bool:
    """Arabic cell that is just the English acronym, with no Arabic word around it (for example "GPT")."""
    return is_latin_only(ar) and bool(re.fullmatch(r"[A-Z0-9][A-Z0-9\-./+]*s?", ar.strip()))


def split_packed(s: str) -> list[str]:
    """Several translations packed into one cell, split on ; ؛ / ، | or أو."""
    parts = [p.strip() for p in PACKED_SEP.split(s) if p and p.strip()]
    return parts or [s.strip()]


# --- English acronyms and short forms ------------------------------------------------------


def acronym_kinds(en: str) -> set[str]:
    """Which short-form patterns an English term shows (empty set for an ordinary term)."""
    kinds: set[str] = set()
    words = en.split()
    for w in words:
        core = w.strip("()[],")
        letters = [c for c in core if c.isalpha()]
        if len(letters) >= 2 and all(c.isupper() for c in letters) and not re.fullmatch(r"[A-Z][a-z]+", core):
            kinds.add("all_caps")
        if re.search(r"[A-Za-z]", core) and re.search(r"\d", core):
            kinds.add("digit_mix")
        if re.fullmatch(r"[A-Z]{2,}s", core):
            kinds.add("acronym_plural")
    if re.search(r"\b[A-Za-z]\s?/\s?[A-Za-z]\b", en):
        kinds.add("slash")
    if re.search(r"\b(?:[A-Za-z]\.){2,}", en):
        kinds.add("dots")
    return kinds


ACRONYM_TOKEN = re.compile(r"(?:[A-Z][A-Za-z0-9]*[A-Z0-9][A-Za-z0-9]*|[A-Z]{2,})(?:[-.][A-Za-z0-9]+)*s?")


def is_acronym_term(en: str) -> bool:
    """The term itself is a short form that needs a full English expansion: one token like SAC, A2C, GPT-4, LLMs,
    or a short-form pattern like A/B testing or i.i.d. A longer term that only contains an acronym
    ("USB port", "Power BI Report Server") is not one: see has_acronym."""
    s = en.strip()
    if re.fullmatch(r"(?:[A-Za-z]\.){2,}", s) or re.match(r"[A-Za-z]\s?/\s?[A-Za-z]\b", s):
        return True
    if " " in s:
        return False
    letters = [c for c in s if c.isalpha()]
    upper = sum(c.isupper() for c in letters)
    has_digit = bool(re.search(r"\d", s))
    if not letters or len(s) > 10 or (len(letters) < 2 and not has_digit):
        return False
    return (upper == len(letters) or (upper >= 2 and has_digit) or bool(re.fullmatch(r"[A-Z]{2,}s", s)))


def has_acronym(en: str) -> bool:
    return bool(acronym_kinds(en) & {"all_caps", "acronym_plural"})


# --- normalisation (stage 2) ---------------------------------------------------------------


def normalise_ar(s: str) -> str:
    """Display-safe Arabic: NFC, presentation forms to standard letters, no tatweel or HTML,
    Western digits, Arabic punctuation, single spaces. Diacritics are kept (they can matter)."""
    s = html.unescape(HTML_TAG.sub(lambda m: m.group() if m.group().startswith("&") else " ", s))
    s = unicodedata.normalize("NFC", s)
    s = PRESENTATION_FORM.sub(lambda m: unicodedata.normalize("NFKC", m.group()), s)
    s = s.replace(TATWEEL, "").translate(_EASTERN_TO_WESTERN)
    if ARABIC_LETTER.search(s):
        s = re.sub(r"\s*,\s*", "، ", s)
        s = re.sub(r"\s*;\s*", "؛ ", s)
        s = s.replace("?", "؟")
    return re.sub(r"\s+", " ", s).strip()


def normalise_en(s: str) -> str:
    s = html.unescape(HTML_TAG.sub(" ", s))
    s = unicodedata.normalize("NFC", s).replace("’", "'").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", s).strip()


def ar_key(s: str) -> str:
    """Matching key for Arabic, never shown: no diacritics, alef forms to ا, ى to ي, ة to ه."""
    s = DIACRITIC.sub("", normalise_ar(s))
    s = re.sub("[أإآٱ]", "ا", s).replace("ى", "ي").replace("ة", "ه")
    return s


def _singular(word: str) -> str:
    w = word
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 4 and w.endswith(("sses", "shes", "ches", "xes")):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith(("ss", "us", "is", "ous")):
        return w[:-1]
    return w


def en_key(s: str) -> str:
    """Matching key for English, never shown. Lower case and singular last word, but acronyms keep their
    case ("IT" stays apart from "it") and acronym plurals drop the s (LLMs -> LLM)."""
    s = normalise_en(s)
    s = re.sub(r"[\-_/]", " ", s)
    s = re.sub(r"[^\w\s.+#']", "", s)
    words = s.split()
    out = []
    for i, w in enumerate(words):
        last = i == len(words) - 1
        if re.fullmatch(r"[A-Z]{2,}s", w):
            out.append(w[:-1])
        elif sum(c.isupper() for c in w) >= 2 and not w.isdigit():
            out.append(w)  # acronym or mixed-case product name: keep case
        else:
            lw = w.lower()
            out.append(_singular(lw) if last else lw)
    return " ".join(out)


def ar_compare_key(s: str) -> str:
    """Looser key for spotting real disagreements between sources: ar_key without a leading "ال" on each word,
    so المصدر and مصدر count as the same translation."""
    return " ".join(w[2:] if w.startswith("ال") and len(w) > 4 else w for w in ar_key(s).split())
