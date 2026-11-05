# Darby (دربي): hackathon brief

Qai x Hugging Face Hackathon 01, Doha, 5 to 6 November 2026.

## The challenge

"Build an AI system that solves a real problem in Qatar. Must be grounded in Qatar or the wider Middle East, and run on Hugging Face. Projects that aren't clearly regional are disqualified." Themes: everyday life, government services, business, education, transport, culture, industry.

## The problem we solve

Arabic-speaking professionals in Qatar are expected to use AI at work, but the material, the tools and the vocabulary are all in English. An employee gets an email that says "check it for hallucinations and give the model more context in your prompt" and has no one to ask. Existing Arabic options are short government workshops, paid video courses, or scattered YouTube.

## The product

Darby (دربي, "my path") is a web app that teaches AI and its English vocabulary in simple Arabic or Gulf dialect, through short game mechanics. It runs entirely on Hugging Face. Its brain is Fanar 2, the Arabic model built in Qatar by QCRI, served on Hugging Face hardware. Every model, job, dataset and file runs on or lives on Hugging Face (see `docs/HF_PLAN.md`).

Pitch line: a Qatari model teaching Qataris the language of AI.

Name: Darby / دربي everywhere in the UI. The repo is `arabize-hf` (the old product was Arabize).

## Judging and budget

Judged on impact, use of Hugging Face, technical execution, efficiency of compute spend, and the demo. USD 100 of credits for the whole team. Use as many HF surfaces as genuinely help (Spaces, Endpoints, Jobs, Hub models, Hub datasets, a collection) and spend as little as possible. `docs/HF_PLAN.md` is binding for every infrastructure choice.

## Features, in build priority

Build in this order. Each one must be demoable before the next starts.

### P0-1. Smart Explain (the hero, the demo opens here)
- Learner pastes any English work text (email, report, Slack message), up to 2,000 characters.
- Known terms are found deterministically from the term bank (our glossary, GIST's 5,000 AI terms, the Microsoft software glossary; see `docs/HF_PLAN.md`), case-insensitive, plural and simple suffix forms, longest multi-word match first (Aho-Corasick or a trie). No AI needed for this step. Known terms show in teal ("in your dictionary"), new or AI-found terms in maroon ("new to you").
- "فهّمني" sends the text to Fanar, which returns JSON: a plain explanation of the text in the chosen language, a card per important term (term_en, term_ar, explanation, analogy, related terms), and one multiple-choice practice question with 4 options and the correct answer.
- Explanation language: EN, فصحى (simple MSA), or خليجي (simple Gulf). Seven explanation styles from the old repo (`school, life, technical, one_line, code, sentences, work`) as chips, default `work`.
- Every explanation ends in the practice question. Right answer: points and a small celebration. Wrong: show why, no telling-off.
- Save a term to "my dictionary" (local storage).
- Nothing the learner pastes is stored. Text that looks private (emails, phone numbers, QID-like numbers) gets a warning before sending.

### P0-2. Glossary (القاموس)
- All terms with English, MSA, Gulf usage, definition in both languages, analogy, common mistake, example sentence, related terms. Source: `content/glossary.json` (28 AI terms) and `content/terms-computing.json`.
- Search in both languages, filter by domain, a listen button per term (voice, see P1).
- Every term in the bank gets a full Arabic translation, acronyms included (A2C becomes الممثل والناقد ذو الميزة (A2C: Advantage Actor-Critic)); the cleaning, EDA and translation pipeline is in `docs/DATA_PIPELINE.md`.
- Choose about 100 office-relevant terms from GIST for full cards, using GIST's human Arabic as the MSA term. Expand the glossary to those terms in an HF Job (`jobs/generate_content.py`: full bf16 Fanar 2 with vLLM on 1x A100, explicit timeout), marked `"reviewed": false`, pushed straight to the Hub from inside the job. A team member spot-checks the Arabic.
- Publish the glossary as a Hugging Face Dataset (`<org>/darby-ai-glossary-ar-en`) with a dataset card. The Space loads it from the Hub at startup. This is a regional open resource and a strong judging point.
- Semantic search across both languages with `intfloat/multilingual-e5-small` on CPU, so "الأوامر" finds Prompt and "made-up facts" finds Hallucination.

### P0-3. AI tutor + prompt lab
- Tutor: chat scoped to the current lesson and glossary, answers in the learner's chosen language, streams tokens, refuses unrelated or unsafe requests politely, labels general knowledge as such. Cap 20 messages per session per IP.
- Prompt lab: learner writes a prompt for a real Doha work task (from the lesson's `prompt_lab` block). The model scores goal, context, format and constraints from 1 to 5 with feedback, and returns an improved prompt. Port the rubric and the escaping from `../arabaize/src/lib/ai/prompt-lab.ts`.

### P0-4. Your path (دربك) + daily code (شيفرة اليوم)
- Home screen: greeting, daily goal, streak and points, the daily code card, and the path of 7 lessons from `content/day-1.json` to `day-7.json` (done, current, locked), plus "3 terms to review today".
- Lesson player: one step per screen with a progress bar: hook, concept, example, term cards, exercises, prompt lab, recap. Missed exercises come back before the recap. Text in `en`, `ar` or `gulf` (gulf falls back to ar). Glossary terms in lesson text are marked `[[Prompt]]` or `[[Prompt|الأمر]]` and are tappable.
- Daily code: guess a one-word glossary term (3 to 9 letters) in 6 tries, English or Arabic, with its meaning in the other language as the clue. The server picks the word by date in Qatar time and marks guesses; the client never receives the answer before the game ends. A guess must be a real word (`content/words-en.json`, `content/words-ar.json`) or it is refused at no cost. Port normalisation and marking rules from `../arabaize/supabase/migrations/20261102000003_daily_code.sql` and `../arabaize/mobile/src/lib/learning.ts`. Shareable result grid that never shows the word. Do not call it Wordle.
- XP, streaks, mastery and progress live in local storage for the hackathon (no accounts). Use the XP rules from `../arabaize/CLAUDE.md`.

### P1. Voice (infrastructure now, switch on once P0 is solid)
- `/api/tts` and `/api/asr` behind a `VOICE_ENABLED` flag and a provider interface, so models can be swapped.
- English TTS: `hexgrad/Kokoro-82M` (Apache 2.0) in the browser through Transformers.js (`kokoro-js`), with a server copy in the Space as fallback (`pip install kokoro soundfile`, `apt espeak-ng`). Kokoro has no Arabic.
- Arabic TTS: `facebook/mms-tts-ara` (transformers `VitsModel`, CPU). Check `tokenizer.is_uroman`; if true, romanise with the `uroman` package first. Licence is CC BY-NC 4.0: fine for a hackathon demo, flag it in the README. If quality is poor, try `MBZUAI/speecht5_tts_clartts_ar`.
- ASR (later): `openai/whisper-large-v3-turbo` for asking the tutor by voice.
- Cache generated audio per term on disk so the glossary plays instantly in the demo. Pre-generate audio for all glossary terms at build or startup.

### Out of scope
Accounts, payments, Supabase, the Expo app, the App Store work, admin CMS, leaderboards.

## Tech

| Layer | Choice |
|---|---|
| Hosting | One Hugging Face Docker Space (`sdk: docker`, `app_port: 7860`), public, under the team's HF org |
| Frontend | Vite + React 19 + TypeScript + Tailwind CSS 4, built to static files and served by the backend |
| Backend | Python 3.11, FastAPI, uvicorn, pydantic v2, `huggingface_hub` |
| LLM | `QCRI/Fanar-2-27B-Instruct` for every feature: quantized GGUF on an HF Inference Endpoint (llama.cpp, 1x L4, scale to zero). All calls go through `huggingface_hub.InferenceClient` (OpenAI-compatible chat completions). See `docs/HF_PLAN.md` |
| LLM fallback | If the endpoint is waking or failing: a friendly "waking up" state and the offline `DEMO_MODE` fixtures. Kept warm during judging |
| Kernels | HF `kernels` used in the quality Job to benchmark Fanar with and without Hub kernels |
| Voice | Kokoro-82M (EN, in the browser), mms-tts-ara (AR, in the Space), glossary audio pre-generated in a Job and served from an HF Storage Bucket, Whisper (later) |
| More HF | Storage Buckets, Transformers.js, Gradio MCP server, smolagents tutor, Sign in with HF, scheduled Jobs: tiers and order in `docs/HF_PLAN.md` |
| Data | JSON content files in `content/`, the glossary also published as an HF Dataset. No database |

Environment variables (Space secrets): `HF_TOKEN`, `FANAR_ENDPOINT_URL`, `FANAR_MODEL` (default `QCRI/Fanar-2-27B-Instruct`), `HF_BUCKET` (audio and progress bucket), `VOICE_ENABLED`, `DEMO_MODE`.

### LLM rules
- One module, `server/llm.py`, owns every model call. Nothing else imports the client.
- Fanar 2 (and other reasoning models) can emit `<think>...</think>` blocks. Turn reasoning off in the request where supported, and always strip think blocks before parsing or streaming to the user.
- Structured answers (explain, prompt lab, practice questions) use JSON with a pydantic schema. Use guided decoding / `response_format` with a JSON schema when the endpoint supports it, otherwise ask for JSON, parse, validate, retry once, then fall back to a glossary-only answer. Temperature 0.3 for JSON, 0.6 for tutor chat.
- Learner text is data, never instructions: wrap it in tags and escape `<` and `>` (port `escapeLearnerText`).
- Timeouts: 30 s for JSON calls, streaming for the tutor. First token under 2 s is the target.
- In-memory rate limit per IP (for example 30 AI calls per 10 minutes). Cap input at 2,000 characters.
- `DEMO_MODE=1` or an endpoint failure serves recorded responses for the three demo inputs in `server/fixtures/`, so the pitch never breaks on stage. Record them from real Fanar output once the endpoint is up.
- Arabic terms: the word for "prompt" is أمر (plural الأوامر). Keep English terms in brackets after the Arabic term.

### Repo layout
```
arabize-hf/
  README.md            HF Space card (YAML front matter) + project readme
  Dockerfile           multi-stage: build web/, then python image serving it on 7860
  CLAUDE.md
  docs/BRIEF.md        this file
  docs/design/         design references and tokens
  content/             lessons, glossary, word lists (copied from ../arabaize/mobile/content)
  server/              FastAPI app: main.py, llm.py, prompts/, routes/, voice/, game/, fixtures/
  web/                 Vite React app
  scripts/             expand_glossary.py, push_dataset.py, pregen_audio.py
  tests/               pytest for server, vitest for web
```

## UI and UX

The old app's look is retired. The new direction is in `docs/design/` (open the two `.reference.html` files; they are design-canvas files, so read them as markup and inline styles, not as code to copy). Summary:

- Qatari colours with game mechanics: maroon as the brand, a cream sand page, white cards with a chunky bottom shadow, gold for points, flame for streaks, teal for known terms, green for correct.
- Arabic first, right to left. Use logical properties only (`ms-`, `pe-`, `start-`, `text-start`). English passages, code and prompts are always `dir="ltr"`. English terms inside Arabic sentences go in `<bdi>`. Western digits (0 to 9) everywhere.
- UI language toggle (AR, EN) and a separate explanation language (EN, فصحى, خليجي).
- Phone first: every screen works at 360 px with no horizontal scroll; at 360 px the page padding drops to 16 px and cards to 20 px.
- State is shown with an icon and words, never colour alone. Text contrast at least 4.5:1. Targets at least 44 px. Keyboard reachable. Reduce Motion respected.
- Small delights: points fly up on a right answer, the streak flame pulses, the current path node gently glows. Nothing loud.
- One home screen holds both: Smart Explain is the main column (the hero), and the daily code, the path (دربك) and the review banner sit in a side column. See `docs/design/home.reference.html`; `explain.reference.html` shows the explain result at full size.
- Navigation: الرئيسية (home), القاموس (glossary), المعلّم (tutor). Lessons open from the path.
- Headings use Readex Pro, not a heavy Kufi face.

## The demo (3 minutes)

1. Problem in one line, with a real-looking work email in English (15 s).
2. Paste it into Smart Explain in Gulf dialect: terms light up, Fanar explains, tap listen, answer the question, points fly (60 s).
3. Open the glossary, search "الهلوسة", play the pronunciation (20 s).
4. Ask the tutor a follow-up in Gulf Arabic, then score a prompt in the prompt lab (40 s).
5. Home: today's daily code and the path (20 s).
6. Show it all runs on Hugging Face: the Space, the Fanar endpoint, the quality and kernels results in the eval dataset, the published glossary dataset, total spend (20 s).
7. What's next: our own fine-tune of Fanar on consented, reviewed learner data; companies as customers (10 s).

## Writing style
No em dashes or en dashes anywhere (UI, docs, comments, commits). Plain factual wording; no invented numbers, users or testimonials. Commits have no AI co-author trailer or AI attribution.
