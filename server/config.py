"""Settings read once from the environment (Space secrets in production)."""

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, "1" if default else "0").strip().lower() in {"1", "true", "yes", "on"}


def _cached_token() -> str | None:
    """Local development: fall back to the token saved by `hf auth login`. In the Space, HF_TOKEN is a secret."""
    try:
        from huggingface_hub import get_token

        return get_token()
    except Exception:
        return None


@dataclass(frozen=True)
class Settings:
    hf_token: str | None
    fanar_endpoint_url: str | None
    fanar_model: str
    hf_bucket: str | None
    voice_enabled: bool
    demo_mode: bool
    web_dist: Path
    content_dir: Path
    record_dir: Path | None = None  # local only: save real Fanar answers as fixtures
    mcp_enabled: bool = True  # Gradio MCP tools at /mcp-tools
    termbank_source: str = "hub"  # "hub" loads the full bank in the background; "off" keeps our glossary only
    asr_enabled: bool = False  # speech to text with Whisper small on the Space CPU
    image_enabled: bool = False  # photo explain (Oryx-IVU) and image prompts (Oryx-IG), behind a switch
    oryx_ivu_url: str | None = None  # llama.cpp endpoint serving Fanar-2-Oryx-IVU
    oryx_ig_url: str | None = None  # diffusers endpoint serving FLUX.1-schnell with the Fanar-2-Oryx-IG LoRA


def load_settings() -> Settings:
    return Settings(
        hf_token=os.getenv("HF_TOKEN") or _cached_token(),
        fanar_endpoint_url=os.getenv("FANAR_ENDPOINT_URL") or None,
        fanar_model=os.getenv("FANAR_MODEL", "QCRI/Fanar-2-27B-Instruct"),
        hf_bucket=os.getenv("HF_BUCKET") or None,
        voice_enabled=_flag("VOICE_ENABLED"),
        demo_mode=_flag("DEMO_MODE"),
        web_dist=Path(os.getenv("DARBY_WEB_DIST", ROOT / "web" / "dist")),
        content_dir=Path(os.getenv("DARBY_CONTENT_DIR", ROOT / "content")),
        record_dir=Path(os.environ["DARBY_RECORD_FIXTURES"]) if os.getenv("DARBY_RECORD_FIXTURES") else None,
        termbank_source=os.getenv("DARBY_TERMBANK", "hub"),
        mcp_enabled=_flag("MCP_ENABLED", default=True),
        asr_enabled=_flag("ASR_ENABLED", default=False),
        image_enabled=_flag("IMAGE_ENABLED", default=False),
        oryx_ivu_url=os.getenv("ORYX_IVU_URL") or None,
        oryx_ig_url=os.getenv("ORYX_IG_URL") or None,
    )
