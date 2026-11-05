"""Settings read once from the environment (Space secrets in production)."""

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, "1" if default else "0").strip().lower() in {"1", "true", "yes", "on"}


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


def load_settings() -> Settings:
    return Settings(
        hf_token=os.getenv("HF_TOKEN") or None,
        fanar_endpoint_url=os.getenv("FANAR_ENDPOINT_URL") or None,
        fanar_model=os.getenv("FANAR_MODEL", "QCRI/Fanar-2-27B-Instruct"),
        hf_bucket=os.getenv("HF_BUCKET") or None,
        voice_enabled=_flag("VOICE_ENABLED"),
        demo_mode=_flag("DEMO_MODE"),
        web_dist=Path(os.getenv("DARBY_WEB_DIST", ROOT / "web" / "dist")),
        content_dir=Path(os.getenv("DARBY_CONTENT_DIR", ROOT / "content")),
    )
