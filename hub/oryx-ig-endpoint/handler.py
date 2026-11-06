"""Hugging Face Inference Endpoint handler: FLUX.1-schnell with QCRI's Fanar-2-Oryx-IG LoRA (culturally aligned image
generation for the Gulf). Input {"inputs": prompt, "parameters": {"width", "height", "steps", "seed"}}, output
{"image": base64 JPEG, "seed"}. Settings from the model card: guidance 0, 2 to 6 steps, trained at 1024x1024."""

import base64
import io
import os
import random

import torch
from diffusers import FluxPipeline

BASE = "black-forest-labs/FLUX.1-schnell"
LORA = "QCRI/Fanar-2-Oryx-IG"


class EndpointHandler:
    def __init__(self, path: str = ""):
        token = os.environ.get("HF_TOKEN")
        self.pipe = FluxPipeline.from_pretrained(BASE, torch_dtype=torch.bfloat16, token=token)
        self.pipe.load_lora_weights(LORA, weight_name="Fanar-2-Oryx-IG.safetensors", token=token)
        self.pipe.to("cuda")

    def __call__(self, data: dict) -> dict:
        prompt = str(data.get("inputs", "")).strip()[:1000]
        if not prompt:
            return {"error": "empty prompt"}
        p = data.get("parameters") or {}
        size = lambda v, d: max(512, min(1024, int(v or d)) // 64 * 64)  # noqa: E731
        width, height = size(p.get("width"), 768), size(p.get("height"), 768)
        steps = max(2, min(6, int(p.get("steps") or 4)))
        seed = int(p.get("seed") if p.get("seed") is not None else random.randrange(2**31))
        image = self.pipe(
            prompt=prompt,
            guidance_scale=0.0,
            width=width,
            height=height,
            num_inference_steps=steps,
            generator=torch.Generator("cuda").manual_seed(seed),
        ).images[0]
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=88)
        return {"image": base64.b64encode(buf.getvalue()).decode(), "seed": seed, "width": width, "height": height}
