---
license: apache-2.0
base_model: QCRI/Fanar-2-Oryx-IVU
base_model_relation: quantized
language:
- ar
- en
library_name: gguf
pipeline_tag: image-text-to-text
tags:
- gguf
- llama.cpp
- vision
- arabic
- qatar
- darbi
---

# Fanar 2 Oryx IVU, Q8_0 GGUF with vision projector (Darbi)

A two-file copy of the `Q8_0` quantization and the f16 vision projector of [QCRI/Fanar-2-Oryx-IVU](https://huggingface.co/QCRI/Fanar-2-Oryx-IVU), QCRI's Arabic-first image and video understanding model (based on Qwen2.5-VL 7B). The quantization was made by [mradermacher](https://huggingface.co/mradermacher/Fanar-2-Oryx-IVU-GGUF) at revision `3dbf1c82aa4298aff7ddc41862e5315dcdd8d0b2`:

| File | Size | sha256 |
|---|---|---|
| `Fanar-2-Oryx-IVU.Q8_0.gguf` | 8.1 GB | `7ab8ad3377b7ec3efd4567684ce9c290db9443f1cdd9fceffb81f8820a5fd62d` |
| `Fanar-2-Oryx-IVU.mmproj-f16.bin` (source name `Fanar-2-Oryx-IVU.mmproj-f16.gguf`) | 1.4 GB | `31c701d2b14e467c73c8694006e8d9166c2b896639aab58ca62853cb66153e71` |

They were copied here unchanged so an Inference Endpoint downloads two files instead of every quantization in the source repo. The projector carries a `.bin` name because a llama.cpp endpoint downloads only the chosen `.gguf` plus non-GGUF files; llama.cpp reads it by its contents.

It powers photo explain in Darbi (دربي), an app that teaches Arabic-speaking professionals in Qatar the language of AI: a learner photographs an English screen, slide or email and Darbi reads it, then explains it in Gulf Arabic. Built for the Qai x Hugging Face Hackathon 01 in Doha.

## Serving

llama.cpp's server on a Hugging Face Inference Endpoint (1x NVIDIA L4, scale to zero) with `LLAMA_ARG_MMPROJ=/repository/Fanar-2-Oryx-IVU.mmproj-f16.bin`, OpenAI-compatible chat completions with `image_url` content.
