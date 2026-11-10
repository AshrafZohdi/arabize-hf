# Running Darbi on Jais 3

Darbi's AI features (Smart Explain, the tutor, the prompt lab and translate) run on
[inception42/Jais-3-375B-A23B](https://huggingface.co/inception42/Jais-3-375B-A23B). Darbi does not load the model
itself. It talks to a model server over the OpenAI-compatible chat completions API, through `server/llm.py` and
nothing else.

## What the model needs

Facts from the model card (read 10 November 2026), not measured by us:

| | |
|---|---|
| Size | 375B parameters stored, 23B active per token (sparse Mixture of Experts), 512K context |
| Languages | Arabic and English |
| Licence | Apache 2.0, not gated |
| Hosted inference | None. The card says no Inference Provider serves it, so it has to be self-hosted |
| Reference hardware | 16 NVIDIA H100 (80 GB) across two 8-GPU nodes, or one 8-GPU H200 node |
| Servers | vLLM 0.30.0 or later, SGLang, Transformers. An FP8 build exists: `IFM/Jais-3-375B-A23B-FP8` |

This is a different scale from the 27B model Darbi used before, which ran on one A10G. Budget and hosting for the
model server are the main open decision for the product (see "Open questions" below).

## Start a server

vLLM, on one 8-GPU H200 node (from the model card; use `--tensor-parallel-size 16` on two H100 nodes):

```bash
vllm serve inception42/Jais-3-375B-A23B \
  --trust-remote-code --dtype bfloat16 \
  --tensor-parallel-size 8 --enable-expert-parallel \
  --reasoning-parser k2_horizon \
  --enable-auto-tool-choice --tool-call-parser k2_horizon \
  --api-key "$JAIS_API_KEY"
```

`--reasoning-parser k2_horizon` matters: it moves the model's thinking into `reasoning_content`, so only the answer
reaches the learner. Darbi also strips any `<think>` block that still arrives in the text, as a second line of defence.

## Point Darbi at it

```bash
JAIS_BASE_URL=http://<host>:8000/v1   # the API root, ending in /v1
JAIS_API_KEY=<the key you started the server with>   # leave empty if the server has none
```

Optional settings, with their defaults:

| Variable | Default | Meaning |
|---|---|---|
| `JAIS_MODEL` | `inception42/Jais-3-375B-A23B` | Model name sent in each request |
| `JAIS_REASONING_EFFORT` | `high` | Sent as `chat_template_kwargs.reasoning_effort` on every request, as the card asks. Empty leaves it to the server |
| `JAIS_TEMPERATURE` | `0.7` | The card's value for Arabic with thinking on (it gives 1.0 for English, 0.2 with thinking off) |
| `JAIS_MAX_TOKENS` | `32768` | Reasoning counts towards this, so it is the card's budget, not the length of an answer |
| `JAIS_TIMEOUT_S` | `180` | Time allowed for one answer |
| `AI_RATE_LIMIT`, `AI_RATE_WINDOW_S` | `60`, `600` | AI calls per client IP per window. `0` switches the limit off |

Every request also carries `top_p=0.95` and `top_k=20` from the card. Structured answers ask for
`response_format: {"type": "json_schema", ...}`; if the server rejects that, Darbi falls back to asking for JSON in
the prompt and validates the reply either way.

Check the connection at `/api/health`: `llm.state` is `unconfigured` (no URL), `unknown` (no call yet), `ready`,
`unavailable` (down, busy or timed out) or `error` (wrong URL, key or model name: see the server log).

## When the model is not reachable

Nothing breaks. Smart Explain still highlights terms and shows glossary cards and a glossary-built question, with a
note that Jais is not answering. The tutor, prompt lab and translate say they are unavailable. The glossary, search,
lessons, daily code and voice never need the model.

## Not verified yet

- **No request from Darbi has reached a real Jais 3 server.** The client is tested against a local stand-in that
  speaks the same wire format (see `tests/test_llm_wire.py`): URL, key, sampling settings, schema, streaming and
  `reasoning_content` handling. Prompts have not been tuned on real Jais output.
- Whether `response_format` with a JSON schema works together with the `k2_horizon` reasoning parser on vLLM.
- Latency. With reasoning at `high`, the first words of an answer arrive after the model finishes thinking. If that
  feels slow, try a lower effort; the card says `low` (no reasoning) is not recommended outside research.
- How well Jais 3 holds the Qatari Gulf dialect. `server/dialect.py` counts Gulf marker words in Gulf answers and the
  explain route reports the count (`dialect.gulf_markers`), so drift to Standard Arabic can be measured.

## Open questions

1. Where the model server runs and who pays for it. 8 H200 or 16 H100 around the clock is a serious cost; a shared
   endpoint from the model's publisher or a national compute programme may be the realistic route.
2. Whether the FP8 build is good enough for teaching use. At 8 bits per weight instead of 16 it should need about half the memory; the card gives no figures.
3. Whether a smaller model is the better default for a classroom pilot. The card calls this one the flagship of the Jais 3 family; we have not looked at the rest of the family. Any OpenAI-compatible server works: set `JAIS_MODEL` and `JAIS_BASE_URL`.
