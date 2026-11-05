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
