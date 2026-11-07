"""The term bank in the Space: about 24,000 English terms with Arabic, loaded at startup.

Built in memory with the same pipeline code as the data work (data/pipeline.py), from the Hub at pinned revisions:
our glossary (content/), GIST and the Microsoft glossary (referenced, never re-uploaded), then our stage 3 results
and reviewer overrides from `nuvais/darby-term-bank`, then the search vectors. Any step that fails is logged and
skipped, so the app always starts; with nothing from the Hub it falls back to our own glossary.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from server.terms import Term, TermFinder, singular_forms

log = logging.getLogger("darby.termbank")
TERM_BANK_REPO = "nuvais/darby-term-bank"
SOURCE_RANK = {"darby_editor": 0, "human_gist": 1, "fanar_generated": 2, "human_ms": 3}
FIELDS = ("id", "en", "en_key", "en_expanded", "is_acronym", "ar_display", "ar_full", "ar_key", "ar_origin", "reviewed", "needs_review", "domain", "source_names", "has_full_card", "highlight")


def _ar_norm(s: str) -> str:
    s = re.sub(r"[ً-ٰٟـ]", "", s)
    s = re.sub("[أإآٱ]", "ا", s).replace("ى", "ي").replace("ة", "ه")
    return " ".join(w[2:] if w.startswith("ال") and len(w) > 4 else w for w in s.split())


@dataclass
class TermBank:
    rows: list[dict[str, Any]]
    finder: TermFinder
    vectors: np.ndarray | None = None
    status: dict[str, Any] = field(default_factory=dict)
    _card_boost: np.ndarray | None = None

    def enrich_cards(self, embedder: Any, cards: dict[str, str], boost: float = 0.02) -> int:
        """Re-embed terms that have a full Darby card with their definition, so a description of the meaning
        ("made-up facts") finds them, and give them a small ranking boost. Returns how many were updated."""
        if self.vectors is None:
            return 0
        idx = [i for i, r in enumerate(self.rows) if r["id"] in cards]
        if not idx:
            return 0
        self.vectors[idx] = embedder.encode([cards[self.rows[i]["id"]] for i in idx])
        self._card_boost = np.zeros(len(self.rows), dtype=np.float32)
        self._card_boost[idx] = boost
        return len(idx)

    def __post_init__(self) -> None:
        self.by_id = {r["id"]: r for r in self.rows}
        self._en = [r["en"].lower() for r in self.rows]
        self._ar = [_ar_norm(r["ar_display"]) for r in self.rows]
        self._aliases: dict[str, list[int]] = {}

    def add_aliases(self, pairs: list[tuple[str, str]]) -> None:
        """Extra exact-match forms, for example the plural الأوامر for Prompt (data/curated/aliases.csv)."""
        by_key = {r["en_key"]: i for i, r in enumerate(self.rows)}
        for key, alias in pairs:
            if key in by_key:
                self._aliases.setdefault(_ar_norm(alias), []).append(by_key[key])
                self._aliases.setdefault(alias.lower(), []).append(by_key[key])

    def add_rows(self, new: list[dict[str, Any]]) -> int:
        """Append curated rows after the bank is built. They get zero vectors (never a meaning match) so the
        published embeddings stay aligned with the rows they belong to."""
        for r in new:
            self.rows.append(r)
            self.by_id[r["id"]] = r
            self._en.append(r["en"].lower())
            self._ar.append(_ar_norm(r["ar_display"]))
            if r["highlight"]:
                self.finder.add(Term(id=r["id"], en=r["en"], ar=r["ar_display"], source=r["ar_origin"], has_card=bool(r["has_full_card"])))
        if self.vectors is not None and new:
            self.vectors = np.vstack([self.vectors, np.zeros((len(new), self.vectors.shape[1]), dtype=self.vectors.dtype)])
        if self._card_boost is not None and new:
            self._card_boost = np.concatenate([self._card_boost, np.zeros(len(new), dtype=np.float32)])
        return len(new)

    def add_abbreviations(self, pairs: list[tuple[str, str]] | list[tuple[str, str, bool | None]]) -> int:
        """Highlight abbreviations as their full term, for example RAG as retrieval-augmented generation
        (data/curated/abbreviations.csv). Pairs whose full term is not in the bank are skipped. Returns how many were added."""
        by_en: dict[str, tuple[int, dict[str, Any]]] = {}
        for i, r in enumerate(self.rows):  # the first row for a name wins, like the finder
            by_en.setdefault(r["en"].lower(), (i, r))
        added = 0
        for abbr, en, *flag in pairs:
            hit = by_en.get(en.lower())
            if hit is None:
                continue
            i, r = hit
            self._aliases.setdefault(abbr.lower(), []).append(i)  # search finds rag, Rag and RAG
            term = Term(id=r["id"], en=r["en"], ar=r["ar_display"], source=r["ar_origin"], has_card=bool(r["has_full_card"]))
            any_case = flag[0] if flag and flag[0] is not None else sum(c.isalpha() for c in abbr) >= 3
            self.finder.add(term, surface=abbr, any_case=any_case)
            added += 1
        return added

    @classmethod
    def from_rows(cls, rows: list[dict[str, Any]], status: dict[str, Any] | None = None, vectors: np.ndarray | None = None) -> TermBank:
        rows = sorted(rows, key=lambda r: (SOURCE_RANK.get(r["ar_origin"], 9), r["en"].lower()))
        terms = [Term(id=r["id"], en=r["en"], ar=r["ar_display"], source=r["ar_origin"], has_card=bool(r["has_full_card"])) for r in rows if r["highlight"]]
        return cls(rows=rows, finder=TermFinder(terms), vectors=vectors, status=status or {})

    def lexical(self, q: str, limit: int = 30) -> list[tuple[float, int]]:
        """Exact, prefix and substring matches in English or Arabic, scored so exact and our own terms come first."""
        ql, qa = q.strip().lower(), _ar_norm(q.strip())
        if not ql:
            return []
        hits: list[tuple[float, int]] = [(3.5, i) for i in self._aliases.get(qa, []) + self._aliases.get(ql, [])]
        # A plural search ("skills", "queries") finds the singular entry ("skill", "query").
        last = ql.rsplit(" ", 1)
        singulars = {f"{last[0]} {s}" if len(last) == 2 else s for s in singular_forms(last[-1])}
        hits += [(3.4, i) for s in singulars for i in self._aliases.get(s, [])]  # plurals of other spellings: plugins
        for i, (en, ar) in enumerate(zip(self._en, self._ar)):
            score = 0.0
            if en == ql or (qa and ar == qa):
                score = 3.0
            elif en in singulars:
                score = 2.9
            elif en.startswith(ql) or (qa and ar.startswith(qa)):
                score = 2.0
            elif (len(ql) >= 3 and ql in en) or (qa and len(qa) >= 3 and qa in ar):
                score = 1.0
            if score:
                score -= SOURCE_RANK.get(self.rows[i]["ar_origin"], 9) * 0.1 + len(en) * 0.001
                hits.append((score, i))
        hits.sort(reverse=True)
        return hits[:limit]

    def suggest(self, q: str) -> int | None:
        """The nearest term for a query with no word match (a typo such as "halucination"): Darby cards first, then the bank."""
        import difflib

        ql = q.strip().lower()
        if len(ql) < 4:
            return None
        cards = [i for i, r in enumerate(self.rows) if r["has_full_card"]]
        for pool, cutoff in ((cards, 0.75), (range(len(self.rows)), 0.85)):
            names = {self._en[i]: i for i in pool}
            close = difflib.get_close_matches(ql, list(names), n=1, cutoff=cutoff)
            if close:
                return names[close[0]]
        return None

    def browse(self, domain: str = "all", letter: str = "", offset: int = 0, limit: int = 50) -> tuple[list[dict[str, Any]], int]:
        """Every term A to Z, optionally one field and one first letter ("#" for terms that start with a digit)."""
        if not hasattr(self, "_alpha"):
            self._alpha = sorted(range(len(self.rows)), key=lambda i: (self._en[i].lstrip("-.'\" "), self._en[i]))
        def first(i: int) -> str:
            c = self._en[i].lstrip("-.'\" ")[:1]
            return c if c.isalpha() else "#"
        picked = [i for i in self._alpha if (domain == "all" or self.rows[i]["domain"] == domain) and (not letter or first(i) == letter)]
        return [self.rows[i] for i in picked[offset : offset + limit]], len(picked)

    def card_semantic(self, query_vec: np.ndarray, k: int = 3, minimum: float = 0.80) -> list[tuple[float, int]]:
        """Meaning search among terms with a full Darby card only (re-embedded with their definitions).
        e5-small leans on shared words across the whole bank ("made-up facts" scores "fact table" highest),
        but among the cards it ranks by meaning well enough to show the closest few."""
        if self.vectors is None or self._card_boost is None:
            return []
        idx = np.flatnonzero(self._card_boost)
        sims = self.vectors[idx] @ query_vec
        order = np.argsort(-sims)[:k]
        return [(float(sims[j]), int(idx[j])) for j in order if sims[j] >= minimum]

    def semantic(self, query_vec: np.ndarray, limit: int = 30) -> list[tuple[float, int]]:
        if self.vectors is None:
            return []
        sims = self.vectors @ query_vec
        if self._card_boost is not None:
            sims = sims + self._card_boost
        top = np.argpartition(-sims, min(limit, len(sims) - 1))[:limit]
        return sorted(((float(sims[i]), int(i)) for i in top), reverse=True)


def _rows_from_frame(df) -> list[dict[str, Any]]:
    out = []
    for r in df.to_dict("records"):
        row = {k: r.get(k) for k in FIELDS}
        row["source_names"] = [str(s) for s in (r.get("source_names") if r.get("source_names") is not None else [])]
        for k in ("en_expanded", "ar_full"):
            if not isinstance(row[k], str):
                row[k] = None
        row["ar_full"] = row["ar_full"] or row["ar_display"]
        out.append(row)
    return out


def non_technical(content_dir: Path) -> set[str]:
    """Emoji, sticker, slang and everyday entries from the Microsoft terminology (data/curated/non_technical.csv),
    left out of search, browse and highlighting."""
    import csv

    try:
        with open(content_dir.parent / "data" / "curated" / "non_technical.csv", encoding="utf-8") as f:
            return {r["en"] for r in csv.DictReader(f)}  # exact case: "man" is an emoji, "MAN" a network
    except OSError:
        return set()


def _highlightable(en: str) -> bool:
    """The finder works on letters and digits, so a name like C++ or C# would shrink to one letter."""
    return re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .'-]*", en) is not None


def english_words(content_dir: Path) -> set[str] | None:
    """Ordinary English words (data/curated/english_words.txt), so acronyms can match in any case without "it" becoming IT."""
    try:
        with open(content_dir.parent / "data" / "curated" / "english_words.txt", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip() and not line.startswith("#")}
    except OSError:
        return None


def apply_curated(tb: TermBank, content_dir: Path, status: dict[str, Any]) -> None:
    """Our additions (data/curated/additions.csv), then abbreviations (data/curated/abbreviations.csv), then the
    English word list that lets acronyms match in any case."""
    import csv

    curated = content_dir.parent / "data" / "curated"
    tb.finder.english = english_words(content_dir)
    status["steps"]["english_words"] = f"ok ({len(tb.finder.english)})" if tb.finder.english else "skipped: exact case for acronyms"
    try:
        with open(curated / "additions.csv", encoding="utf-8") as f:
            wanted = list(csv.DictReader(f))
        new, switched = [], 0
        for w in wanted:
            existing = next((r for r in tb.rows if r["en"].lower() == w["en"].lower()), None)
            if existing is not None:
                if not existing["highlight"] and _highlightable(w["en"]):
                    existing["highlight"] = True
                    tb.finder.add(Term(id=existing["id"], en=existing["en"], ar=existing["ar_display"], source=existing["ar_origin"], has_card=bool(existing["has_full_card"])))
                    switched += 1
                continue
            slug = re.sub(r"[^a-z0-9]+", "-", w["en"].lower().replace("++", "pp").replace("#", "sharp")).strip("-")
            new.append({
                "id": slug, "en": w["en"], "en_key": w["en"].lower(), "en_expanded": None, "is_acronym": False,
                "ar_display": w["ar"], "ar_full": w["ar"], "ar_key": w["ar"], "ar_origin": "darby_editor",
                "reviewed": False, "needs_review": True, "domain": w["domain"], "source_names": ["darby"],
                "has_full_card": False, "highlight": _highlightable(w["en"]),
            })
        status["steps"]["additions"] = f"ok ({tb.add_rows(new)} added, {switched} switched on)"
    except Exception as e:
        status["steps"]["additions"] = f"skipped: {type(e).__name__}"
    try:
        with open(curated / "abbreviations.csv", encoding="utf-8") as f:
            pairs = [(r["abbreviation"], r["en"], {"yes": True, "no": False}.get(r.get("any_case") or "")) for r in csv.DictReader(f)]
        status["steps"]["abbreviations"] = f"ok ({tb.add_abbreviations(pairs)} of {len(pairs)})"
    except Exception as e:
        status["steps"]["abbreviations"] = f"skipped: {type(e).__name__}"


def load_term_bank(content_dir: Path, token: str | None = None, full_card_ids: set[str] | None = None) -> TermBank:
    """Build the bank from the Hub. Steps that fail are skipped and reported in `status`."""
    import pandas as pd

    from data.pipeline import build_clean, hub_rows

    t0 = time.time()
    status: dict[str, Any] = {"steps": {}}
    try:
        bank, _, _ = build_clean(hub_rows())
        status["steps"]["sources"] = "ok"
    except Exception as e:
        log.error("term bank: sources failed (%s), using our glossary only", type(e).__name__)
        status["steps"]["sources"] = f"failed: {type(e).__name__}"
        return _glossary_only(content_dir, status)

    from huggingface_hub import hf_hub_download

    from data.publish import apply_public, key_hash

    def hub(path: str) -> str:
        return hf_hub_download(TERM_BANK_REPO, path, repo_type="dataset", token=token)

    try:
        train = pd.read_parquet(hub("data/train.parquet"))
        completions = pd.read_parquet(hub("completions/ms.parquet"))
        overrides = pd.read_csv(hub("curated/overrides.csv"), dtype=str).fillna("")
        frame = apply_public(bank, train, completions, overrides)
        status["steps"]["published"] = f"ok ({len(train)} own and GIST terms, {len(completions)} Microsoft completions)"
    except Exception as e:
        log.warning("term bank: published files not loaded (%s)", type(e).__name__)
        status["steps"]["published"] = f"skipped: {type(e).__name__}"
        frame = bank

    rows = _rows_from_frame(frame)
    dropped = non_technical(content_dir)
    rows = [r for r in rows if r["en"] not in dropped]
    status["steps"]["non_technical"] = f"{len(dropped)} emoji, sticker and everyday entries left out"
    for r in rows:  # cards published in the glossary dataset (ours and Fanar's) count as full cards
        if full_card_ids and r["id"] in full_card_ids:
            r["has_full_card"] = True
    tb = TermBank.from_rows(rows, status)
    try:
        aliases = pd.read_csv(content_dir.parent / "data" / "curated" / "aliases.csv", dtype=str)
        tb.add_aliases(list(zip(aliases.en_key, aliases.alias)))
        status["steps"]["aliases"] = f"ok ({len(aliases)})"
    except Exception as e:
        status["steps"]["aliases"] = f"skipped: {type(e).__name__}"
    try:
        from huggingface_hub import hf_hub_download

        emb = pd.read_parquet(hub("embeddings/e5_small.parquet"))
        index = dict(zip(emb.key, emb.vector))
        missing = sum(key_hash(r["en_key"]) not in index for r in tb.rows)
        if missing:
            status["steps"]["vectors"] = f"skipped: {missing} terms without a vector"
        else:
            # Built from the bank's own row order, so row i and vector i always belong together.
            tb.vectors = np.stack([np.asarray(index[key_hash(r["en_key"])], dtype=np.float32) for r in tb.rows])
            status["steps"]["vectors"] = f"ok ({len(tb.vectors)})"
    except Exception as e:
        status["steps"]["vectors"] = f"skipped: {type(e).__name__}"

    apply_curated(tb, content_dir, status)  # after the vectors, which are matched to the published rows
    status.update({"terms": len(tb.rows), "highlight_terms": tb.finder.size, "seconds": round(time.time() - t0, 1)})
    log.info("term bank ready: %s", status)
    return tb


def _glossary_only(content_dir: Path, status: dict[str, Any]) -> TermBank:
    from server.glossary import load_glossary

    g = load_glossary(content_dir)
    rows = [
        {
            "id": k, "en": e["term_en"], "en_key": e["term_en"].lower(), "en_expanded": None, "is_acronym": False, "ar_display": e["term_msa"],
            "ar_full": e["term_msa"], "ar_key": e["term_msa"], "ar_origin": "darby_editor", "reviewed": False, "needs_review": False,
            "domain": e.get("domain", "ai"), "source_names": ["darby"], "has_full_card": True, "highlight": True,
        }
        for k, e in g.entries.items()
    ]
    tb = TermBank.from_rows(rows, status)
    apply_curated(tb, content_dir, status)
    status.update({"terms": len(rows), "highlight_terms": tb.finder.size})
    return tb
