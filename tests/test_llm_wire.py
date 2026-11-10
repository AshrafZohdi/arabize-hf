"""The real Jais client against a local OpenAI-compatible stub: checks URL, headers and body on the wire."""

import asyncio
import json
import threading
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from pydantic import BaseModel

from server.config import load_settings
from server.llm import LLM


class Card(BaseModel):
    term_en: str
    term_ar: str


class Stub(BaseHTTPRequestHandler):
    requests: list[tuple[str, dict, str | None]] = []

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Stub.requests.append((self.path, body, self.headers.get("Authorization")))
        if body.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            # A server started with a reasoning parser sends the thinking in reasoning_content, then the answer.
            deltas = [{"reasoning_content": "The learner greets me."}, {"content": "مرحبا"}, {"content": " بك"}]
            for delta in deltas:
                chunk = {"id": "1", "object": "chat.completion.chunk", "created": 0, "model": "m", "choices": [{"index": 0, "delta": delta, "finish_reason": None}]}
                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
            return
        content = json.dumps({"term_en": "Prompt", "term_ar": "الأمر"}, ensure_ascii=False)
        resp = {
            "id": "1", "object": "chat.completion", "created": 0, "model": "m",
            "choices": [{"index": 0, "message": {"role": "assistant", "reasoning_content": "thinking", "content": content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        data = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture
def stub_url():
    Stub.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), Stub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_real_client_json_and_stream(stub_url):
    settings = replace(load_settings(), jais_base_url=stub_url + "/v1", jais_api_key="test-key", jais_reasoning_effort="high")
    llm = LLM(settings)

    res = asyncio.run(llm.json(feature="explain", system="s", user="u", schema=Card))
    assert res.data.term_ar == "الأمر"

    async def collect():
        return "".join([p async for p in llm.stream(feature="tutor", system="s", messages=[{"role": "user", "content": "q"}])])

    assert asyncio.run(collect()) == "مرحبا بك"

    path, body, auth = Stub.requests[0]
    assert path == "/v1/chat/completions" and auth == "Bearer test-key"
    assert body["chat_template_kwargs"] == {"reasoning_effort": "high"}
    assert body["top_k"] == 20 and body["top_p"] == 0.95
    assert body["response_format"]["type"] == "json_schema"
    assert set(body["response_format"]["json_schema"]["schema"]["properties"]) == {"term_en", "term_ar"}
    assert body["model"] == settings.jais_model
    assert Stub.requests[1][1]["stream"] is True


def test_real_client_reports_http_errors_as_unavailable():
    import socket

    from server.llm import LLMUnavailable

    with socket.socket() as s:  # a port nothing listens on
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    llm = LLM(replace(load_settings(), jais_base_url=f"http://127.0.0.1:{port}/v1"))
    with pytest.raises(LLMUnavailable) as e:
        asyncio.run(llm.json(feature="explain", system="s", user="u", schema=Card))
    assert e.value.state == "unavailable"
