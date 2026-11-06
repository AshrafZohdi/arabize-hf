# Compute budget log

USD 100 shared credits. Every paid run is logged here (time in Qatar time, hardware, minutes, cost). Estimates in `docs/HF_PLAN.md`.

| Date and time | What | Hardware | Minutes | Cost (USD) | Notes |
|---|---|---|---|---|---|
| 2026-11-05 21:19 | Space `FayezAlkh12/darby` running (Docker needs PRO on free cpu-basic, so upgraded CPU) | cpu-upgrade, 8 vCPU, 32 GB, USD 0.03/h, sleeps after 1 idle hour | ongoing | about 0.03 per awake hour | Update the total when it is switched off or at judging |
| 2026-11-05 21:37 | Fanar endpoint `FayezAlkh12/darby-fanar` first boot: two failed starts (model path, then chat template), running from 21:50, verification calls, then idle until scale to zero | 1x L4 (AWS us-east-1), USD 0.80/h | about 35 (estimate until the billing page confirms) | about 0.47 | Measured 11.5 to 12.1 tokens/s generation, 150 tokens/s prompt |
| 2026-11-05 21:59 | Fanar endpoint moved to A10G (team decision, about 2x faster for USD 0.20/h more), speed and streaming tests, then idle until scale to zero | 1x A10G (AWS us-east-1), USD 1.00/h | about 25 (estimate) | about 0.42 | Measured 22.5 tokens/s generation, 238 tokens/s prompt |
| 2026-11-05 22:40 | Fanar endpoint woken (cold start 236 s) for a 2 x 14 row preview of the stage 3 prompts, then idle until scale to zero | 1x A10G, USD 1.00/h | about 25 (estimate) | about 0.42 | Preview found invented expansions (CLS, CEAS, FLR) and led to the corroboration and human-Arabic checks |
| 2026-11-05 22:57 | Stage 3 Job `darby-stage3` (job 6aecdfb5c78863f9c6338f17): expand 265 acronyms, translate untranslated terms, back-translation check | 1x A100 80 GB, USD 2.50/h, timeout 45 min | about 4 running (22 queued, not billed) | about 0.17 | Failed after loading the model: vLLM needed nvcc for a FlashInfer JIT kernel, which the uv image lacks |

| 2026-11-05 23:20 | Stage 3 Job rerun (job 6aece4f6c78863f9c63392c7): 265 expansions, 101 translations, back-translation and source checks | 1x A100 80 GB, USD 2.50/h | 4.2 (139 s model load, 49 s generation) | about 0.18 | Completed; results pushed |
| 2026-11-05 23:10 | Search vectors Job `darby-embed` (job 6aece2d1c78863f9c633914d): 24,000 terms, e5-small ONNX | cpu-upgrade, USD 0.03/h | about 2 | under 0.01 | 71 s |
| 2026-11-06 01:54 | Cards Job `darby-cards` (job 6aed0936c78863f9c633aef4): rate 1,528 GIST candidates, write 100 cards | 1x A100 80 GB, USD 2.50/h, timeout 30 min | 5.7 | about 0.24 | Worked, but the selection tie-broke alphabetically; not used |
| 2026-11-06 02:01 | Cards Job rerun (job 6aed0ac9c78863f9c633afe7): two scores, Gulf instruction | 1x A100 80 GB, USD 2.50/h, timeout 30 min | 7.1 | about 0.30 | 100 cards, 0 failures, in private staging for a look before publishing |
| 2026-11-06 02:10 | Fanar endpoint woken by the first live Space call (cold start about 4 min), one explain verified end to end, then idle until scale to zero | 1x A10G, USD 1.00/h | about 20 (estimate) | about 0.33 | First text 2.8 s, full answer 12.3 s through the Space |
| 2026-11-06 15:55 | Arabic term audio Job `darby-audio-ar` (job 6aedce470e0338d1bb814bae): 140 cards, mms-tts-ara ONNX | cpu-upgrade, USD 0.03/h | 4.1 | under 0.01 | Written into the bucket `FayezAlkh12/darby-media` |
| 2026-11-06 15:55 | English term audio Job `darby-audio-en`: first run failed (module path), rerun (job 6aedceb3c78863f9c6344f3a) 140 cards with kokoro-js | cpu-upgrade, USD 0.03/h | 15 | under 0.01 | Same engine and voice as the browser |
| 2026-11-06 12:30 | Fanar endpoint awake for live tutor and prompt lab tests and recordings, then idle until scale to zero | 1x A10G, USD 1.00/h | about 30 (estimate) | about 0.50 | |
| 2026-11-06 20:55 | Copy Job: Q8_0 GGUF and vision projector of Fanar-2-Oryx-IVU into `nuvais/Fanar-2-Oryx-IVU-Q8_0-GGUF` (job 6aee1449c78863f9c634e6ed), sha256 checked | cpu-basic | about 6 | under 0.01 | |
| 2026-11-06 21:05 | Endpoint `FayezAlkh12/darby-oryx-ivu` created for photo explain (Fanar-2-Oryx-IVU Q8_0, llama.cpp with `--mmproj`) | 1x L4, about USD 0.80/h, scale to zero after 15 min | first boot and tests | about 0.30 (estimate) | Approved by the team (plan point 2) |
| 2026-11-06 21:30 | Endpoint `FayezAlkh12/darby-oryx-ig` created for image prompts (FLUX.1-schnell with the Fanar-2-Oryx-IG LoRA, custom handler `nuvais/darbi-oryx-ig-endpoint`) | 1x L40S, about USD 1.80/h, scale to zero after 15 min | first boot (about 35 GB download) and tests | about 0.80 (estimate) | Approved by the team (plan point 3) |
| 2026-11-06 22:00 | Arabic voice comparison Job (job 6aee2b81c78863f9c6351d21, rerun 6aee2c480e0338d1bb821068 after a script naming mistake): Chatterbox Multilingual and VoxCPM2 against mms-tts-ara on 12 card terms, scored by Whisper large-v3 | a10g-small, USD 1.00/h, 30 min timeout | up to 30 | under 0.50 | Approved by the team |
| 2026-11-06 22:20 | Re-record the 140 Arabic card words with VoxCPM2 (job 6aee30820e0338d1bb8216fb, 637 s), then retry the six weakest with vowel marks (job 6aee354b0e0338d1bb821e33, 300 s), Whisper-checked, MMS files backed up | a10g-small, USD 1.00/h | 16 | about 0.27 | Approved by the team |

Total spent: about USD 3.70 (endpoint estimates, four A100 Job runs, one CPU Job, Space hours; to be checked against the billing page)
