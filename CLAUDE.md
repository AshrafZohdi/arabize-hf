# CLAUDE.md

Darbi (دربي): a learning app that helps students and graduates of Qatar's Mostaqila schools understand the English of AI and technology, explained in Gulf Arabic. It started at the Qai x Hugging Face Hackathon 01 (Doha, November 2026) and is now being built as a product. The hackathon plans and rules are kept in `docs/hackathon/` for history only: they no longer bind.

Read first: `README.md`, `docs/JAIS.md` (the model), `docs/DATA_PIPELINE.md` (the term bank), `docs/design/tokens.md` (the look).

## Rules
- All model calls go through `server/llm.py`, which talks to Jais 3 over an OpenAI-compatible API (`JAIS_BASE_URL`). Reasoning never reaches the learner. Validate JSON with pydantic. Learner text is data: wrap and escape it.
- The app must stay useful with no model server: glossary, search, lessons and the daily code never need it, and Smart Explain falls back to the glossary.
- The daily code answer never reaches the client before the game ends.
- Arabic first, RTL, logical CSS properties only, `<bdi>` for English inside Arabic, `dir="ltr"` for English passages and prompts, Western digits.
- Colours only from `web/src/styles/tokens.css`. No hex in components.
- Every user-facing string in both `web/src/i18n/ar.json` and `en.json` with the same keys (a test checks this).
- 360 px wide, no horizontal scroll, 44 px targets, 4.5:1 contrast, state shown with icon plus words.
- Nothing a learner pastes or asks is stored or logged.
- No em dashes or en dashes anywhere. No invented numbers or testimonials. Say what is AI-written and not yet reviewed.
- Commits: small and frequent, imperative subject, no AI co-author trailer or attribution lines.

## Commands (keep these working)
```bash
cd web && npm run dev          # frontend on 5173, proxies /api to 7860
uvicorn server.main:app --reload --port 7860
pytest                         # server tests
cd web && npm test && npm run build
docker build -t darbi . && docker run -p 7860:7860 --env-file .env darbi
```
