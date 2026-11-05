"""What goes into the public `nuvais/darby-term-bank`, and how the Space reads it back.

The Microsoft glossary is referenced, not re-uploaded (docs/HF_PLAN.md). So the public files hold:
  data/train.parquet            every term whose first source is ours or GIST, in full
  completions/ms.parquet        our stage 3 output for terms whose first source is Microsoft, keyed by a hash
                                (no Microsoft text in the file)
  embeddings/e5_small.parquet   search vectors for every term, keyed by the same hash
The Space rebuilds the Microsoft terms from `ymoslem/MS-Glossary-EN-AR` at the pinned revision and joins on the hash.
Job inputs and raw Job outputs live in the private `nuvais/darby-term-bank-staging`.
"""

from __future__ import annotations

import hashlib

PUBLIC_REPO = "nuvais/darby-term-bank"
STAGING_REPO = "nuvais/darby-term-bank-staging"
TRAIN_COLUMNS = [
    "id", "en", "en_key", "en_expanded", "is_acronym", "has_acronym", "ar_display", "ar_full", "ar_variants", "ar_key",
    "ar_origin", "reviewed", "needs_review", "review_issues", "domain", "sources", "source_names", "has_full_card", "highlight",
]
COMPLETION_COLUMNS = ["key", "en_expanded", "ar_full_generated", "needs_review", "review_issues"]


def key_hash(en_key: str) -> str:
    """Stable join key that does not reveal the term."""
    return hashlib.sha256(en_key.encode("utf-8")).hexdigest()[:16]


def is_ms_first(row) -> bool:
    names = list(row["source_names"])
    return bool(names) and names[0] == "ms"


def public_frames(final, embeddings=None):
    """Split the final bank (after stage 3 and overrides) into the public files."""
    import pandas as pd

    ms_first = final.apply(is_ms_first, axis=1)
    train = final[~ms_first][TRAIN_COLUMNS].reset_index(drop=True)
    # Keep only Arabic variants from our glossary and GIST: Microsoft's own wording stays in its repo.
    own = final[~ms_first]
    train["ar_variants"] = [[v for v, src in zip(vs, ss) if src != "ms"] for vs, ss in zip(own.ar_variants, own.ar_variant_sources)]
    ms = final[ms_first]
    touched = ms[ms.en_expanded.notna() | (ms.ar_origin == "fanar_generated") | ms.needs_review]
    completions = pd.DataFrame(
        {
            "key": touched.en_key.map(key_hash),
            "en_expanded": touched.en_expanded,
            "ar_full_generated": touched.ar_full.where(touched.ar_origin == "fanar_generated"),
            "needs_review": touched.needs_review.astype(bool),
            "review_issues": touched.review_issues.map(list),
        }
    ).reset_index(drop=True)
    emb = None
    if embeddings is not None:
        emb = pd.DataFrame({"key": embeddings.en_key.map(key_hash), "vector": embeddings.vector})
    return train, completions, emb


def apply_public(clean, train, completions, overrides):
    """In the Space: rebuild the final bank from the clean rebuild (all sources) plus the public files.
    Terms from ours or GIST come from `train` as published; Microsoft terms get our completions by hash."""
    import pandas as pd

    from data.pipeline import apply_overrides, display_form
    from data.text import ar_key, has_arabic

    ms_first = clean.apply(is_ms_first, axis=1)
    ms = clean[ms_first].copy()
    comp = completions.set_index("key")
    rows = []
    for r in ms.to_dict("records"):
        r["review_issues"] = []
        k = key_hash(r["en_key"])
        if k in comp.index:
            c = comp.loc[k]
            expanded = c["en_expanded"] if isinstance(c["en_expanded"], str) else None
            if r["is_acronym"]:
                r["en_expanded"] = expanded
            if isinstance(c["ar_full_generated"], str):
                r["ar_full"] = c["ar_full_generated"]
                r["ar_origin"] = "fanar_generated"
                r["reviewed"] = False
                r["ar_display"] = display_form(c["ar_full_generated"], r["en"], expanded)
            elif r["is_acronym"] and has_arabic(r["ar_display"]):
                r["ar_full"] = r["ar_display"]
                disputed = any("disagrees with the human Arabic" in str(i) for i in c["review_issues"])
                r["ar_display"] = display_form(r["ar_display"], r["en"], None if disputed else expanded)
            r["needs_review"] = bool(c["needs_review"])
            r["review_issues"] = list(c["review_issues"])
        r["ar_full"] = r.get("ar_full") or r["ar_display"]
        rows.append(r)
    ms_final = pd.DataFrame(rows)
    final = pd.concat([train, ms_final[TRAIN_COLUMNS] if len(ms_final) else ms_final], ignore_index=True)
    final = apply_overrides(final, overrides[overrides.id.isin(set(final.id))]) if len(overrides) else final
    final["ar_key"] = final.ar_display.map(ar_key)
    held = ~final.ar_display.map(has_arabic) | (final.is_acronym & final.en_expanded.isna())
    return final[~held].reset_index(drop=True)


CARD_TEMPLATE = """---
license: apache-2.0
language:
- ar
- en
pretty_name: Darby AI and software term bank (Arabic, English)
size_categories:
- 1K<n<10K
task_categories:
- translation
tags:
- arabic
- terminology
- glossary
- qatar
- ai
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train.parquet
---

# Darby term bank: AI and software terms in Arabic and English

<div dir="rtl" lang="ar">

## بنك مصطلحات دربي

مصطلحات الذكاء الاصطناعي والبرمجيات بالإنجليزي والعربي، لتطبيق «دربي» الذي يعلّم الموظفين في قطر لغة الذكاء الاصطناعي بعربي بسيط أو باللهجة الخليجية. كل مصطلح له ترجمة عربية تشرح معناه، والاختصارات لها اسمها الكامل، مثل: نموذج لغوي كبير (LLM: Large language model).

- مصدر كل ترجمة مذكور: مراجعة فريق دربي، أو ترجمة بشرية من GIST، أو مسرد مايكروسوفت، أو ترجمة كتبها نموذج «فنار 2» القطري.
- ما كتبه «فنار» معلَّم بـ `reviewed = false`، وما يحتاج مراجعة بشرية معلَّم بـ `needs_review = true`.
- صنعناه في هاكاثون Qai x Hugging Face في الدوحة، نوفمبر 2026.

</div>

## What this is

{published_own:,} English terms with Arabic, from Darby's own reviewed glossary and from GIST, plus our completions for Microsoft glossary terms. Every term has an Arabic meaning (not only a transliteration), acronyms have their full English form, and every row says where its Arabic came from.

Built for Darby (دربي), an app that teaches Arabic-speaking professionals in Qatar the vocabulary of AI at work, at the Qai x Hugging Face Hackathon 01 in Doha (November 2026). The app runs on Hugging Face and uses Qatar's Fanar 2 model.

## Files

| Path | What |
|---|---|
| `data/train.parquet` | {published_own:,} terms whose first source is Darby's glossary or GIST, all fields |
| `completions/ms.parquet` | Our stage 3 output (full English forms, Arabic written by Fanar 2, review flags) for {ms_completions:,} Microsoft glossary terms, keyed by `sha256(en_key)[:16]` |
| `embeddings/e5_small.parquet` | `intfloat/multilingual-e5-small` vectors (384 dimensions) for all {all_terms:,} terms, same key |
| `curated/` | Hand-made tables: acronym expansions, reviewer overrides (always win), Arabic aliases |
| `reports/` | EDA and cleaning reports with before and after counts |

The Microsoft glossary is referenced, not re-uploaded: rebuild those rows from [`ymoslem/MS-Glossary-EN-AR`]({ms_url}) at revision `{ms_rev}` with `data/pipeline.py` in the [Darby repo]({github}) and join our completions on the hash of `en_key`. The Darby app does this at startup.

## Fields (`data/train.parquet`)

| Field | Meaning |
|---|---|
| `id` | Stable slug |
| `en` | English term as written in the source |
| `en_key` | Matching key: lower case, singular, hyphens as spaces; acronyms keep their case (IT is not it) |
| `en_expanded` | Full English form of an acronym (A2C: Advantage Actor-Critic) |
| `is_acronym` / `has_acronym` | The term is a short form / the term contains one ("USB port") |
| `ar_display` | Arabic for display: meaning first, original in brackets for acronyms and generated translations |
| `ar_full` | Arabic meaning without the brackets |
| `ar_variants` | Other Arabic translations from Darby and GIST |
| `ar_key` | Arabic matching key: no diacritics, unified alef, ى and ة |
| `ar_origin` | `darby_editor`, `human_gist`, `human_ms` or `fanar_generated` |
| `reviewed` | A person checked this Arabic (Darby's own terms and reviewer overrides) |
| `needs_review` / `review_issues` | Automatic checks flagged the row, and why |
| `domain` | `ai` or `software` |
| `sources` / `source_names` | Every source row merged into this term |
| `has_full_card` | Darby has a full learning card for it |
| `highlight` | Darby's term finder highlights it in pasted text |

## How it was made

1. **Snapshot.** Each source downloaded at a pinned revision and checked by sha256: Darby's glossary ({rows_darby} terms), GIST `Jerry999/multilingual-terminology` Arabic.csv ({rows_gist:,} rows, Apache 2.0) and the Microsoft glossary ({rows_ms:,} rows).
2. **EDA.** Duplicates, untranslated rows, acronyms, script problems (tatweel, presentation forms, mixed scripts), packed translations, conflicts between sources and noise in real text. Key findings: GIST copies the English as the Arabic for {gist_same} terms (for example AI, API, CamemBERT); the sources disagree on core terms (prompt: Darby أمر, GIST موجه, Microsoft مطالبة); Microsoft single words would mark 31.5 words in every 100 of ordinary work text, so only the ones GIST also uses in at least 5 AI terms are highlighted.
3. **Cleaning.** Unicode NFC, presentation forms to standard letters, tatweel removed, Western digits, Arabic punctuation, packed translations split, duplicates merged on `en_key` (Darby, then GIST, then Microsoft wins), {dropped} UI sentences dropped and logged. {rows_in:,} rows became {terms_out:,} terms.
4. **Completion with Fanar 2** (`QCRI/Fanar-2-27B-Instruct`, bf16, vLLM, in an HF Job). {acronyms} acronyms got a full English form and {translated} terms without an Arabic meaning got one. Checks: every translation back-translated by Fanar and compared with `multilingual-e5-small` (threshold 0.85); every expansion checked against the term bank in the same domain and against the human Arabic where one exists. That second check caught GCC: Fanar said Gulf Cooperation Council, the Microsoft Arabic says Government Community Cloud. Flagged rows: {needs_review}. Rows still without an Arabic meaning are held back from this release ({held}).
5. **Review.** A Gulf Arabic speaker on the team goes through the review queue; decisions go into `curated/overrides.csv`, which always wins.

## Known limits

- Fanar-written Arabic and descriptions of model and dataset names are not reviewed unless `reviewed` is true. Expansions of rare research acronyms may be wrong; those that no source confirms are flagged.
- Microsoft entries are software localisation terms, some outside AI (currencies, medical tests).
- GIST's Arabic for some AI terms differs from Darby's choices (for example موجه for prompt); Darby's reviewed choices win for its own terms, and prompt terms that do not use أمر are flagged.
- Search vectors come from a small model that leans on shared words more than meaning.

## Licence and credit

Our data: Apache 2.0. GIST: Apache 2.0, Jiarui Liu et al., [arXiv 2412.18367](https://arxiv.org/abs/2412.18367). Microsoft glossary: Microsoft localisation terminology via [`ymoslem/MS-Glossary-EN-AR`]({ms_url}) (licence not stated on its card; referenced, not redistributed). Fanar 2 by QCRI, Apache 2.0.
"""


def write_public(folder, final, embeddings, reports_dir, curated_dir, numbers: dict) -> None:
    """Write the public dataset folder: parquet files, curated tables, reports, card."""
    import shutil
    from pathlib import Path

    folder = Path(folder)
    train, completions, emb = public_frames(final, embeddings)
    for sub in ("data", "completions", "embeddings", "curated", "reports"):
        (folder / sub).mkdir(parents=True, exist_ok=True)
    train.to_parquet(folder / "data" / "train.parquet", index=False)
    completions.to_parquet(folder / "completions" / "ms.parquet", index=False)
    if emb is not None:
        emb.to_parquet(folder / "embeddings" / "e5_small.parquet", index=False)
    for name in ("expansions.csv", "overrides.csv", "aliases.csv"):
        shutil.copy(Path(curated_dir) / name, folder / "curated" / name)
    # dropped.csv and the review queue name Microsoft rows, so they stay out of the public repo.
    for name in ("eda.md", "eda_lengths.png", "stage2.md", "stage3.md"):
        if (Path(reports_dir) / name).exists():
            shutil.copy(Path(reports_dir) / name, folder / "reports" / name)
    numbers = numbers | {"published_own": len(train), "ms_completions": len(completions)}
    (folder / "README.md").write_text(CARD_TEMPLATE.format(**numbers), encoding="utf-8")
