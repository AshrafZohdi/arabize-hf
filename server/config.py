"""Settings read once from the environment."""

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

JAIS_MODEL = "inception42/Jais-3-375B-A23B"


def _flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, "1" if default else "0").strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "") or default)
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, "") or default)
    except ValueError:
        return default


def _cached_token() -> str | None:
    """Local development: fall back to the token saved by `hf auth login`. Only used to read Hub datasets."""
    try:
        from huggingface_hub import get_token

        return get_token()
    except Exception:
        return None


@dataclass(frozen=True)
class Settings:
    # Jais 3, served by any OpenAI-compatible server (vLLM or SGLang, see docs/JAIS.md).
    jais_base_url: str | None  # for example http://jais.internal:8000/v1
    jais_api_key: str | None  # optional: vLLM and SGLang accept any value unless started with --api-key
    jais_model: str
    jais_reasoning_effort: str  # sent as chat_template_kwargs.reasoning_effort on every request; "" leaves it out
    jais_max_tokens: int  # reasoning counts towards this, so it is far above the length of an answer
    jais_timeout_s: float  # time allowed for a whole answer
    jais_temperature: float
    hf_token: str | None  # reads the term bank, glossary and lessons from the Hub; never sent to the model server
    hf_bucket: str | None
    voice_enabled: bool
    web_dist: Path
    content_dir: Path
    mcp_enabled: bool = True  # Gradio MCP tools at /mcp-tools
    termbank_source: str = "hub"  # "hub" loads the full bank in the background; "off" keeps our glossary only
    asr_enabled: bool = False  # speech to text with Whisper small on the server CPU
    rate_limit: int = 60  # AI calls per client per window; 0 switches the limit off
    rate_window_s: int = 600


def load_settings() -> Settings:
    return Settings(
        jais_base_url=(os.getenv("JAIS_BASE_URL") or "").rstrip("/") or None,
        jais_api_key=os.getenv("JAIS_API_KEY") or None,
        jais_model=os.getenv("JAIS_MODEL", JAIS_MODEL),
        jais_reasoning_effort=os.getenv("JAIS_REASONING_EFFORT", "high").strip(),
        jais_max_tokens=_int("JAIS_MAX_TOKENS", 32768),
        jais_timeout_s=_float("JAIS_TIMEOUT_S", 180.0),
        jais_temperature=_float("JAIS_TEMPERATURE", 0.7),
        hf_token=os.getenv("HF_TOKEN") or _cached_token(),
        hf_bucket=os.getenv("HF_BUCKET") or None,
        voice_enabled=_flag("VOICE_ENABLED"),
        web_dist=Path(os.getenv("DARBY_WEB_DIST", ROOT / "web" / "dist")),
        content_dir=Path(os.getenv("DARBY_CONTENT_DIR", ROOT / "content")),
        termbank_source=os.getenv("DARBY_TERMBANK", "hub"),
        mcp_enabled=_flag("MCP_ENABLED", default=True),
        asr_enabled=_flag("ASR_ENABLED", default=False),
        rate_limit=_int("AI_RATE_LIMIT", 60),
        rate_window_s=_int("AI_RATE_WINDOW_S", 600),
    )
