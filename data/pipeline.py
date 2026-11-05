"""Term bank pipeline (docs/DATA_PIPELINE.md). One function per stage, deterministic and idempotent.

    python -m data.pipeline stage0     raw snapshot + manifest
    python -m data.pipeline stage2     clean, normalise, dedupe -> data/interim/term_bank_clean.parquet

Stage 1 (EDA) is notebooks/eda.ipynb. Stage 3 (acronym expansion and translation) runs as an HF Job.
Raw files are never edited.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
REPORTS = ROOT / "data" / "reports"
MANIFEST = ROOT / "data" / "manifest.json"

# Pinned source revisions: the pipeline always reads exactly these bytes.
SOURCES = {
    "gist": {
        "repo_id": "Jerry999/multilingual-terminology",
        "revision": "0a4c2be4f2c49a7fc8d0bbb074c31616112fd7c9",
        "filename": "Arabic.csv",
        "licence": "apache-2.0",
    },
    "ms": {
        "repo_id": "ymoslem/MS-Glossary-EN-AR",
        "revision": "580155fa32168ebac2ec52a4ae5c041a4519977a",
        "filename": "data/train-00000-of-00001.parquet",
        "licence": "not stated on the card (team decision: used for the hackathon, referenced by repo id, not re-uploaded)",
    },
}
OURS = {
    "darby_glossary": ROOT / "content" / "glossary.json",
    "darby_computing": ROOT / "content" / "terms-computing.json",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def raw_path(name: str) -> Path:
    return RAW / name / Path(SOURCES[name]["filename"]).name


def read_source(name: str):
    import pandas as pd

    if name in OURS:
        return pd.DataFrame(json.loads(OURS[name].read_text(encoding="utf-8")))
    path = raw_path(name)
    if name == "gist":
        # Read every column as text: some cells look numeric, and the Hub viewer fails on these mixed columns.
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    return pd.read_parquet(path)


def stage0() -> dict:
    """Download each source at its pinned revision and write the manifest."""
    from huggingface_hub import hf_hub_download

    manifest: dict = {"sources": {}}
    for name, src in SOURCES.items():
        target = raw_path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        cached = hf_hub_download(src["repo_id"], src["filename"], repo_type="dataset", revision=src["revision"])
        target.write_bytes(Path(cached).read_bytes())
        df = read_source(name)
        manifest["sources"][name] = {
            **src,
            "local_path": str(target.relative_to(ROOT)),
            "rows": int(len(df)),
            "columns": list(map(str, df.columns)),
            "sha256": sha256(target),
        }
    for name, path in OURS.items():
        df = read_source(name)
        manifest["sources"][name] = {
            "repo_id": None,
            "local_path": str(path.relative_to(ROOT)),
            "rows": int(len(df)),
            "columns": sorted(map(str, df.columns)),
            "sha256": sha256(path),
            "licence": "ours",
        }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


# MS single words are highlighted only when GIST (AI research terms) uses the word in at least this many terms.
# Measured in the EDA: all MS single words = 31.5 matches per 100 words of lesson text; with this rule about 9,
# and the demo email marks exactly model, context, prompt, source (docs/DECISIONS.md D11).
MS_SINGLE_WORD_MIN_GIST_USES = 5
MAX_TERM_WORDS = 8
DOMAIN = {"darby_glossary": "ai", "darby_computing": "software", "gist": "ai", "ms": "software"}
ORIGIN = {"darby": "darby_editor", "gist": "human_gist", "ms": "human_ms"}
PRIORITY = {"darby": 0, "gist": 1, "ms": 2}


def _rows():
    """Every source as rows of (source, origin_name, row_id, en, ar), in priority order."""
    import pandas as pd

    o1, o2, g, m = read_source("darby_glossary"), read_source("darby_computing"), read_source("gist"), read_source("ms")
    frames = [
        pd.DataFrame({"source": "darby", "set": "darby_glossary", "row_id": "glossary.json#" + o1.index.astype(str), "en": o1.term_en, "ar": o1.term_msa}),
        pd.DataFrame({"source": "darby", "set": "darby_computing", "row_id": "terms-computing.json#" + o2.index.astype(str), "en": o2.term_en, "ar": o2.term_msa}),
        pd.DataFrame({"source": "gist", "set": "gist", "row_id": SOURCES["gist"]["repo_id"] + "#" + g["Index"].astype(str), "en": g.English, "ar": g.Arabic}),
        pd.DataFrame({"source": "ms", "set": "ms", "row_id": SOURCES["ms"]["repo_id"] + "#" + m.index.astype(str), "en": m.text_en, "ar": m.text_ar}),
    ]
    return pd.concat(frames, ignore_index=True).fillna("")


def stage2() -> dict:
    """Clean, normalise and deduplicate into data/interim/term_bank_clean.parquet. Logs every dropped row."""
    import re
    from collections import Counter

    import pandas as pd

    from data.text import ar_key, arabic_share, en_key, has_acronym, is_acronym_term, is_latin_only, keeps_acronym_only, normalise_ar, normalise_en, split_packed
    from server.glossary import slug

    verify_raw()
    df = _rows()
    report: dict = {"rows_in": int(len(df)), "rows_in_by_source": df.groupby("source").size().astype(int).to_dict()}

    df["en"] = df.en.map(normalise_en)
    df["ar"] = df.ar.map(normalise_ar)
    df["n_words"] = df.en.str.split().map(len)

    # Junk: logged, never silently dropped.
    reasons = pd.Series("", index=df.index)
    reasons[df.en == ""] = "empty English"
    reasons[(reasons == "") & ~df.en.str.contains(r"[A-Za-z]")] = "no letters in English"
    reasons[(reasons == "") & (df.en.str.len() <= 1)] = "single character"
    reasons[(reasons == "") & (df.n_words > MAX_TERM_WORDS)] = f"more than {MAX_TERM_WORDS} words (a UI sentence, not a term)"
    reasons[(reasons == "") & (df.ar == "")] = "empty Arabic"
    dropped = df[reasons != ""].assign(reason=reasons[reasons != ""])
    REPORTS.mkdir(parents=True, exist_ok=True)
    dropped[["source", "row_id", "en", "ar", "reason"]].to_csv(REPORTS / "dropped.csv", index=False)
    df = df[reasons == ""].copy()
    report["dropped"] = dropped.groupby("reason").size().astype(int).to_dict()

    df["key"] = df.en.map(en_key)
    df["prio"] = df.source.map(PRIORITY)
    df = df.sort_values(["prio", "row_id"], kind="stable")

    gist = df[df.source == "gist"]
    gist_word_uses = Counter(w for t in gist.en for w in set(re.findall(r"[a-z]+", t.lower())))

    out = []
    for key, d in df.groupby("key", sort=False):
        first = d.iloc[0]
        variants: list[str] = []
        for a in d.ar:
            for v in split_packed(a):
                if v not in variants:
                    variants.append(v)
        top = d[d.prio == d.prio.min()]
        if first.source == "ms":
            # MS often lists the same term several times: take its most common translation.
            counts = Counter(v for a in top.ar for v in split_packed(a))
            ar_display = sorted(counts, key=lambda v: (-counts[v], variants.index(v)))[0]
        else:
            ar_display = split_packed(first.ar)[0]
        sources = sorted({s for s in d.source}, key=PRIORITY.get)
        is_acr = is_acronym_term(first.en)
        untranslated = is_latin_only(ar_display) or keeps_acronym_only(ar_display) or ar_display.lower() == first.en.lower()
        highlight = first.source != "ms" or first.n_words > 1 or gist_word_uses.get(first.en.lower(), 0) >= MS_SINGLE_WORD_MIN_GIST_USES
        out.append(
            {
                "en": first.en,
                "en_key": key,
                "en_expanded": None,
                "is_acronym": bool(is_acr),
                "has_acronym": bool(has_acronym(first.en)),
                "ar_display": ar_display,
                "ar_full": None,
                "ar_variants": variants,
                "ar_key": ar_key(ar_display),
                "ar_origin": ORIGIN[first.source],
                "reviewed": first.source == "darby",
                "needs_review": False,
                "domain": DOMAIN[first.set],
                "sources": [f"{s}:{r}" for s, r in zip(d.source, d.row_id)],
                "source_names": sources,
                "has_full_card": first.source == "darby",
                "highlight": bool(highlight),
                "arabic_share": round(arabic_share(ar_display), 3),
                "stage3_reason": "acronym without expansion" if is_acr else ("untranslated" if untranslated else None),
            }
        )
    bank = pd.DataFrame(out)

    # Stable, readable ids. Darby terms keep their glossary slug; a case-only clash (IT vs it) gets a suffix.
    ids, seen = [], Counter()
    for en, key in zip(bank.en, bank.en_key):
        base = slug(en) or "term"
        seen[base] += 1
        ids.append(base if seen[base] == 1 else f"{base}-{seen[base]}")
    bank.insert(0, "id", ids)

    INTERIM.mkdir(parents=True, exist_ok=True)
    bank.to_parquet(INTERIM / "term_bank_clean.parquet", index=False)
    report.update(
        {
            "rows_after_drop": int(len(df)),
            "terms_out": int(len(bank)),
            "merged_rows": int(len(df) - len(bank)),
            "terms_by_first_source": bank.ar_origin.value_counts().astype(int).to_dict(),
            "multi_source_terms": int((bank.source_names.map(len) > 1).sum()),
            "highlight_terms": int(bank.highlight.sum()),
            "acronyms": int(bank.is_acronym.sum()),
            "stage3_queue": bank.stage3_reason.value_counts().astype(int).to_dict(),
            "packed_variant_terms": int((bank.ar_variants.map(len) > 1).sum()),
        }
    )
    (REPORTS / "stage2.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = [
        "# Stage 2: cleaning and normalisation",
        "",
        "Generated by `python -m data.pipeline stage2`.",
        "",
        "| Step | Rows |",
        "|---|---|",
        f"| Rows in (Darby {report['rows_in_by_source']['darby']}, GIST {report['rows_in_by_source']['gist']}, MS {report['rows_in_by_source']['ms']}) | {report['rows_in']} |",
        *[f"| Dropped: {k} (listed in `dropped.csv`) | {v} |" for k, v in report["dropped"].items()],
        f"| Rows after dropping | {report['rows_after_drop']} |",
        f"| Merged into an existing term (same `en_key`) | {report['merged_rows']} |",
        f"| **Terms out** | **{report['terms_out']}** |",
        "",
        f"First source of each term: {', '.join(f'{k} {v}' for k, v in report['terms_by_first_source'].items())}. "
        f"Terms found in more than one source: {report['multi_source_terms']}. Terms with several Arabic variants: {report['packed_variant_terms']}.",
        "",
        f"Highlighted by the term finder: {report['highlight_terms']} (MS single words only when GIST uses the word in at least {MS_SINGLE_WORD_MIN_GIST_USES} terms).",
        "",
        f"Stage 3 queue: {', '.join(f'{k} {v}' for k, v in report['stage3_queue'].items())}.",
        "",
        "Steps: Unicode NFC; Arabic presentation forms to standard letters; tatweel removed; Western digits; Arabic punctuation in Arabic fields; "
        "HTML stripped; whitespace collapsed; packed translations split into `ar_variants`; `ar_display` chosen as our reviewed term, then GIST, "
        "then the most common MS variant; deduplicated on `en_key` with every source kept in `sources`.",
    ]
    (REPORTS / "stage2.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return report


def verify_raw() -> None:
    """Fail loudly if a raw file is missing or changed since the manifest was written."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for name, entry in manifest["sources"].items():
        path = ROOT / entry["local_path"]
        if not path.exists():
            raise FileNotFoundError(f"{path} missing: run `python -m data.pipeline stage0`")
        if sha256(path) != entry["sha256"]:
            raise ValueError(f"{path} changed since the manifest (sha256 mismatch)")


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else ""
    if stage == "stage0":
        print(json.dumps(stage0(), ensure_ascii=False, indent=2))
    elif stage == "stage2":
        print(json.dumps(stage2(), ensure_ascii=False, indent=2))
    else:
        raise SystemExit(__doc__)
