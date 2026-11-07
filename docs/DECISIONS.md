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

## D15. 2026-11-06: Voice without PyTorch in the Space
- Arabic: `facebook/mms-tts-ara` (CC BY-NC 4.0, fine for the hackathon demo, flagged in the README) through its ONNX export `Xenova/mms-tts-ara` (revision e9dd80f9) on ONNX Runtime, which the Space already has for search. `is_uroman` is false, so no romanisation. The VitsTokenizer is ported (vocabulary filter, blank token between characters). About 0.2 s per term on CPU after loading.
- English: Kokoro-82M (Apache 2.0) with `kokoro-js` in the learner's browser, loaded only on the first listen that has no recording (2.2 MB code chunk, gzipped 905 KB, plus the q8 model from the Hub). `kokoro-js` cannot pin a model revision; it follows main (1939ad2a when built).
- Pre-generated audio for all 140 cards, both languages, written by CPU Jobs straight into the public Storage Bucket `FayezAlkh12/darby-media` (mounted at `/out`; the Space repo mounted read-only at `/code`, so the Jobs run the app's own voice code). The Space redirects `/api/tts/term/{id}` to the bucket file; the browser prefers the recording over generating speech.
- Voice is behind `VOICE_ENABLED` (a Space variable, now on). `/api/asr` is a 501 stub for Whisper.

## D16. 2026-11-06: Darby as an MCP server
A Gradio app mounted in FastAPI at `/mcp-tools` with `mcp_server=True` exposes `lookup_term`, `explain_text` (deterministic, no model call, free) and `todays_code_clue` (clue and length, never the answer). It is mounted before the web app's catch-all route. Endpoint for MCP clients (streamable HTTP): `https://fayezalkh12-darby.hf.space/mcp-tools/gradio_api/mcp/`. Verified with the `mcp` Python client against the live Space. Gradio 6.31 needs pydantic 2.12.x, so the Space pins pydantic 2.12.5 (all tests pass on it).

## D17. 2026-11-06: Frosted Dunes redesign
The team supplied page mockups (`darby-frosted-dunes-mockups/`, kept out of git at 34 MB). Same tokens and fonts; only the surface and motion change.
- Page light (brand radial gradients, dune lines, grain) on a fixed layer behind glass cards (`.card`, `.glass`: surface 58%, blur 24px, white border, inner highlight, the ledge shadow).
- One section nav landmark: inside the header pill from 640 px, a fixed glass tab bar at the bottom on phones. The header glass sits on a background layer, because `backdrop-filter` on an ancestor would pin a fixed child to the header.
- Home: review and daily goal pills next to the greeting, the explanation language toggle inside the Smart Explain card, all 7 lessons on a numbered rail, "attempt k of 6" on the daily code, tiles flip only on the row just played.
- Daily goal: 30 points a day, counted per Qatar date in local storage. The old Arabize app had a per-day XP goal; 30 matches the mockup and is about two quick questions.
- Daily code win opens a modal over Home (trophy, the word, its meaning, points, streak, a share grid without the word, a countdown to the next Qatar midnight). The 404 page got the illustrated layout with links back.
- Tutor: a side column with three question templates filled with the lesson's key terms (not model generated) and the terms linked to the glossary. Only the recorded demo question has a fixture, so suggestions need the endpoint awake.
- Lesson: a lesson bar (lesson k of n, progress, minutes), a step rail on wide screens, and the finish screen with points, streak and lesson terms plus a next lesson button. The one step per screen flow is unchanged.
- Motion respects `prefers-reduced-motion`. axe covers the 404 and the open win dialog.

## D18. 2026-11-06: Highlights and term cards always match
Found in testing: the highlighter only knew the exact bank form, so RAG, PPO and even LLM were not highlighted, while Fanar wrote cards for them anyway. Highlights and the cards under "what the text means" came from different places and disagreed both ways.
- `data/curated/abbreviations.csv`: 39 common abbreviations, each mapped to a full term that exists in the bank (checked against the live bank). AR, CV and DL are left out because in work texts they usually mean Arabic, a resume and a download. Abbreviations keep their case like other acronyms.
- Fanar may only write cards for highlighted terms without a Darby card; the server drops any other model card.
- Every highlighted term gets a card: a Darby card, a Fanar card, or its term bank entry (English, Arabic, source, a note to ask the tutor). Tapping a highlighted word opens its card.

## D19. 2026-11-06: Polish from team testing
1. Lessons have a back button. Steps already passed stay passable; points are paid once and a missed exercise is queued for retry once.
2. The term card being read no longer swaps when Fanar's answer arrives: chips keep their order (new ones join at the end) and the choice is kept by term. A placeholder holds the quick question's place while Fanar finishes.
3. Term bank cards (no Darby or Fanar card) link to the tutor with "What does X mean?" filled in.
4. and 5. Abbreviations of 3 or more letters highlight in any case (rag, Rag, RAG); 2 letter ones stay case-sensitive so "it" and "us" are never caught. Glossary search finds abbreviations in any case and suggests the nearest term for a typo (Darby cards first, then the bank).
6. Listen buttons play recordings straight from the Storage Bucket (the recording list is fetched once from `/api/tts/recordings`) and the open card's audio is preloaded, instead of a redirect through the Space on every tap.
7. `data/curated/non_technical.csv`: 110 emoji, sticker, slang and everyday entries from the Microsoft terminology (for example "WTF…" and "a man and his dog") are left out of search, browse and highlighting. Picked with rules plus an E5 score (closer to everyday topics than to technical ones), then reviewed by hand to keep real terms such as "A record", "MAN" and "man-in-the-middle". Exact case, because "man" is an emoji and "MAN" a network. The published dataset is unchanged.

## D20. 2026-11-06: Second round of team testing
- Lessons: word order exercises in lessons 1, 3 and 5 rendered empty (their items are plain words, the view expected {en, ar}); fixed, and a test renders all 21 exercises in 3 languages and fails on any empty control. Lessons remember the step you left on and the furthest step reached; the step list (a collapsible list on phones) jumps to any step already reached.
- Prompt lab: switching the language keeps the prompt and its score; the task shows its English under the Arabic with key terms highlighted.
- Terms: `data/curated/additions.csv` adds programming languages (Python, JavaScript, TypeScript, Rust, Java, Kotlin, Ruby, PHP, C++ and C# in search only), multi-core processing terms, file extension, and switches on "script". Standard Arabic names, marked needs review. AI, API, SQL, HTML and CSS now match in lower case; .cpp, .py, .js, .ts and .rs highlight as their language.
- English audio: the recordings are 32-bit float at 24 kHz (3x the bytes of the Arabic ones), and cards without a recording downloaded Kokoro on the first tap. Cards now preload, and English without a recording uses an on-device system voice (localService only, nothing sent over the network) before falling back to Kokoro.
- Logo: the Arabic wordmark has its own line height so its dots no longer sit on "Darby".
- Not done: speech to text (needs Whisper on Hugging Face; the browser's built-in recognition sends audio to Google or Apple).
- Translate: `/api/translate` (Fanar, rate limited, learner text wrapped as data) behind a button on tutor replies, term cards (explanation and analogy) and the improved prompt in the prompt lab. Arabic goes to English; English goes to Gulf or Standard Arabic following the explanation language. Fetched once per text and cached in the page. No fixtures: with the endpoint asleep the button says Fanar is waking.
- Prompt lab: Fanar rewrote English prompts in Arabic; the prompt's language is now detected and stated next to the learner text (verified live: English prompt, English improved prompt, Gulf feedback).
- QA: `CROSS=1 npx playwright test` adds iPhone WebKit and desktop Firefox; the demo and axe suites pass on all four (Chromium phone and desktop, WebKit iPhone, Firefox desktop).

## D21. 2026-11-06: Third round of team testing
- The English name is spelled Darbi in everything people see (interface, page title, README, MCP tool text, model prompts). Repo, Space and dataset IDs keep `darby` so links do not break.
- Logo: Arabic and Latin names sit side by side on one baseline; stacked, the dots under the Arabic ran into the Latin name.
- Prompt lab: each criterion can score 0, and a text that is not a real prompt scores 0 on every criterion.
- Smart Explain: the text box always stays open; after explaining, the text shows again below it with tappable highlighted terms.
- Term cards: long Arabic terms wrap in their own column and never run under the listen buttons.
- Lessons only move forward: the rule that brought missed exercises back before the recap (from the old app) is removed, because it looked like being sent back to an earlier exercise. All 21 exercises keep their render test.

## D22. 2026-11-06: Photo explain and image prompts with QCRI's Oryx models
Approved by the team (plan points 2 and 3); speech to text waits for a decision (Whisper is the only open model on the Hub that understands Arabic; Hugging Face's own Distil-Whisper is English only).
- Photo explain: `QCRI/Fanar-2-Oryx-IVU` (image understanding, Apache 2.0, Qwen2.5-VL 7B base) as a Q8_0 GGUF with its vision projector on a llama.cpp endpoint (1x L4, scale to zero). The browser shrinks the photo to 1,600 px, Oryx copies the English text word for word plus one sentence on what the image shows, and the text goes into Smart Explain. Tested live: a rendered email read word for word in about 4 s, in all three languages. The projector repo file is named `.bin` and the endpoint framework is `custom`, because the `llamacpp` framework downloads only the model GGUF.
- Image prompts: a Draw tab. Fanar scores an image prompt on subject, setting, style and details and writes the improved prompt in English (Oryx-IG reads English), Fanar checks the prompt suits a workplace learning app (no sexual content, violence, hate, alcohol, weapons, real people by name or brands), then `QCRI/Fanar-2-Oryx-IG` (a LoRA on FLUX.1-schnell, 4 steps, 768 px) draws it on a custom-handler endpoint. Blocked until the FLUX.1-schnell terms are accepted on the account; the handler is in `hub/oryx-ig-endpoint`.
- Both sit behind `IMAGE_ENABLED`, off by default; buttons and tabs appear only when the Space reports them on. Images and photos are never stored or logged.

## D23. 2026-11-06: Speech to text, tutor photos, image generation live
- Speech to text: Whisper small (OpenAI's open weights, MIT; CTranslate2 build `Systran/faster-whisper-small` pinned to 536b0662) with `faster-whisper` on the Space CPU, behind `ASR_ENABLED`. Measured on CPU with an Arabic question: small about 1.5 s, medium about 7.6 s, large-v3-turbo about 7 s with the same words, so small. Hugging Face's own Distil-Whisper is English only. The browser records 16 kHz mono WAV with Web Audio (no new browser dependency), up to 30 s; nothing is stored. Mic buttons on Smart Explain, tutor, prompt lab and the Draw tab.
- Tutor: a photo button reads the photo with Oryx-IVU and puts "what does this text mean?" with the text into the message box.
- Image generation: endpoint `darby-oryx-ig` (1x L40S, custom handler in `nuvais/darbi-oryx-ig-endpoint`) runs after the FLUX.1-schnell terms were accepted. Tested live: 768 px images in about 3 s, culturally right; it does not always follow every detail (asked for a man and a woman, drew two men).

## D24. 2026-11-06: Layout and usability pass (design critique)
Screens captured at 360 and 1280 px in Arabic in real states, critiqued, fixed and recaptured. Colours and tokens unchanged.
- Smart Explain: the highlighted copy of the text moved from the input card to the top of the answer card (it showed the text twice), and on screens under 1,024 px the page scrolls to the answer when it starts. The seven style chips have a visible label and scroll sideways in one row on phones (they took three rows).
- Home: the path moved under Smart Explain in the main column and the daily code is the side column, sticky on wide screens; the columns were badly unbalanced.
- Glossary: 12 Darby cards first with "show all"; A to Z entries are compact (source and actions on one line); the letter strip scrolls sideways on phones; a shorter search placeholder that fits 360 px. The phone page is 34% shorter.
- Tutor: avatars only from 640 px, so replies use the bubble width on phones.
- Lesson bar: the progress bar has its own row, so the lesson title is not squeezed into two short lines.

## D25. 2026-11-06: Arabic card voice moves from mms-tts-ara to VoxCPM2
The team heard wrong pronunciations. Cause: mms-tts-ara's alphabet has no vowel marks, so it guesses every short vowel from bare consonants, and it learned from read religious text, not technical words. Bake-off on 12 card words, scored by Whisper large-v3 transcribing each clip (character error rate against the intended word): mms-tts-ara 0/12 exact, 40%; Chatterbox Multilingual 5/12, 67% (adds invented speech after short inputs); VoxCPM2 9/12, 8%. All 140 Arabic card recordings are re-made with VoxCPM2 (best of 3 takes by the same Whisper check; a word keeps its MMS file if that scored better), 24 kHz 16-bit, MMS files kept in `audio/ar-mms-backup`. Live Arabic speech for words without a recording is still mms-tts-ara on the Space CPU (VoxCPM2 needs a GPU). Result over all 140 words (Whisper large-v3, character error rate): VoxCPM2 1.4% with 134 exact against mms-tts-ara 40% with 13 exact on the same words. A follow-up Job retried the six weakest with vowel-marked spellings, which VoxCPM2 reads (for example أَمْر for prompt, which had failed every plain take): five became exact. Final: 139 of 140 words heard exactly; بت (bit) is the one left, still better than MMS. Scripts: `jobs/tts_bakeoff.sh`, `jobs/regen_audio_ar_voxcpm.sh`, `jobs/fix_audio_ar_short.sh`. Rollback: copy `audio/ar-mms-backup/*` back over `audio/ar/` and `manifest-ar.json`.

## D26. 2026-11-07: Audience and scope
Set by the team: "Darbi helps graduates of Qatar's Mostaqila schools understand the English language of AI and use AI well at work, explained in the Gulf dialect they speak every day." The sentence lives in `server/about.py` (English and Gulf Arabic). The tutor answers "what is Darbi" with it, every model prompt names this audience, the footer shows it, and the README, brief and Hub cards use it. `tests/test_about.py` fails if the interface text and the server sentence differ or the old wording ("professionals in Qatar") comes back in the app. Past Job scripts keep their original wording because they record how the data was made.
