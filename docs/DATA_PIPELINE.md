# Term bank data pipeline

How the raw term sources become one clean, fully translated term bank. Treat this as a real data engineering task: inspect before transforming, keep raw data untouched, make every step reproducible, measure quality, and send real ambiguity to a human.

## Sources

| Source | Rows (approx.) | Arabic origin |
|---|---|---|
| `content/glossary.json` + `content/terms-computing.json` (ours) | 28 + computing terms | Written by us, reviewed choices |
| `Jerry999/multilingual-terminology` (GIST), file `Arabic.csv` (`Index`, `English`, `Arabic`) | about 5,000 AI terms | Human translation, refined with GPT-4o |
| `ymoslem/MS-Glossary-EN-AR` (Parquet; inspect real column names) | about 22,000 software terms | Microsoft localisation |

## Stage 0: raw snapshot
- Download each source with `huggingface_hub` (GIST: `hf_hub_download` of the CSV, since `load_dataset` fails on its mixed columns). Use the Dataset Viewer API or the `huggingface-datasets` skill to inspect splits and columns first.
- Save untouched copies under `data/raw/` with a manifest: repo id, revision (commit sha), file, row count, sha256. Never edit raw files.

## Stage 1: EDA (exploratory data analysis)
Write `notebooks/eda.ipynb` (executed, outputs saved) and a short `data/reports/eda.md`. At minimum:
- Row counts per source; nulls and empty strings per column.
- Duplicates: exact, case-insensitive, after normalisation; within and across sources.
- Untranslated rows: Arabic empty, Arabic identical to English, Arabic that is Latin script only, Arabic that keeps the English acronym with no Arabic words.
- Acronyms and short forms in English: all caps, digits mixed with letters (A2C, GPT-4, F1), slashes (A/B testing), dots (e.g., i.i.d.), plurals of acronyms (LLMs). Count them and list the top 50.
- Script analysis: share of Arabic characters per Arabic value, diacritics present, tatweel (ـ), Arabic presentation forms, mixed digits (Eastern Arabic vs Western), stray HTML, extra whitespace, odd punctuation.
- Multiple translations packed into one cell (separated by `;`, `/`, `،`, `or`, `أو`).
- Conflicts: the same English term with different Arabic across sources (expected between GIST and MS; list them).
- Length distributions (characters and words) to spot junk rows.
- Coverage: which terms actually appear in our 7 lessons, our demo emails, and typical office text; this guides which about 100 terms get full cards.
- Charts saved as images in `data/reports/`.

Share the EDA summary with the team before moving on.

## Stage 2: cleaning and normalisation
- Unicode NFC; convert Arabic presentation forms to standard letters; remove tatweel; collapse whitespace; strip HTML; Western digits; standard Arabic punctuation (، ؛ ؟) in Arabic fields.
- Split packed variants into `ar_variants` (list). Choose `ar_display` by rule: our reviewed choice, then GIST, then MS, then the most common variant.
- Keys for matching only, never for display:
  - `en_key`: lower case, punctuation-normalised, simple plural and suffix handling, acronyms kept exact (do not lower-case-merge "IT" with "it": acronym keys are case-sensitive).
  - `ar_key`: diacritics stripped, alef forms (أ إ آ) to ا, ى to ي, ة to ه.
- Deduplicate on `en_key`, merging variants and keeping every source in `sources`.
- Drop rows that are clearly junk (empty English, pure numbers, single characters), but log every dropped row with its reason in `data/reports/dropped.csv`.

## Stage 3: complete the translations (acronyms and untranslated terms)
Every term must have an Arabic translation of its full meaning, including short terms and acronyms. Transliteration alone is not a translation.

1. Find candidates: every row from Stage 1's untranslated and acronym lists.
2. Expand to the full English form (`en_expanded`):
   - First, deterministic: if the same source or another source has both the acronym and its long form, link them. Keep a small curated table `data/curated/expansions.csv` for common ones.
   - Then Fanar 2 (full bf16 in an HF Job, temperature 0, JSON schema output) with the term, its source domain (AI research for GIST, software for MS) and a few neighbouring terms as context.
   - If an acronym has several plausible expansions in the domain (for example SAC, PPO is fine, "MoE" is fine), set `needs_review` and list the options.
3. Translate the full form into Arabic (`ar_full`), using established Arabic technical terminology where it exists (prefer GIST and MS conventions, then standard usage); transliterate only established loanwords (for example بايثون), and then also give a meaning.
4. Build the display form: Arabic meaning first, original in brackets.
   - A2C: `الممثل والناقد ذو الميزة (A2C: Advantage Actor-Critic)`, possibly with a longer explanatory variant such as `خوارزمية الممثل والناقد بالاعتماد على الميزة`.
   - A/B testing: `اختبار المقارنة بين نسختين (A/B testing)`.
   - LLM: `نموذج لغوي كبير (LLM: Large Language Model)`.
   These are examples of the pattern, not final wording.
5. Check every generated translation automatically:
   - Back-translate `ar_full` to English with Fanar and compare it with `en_expanded` using `multilingual-e5-small` cosine similarity; below the threshold, set `needs_review`.
   - Reject outputs that are Latin-only, empty, or identical to the input.
6. Never overwrite a human translation. Stage 3 only fills gaps. Record `ar_origin`: `darby_editor`, `human_gist`, `human_ms`, or `fanar_generated`, plus `reviewed` (true or false).
7. Write the review queue to `data/review/needs_review.csv` (term, expansion options, proposed Arabic, reason) and ask the team's Arabic speaker to go through it. Apply their answers through `data/curated/overrides.csv`, which always wins.

## Output schema (`term_bank`)
`id`, `en`, `en_key`, `en_expanded`, `is_acronym`, `ar_display`, `ar_full`, `ar_variants`, `ar_key`, `ar_origin`, `reviewed`, `needs_review`, `domain` (ai, software, general), `sources` (list of repo id and row id), `has_full_card`, `embedding` (stored in a separate parquet column or file).

## Quality gates (pytest, run in CI and before publishing)
- No row without `ar_display`; no `ar_display` that is Latin-only.
- Every acronym has `en_expanded`.
- `en_key` unique.
- Every row has at least one source.
- Report, do not hide: counts before and after each stage, rows dropped, rows generated, rows needing review, back-translation similarity distribution.

## Running and publishing
- `data/pipeline.py` with one function per stage, deterministic and idempotent, cached between stages. Stages 0 to 2 run locally on CPU; Stage 3 and the embeddings run as an HF Job (explicit timeout, cost shown to the team first) and push results to the Hub from inside the Job.
- Publish `<org>/darby-term-bank` with a dataset card in English and Arabic: sources and licences, the EDA summary, every cleaning step, before and after counts, how translations were completed and checked, and known limits. Microsoft rows are referenced by repo id (the Space merges them at startup) rather than re-uploaded.
