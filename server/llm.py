"""Every model call in Darbi goes through this module.

Jais 3 (inception42/Jais-3-375B-A23B) is reached over the OpenAI-compatible chat completions API that vLLM and
SGLang expose (`JAIS_BASE_URL`, see docs/JAIS.md). Nothing else in the app talks to the model server.

What this module guarantees:
- the model card's sampling settings on every request (top_p 0.95, top_k 20, reasoning effort in
  `chat_template_kwargs`), with reasoning kept out of what the learner sees: the server's reasoning parser puts it
  in `reasoning_content`, and any `<think>` block that still reaches the text is stripped;
- structured answers validated with pydantic, schema-guided decoding when the server allows it, one retry with
  the validation error, then the caller falls back;
- learner text is data: wrapped in tags with `<` and `>` escaped;
- a timeout for every call and an in-memory rate limit per client;
- when the model server is down or not configured, callers get LLMUnavailable and show the glossary instead.
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
from types import SimpleNamespace
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ValidationError

from server.config import Settings

log = logging.getLogger("darby.llm")

MAX_INPUT_CHARS = 6000
# Sampling from the Jais 3 model card. Temperature, reasoning effort and the token budget come from Settings.
TOP_P = 0.95
TOP_K = 20

T = TypeVar("T", bound=BaseModel)
Source = Literal["jais"]
State = Literal["ready", "unavailable", "error", "unconfigured", "unknown"]


# --- errors -------------------------------------------------------------------------------


class LLMError(Exception):
    """Base for model errors the routes turn into friendly responses."""


class LLMUnavailable(LLMError):
    """The model server is not configured, not reachable, or answered with an error."""

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
    """Sliding window per key (client IP). In memory: one counter per server process."""

    def __init__(self, limit: int, window_s: float, clock: Callable[[], float] = time.monotonic):
        self.limit, self.window_s, self._clock = limit, window_s, clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str) -> None:
        if self.limit <= 0:
            return
        now = self._clock()
        q = self._hits[key]
        while q and q[0] <= now - self.window_s:
            q.popleft()
        if len(q) >= self.limit:
            raise RateLimited(retry_after=max(1, int(q[0] + self.window_s - now) + 1))
        q.append(now)


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
    """Timeout, connection failure, overload or 5xx: the model server is down or busy."""
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError, ConnectionError, OSError)):
        return True
    name = type(exc).__name__
    if any(k in name for k in ("Timeout", "Connect", "RemoteProtocol", "NetworkError")):
        return True
    status = _status_of(exc)
    return status in _UNAVAILABLE_STATUS if status else False


def _is_response_format_rejected(exc: BaseException) -> bool:
    status = _status_of(exc)
    text = (str(exc) + " " + str(getattr(getattr(exc, "response", None), "text", ""))).lower()
    return status in {400, 422} and any(k in text for k in ("response_format", "schema", "grammar", "guided", "structured"))


def _ns(value: Any) -> Any:
    """JSON from the server as objects, so replies read as `out.choices[0].message.content`."""
    if isinstance(value, dict):
        return SimpleNamespace(**{k: _ns(v) for k, v in value.items()})
    if isinstance(value, list):
        return [_ns(v) for v in value]
    return value


class JaisClient:
    """The few lines of the OpenAI chat completions protocol that Darbi needs, over httpx.

    `base_url` is the server's API root (it normally ends in /v1). A new HTTP client is opened per call, which
    costs nothing next to a model answer and keeps the class safe to use from any event loop.
    """

    def __init__(self, base_url: str, api_key: str | None, timeout_s: float):
        base = base_url.rstrip("/")
        self.url = base if base.endswith("/chat/completions") else f"{base}/chat/completions"
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._timeout_s = timeout_s

    def _http(self) -> Any:
        import httpx

        # read: the longest silence allowed between two pieces of an answer (reasoning arrives as pieces too).
        return httpx.AsyncClient(timeout=httpx.Timeout(self._timeout_s, connect=10.0), headers=self._headers)

    async def chat_completion(self, **body: Any) -> Any:
        if body.get("stream"):
            return await self._stream(body)
        async with self._http() as http:
            r = await http.post(self.url, json=body)
            r.raise_for_status()
            return _ns(r.json())

    async def _stream(self, body: dict[str, Any]) -> AsyncIterator[Any]:
        http = self._http()
        try:
            resp = await http.send(http.build_request("POST", self.url, json=body), stream=True)
            if resp.status_code >= 400:
                await resp.aread()
                resp.raise_for_status()
        except BaseException:
            await http.aclose()
            raise

        async def chunks() -> AsyncIterator[Any]:
            try:
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    if data:
                        yield _ns(json.loads(data))
            finally:
                await resp.aclose()
                await http.aclose()

        return chunks()


def _delta_text(chunk: Any) -> str:
    """The answer text in a streamed chunk. Reasoning travels in `reasoning_content` and is left out."""
    choices = getattr(chunk, "choices", None)
    if not choices:
        return ""
    return getattr(getattr(choices[0], "delta", None), "content", None) or ""


class LLM:
    def __init__(self, settings: Settings, client: Any | None = None, clock: Callable[[], float] = time.monotonic):
        self.settings = settings
        self._clock = clock
        self._client = client
        self._schema_supported = True
        self._state: State = "unknown"
        self._down_since: float | None = None

    # The client is created lazily so the app starts (and tests run) without a model server.
    def _get_client(self) -> Any:
        if self._client is None:
            s = self.settings
            self._client = JaisClient(s.jais_base_url or "", s.jais_api_key, s.jais_timeout_s)
        return self._client

    @property
    def state(self) -> State:
        if not self.settings.jais_base_url:
            return "unconfigured"
        return self._state

    def status(self) -> dict[str, Any]:
        down_for = int(self._clock() - self._down_since) if self._down_since is not None else None
        return {"state": self.state, "down_for_s": down_for, "model": self.settings.jais_model}

    def _request(self, messages: list[dict[str, Any]], *, temperature: float | None, schema: type[BaseModel] | None, stream: bool) -> dict[str, Any]:
        s = self.settings
        body: dict[str, Any] = dict(
            model=s.jais_model,
            messages=messages,
            max_tokens=s.jais_max_tokens,
            temperature=s.jais_temperature if temperature is None else temperature,
            top_p=TOP_P,
            top_k=TOP_K,
        )
        if s.jais_reasoning_effort:
            # The model card asks for this on every request.
            body["chat_template_kwargs"] = {"reasoning_effort": s.jais_reasoning_effort}
        if stream:
            body["stream"] = True
        if schema is not None and self._schema_supported:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()},
            }
        return body

    def _mark_ready(self) -> None:
        self._state, self._down_since = "ready", None

    def _failed(self, exc: BaseException) -> LLMUnavailable:
        """Record a failed call and return the error the routes turn into the glossary-only answer."""
        if _is_unavailable(exc):
            if self._down_since is None:
                self._down_since = self._clock()
            self._state = "unavailable"
            log.warning("model server unavailable (%s: %s)", type(exc).__name__, str(exc)[:200])
            return LLMUnavailable("unavailable")
        # Wrong URL, key or model name, or a request the server refuses: a setup problem, so it is logged loudly.
        self._state = "error"
        log.error("model server error %s (status %s): %s", type(exc).__name__, _status_of(exc), str(exc)[:300])
        return LLMUnavailable("error")

    async def _send(self, messages: list[dict[str, Any]], *, temperature: float | None, schema: type[BaseModel] | None, stream: bool) -> Any:
        body = self._request(messages, temperature=temperature, schema=schema, stream=stream)
        try:
            return await asyncio.wait_for(self._get_client().chat_completion(**body), timeout=self.settings.jais_timeout_s)
        except Exception as e:
            if "response_format" in body and _is_response_format_rejected(e):
                log.info("server rejected response_format; asking for JSON in the prompt only")
                self._schema_supported = False
                return await self._send(messages, temperature=temperature, schema=schema, stream=stream)
            raise

    async def _chat(self, messages: list[dict[str, Any]], *, temperature: float | None, schema: type[BaseModel] | None) -> str:
        out = await self._send(messages, temperature=temperature, schema=schema, stream=False)
        return out.choices[0].message.content or ""

    async def json(self, *, feature: str, system: str, user: str, schema: type[T], temperature: float | None = None) -> JsonResult[T]:
        """Structured answer validated against `schema`.

        Raises LLMUnavailable (no server, or it failed) or LLMBadOutput (two invalid replies).
        """
        started = self._clock()
        if self.state == "unconfigured":
            raise LLMUnavailable("unconfigured")
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": f"{system}\n\n{json_instruction(schema)}"},
            {"role": "user", "content": user},
        ]
        error = ""
        for attempt in (1, 2):
            try:
                text = await self._chat(messages, temperature=temperature, schema=schema)
            except Exception as e:
                raise self._failed(e) from e
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
            return JsonResult(data, "jais", int((self._clock() - started) * 1000), attempt)
        raise LLMBadOutput(error)

    async def json_stream(
        self, *, feature: str, system: str, user: str, schema: type[T], stream_field: str, temperature: float | None = None
    ) -> AsyncIterator[JsonEvent[T]]:
        """Structured answer, with one string field streamed as it is written.

        Yields `partial` events with new text of `stream_field`, then one `result` event with the validated
        object. On an invalid object it makes one non-streaming correction call, then raises LLMBadOutput.
        """
        started = self._clock()
        if self.state == "unconfigured":
            raise LLMUnavailable("unconfigured")
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": f"{system}\n\n{json_instruction(schema)}"},
            {"role": "user", "content": user},
        ]
        try:
            chunks = await self._send(messages, temperature=temperature, schema=schema, stream=True)
        except Exception as e:
            raise self._failed(e) from e

        self._mark_ready()
        raw = ""
        field = PartialStringField(stream_field)
        try:
            async for chunk in chunks:
                piece = _delta_text(chunk)
                if not piece:
                    continue
                raw += piece
                new = field.feed(strip_think(raw))
                if new:
                    yield JsonEvent("partial", text=new)
        except Exception as e:
            raise self._failed(e) from e

        try:
            data = parse_json(raw, schema)
            yield JsonEvent("result", result=JsonResult(data, "jais", int((self._clock() - started) * 1000), 1))
            return
        except ValueError as e:
            error = str(e)
        log.info("%s: invalid streamed JSON: %s", feature, error[:300])
        retry = messages + [
            {"role": "assistant", "content": strip_think(raw)},
            {"role": "user", "content": f"That was not valid. Problem: {error}. Reply again with the corrected JSON object only."},
        ]
        try:
            text = await self._chat(retry, temperature=temperature, schema=schema)
        except Exception as e:
            raise self._failed(e) from e
        try:
            data = parse_json(text, schema)
        except ValueError as e:
            raise LLMBadOutput(str(e)) from e
        yield JsonEvent("result", result=JsonResult(data, "jais", int((self._clock() - started) * 1000), 2))

    async def stream(self, *, feature: str, system: str, messages: list[dict[str, str]], temperature: float | None = None) -> AsyncIterator[str]:
        """Yield visible text pieces (reasoning removed). Raises LLMUnavailable when the server cannot answer."""
        if self.state == "unconfigured":
            raise LLMUnavailable("unconfigured")
        try:
            chunks = await self._send([{"role": "system", "content": system}, *messages], temperature=temperature, schema=None, stream=True)
        except Exception as e:
            raise self._failed(e) from e

        self._mark_ready()
        stripper = ThinkStripper()
        try:
            async for chunk in chunks:
                visible = stripper.feed(_delta_text(chunk))
                if visible:
                    yield visible
        except Exception as e:
            raise self._failed(e) from e
        tail = stripper.flush()
        if tail:
            yield tail


# Shared limiter for AI calls per client IP. create_app() sets the limit and window from Settings.
ai_rate_limiter = RateLimiter(limit=60, window_s=600)
