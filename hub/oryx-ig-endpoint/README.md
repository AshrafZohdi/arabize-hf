---
license: apache-2.0
base_model:
- black-forest-labs/FLUX.1-schnell
- QCRI/Fanar-2-Oryx-IG
pipeline_tag: text-to-image
tags:
- inference-endpoints
- custom-handler
- darbi
---

# Fanar-2-Oryx-IG endpoint handler (Darbi)

A custom handler for a Hugging Face Inference Endpoint that serves [QCRI/Fanar-2-Oryx-IG](https://huggingface.co/QCRI/Fanar-2-Oryx-IG), QCRI's culturally aligned image generation LoRA, on its base model [black-forest-labs/FLUX.1-schnell](https://huggingface.co/black-forest-labs/FLUX.1-schnell) (Apache 2.0; gated, so the endpoint's token must have accepted its terms). No weights are stored here: the handler downloads both at start-up, with the versions the model card was tested with (diffusers 0.37.1, peft 0.18.1).

Request `{"inputs": "A falconer at Souq Waqif", "parameters": {"width": 768, "height": 768, "steps": 4, "seed": 1}}`, response `{"image": "<base64 JPEG>", "seed": 1, "width": 768, "height": 768}`.

Darbi (دربي) uses it for image prompts in its prompt lab: a learner writes a prompt for an image, Darbi scores it, and Oryx draws the improved prompt. Built for the Qai x Hugging Face Hackathon 01 in Doha.
