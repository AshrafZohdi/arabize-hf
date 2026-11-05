"""Term bank pipeline (docs/DATA_PIPELINE.md). One function per stage, deterministic and idempotent.

    python -m data.pipeline stage0     raw snapshot + manifest
    python -m data.pipeline stage2     clean, normalise, dedupe -> data/interim/term_bank_clean.parquet

Stage 1 (EDA) is notebooks/eda.ipynb. Stage 3 (acronym expansion and translation) runs as an HF Job.
Raw files are never edited.
"""

from __future__ import annotations

import hashlib
import re
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
REPORTS = ROOT / "data" / "reports"
MANIFEST = ROOT / "data" / "manifest.json"
PROCESSED = ROOT / "data" / "processed"
REVIEW = ROOT / "data" / "review"
CURATED = ROOT / "data" / "curated"
TERM_BANK_REPO = "nuvais/darby-term-bank"
OVERRIDE_FIELDS = {"ar_display", "ar_full", "en_expanded", "reviewed", "needs_review", "drop"}

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


def build_clean(df):
    """Stage 2 as a pure function: rows (source, set, row_id, en, ar) to (bank, dropped, report).
    Used by `stage2()` and by the Space, which rebuilds the bank in memory from the pinned sources."""
    import re
    from collections import Counter

    import pandas as pd

    from data.text import ar_key, arabic_share, en_key, has_acronym, is_acronym_term, is_latin_only, keeps_acronym_only, normalise_ar, normalise_en, split_packed
    from server.glossary import slug

    df = df.copy()
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
        variant_sources: list[str] = []
        for a, src in zip(d.ar, d.source):
            for v in split_packed(a):
                if v not in variants:
                    variants.append(v)
                    variant_sources.append(src)
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
                "ar_variant_sources": variant_sources,
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
    for en in bank.en:
        base = slug(en) or "term"
        seen[base] += 1
        ids.append(base if seen[base] == 1 else f"{base}-{seen[base]}")
    bank.insert(0, "id", ids)
    report["rows_after_drop"] = int(len(df))
    return bank, dropped, report


def stage2() -> dict:
    """Clean, normalise and deduplicate into data/interim/term_bank_clean.parquet. Logs every dropped row."""
    verify_raw()
    bank, dropped, report = build_clean(_rows())
    REPORTS.mkdir(parents=True, exist_ok=True)
    dropped[["source", "row_id", "en", "ar", "reason"]].to_csv(REPORTS / "dropped.csv", index=False)
    INTERIM.mkdir(parents=True, exist_ok=True)
    bank.to_parquet(INTERIM / "term_bank_clean.parquet", index=False)
    report.update(
        {
            "terms_out": int(len(bank)),
            "merged_rows": int(report["rows_after_drop"] - len(bank)),
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


def display_form(ar: str, en: str, expanded: str | None) -> str:
    """Arabic meaning first, the original in brackets: الممثل والناقد ذو الميزة (A2C: Advantage Actor-Critic)."""
    original = f"{en}: {expanded}" if expanded and expanded.lower() != en.lower() else en
    if en.lower() in ar.lower():
        return ar
    return f"{ar} ({original})"


def apply_overrides(bank, overrides):
    """Reviewer decisions from data/curated/overrides.csv always win. Columns: id, field, value, reviewer, note."""
    bank = bank.copy()
    for o in overrides.itertuples():
        if o.field not in OVERRIDE_FIELDS:
            raise ValueError(f"override field {o.field!r} not allowed")
        if o.id not in set(bank.id):
            raise ValueError(f"override for unknown id {o.id!r}")
        if o.field == "drop":
            bank = bank[bank.id != o.id]
            continue
        value = {"true": True, "false": False}.get(str(o.value).lower(), o.value) if o.field in ("reviewed", "needs_review") else o.value
        bank.loc[bank.id == o.id, o.field] = value
        bank.loc[bank.id == o.id, "reviewed"] = True if o.field != "reviewed" else value
        bank.loc[bank.id == o.id, "needs_review"] = False if o.field != "needs_review" else value
    return bank


# Darby's term for prompt (AI sense) is أمر (plural أوامر), docs/BRIEF.md. The command-line sense is left alone.
PROMPT_AI_SENSE = re.compile(r"\b(?:prompt|prompts|prompting)\b", re.I)
PROMPT_OTHER_SENSE = re.compile(r"\b(?:command|elevation|consent|credential|ms-dos|tele)", re.I)


def terminology_issues(en: str, ar: str, domain: str) -> list[str]:
    if PROMPT_AI_SENSE.search(en) and not PROMPT_OTHER_SENSE.search(en) and not re.search("أمر|أوامر", ar):
        return ["terminology: Darby uses أمر for prompt"]
    return []


def review_priority(r) -> int:
    """1 prompt terminology, 2 held back, 3 AI terms, 4 software disagreements, 5 other software, 6 name descriptions."""
    issues = r["issues"]
    if "terminology" in issues:
        return 1
    if r["held_back"]:
        return 2
    if "description of a name" in issues:
        return 6
    if r["domain"] == "ai":
        return 3
    return 4 if "disagrees" in issues else 5


def merge_stage3(bank, res, overrides):
    """Stage 3 merge as a pure function: (clean bank, Job results, overrides) to (final, published, held).
    Rows still without an Arabic meaning, or acronyms without an expansion, are held back from `published`."""
    import pandas as pd

    from data.text import ar_key, has_arabic

    res = res.set_index("id") if "id" in res.columns else res
    rows = []
    for r in bank.to_dict("records"):
        x = res.loc[r["id"]] if r["id"] in res.index else None
        if x is not None:
            expanded = x.get("en_expanded") if isinstance(x.get("en_expanded"), str) else None
            if r["is_acronym"]:
                r["en_expanded"] = expanded
            if isinstance(x.get("ar_full"), str):
                r["ar_full"] = x["ar_full"]
                r["ar_origin"] = "fanar_generated"
                r["reviewed"] = False
                r["ar_display"] = display_form(x["ar_full"], r["en"], expanded)
            elif r["is_acronym"] and has_arabic(r["ar_display"]):
                r["ar_full"] = r["ar_display"]
                # A disputed expansion stays out of the display: the human Arabic meaning is shown on its own.
                disputed = any("disagrees with the human Arabic" in str(i) for i in x["issues"])
                r["ar_display"] = display_form(r["ar_display"], r["en"], None if disputed else expanded)
            r["needs_review"] = bool(x["needs_review"])
            r["review_issues"] = [str(i) for i in x["issues"]]
        else:
            r["ar_full"] = r["ar_full"] or r["ar_display"]
            r["review_issues"] = []
        if r["ar_origin"] != "darby_editor":
            issues = terminology_issues(r["en"], r["ar_display"], r["domain"])
            if issues:
                r["review_issues"] = list(r["review_issues"]) + issues
                r["needs_review"] = True
        rows.append(r)
    final = apply_overrides(pd.DataFrame(rows), overrides)
    final["ar_key"] = final.ar_display.map(ar_key)
    held_mask = ~final.ar_display.map(has_arabic) | (final.is_acronym & final.en_expanded.isna())
    published = final[~held_mask].drop(columns=["stage3_reason"])
    return final, published, final[held_mask]


def stage3(results_path: Path | None = None) -> dict:
    """Merge the stage 3 Job results (pushed to the Hub) into the clean bank, apply overrides, write the final
    bank and the review queue."""
    import pandas as pd

    bank = pd.read_parquet(INTERIM / "term_bank_clean.parquet")
    if results_path is None:
        from huggingface_hub import hf_hub_download

        results_path = Path(hf_hub_download(TERM_BANK_REPO, "stage3/results.parquet", repo_type="dataset"))
    res = pd.read_parquet(results_path)
    overrides = pd.read_csv(CURATED / "overrides.csv", dtype=str).fillna("")
    final, published, held = merge_stage3(bank, res, overrides)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    published.to_parquet(PROCESSED / "term_bank.parquet", index=False)

    queue = final[final.needs_review | final.index.isin(held.index)].copy()
    queue["held_back"] = queue.index.isin(held.index)
    queue["issues"] = queue.review_issues.map("; ".join)
    queue["priority"] = queue.apply(review_priority, axis=1)
    review_cols = ["priority", "id", "en", "domain", "ar_origin", "en_expanded", "ar_display", "held_back", "issues"]
    queue.sort_values(["priority", "en"])[review_cols].to_csv(REVIEW / "needs_review.csv", index=False)

    report = {
        "terms_in": int(len(bank)),
        "stage3_rows": int(len(res)),
        "fanar_translations": int((final.ar_origin == "fanar_generated").sum()),
        "acronyms_expanded": int(final.en_expanded.notna().sum()),
        "needs_review": int(final.needs_review.sum()),
        "held_back": int(len(held)),
        "published": int(len(published)),
        "overrides_applied": int(len(overrides)),
    }
    (REPORTS / "stage3.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def publish(folder: Path = ROOT / "data" / "public") -> dict:
    """Write the public dataset folder from the final bank (stage 3 merge) and the staging vectors."""
    import pandas as pd
    from huggingface_hub import hf_hub_download

    from data.publish import STAGING_REPO, write_public

    bank = pd.read_parquet(INTERIM / "term_bank_clean.parquet")
    res = pd.read_parquet(hf_hub_download(STAGING_REPO, "stage3/results.parquet", repo_type="dataset"))
    overrides = pd.read_csv(CURATED / "overrides.csv", dtype=str).fillna("")
    final, published, held = merge_stage3(bank, res, overrides)
    emb = pd.read_parquet(hf_hub_download(STAGING_REPO, "embeddings/e5_small.parquet", repo_type="dataset"))
    s2 = json.loads((REPORTS / "stage2.json").read_text(encoding="utf-8"))
    eda = json.loads((REPORTS / "eda_summary.json").read_text(encoding="utf-8"))
    numbers = {
        "rows_darby": s2["rows_in_by_source"]["darby"], "rows_gist": s2["rows_in_by_source"]["gist"], "rows_ms": s2["rows_in_by_source"]["ms"],
        "gist_same": eda["untranslated"]["gist"]["ar_same_as_en"], "dropped": sum(s2["dropped"].values()), "rows_in": s2["rows_in"],
        "terms_out": s2["terms_out"], "acronyms": int(final.en_expanded.notna().sum()), "translated": int((final.ar_origin == "fanar_generated").sum()),
        "needs_review": int(final.needs_review.sum()), "held": int(len(held)), "all_terms": int(len(emb)),
        "ms_url": "https://huggingface.co/datasets/" + SOURCES["ms"]["repo_id"], "ms_rev": SOURCES["ms"]["revision"],
        "github": "https://github.com/AshrafZohdi/arabize-hf",
    }
    # Publish exactly what the Space shows: the held-back rows stay out.
    write_public(folder, published.assign(ar_variant_sources=final.loc[published.index, "ar_variant_sources"]), emb, REPORTS, CURATED, numbers)
    stage3_md = [
        "# Stage 3: completing the translations",
        "",
        f"Fanar 2 (bf16, vLLM, HF Job on 1x A100) on {len(res)} queued terms. Full English forms: {numbers['acronyms']}. "
        f"Arabic written by Fanar: {numbers['translated']}. Flagged for review: {numbers['needs_review']}. Held back (no Arabic meaning yet): {numbers['held']}. "
        f"Reviewer overrides applied: {len(overrides)}.",
        "",
        "Checks: back-translation similarity with multilingual-e5-small (threshold 0.85); every expansion compared with the term bank in the same domain "
        "and with the human Arabic where one exists; prompt terms that do not use أمر flagged.",
    ]
    (REPORTS / "stage3.md").write_text("\n".join(stage3_md) + "\n", encoding="utf-8")
    import shutil

    shutil.copy(REPORTS / "stage3.md", folder / "reports" / "stage3.md")
    return {"folder": str(folder.relative_to(ROOT)), **numbers}


def hub_rows():
    """The same rows as `_rows()`, read from the Hub at the pinned revisions (no local raw files): for the Space."""
    import pandas as pd
    from huggingface_hub import hf_hub_download

    frames = []
    for name in ("darby_glossary", "darby_computing"):
        frames.append(read_source(name))
    g = pd.read_csv(hf_hub_download(SOURCES["gist"]["repo_id"], SOURCES["gist"]["filename"], repo_type="dataset", revision=SOURCES["gist"]["revision"]), dtype=str, keep_default_na=False)
    m = pd.read_parquet(hf_hub_download(SOURCES["ms"]["repo_id"], SOURCES["ms"]["filename"], repo_type="dataset", revision=SOURCES["ms"]["revision"]))
    o1, o2 = frames
    return pd.concat(
        [
            pd.DataFrame({"source": "darby", "set": "darby_glossary", "row_id": "glossary.json#" + o1.index.astype(str), "en": o1.term_en, "ar": o1.term_msa}),
            pd.DataFrame({"source": "darby", "set": "darby_computing", "row_id": "terms-computing.json#" + o2.index.astype(str), "en": o2.term_en, "ar": o2.term_msa}),
            pd.DataFrame({"source": "gist", "set": "gist", "row_id": SOURCES["gist"]["repo_id"] + "#" + g["Index"].astype(str), "en": g.English, "ar": g.Arabic}),
            pd.DataFrame({"source": "ms", "set": "ms", "row_id": SOURCES["ms"]["repo_id"] + "#" + m.index.astype(str), "en": m.text_en, "ar": m.text_ar}),
        ],
        ignore_index=True,
    ).fillna("")


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
    elif stage == "publish":
        print(json.dumps(publish(), ensure_ascii=False, indent=2))
    elif stage == "stage3":
        print(json.dumps(stage3(Path(sys.argv[2]) if len(sys.argv) > 2 else None), ensure_ascii=False, indent=2))
    else:
        raise SystemExit(__doc__)
