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

Total spent: about USD 2.75 (endpoint estimates, four A100 Job runs, one CPU Job, Space hours; to be checked against the billing page)
