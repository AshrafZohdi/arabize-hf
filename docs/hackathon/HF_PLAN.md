# Hugging Face usage, models and budget

Binding for every infrastructure and model choice. Goal: every piece of AI and compute runs on Hugging Face's own hardware, and we use as many HF products as genuinely add something to the product or the proof.

Judging criteria (from the organisers): 1 Impact and relevance, 2 Use of Hugging Face ("the system genuinely runs on HF infrastructure"), 3 Technical execution ("it actually works, end to end"), 4 Efficiency ("smart, resourceful use of the compute budget"), 5 Demo and pitch.

Credits: USD 100 per team, one shared pool, no top-ups. HF Jobs stop after 30 minutes by default; save results to the Hub from inside the job.

## Models

| Role | Model | Where it runs |
|---|---|---|
| The brain: Smart Explain, tutor, prompt lab, content | `QCRI/Fanar-2-27B-Instruct` (Qatar, QCRI, Apache 2.0) | Quantized GGUF (Q5_K_M, or Q4_K_M if memory is tight) on an HF Inference Endpoint, llama.cpp container, 1x L4, scale to zero after 15 idle minutes. Full bf16 only inside Jobs |
| Grader for the quality test (never shown to learners) | `openai/gpt-oss-120b` (open weights on the Hub) | vLLM inside the same HF Job as the test |
| English voice | `hexgrad/Kokoro-82M` | In the learner's browser through Transformers.js (`kokoro-js`), so live English audio costs no server compute; server copy in the Space as fallback |
| Arabic voice | `facebook/mms-tts-ara` (check `tokenizer.is_uroman`; licence CC BY-NC 4.0, fine for a demo, say so in the README) | In the Space on CPU; glossary audio pre-generated in a Job and served from an HF Storage Bucket |
| Semantic search | `intfloat/multilingual-e5-small` | In the Space on CPU (term vectors pre-computed in a Job and stored with the dataset) |
| Voice questions (P1) | `openai/whisper-large-v3-turbo` in the Space, or a small Whisper in the browser through Transformers.js | Space CPU or browser |

No Inference Providers, no outside AI APIs, never Fanar's own API (api.fanar.qa). If the Fanar endpoint is asleep or failing, the app shows a "waking up" state and serves `DEMO_MODE` fixtures; during judging the endpoint is kept warm so this never shows.

## Community datasets we build on

| Dataset | What it is | Licence | How we use it |
|---|---|---|---|
| `Jerry999/multilingual-terminology` (GIST) | About 5,000 English AI terms from award-winning papers at 18 top AI conferences (2000 to 2023), with human Arabic translations refined by GPT-4o (paper: arXiv 2412.18367). Columns `Index`, `English`, `Arabic`. CSV per language; the Hub viewer errors, so download `Arabic.csv` with `hf_hub_download` instead of `load_dataset` | Apache 2.0 | (1) Term bank for Smart Explain, so any of 5,000 AI terms is recognised, not only our 100. (2) Source of the MSA term when generating glossary cards: Fanar writes the Gulf usage, definition, analogy and example around the human translation instead of inventing the Arabic. (3) Eval metric: does Fanar use the standard Arabic term? (4) Credited in our dataset card. Many terms are research-level ("Bellman operator"); pick the about 100 card terms by relevance to office work. Spot-check the Arabic |
| `ymoslem/MS-Glossary-EN-AR` | English to Arabic part of the Microsoft software localization glossary, about 22,000 term pairs ("log off" تسجيل الخروج, "drop-down menu" قائمة منسدلة). Parquet; the card and viewer disagree on column names (`text_en`/`text_ar` vs `en_term`/`ar_term`/`en_def`), so inspect the file | Not stated on the card (team decision: use it for the hackathon) | Term bank for everyday software words in work emails (Excel, Teams, Outlook) and the computing course. Used fully in the app and Jobs, credited to Microsoft and to the uploader. Our published dataset references it by repo id instead of re-uploading its rows, which costs nothing in features |

Term bank rules (full pipeline, EDA, cleaning and acronym translation in `docs/DATA_PIPELINE.md`):
- Build `term_bank` in a Job: our glossary, then GIST, then MS, normalised (case, plurals, simple suffixes), deduped. Our reviewed choices win on conflicts (for example أمر for prompt), then GIST for AI terms, then MS for software terms. Keep a `source` field on every entry.
- Two levels in the UI: a full Darby card (our about 100 terms: Gulf, analogy, example, audio) or a quick card (term bank: English, Arabic, source, plus "ask Fanar to explain").
- Search vectors for the whole bank (about 27,000 terms) are computed once in a CPU Job with `multilingual-e5-small` and stored with the dataset.
- The published `term_bank` dataset holds our entries and GIST in full, and links to `ymoslem/MS-Glossary-EN-AR` for the Microsoft entries (the Space merges them at startup).

## Every HF product we use

### P0: core (build these as part of the normal build order)
| # | HF product | What we use it for |
|---|---|---|
| 1 | Spaces (Docker) | The Darby app: React frontend, FastAPI backend, Arabic TTS, search |
| 2 | Inference Endpoints | Fanar 2 27B, scale to zero |
| 3 | Hub models | Every model above, loaded from the Hub |
| 4 | Hub datasets | `<org>/darby-ai-glossary-ar-en` (with search vectors), `<org>/darby-lessons`, `<org>/darby-eval`. The Space loads glossary and lessons from the Hub at startup, so content lives on HF |
| 5 | Jobs | (a) Content generation with full Fanar (glossary to about 100 terms, Gulf versions, practice questions). (b) Audio and search-vector pre-generation. (c) Quality and kernels test |
| 6 | Kernels | Hub kernels benchmark inside the quality Job |
| 7 | Storage Buckets | Pre-generated audio for every term (and any other generated media), served to the app from the bucket. Read https://huggingface.co/docs/hub/storage-buckets first |
| 8 | Collection | `<org>/darby`: Space, datasets, bucket, models, eval and kernels results. Shown in the pitch |
| 9 | Dataset Viewer and cards | Proper dataset cards (bilingual description, fields, licence, how it was made, "AI-drafted, spot-checked") so the Hub pages look professional to judges |

### P1: after every P0 feature demos end to end
| # | HF product | What we use it for |
|---|---|---|
| 10 | Transformers.js | Kokoro English voice in the browser (`kokoro-js`); optionally a small Whisper in the browser for voice questions. Pitch point: "pronunciation runs on your own device, zero server cost" |
| 11 | Gradio MCP server | Mount a small Gradio app inside FastAPI (`gr.mount_gradio_app`) with `mcp_server=True`, exposing `lookup_term`, `explain_text` and `todays_code_clue` as tools, so any AI assistant can use Darby's Arabic AI glossary. Read the Gradio MCP and `mount_gradio_app` docs first |
| 12 | smolagents | The tutor as a small agent with tools (glossary lookup, current lesson lookup), running on Fanar, so its answers are grounded in our content |
| 13 | Sign in with Hugging Face | OAuth on the Space; progress (XP, streak, saved terms) saved per user as a small JSON file in the Storage Bucket. Without sign-in, progress stays in local storage as now |
| 14 | Scheduled Jobs | A CPU-basic Job each morning (Qatar time) that prepares the day's code word, clue and audio and pushes them to the Hub. Costs about USD 0.01 per run |
| 15 | QCRI's `FanarGuard` dataset | If its licence allows, add 10 of its Arabic safety cases to our eval to test the tutor's refusals. Check the licence first; skip if unclear |

### Stretch: only with time and budget left
| # | HF product | What we use it for |
|---|---|---|
| 16 | `QCRI/Fanar-2-Oryx-IVU` (image understanding) | Photo explain: snap a slide or English screen, Fanar reads it, Smart Explain runs. Second L4 endpoint, scale to zero |
| 17 | `QCRI/Fanar-2-Oryx-IG` (image generation) | A Job that draws one illustration per lesson in a Qatari setting, saved to the bucket |
| 18 | TRL + PEFT in a Job | LoRA fine-tune on Fanar's reviewed explain outputs, adapter pushed to the Hub with a model card. Pitched as the path to our own model |
| 19 | lighteval | Use it as the eval harness for the quality Job if our tasks fit it; otherwise keep the custom script |

## Quality and kernels Job (`jobs/bakeoff.py`)
Evidence for the pitch, not a model choice.
- Test set `<org>/darby-eval`: about 30 items written by us: 12 Smart Explain texts (scored in Gulf and MSA), 8 tutor questions in Gulf Arabic, 6 prompt lab prompts, 4 safety and refusal cases (plus FanarGuard items if allowed).
- Answers from full bf16 Fanar 2 (vLLM in the Job) and from our quantized endpoint. Graded by gpt-oss-120b, loaded in vLLM in the same Job after Fanar is unloaded, with a fixed rubric: valid JSON rate, technical accuracy, natural Gulf dialect, correct Arabic terms (أمر for prompt), refusals where expected. Plus latency and cost per 1,000 answers. A team member who speaks Gulf Arabic checks 10 answers by hand and we report agreement.
- Kernels: Fanar 2 in transformers on the same prompts with default attention, then with Hub kernels (for example `kernels-community/flash-attn3` on Hopper). Tokens per second, time to first token, peak memory, cost per 1,000 answers. Check `has_kernel(...)` first and fall back cleanly. Read https://huggingface.co/docs/kernels first.
- Hardware: 1x H200 (141 GB, USD 5 per hour; fits each model in turn and supports flash-attn3). Explicit timeout. Results pushed to `<org>/darby-eval` from inside the Job, and a table in the README.

## Budget (USD 100)

| Item | Estimate |
|---|---|
| Fanar endpoint, about 15 awake hours (dev, testing, judging) | 12 |
| Quality and kernels Job (2 runs, about 45 min each on H200) | 8 |
| Content generation, audio and vector Jobs | 6 |
| Scheduled daily Job | under 1 |
| Stretch (Oryx endpoint, image Job, LoRA) | up to 20 |
| Reserve | 50+ |

Rules:
- Never leave a GPU awake by accident. Scale-to-zero on every endpoint, an explicit timeout on every Job.
- Before any paid Job or endpoint, tell the team the hardware, timeout and expected cost.
- Log every paid run in `docs/BUDGET.md` (time, hardware, minutes, cost). This is evidence for criterion 4.
- Build against fixtures and a mock first; wake the endpoint only when real output is needed.
- Before judging: wake the endpoint 15 minutes early and keep it warm with a health ping until the pitch ends.
- Fonts are bundled in the app (self-hosted woff2 files), not loaded from Google, so the Space depends on nothing outside HF at run time.

## Pitch line for criteria 2 and 4
"Every part of Darby runs on Hugging Face. Its brain is Qatar's own Fanar 2 on an Inference Endpoint that sleeps when idle. Its content was generated, voiced and quality-tested in HF Jobs, with Hub kernels making inference faster, and it lives in open Hub datasets and a Storage Bucket. English pronunciation runs in your browser with Transformers.js, and any AI assistant can use our glossary through the Space's MCP server. Total compute spend: USD [X] of 100."
