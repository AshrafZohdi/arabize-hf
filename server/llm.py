"""Every model call in Darby goes through this module.

Fanar 2 runs on a scale-to-zero HF Inference Endpoint (llama.cpp, OpenAI-compatible chat
completions) reached with `huggingface_hub.AsyncInferenceClient(base_url=...)`. Nothing else
in the app imports the client.

Rules from docs/BRIEF.md:
- reasoning off where supported, and `<think>` blocks always stripped before parsing or streaming;
- structured answers validated with pydantic, schema-guided decoding when the endpoint allows it,
  one retry with the validation error, then the caller falls back;
- learner text is data: wrapped in tags with `<` and `>` escaped;
- 30 s timeout for JSON calls, an in-memory rate limit per IP, input capped at 2,000 characters;
- DEMO_MODE or a cold or failing endpoint serves recorded fixtures from `server/fixtures/`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ValidationError

from server.config import Settings

log = logging.getLogger("darby.llm")

MAX_INPUT_CHARS = 2000
JSON_TIMEOUT_S = 30.0
STREAM_TIMEOUT_S = 60.0
JSON_TEMPERATURE = 0.3
CHAT_TEMPERATURE = 0.6
# Fanar 2's chat template adds an empty think block when this kwarg is set (see its chat_template.jinja).
NO_THINKING = {"chat_template_kwargs": {"no_thinking": True}}
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

T = TypeVar("T", bound=BaseModel)
Source = Literal["fanar", "fixture"]
State = Literal["ready", "waking", "demo", "unconfigured", "unknown"]


# --- errors -------------------------------------------------------------------------------


class LLMError(Exception):
    """Base for model errors the routes turn into friendly responses."""


class LLMUnavailable(LLMError):
    """The endpoint is asleep, waking, failing, switched off, or DEMO_MODE is on, and no fixture matches."""

    def __init__(self, state: State):
        super().__init__(state)
        self.state = state


class LLMBadOutput(LLMError):
    """The model answered twice without valid JSON for the schema."""


class RateLimited(LLMError):
    def __init__(self, retry_after: int):
        super().__init__(f"retry after {retry_after} s")
        self.retry_after = retry_after


# --- learner text -------------------------------------------------------------------------


def escape_learner_text(text: str) -> str:
    """Neutralise anything that could open or close our tags, so instructions inside are read as text."""
    return text.replace("<", "‹").replace(">", "›")


def wrap_learner_text(text: str, tag: str = "learner_text") -> str:
    return f"<{tag}>{escape_learner_text(text)}</{tag}>"


# --- think blocks ---------------------------------------------------------------------------

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def strip_think(text: str) -> str:
    """Remove reasoning from a full reply.

    Handles complete blocks, a reply that starts inside a block the template opened (only the
    closing tag is present), and a block that never closes (the reply ran out inside it).
    """
    text = _THINK_BLOCK.sub("", text)
    lower = text.lower()
    close = lower.find("</think>")
    if close != -1:
        text = text[close + len("</think>") :]
        lower = text.lower()
    open_ = lower.find("<think>")
    if open_ != -1:
        text = text[:open_]
    return text.strip()


class ThinkStripper:
    """Streaming version of strip_think: feed chunks, get only the visible text back.

    Tags can be split across chunks, so a short tail that could be the start of a tag is held
    back until the next chunk decides it.
    """

    OPEN, CLOSE = "<think>", "</think>"

    def __init__(self) -> None:
        self._buf = ""
        self._inside = False
        self._started = False  # leading whitespace before the first visible text is dropped

    def feed(self, chunk: str) -> str:
        self._buf += chunk
        out: list[str] = []
        while True:
            lower = self._buf.lower()
            if self._inside:
                i = lower.find(self.CLOSE)
                if i == -1:
                    self._buf = self._buf[-(len(self.CLOSE) - 1) :]
                    break
                self._buf = self._buf[i + len(self.CLOSE) :]
                self._inside = False
                continue
            i_open = lower.find(self.OPEN)
            i_close = lower.find(self.CLOSE)
            if i_close != -1 and (i_open == -1 or i_close < i_open):
                # Reply began inside a block the template opened: drop everything before the close tag.
                out.clear()
                self._buf = self._buf[i_close + len(self.CLOSE) :]
                continue
            if i_open != -1:
                out.append(self._buf[:i_open])
                self._buf = self._buf[i_open + len(self.OPEN) :]
                self._inside = True
                continue
            keep = _partial_tag_suffix(lower)
            out.append(self._buf[: len(self._buf) - keep])
            self._buf = self._buf[len(self._buf) - keep :]
            break
        return self._visible("".join(out))

    def flush(self) -> str:
        rest = "" if self._inside else self._buf
        self._buf = ""
        return self._visible(rest)

    def _visible(self, text: str) -> str:
        if not self._started:
            text = text.lstrip()
            if text:
                self._started = True
        return text


def _partial_tag_suffix(lower: str) -> int:
    """Length of the longest suffix that is a prefix of a think tag."""
    best = 0
    for tag in (ThinkStripper.OPEN, ThinkStripper.CLOSE):
        for n in range(1, len(tag)):
            if lower.endswith(tag[:n]):
                best = max(best, n)
    return best


# --- JSON -----------------------------------------------------------------------------------


def extract_json(text: str) -> Any:
    """Find the JSON object in a reply (models sometimes add fences or a sentence) and parse it."""
    text = strip_think(text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found")
    return json.loads(text[start : end + 1])


def parse_json(text: str, schema: type[T]) -> T:
    try:
        raw = extract_json(text)
    except (ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"invalid JSON ({e})") from e
    try:
        return schema.model_validate(raw)
    except ValidationError as e:
        problems = "; ".join(f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()[:8])
        raise ValueError(problems) from e


def json_instruction(schema: type[BaseModel]) -> str:
    return (
        "Reply with one JSON object only, no other text and no code fences. "
        f"It must match this JSON Schema:\n{json.dumps(schema.model_json_schema(), ensure_ascii=False)}"
    )


# --- rate limit -----------------------------------------------------------------------------


class RateLimiter:
    """Sliding window per key (client IP). In memory: fine for one Space replica."""

    def __init__(self, limit: int, window_s: float, clock: Callable[[], float] = time.monotonic):
        self.limit, self.window_s, self._clock = limit, window_s, clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str) -> None:
        now = self._clock()
        q = self._hits[key]
        while q and q[0] <= now - self.window_s:
            q.popleft()
        if len(q) >= self.limit:
            raise RateLimited(retry_after=max(1, int(q[0] + self.window_s - now) + 1))
        q.append(now)


# --- fixtures -------------------------------------------------------------------------------


def _norm_text(s: str) -> str:
    return " ".join(s.split()).lower()


def _canonical(inp: dict[str, Any]) -> str:
    return json.dumps({k: _norm_text(v) if isinstance(v, str) else v for k, v in sorted(inp.items())}, ensure_ascii=False)


class Fixtures:
    """Recorded answers in `server/fixtures/<feature>/*.json`: {"input": {...}, "output": ...}.

    Lookup is an exact match on the normalised input first, then a match on its "text" field only,
    so a demo input still gets its recording if a chip or language toggle differs.
    """

    def __init__(self, root: Path = FIXTURES_DIR):
        self._exact: dict[tuple[str, str], Any] = {}
        self._by_text: dict[tuple[str, str], Any] = {}
        for path in sorted(root.glob("*/*.json")) if root.is_dir() else []:
            feature = path.parent.name
            data = json.loads(path.read_text(encoding="utf-8"))
            inp, out = data["input"], data["output"]
            self._exact[(feature, _canonical(inp))] = out
            if isinstance(inp.get("text"), str):
                self._by_text.setdefault((feature, _norm_text(inp["text"])), out)

    def lookup(self, feature: str, inp: dict[str, Any] | None) -> Any | None:
        if inp is None:
            return None
        hit = self._exact.get((feature, _canonical(inp)))
        if hit is None and isinstance(inp.get("text"), str):
            hit = self._by_text.get((feature, _norm_text(inp["text"])))
        return hit


# --- the client -----------------------------------------------------------------------------


@dataclass
class JsonResult(Generic[T]):
    data: T
    source: Source
    latency_ms: int
    attempts: int


@dataclass
class JsonEvent(Generic[T]):
    kind: Literal["partial", "result"]
    text: str = ""
    result: JsonResult[T] | None = None


class PartialStringField:
    """Pull one top-level string field out of a JSON object that is still being written.

    Feed the whole text so far; get back only the newly decoded characters of the field's value.
    """

    def __init__(self, name: str):
        self._key = re.compile(r'"' + re.escape(name) + r'"\s*:\s*"')
        self._start: int | None = None
        self._sent = 0
        self._done = False

    def feed(self, text: str) -> str:
        if self._done:
            return ""
        if self._start is None:
            m = self._key.search(text)
            if not m:
                return ""
            self._start = m.end()
        body, i, end = text[self._start :], 0, None
        while i < len(body):
            if body[i] == "\\":
                width = 6 if i + 1 < len(body) and body[i + 1] == "u" else 2
                if i + width > len(body):
                    end = i  # escape not complete yet: hold it back
                    break
                i += width
                continue
            if body[i] == '"':
                self._done = True
                break
            i += 1
        candidate = body[: i if end is None else end]
        try:
            value = json.loads(f'"{candidate}"')
        except json.JSONDecodeError:
            return ""
        new = value[self._sent :]
        self._sent = len(value)
        return new


_UNAVAILABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


def _status_of(exc: BaseException) -> int | None:
    resp = getattr(exc, "response", None)
    code = getattr(resp, "status_code", None) or getattr(exc, "status_code", None)
    return int(code) if code else None


def _is_unavailable(exc: BaseException) -> bool:
    """Cold start, timeout, connection failure or 5xx: the endpoint is waking or down."""
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError, ConnectionError, OSError)):
        return True
    name = type(exc).__name__
    if any(k in name for k in ("Timeout", "Connect", "RemoteProtocol", "NetworkError")):
        return True
    status = _status_of(exc)
    return status in _UNAVAILABLE_STATUS if status else False


def _is_response_format_rejected(exc: BaseException) -> bool:
    status = _status_of(exc)
    text = str(exc).lower()
    return status in {400, 422} and any(k in text for k in ("response_format", "schema", "grammar"))


class LLM:
    def __init__(
        self,
        settings: Settings,
        client: Any | None = None,
        fixtures: Fixtures | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.settings = settings
        self.fixtures = fixtures if fixtures is not None else Fixtures()
        self._clock = clock
        self._client = client
        self._schema_supported = True
        self._state: State = "unknown"
        self._waking_since: float | None = None

    # The client is created lazily so the app starts (and tests run) without a token or URL.
    def _get_client(self) -> Any:
        if self._client is None:
            from huggingface_hub import AsyncInferenceClient

            self._client = AsyncInferenceClient(
                base_url=self.settings.fanar_endpoint_url, api_key=self.settings.hf_token, timeout=STREAM_TIMEOUT_S
            )
        return self._client

    @property
    def state(self) -> State:
        if self.settings.demo_mode:
            return "demo"
        if not self.settings.fanar_endpoint_url:
            return "unconfigured"
        return self._state

    def status(self) -> dict[str, Any]:
        waking_for = int(self._clock() - self._waking_since) if self._waking_since is not None else None
        return {"state": self.state, "waking_for_s": waking_for, "model": self.settings.fanar_model}

    def _offline(self) -> State | None:
        s = self.state
        return s if s in ("demo", "unconfigured") else None

    def _record(self, feature: str, fixture_input: dict[str, Any] | None, output: Any, latency_ms: int) -> None:
        """With DARBY_RECORD_FIXTURES set, save a real answer as a fixture (used to record the demo inputs)."""
        if self.settings.record_dir is None or fixture_input is None:
            return
        import hashlib

        name = hashlib.sha256(_canonical(fixture_input).encode()).hexdigest()[:12]
        path = self.settings.record_dir / feature / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"input": fixture_input, "output": output, "recorded": {"model": self.settings.fanar_model, "latency_ms": latency_ms}}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        log.info("recorded fixture %s", path)

    def _mark_ready(self) -> None:
        self._state, self._waking_since = "ready", None

    def _mark_waking(self, exc: BaseException) -> None:
        if self._waking_since is None:
            self._waking_since = self._clock()
        self._state = "waking"
        log.warning("endpoint unavailable (%s: %s)", type(exc).__name__, str(exc)[:200])

    async def _chat(self, messages: list[dict[str, str]], *, max_tokens: int, temperature: float, schema: type[BaseModel] | None) -> str:
        kwargs: dict[str, Any] = dict(
            messages=messages, model=self.settings.fanar_model, max_tokens=max_tokens, temperature=temperature, extra_body=NO_THINKING
        )
        if schema is not None and self._schema_supported:
            # llama.cpp's server reads {"type": "json_object", "schema": ...} and builds a grammar from it.
            # The "json_schema" type is not used on purpose: huggingface_hub rewrites it into the TGI shape
            # ({"value": ...}), which llama.cpp ignores (checked in tests/test_llm_wire.py).
            kwargs["response_format"] = {"type": "json_object", "schema": schema.model_json_schema()}
        try:
            out = await asyncio.wait_for(self._get_client().chat_completion(**kwargs), timeout=JSON_TIMEOUT_S)
        except Exception as e:
            if "response_format" in kwargs and _is_response_format_rejected(e):
                log.info("endpoint rejected response_format; asking for JSON in the prompt only")
                self._schema_supported = False
                return await self._chat(messages, max_tokens=max_tokens, temperature=temperature, schema=schema)
            raise
        return out.choices[0].message.content or ""

    async def json(
        self,
        *,
        feature: str,
        system: str,
        user: str,
        schema: type[T],
        max_tokens: int,
        fixture_input: dict[str, Any] | None = None,
        temperature: float = JSON_TEMPERATURE,
    ) -> JsonResult[T]:
        """Structured answer validated against `schema`.

        Raises LLMUnavailable (no endpoint and no fixture) or LLMBadOutput (two invalid replies);
        the route then shows the waking-up state or the glossary-only answer.
        """
        started = self._clock()
        fixture = self.fixtures.lookup(feature, fixture_input)
        offline = self._offline()
        if offline:
            if fixture is None:
                raise LLMUnavailable(offline)
            return JsonResult(schema.model_validate(fixture), "fixture", 0, 0)

        messages = [{"role": "system", "content": f"{system}\n\n{json_instruction(schema)}"}, {"role": "user", "content": user}]
        error = ""
        for attempt in (1, 2):
            try:
                text = await self._chat(messages, max_tokens=max_tokens, temperature=temperature, schema=schema)
            except Exception as e:
                if not _is_unavailable(e):
                    raise
                self._mark_waking(e)
                if fixture is None:
                    raise LLMUnavailable("waking") from e
                return JsonResult(schema.model_validate(fixture), "fixture", int((self._clock() - started) * 1000), attempt)
            self._mark_ready()
            try:
                data = parse_json(text, schema)
            except ValueError as e:
                error = str(e)
                log.info("%s: invalid JSON on attempt %d: %s", feature, attempt, error[:300])
                messages = messages + [
                    {"role": "assistant", "content": strip_think(text)},
                    {"role": "user", "content": f"That was not valid. Problem: {error}. Reply again with the corrected JSON object only."},
                ]
                continue
            latency = int((self._clock() - started) * 1000)
            self._record(feature, fixture_input, data.model_dump(), latency)
            return JsonResult(data, "fanar", latency, attempt)
        raise LLMBadOutput(error)

    async def json_stream(
        self,
        *,
        feature: str,
        system: str,
        user: str,
        schema: type[T],
        stream_field: str,
        max_tokens: int,
        fixture_input: dict[str, Any] | None = None,
        temperature: float = JSON_TEMPERATURE,
    ) -> AsyncIterator[JsonEvent[T]]:
        """Structured answer, with one string field streamed as it is written.

        Yields `partial` events with new text of `stream_field`, then one `result` event with the validated
        object. On an invalid object it makes one non-streaming correction call, then raises LLMBadOutput.
        """
        started = self._clock()
        fixture = self.fixtures.lookup(feature, fixture_input)

        async def from_fixture(attempt: int) -> AsyncIterator[JsonEvent[T]]:
            data = schema.model_validate(fixture)
            async for piece in _replay(str(getattr(data, stream_field, "") or "")):
                yield JsonEvent("partial", text=piece)
            yield JsonEvent("result", result=JsonResult(data, "fixture", int((self._clock() - started) * 1000), attempt))

        offline = self._offline()
        if offline:
            if fixture is None:
                raise LLMUnavailable(offline)
            async for ev in from_fixture(0):
                yield ev
            return

        messages = [{"role": "system", "content": f"{system}\n\n{json_instruction(schema)}"}, {"role": "user", "content": user}]
        kwargs: dict[str, Any] = dict(
            messages=messages, model=self.settings.fanar_model, max_tokens=max_tokens, temperature=temperature, stream=True, extra_body=NO_THINKING
        )
        if self._schema_supported:
            kwargs["response_format"] = {"type": "json_object", "schema": schema.model_json_schema()}
        try:
            chunks = await asyncio.wait_for(self._get_client().chat_completion(**kwargs), timeout=JSON_TIMEOUT_S)
        except Exception as e:
            if not _is_unavailable(e):
                raise
            self._mark_waking(e)
            if fixture is None:
                raise LLMUnavailable("waking") from e
            async for ev in from_fixture(1):
                yield ev
            return

        self._mark_ready()
        raw = ""
        field = PartialStringField(stream_field)
        async for chunk in chunks:
            if not chunk.choices:
                continue
            raw += chunk.choices[0].delta.content or ""
            new = field.feed(strip_think(raw))
            if new:
                yield JsonEvent("partial", text=new)

        try:
            data = parse_json(raw, schema)
            latency = int((self._clock() - started) * 1000)
            self._record(feature, fixture_input, data.model_dump(), latency)
            yield JsonEvent("result", result=JsonResult(data, "fanar", latency, 1))
            return
        except ValueError as e:
            error = str(e)
        log.info("%s: invalid streamed JSON: %s", feature, error[:300])
        retry = messages + [
            {"role": "assistant", "content": strip_think(raw)},
            {"role": "user", "content": f"That was not valid. Problem: {error}. Reply again with the corrected JSON object only."},
        ]
        text = await self._chat(retry, max_tokens=max_tokens, temperature=temperature, schema=schema)
        try:
            data = parse_json(text, schema)
        except ValueError as e:
            raise LLMBadOutput(str(e)) from e
        yield JsonEvent("result", result=JsonResult(data, "fanar", int((self._clock() - started) * 1000), 2))

    async def stream(
        self,
        *,
        feature: str,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        fixture_input: dict[str, Any] | None = None,
        temperature: float = CHAT_TEMPERATURE,
    ) -> AsyncIterator[str]:
        """Yield visible text pieces (think blocks removed). Falls back to a fixture before the first token."""
        fixture = self.fixtures.lookup(feature, fixture_input)
        offline = self._offline()
        if offline:
            if fixture is None:
                raise LLMUnavailable(offline)
            async for piece in _replay(str(fixture)):
                yield piece
            return

        try:
            chunks = await asyncio.wait_for(
                self._get_client().chat_completion(
                    messages=[{"role": "system", "content": system}, *messages],
                    model=self.settings.fanar_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True,
                    extra_body=NO_THINKING,
                ),
                timeout=JSON_TIMEOUT_S,
            )
        except Exception as e:
            if not _is_unavailable(e):
                raise
            self._mark_waking(e)
            if fixture is None:
                raise LLMUnavailable("waking") from e
            async for piece in _replay(str(fixture)):
                yield piece
            return

        self._mark_ready()
        stripper = ThinkStripper()
        async for chunk in chunks:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content or ""
            visible = stripper.feed(delta)
            if visible:
                yield visible
        tail = stripper.flush()
        if tail:
            yield tail


async def _replay(text: str, size: int = 12) -> AsyncIterator[str]:
    """Stream a recorded answer in small pieces so the UI behaves as with the live model."""
    for i in range(0, len(text), size):
        yield text[i : i + size]
        await asyncio.sleep(0.01)


# Shared limiter for AI calls: 30 per 10 minutes per IP (docs/BRIEF.md, LLM rules).
ai_rate_limiter = RateLimiter(limit=30, window_s=600)
