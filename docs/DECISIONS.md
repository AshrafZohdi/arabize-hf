# Decisions

Newest last. Each entry: what, why, what was rejected.

## D1. 2026-11-05: No router library
The app has four routes (home, glossary, tutor, lesson). A 40 line pushState router in `web/src/lib/router.tsx` covers links and back/forward. Rejected: react-router (one more dependency for no extra feature we use). FastAPI serves `index.html` for every non-API, non-file path so deep links work.

## D2. 2026-11-05: Fonts from @fontsource packages
Readex Pro, IBM Plex Sans Arabic and IBM Plex Sans come from `@fontsource/*` npm packages. Vite copies the woff2 files into the build, so the Space loads no font from outside at run time (HF_PLAN rule). Only the Arabic and Latin subsets and the weights in `tokens.md` are imported.

## D3. 2026-11-05: i18n without a library
Flat JSON files `web/src/i18n/ar.json` and `en.json` with the same keys, plural forms through `Intl.PluralRules` (Arabic has zero, one, two, few, many, other). A vitest checks identical keys and plural shapes, and no em or en dashes and no Eastern Arabic digits. Rejected: i18next (bigger than the problem).

## D4. 2026-11-05: Tokens as CSS variables mapped into Tailwind 4
`web/src/styles/tokens.css` is the only file with hex values. `index.css` maps them into Tailwind's `@theme` and resets the default palette (`--color-*: initial`), so a component cannot use a Tailwind colour that is not a token.

## D5. 2026-11-05: Pinned versions
Python deps pinned in `requirements.txt` (runtime) and `requirements-dev.txt` (tests). npm deps installed with `--save-exact` and locked in `package-lock.json`; the Docker build uses `npm ci`. Python 3.11 in the container and locally (`uv venv --python 3.11`).

## D6. 2026-11-05: Hub namespaces split by billing
The USD 100 credits are on Fayez's personal account (`FayezAlkh12`, can pay); the team org `nuvais` ("Nuvai Hackaton 01") has no billing. Team decision: paid compute (the Space, the Fanar endpoint, Jobs, the Storage Bucket) lives under `FayezAlkh12` so it bills the credits; datasets (`nuvais/darby-term-bank`, `nuvais/darby-ai-glossary-ar-en`, `nuvais/darby-lessons`, `nuvais/darby-eval`) and the collection `nuvais/darby` live under the org, since they cost nothing. Rejected: everything under the org (blocked until it can pay), everything personal (no team presence on the Hub).

## D7. 2026-11-05: How llm.py talks to Fanar
- Reasoning off with `extra_body={"chat_template_kwargs": {"no_thinking": True}}`: Fanar 2's `chat_template.jinja` (revision 074005040e9c) then adds an empty think block. Think blocks are still stripped from every reply and stream (`strip_think`, `ThinkStripper`).
- Schema-guided JSON with `response_format={"type": "json_object", "schema": ...}`, the shape llama.cpp's server turns into a grammar. Not `json_schema`: huggingface_hub 2.4 rewrites that into TGI's `{"value": ...}` when `base_url` is set, which llama.cpp ignores; `tests/test_llm_wire.py` runs the real client against a local stub to catch this. If the endpoint rejects `response_format`, it is dropped for the life of the process and the JSON instruction in the prompt does the work.
- Cold or failing endpoint (5xx, 429, timeout, connection error): state becomes `waking` (shown in `/api/health`), and the call serves a matching fixture or raises `LLMUnavailable` for the route to show the waking-up state. 4xx errors are not hidden.
- One retry with the validation error on bad JSON, then `LLMBadOutput` (the route falls back to the glossary-only answer).

## D8. 2026-11-05: Two remotes, LFS objects only on Hugging Face
`origin` is GitHub (`AshrafZohdi/arabize-hf`), `space` is the HF Space (`FayezAlkh12/darby`). HF rejects plain binaries, so images and audio are tracked with Git LFS. The GitHub account is over its LFS budget, so pushes to GitHub skip the LFS upload (`GIT_LFS_SKIP_PUSH=1 git push origin main`): code is complete on GitHub, and screenshots there are pointer files until the budget is raised and `git lfs push origin --all` is run. The HF Space repo holds every LFS object.

## D9. 2026-11-05: Fanar endpoint setup and first measurements
- Model repo `nuvais/Fanar-2-27B-Instruct-Q5_K_M-GGUF`: the static Q5_K_M file from `mradermacher/Fanar-2-27B-Instruct-GGUF` (revision 0816cf7f, sha256 checked), copied server side with `hf repos cp` so the endpoint downloads 19.3 GB instead of every quant in the source repo. Static rather than imatrix quant because we could not check whether the imatrix calibration text covers Arabic.
- Fanar 2's chat template uses `{% raw %}`, which llama.cpp's Jinja engine rejects. The repo carries `chat_template.jinja` with that block written as a string literal; rendering is identical for plain chat, `no_thinking` and tools (checked with jinja2). The endpoint loads it with `LLAMA_ARG_CHAT_TEMPLATE_FILE`.
- Endpoint `FayezAlkh12/darby-fanar`: llama.cpp server image, 1x L4, 2 slots of 4,096 tokens, q8_0 KV cache, flash attention, scale to zero after 15 minutes. `modelPath` is relative to `/repository`.
- Measured on 1x L4: 11.5 to 12.1 tokens/s generation, about 150 tokens/s prompt processing, prompt prefix cache works (965 of 970 tokens cached on a repeat). A full Smart Explain answer (572 tokens, 3 cards) took 51 s. Valid JSON first try with the schema grammar, no think block, used أمر for prompt, but wrote MSA when asked for Gulf.

## D10. 2026-11-05: A10G, streaming, and glossary cards before model cards
- Team decision: the Fanar endpoint runs on 1x A10G (USD 1.00/h) instead of 1x L4 (0.80/h). Measured 22.5 vs 11.5 tokens/s generation and 238 vs 150 tokens/s prompt; same Q5_K_M model and settings.
- Explain streams: `llm.json_stream` sends the `explanation` field as it is written (first text at 3.0 s on A10G), then validates the full object.
- A full answer with 3 model-written cards was about 650 tokens (31.5 s). So terms that already have a Darby glossary card get that card directly, and Fanar writes cards only for important terms the glossary does not cover (at most 2). Fields are ordered explanation, question, cards so the question arrives early.
- The Gulf request is spelled out with everyday Gulf words and an example sentence, placed last in the system prompt; one line saying "Gulf dialect" produced MSA. The word list needs a check by a Gulf Arabic speaker.

## D11. 2026-11-05: Term bank cleaning rules (stages 0 to 2)
- Sources pinned by revision in `data/pipeline.py`; raw files re-download exactly and are checked by sha256 against `data/manifest.json` (raw, interim and processed data are not in git).
- MS column names are `text_en`/`text_ar` (the card's other names do not exist in the file). GIST is read as text only.
- Highlighting: MS single words caused almost all noise (31.5 matches per 100 words of lesson text; multi-word MS terms 0.5). MS single words are highlighted only when GIST uses the word in at least 5 of its terms: the demo email then marks exactly model, context, prompt and source, and send, client, check and more stay plain. Every term stays searchable in the glossary.
- "Acronym" means the term itself is a short form (SAC, A2C, GPT-4, LLMs, F1, A/B testing, i.i.d.), not any term containing one ("USB port"): 265 acronyms need `en_expanded`; a separate `has_acronym` flag marks the rest.
- Rows over 8 words are UI sentences, not terms: 52 dropped, each logged in `data/reports/dropped.csv`.
- Arabic conflicts are compared with `ar_compare_key` (no diacritics, unified alef, ى, ة, no leading ال), so المصدر and مصدر agree.

## D12. 2026-11-05: Publishing the term bank without re-uploading Microsoft rows
- Public `nuvais/darby-term-bank`: our and GIST terms in full (`data/train.parquet`), our stage 3 output for Microsoft terms (`completions/ms.parquet`) and search vectors, both keyed by `sha256(en_key)[:16]`. Arabic variants that came from Microsoft are removed from our rows. `dropped.csv` and the review queue stay out (they name Microsoft rows).
- Job inputs and raw Job outputs live in the private `nuvais/darby-term-bank-staging`. The first private `nuvais/darby-term-bank` had the cleaned Microsoft rows in its history, so (team decision) it was deleted after checking every file was in staging, and recreated public with a clean history.
- The Space rebuilds all terms at startup from the pinned sources with `data/pipeline.py` and joins the public files on the hash (`data/publish.py`; a test checks the round trip equals the direct merge and that no Microsoft text is in the public files).

## D13. 2026-11-05: Semantic search design
Measured: multilingual-e5-small ranks shared words above meaning across the whole bank ("made-up facts": fact table 0.87, Hallucination 0.82). Search order is now: word matches (with curated Arabic aliases, for example الأوامر for Prompt from the brief), then up to 3 Darby cards close in meaning (cards re-embedded with their definitions in English and Arabic), then whole-bank meaning matches only at 0.88 or more. Query vectors come from the ONNX export with ONNX Runtime (identical to sentence-transformers, cosine 1.0 on test strings), so the Space has no PyTorch. A larger embedding model would do better; not switched without a team decision.

## D14. 2026-11-06: Incident: Space down about 11 minutes (12:19 to 12:30 UTC)
- What happened: a test file I added used Node's `fs` and `path`; the web TypeScript build (no Node types) failed in the Space Docker build, and the Space served 503 until the fix built.
- Root cause: I pushed after running the web tests but not the full build. The test runner (vitest) does not typecheck; `tsc -b` in the build does.
- Fix: the check now reads sources with Vite's `import.meta.glob` (no Node types). Full gate passed (pytest, web tests, web build, Docker build) before the fix was pushed.
- Prevention: `scripts/gate.sh` runs every check the Space build depends on, plus a scan for tokens in the staged diff; it runs before every push.
- The bug the test was guarding: Chrome 155 returns a Promise from `scrollIntoView`; an effect with an expression body handed it to React as a cleanup ("destroy is not a function") and blanked the tutor page after sending. Fixed with braced effects, a regression test that mimics the Promise, and the source check.
