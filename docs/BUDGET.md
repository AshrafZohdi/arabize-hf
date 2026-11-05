# Compute budget log

USD 100 shared credits. Every paid run is logged here (time in Qatar time, hardware, minutes, cost). Estimates in `docs/HF_PLAN.md`.

| Date and time | What | Hardware | Minutes | Cost (USD) | Notes |
|---|---|---|---|---|---|
| 2026-11-05 21:19 | Space `FayezAlkh12/darby` running (Docker needs PRO on free cpu-basic, so upgraded CPU) | cpu-upgrade, 8 vCPU, 32 GB, USD 0.03/h, sleeps after 1 idle hour | ongoing | about 0.03 per awake hour | Update the total when it is switched off or at judging |
| 2026-11-05 21:37 | Fanar endpoint `FayezAlkh12/darby-fanar` first boot: two failed starts (model path, then chat template), running from 21:50, verification calls, then idle until scale to zero | 1x L4 (AWS us-east-1), USD 0.80/h | about 35 (estimate until the billing page confirms) | about 0.47 | Measured 11.5 to 12.1 tokens/s generation, 150 tokens/s prompt |

Total spent: about USD 0.50 (endpoint estimate plus Space hours so far)
