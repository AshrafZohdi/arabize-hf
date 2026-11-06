"""Photo explain (P1, docs/HF_PLAN.md #16), behind IMAGE_ENABLED.

POST /api/read-image  {image: data URL (jpeg, png or webp), lang}  ->  {text, description, source}
The browser shrinks the photo before sending it. Nothing is stored or logged.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from server.llm import LLM, LLMBadOutput, LLMUnavailable, RateLimited, ai_rate_limiter
from server.net import client_ip
from server.prompts.vision import ImageReading, build_reading_prompt

router = APIRouter()
MAX_IMAGE_CHARS = 6_000_000  # about 4.5 MB of image after base64
DATA_URL = re.compile(r"^data:image/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$")


class ReadImageIn(BaseModel):
    image: str = Field(min_length=32, max_length=MAX_IMAGE_CHARS)
    lang: Literal["en", "msa", "gulf"] = "gulf"


@router.post("/api/read-image")
async def read_image(body: ReadImageIn, request: Request) -> Any:
    vision: LLM | None = getattr(request.app.state, "vision", None)
    if vision is None:
        raise HTTPException(status_code=404, detail="photo explain is switched off")
    if not DATA_URL.match(body.image):
        raise HTTPException(status_code=422, detail="send a jpeg, png or webp image as a data URL")
    try:
        ai_rate_limiter.hit(client_ip(request))
    except RateLimited as e:
        return JSONResponse({"error": "rate_limited", "retry_after": e.retry_after}, status_code=429, headers={"Retry-After": str(e.retry_after)})
    system, user = build_reading_prompt(body.lang)
    try:
        res = await vision.json(
            feature="read_image",
            system=system,
            user=user,
            schema=ImageReading,
            max_tokens=900,
            images=[body.image],
            fixture_input={"image_sha256": hashlib.sha256(body.image.encode()).hexdigest(), "lang": body.lang},
        )
    except LLMUnavailable as e:
        return JSONResponse({"error": "unavailable", "state": e.state}, status_code=503)
    except LLMBadOutput:
        return JSONResponse({"error": "bad_output"}, status_code=502)
    return {"text": res.data.text.strip(), "description": res.data.description.strip(), "source": res.source}
