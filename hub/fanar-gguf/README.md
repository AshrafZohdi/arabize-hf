---
license: apache-2.0
base_model: QCRI/Fanar-2-27B-Instruct
base_model_relation: quantized
language:
- ar
- en
library_name: gguf
pipeline_tag: text-generation
tags:
- gguf
- llama.cpp
- arabic
- qatar
- darby
---

# Fanar 2 27B Instruct, Q5_K_M GGUF (Darby)

A single-file copy of the static `Q5_K_M` quantization of [QCRI/Fanar-2-27B-Instruct](https://huggingface.co/QCRI/Fanar-2-27B-Instruct), the Arabic model built in Qatar by QCRI. The quantization was made by [mradermacher](https://huggingface.co/mradermacher/Fanar-2-27B-Instruct-GGUF) (file `Fanar-2-27B-Instruct.Q5_K_M.gguf`, revision `0816cf7f1da762a329b072fb8f8bf9e4b5622061`, sha256 `96bd98f19d9ae0151ce7737d3c23ef4de7f6f8c74cec0cffb332540033d7cfcc`). It was copied here unchanged so an Inference Endpoint downloads one 19.3 GB file instead of every quantization in the source repo.

It powers Darby (دربي), an app that teaches Arabic-speaking professionals in Qatar the language of AI, built for the Qai x Hugging Face Hackathon 01 in Doha.

## Serving

Darby runs it with llama.cpp's server on a Hugging Face Inference Endpoint (1x NVIDIA L4, 24 GB, scale to zero), OpenAI-compatible chat completions. Reasoning is switched off per request with `chat_template_kwargs: {"no_thinking": true}`, which Fanar 2's chat template supports.

Memory estimate with [hf-mem](https://github.com/alvarobartt/hf-mem): 19.3 GB of weights, plus 2.1 GB of KV cache at 8,192 tokens with an 8-bit cache.

## Chat template

`chat_template.jinja` is Fanar 2's own template from [QCRI/Fanar-2-27B-Instruct](https://huggingface.co/QCRI/Fanar-2-27B-Instruct/blob/074005040e9c3511b1c43b4298bef09908285534/chat_template.jinja) with one change: its `{% raw %}` block (the tool-calling instructions) is written as a string literal, because llama.cpp's Jinja engine does not support `raw`. The rendered prompt is identical for plain chat, `no_thinking` and tools (checked with jinja2). Pass it with `--chat-template-file` (or `LLAMA_ARG_CHAT_TEMPLATE_FILE`) and `--jinja`.

## Licence

Apache 2.0, the licence of the base model. All credit for the model goes to QCRI, and for the quantization to mradermacher.
