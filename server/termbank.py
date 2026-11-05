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

from server.terms import Term, TermFinder

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
        for i, (en, ar) in enumerate(zip(self._en, self._ar)):
            score = 0.0
            if en == ql or (qa and ar == qa):
                score = 3.0
            elif en.startswith(ql) or (qa and ar.startswith(qa)):
                score = 2.0
            elif (len(ql) >= 3 and ql in en) or (qa and len(qa) >= 3 and qa in ar):
                score = 1.0
            if score:
                score -= SOURCE_RANK.get(self.rows[i]["ar_origin"], 9) * 0.1 + len(en) * 0.001
                hits.append((score, i))
        hits.sort(reverse=True)
        return hits[:limit]

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


def load_term_bank(content_dir: Path, token: str | None = None) -> TermBank:
    """Build the bank from the Hub. Steps that fail are skipped and reported in `status`."""
    import pandas as pd

    from data.pipeline import build_clean, hub_rows, merge_stage3

    t0 = time.time()
    status: dict[str, Any] = {"steps": {}}
    try:
        bank, _, _ = build_clean(hub_rows())
        status["steps"]["sources"] = "ok"
    except Exception as e:
        log.error("term bank: sources failed (%s), using our glossary only", type(e).__name__)
        status["steps"]["sources"] = f"failed: {type(e).__name__}"
        return _glossary_only(content_dir, status)

    try:
        from huggingface_hub import hf_hub_download

        res = pd.read_parquet(hf_hub_download(TERM_BANK_REPO, "stage3/results.parquet", repo_type="dataset", token=token))
        overrides = pd.read_csv(hf_hub_download(TERM_BANK_REPO, "curated/overrides.csv", repo_type="dataset", token=token), dtype=str).fillna("")
        _, published, held = merge_stage3(bank, res, overrides)
        status["steps"]["stage3"] = f"ok ({len(held)} held back for review)"
        frame = published
    except Exception as e:
        log.warning("term bank: stage 3 results not loaded (%s)", type(e).__name__)
        status["steps"]["stage3"] = f"skipped: {type(e).__name__}"
        frame = bank

    tb = TermBank.from_rows(_rows_from_frame(frame), status)
    try:
        aliases = pd.read_csv(content_dir.parent / "data" / "curated" / "aliases.csv", dtype=str)
        tb.add_aliases(list(zip(aliases.en_key, aliases.alias)))
        status["steps"]["aliases"] = f"ok ({len(aliases)})"
    except Exception as e:
        status["steps"]["aliases"] = f"skipped: {type(e).__name__}"
    try:
        from huggingface_hub import hf_hub_download

        emb = pd.read_parquet(hf_hub_download(TERM_BANK_REPO, "embeddings/e5_small.parquet", repo_type="dataset", token=token))
        index = dict(zip(emb.en_key, emb.vector))
        missing = sum(r["en_key"] not in index for r in tb.rows)
        if missing:
            status["steps"]["vectors"] = f"skipped: {missing} terms without a vector"
        else:
            # Built from the bank's own row order, so row i and vector i always belong together.
            tb.vectors = np.stack([np.asarray(index[r["en_key"]], dtype=np.float32) for r in tb.rows])
            status["steps"]["vectors"] = f"ok ({len(tb.vectors)})"
    except Exception as e:
        status["steps"]["vectors"] = f"skipped: {type(e).__name__}"

    status.update({"terms": len(tb.rows), "highlight_terms": tb.finder.size, "seconds": round(time.time() - t0, 1)})
    log.info("term bank ready: %s", status)
    return tb


def _glossary_only(content_dir: Path, status: dict[str, Any]) -> TermBank:
    from server.glossary import load_glossary

    g = load_glossary(content_dir)
    rows = [
        {
            "id": k, "en": e["term_en"], "en_key": e["term_en"].lower(), "en_expanded": None, "is_acronym": False, "ar_display": e["term_msa"],
            "ar_full": e["term_msa"], "ar_key": e["term_msa"], "ar_origin": "darby_editor", "reviewed": True, "needs_review": False,
            "domain": e.get("domain", "ai"), "source_names": ["darby"], "has_full_card": True, "highlight": True,
        }
        for k, e in g.entries.items()
    ]
    tb = TermBank.from_rows(rows, status)
    status.update({"terms": len(rows), "highlight_terms": tb.finder.size})
    return tb
