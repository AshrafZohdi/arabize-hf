# Judging-day runbook

| | |
|---|---|
| App | https://fayezalkh12-darby.hf.space |
| Space repo | https://huggingface.co/spaces/FayezAlkh12/darby (deploys from `main` of the `space` remote) |
| GitHub | https://github.com/AshrafZohdi/arabize-hf |
| Fanar endpoint | `FayezAlkh12/darby-fanar`, https://endpoints.huggingface.co (1x A10G, USD 1.00/h, scale to zero after 15 min) |
| Image endpoint | `FayezAlkh12/darby-oryx-ig` (FLUX.1-schnell with the Fanar-2-Oryx-IG LoRA, custom handler `nuvais/darbi-oryx-ig-endpoint`, 1x L40S, about USD 1.80/h, scale to zero after 15 min). Space variable `ORYX_IG_URL` shows the Draw tab |
| Speech to text | Whisper small in the Space (CPU), Space variable `ASR_ENABLED=1` |
| Photo explain endpoint | `FayezAlkh12/darby-oryx-ivu` (Fanar-2-Oryx-IVU Q8_0, llama.cpp, 1x L4, about USD 0.80/h, scale to zero after 15 min). Framework `custom` with a custom image: the `llamacpp` framework downloads only the model GGUF and skips the 1.4 GB vision projector. Space variables `IMAGE_ENABLED=1` and `ORYX_IVU_URL` switch it on |
| Health | https://fayezalkh12-darby.hf.space/api/health |

## 30 minutes before the pitch

- `scripts/keep_warm.py` now keeps both Fanar and the Oryx photo reader awake (about USD 1.80/h together); `--fanar-only` skips the photo reader.
1. Open `/api/health`: `termbank.terms` 23999, `semantic_search` true, `voice_recordings` 280, `lessons.source` hub. If not, restart the Space (Settings, Restart) and wait about 2 minutes.
2. Wake Fanar at least 15 minutes early (cold start is about 4 minutes): `.venv/bin/python scripts/keep_warm.py` and leave it running until the pitch ends. `/api/health` shows `llm.state` ready after the first real call.
3. Clear the demo browser's site data (or use a private window) so points, streak and today's code start fresh.
4. Run the smoke test against the live Space: `cd web && BASE_URL=https://fayezalkh12-darby.hf.space npm run e2e` (12 checks, about 1 minute).

## Demo path (inputs that have recorded backups)
1. Home, خليجي: paste `Before you send the summary to the client, check it for hallucinations. Give the model more context in your prompt and ask it to cite the source paragraph.` Tap فهّمني. Answer the question (Hallucination). Tap EN and ع on the card.
2. Glossary: search `الهلوسة`, open the card, tap EN and ع. Search `made-up facts` to show meaning search.
3. المعلّم, lesson 1: `شلون أعرف إن الـ AI قاعد يهلوس في التقرير؟`. Then مختبر الأوامر, lesson 2: `اكتب إيميل عن سياسة الإجازات الجديدة`.
4. Home: today's code (any real word; it never shows the answer early) and دربك.
5. Hugging Face: the Space, the endpoint page, the datasets (`nuvais/darby-term-bank`, `nuvais/darby-ai-glossary-ar-en`, `nuvais/darby-lessons`), the bucket `FayezAlkh12/darby-media`, the MCP endpoint `/mcp-tools/gradio_api/mcp/`, `docs/BUDGET.md`.

## If Fanar is slow or down
- The app keeps working: Smart Explain shows a "waking up" note with a glossary answer and question; the demo inputs above return real Fanar answers recorded earlier.
- To force recorded answers for the whole pitch: Space Settings, Variables, set `DEMO_MODE=1` (the Space restarts, about 2 minutes). Set it back to `0` after.

## Rollback
- A bad deploy: `git revert <commit>` and push to both remotes, or in the Space's Files tab restore the previous commit. Last known good is the commit whose build log ends RUNNING and whose `/api/health` passes the checks above.
- Run `scripts/gate.sh` before every push (tests, builds, e2e and accessibility, Docker build, token scan).

## After judging
1. Stop `keep_warm.py`. The endpoint scales to zero after 15 idle minutes; to stop it for good, pause it on the endpoint page.
2. Check the billing page and write the real total into `docs/BUDGET.md`.
3. Optional: the Space runs on cpu-upgrade (USD 0.03/h, sleeps after 1 idle hour).

## Owner actions still open


- Create the collection `nuvais/darby` on the Hub (the API refused: new-account quota). Items: Space `FayezAlkh12/darby`; models `QCRI/Fanar-2-27B-Instruct`, `nuvais/Fanar-2-27B-Instruct-Q5_K_M-GGUF`, `intfloat/multilingual-e5-small`, `Xenova/mms-tts-ara`, `onnx-community/Kokoro-82M-v1.0-ONNX`; datasets `nuvais/darby-term-bank`, `nuvais/darby-ai-glossary-ar-en`, `nuvais/darby-lessons`, `Jerry999/multilingual-terminology`.
- Gulf Arabic review: `data/review/needs_review.csv` (priorities 1 to 3 first), the 100 Fanar cards, the recorded demo answers, and a listen to the voices.
- Raise the GitHub LFS budget if the screenshots should show on GitHub (`git lfs push origin --all`).
- Rotate the HF token that was pasted into `.env.example` (never committed).
