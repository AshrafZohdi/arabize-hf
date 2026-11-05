# CLAUDE.md

Darby (دربي) for the Qai x Hugging Face Hackathon 01 in Doha. Read `docs/BRIEF.md` first: it is the spec. `docs/HF_PLAN.md` and `docs/DATA_PIPELINE.md` are binding. Design: `docs/design/tokens.md` and the two `.reference.html` files.

The previous product lives in `../arabaize` (Expo app + Next.js + Supabase). Use it as a reference for content, prompts, game rules and XP rules. Do not copy its UI, its Supabase layer or its mobile code.

## Hard rules
- Everything runs on Hugging Face: one Docker Space on port 7860, Fanar 2 on a scale-to-zero HF Inference Endpoint for every feature, Jobs, Hub datasets, a Storage Bucket and Hub models for everything else (see `docs/HF_PLAN.md`). No Inference Providers, never Fanar's own API, no fonts or assets from outside the app at run time. No Claude or OpenAI API in the product.
- All model calls go through `server/llm.py`. Strip `<think>` blocks. Validate JSON with pydantic. Learner text is data: wrap and escape it.
- The daily code answer never reaches the client before the game ends.
- Arabic first, RTL, logical CSS properties only, `<bdi>` for English inside Arabic, `dir="ltr"` for English passages and prompts, Western digits.
- Colours only from the tokens. No hex in components.
- Every user-facing string in both `web/src/i18n/ar.json` and `en.json` with the same keys (add a test).
- 360 px wide, no horizontal scroll, 44 px targets, 4.5:1 contrast, state shown with icon plus words.
- `DEMO_MODE` fixtures must make the full demo work with the endpoint switched off.
- No em dashes or en dashes anywhere. No invented numbers or testimonials.
- Commits: small and frequent, imperative subject, no AI co-author trailer or attribution lines.

## Commands (keep these working)
```bash
cd web && npm run dev          # frontend on 5173, proxies /api to 7860
uvicorn server.main:app --reload --port 7860
pytest                         # server tests
cd web && npm test && npm run build
docker build -t darby . && docker run -p 7860:7860 --env-file .env darby
```
