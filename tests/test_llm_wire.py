"""The real huggingface_hub client against a local OpenAI-compatible stub: checks URL and body on the wire."""

import asyncio
import json
import threading
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from pydantic import BaseModel

from server.config import load_settings
from server.llm import LLM, Fixtures


class Card(BaseModel):
    term_en: str
    term_ar: str


class Stub(BaseHTTPRequestHandler):
    requests: list[tuple[str, dict]] = []

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Stub.requests.append((self.path, body))
        if body.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for piece in ["<think>x</think>", "مرحبا", " بك"]:
                chunk = {"id": "1", "object": "chat.completion.chunk", "created": 0, "model": "m", "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}]}
                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
            return
        content = json.dumps({"term_en": "Prompt", "term_ar": "الأمر"}, ensure_ascii=False)
        resp = {
            "id": "1", "object": "chat.completion", "created": 0, "model": "m",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
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


def test_real_client_json_and_stream(stub_url, tmp_path):
    settings = replace(load_settings(), fanar_endpoint_url=stub_url, hf_token="test-token", demo_mode=False)
    llm = LLM(settings, fixtures=Fixtures(tmp_path))

    res = asyncio.run(llm.json(feature="explain", system="s", user="u", schema=Card, max_tokens=50))
    assert res.data.term_ar == "الأمر"

    async def collect():
        return "".join([p async for p in llm.stream(feature="tutor", system="s", messages=[{"role": "user", "content": "q"}], max_tokens=20)])

    assert asyncio.run(collect()) == "مرحبا بك"

    path, body = Stub.requests[0]
    assert path.endswith("/chat/completions")
    assert body["chat_template_kwargs"] == {"no_thinking": True}
    assert body["response_format"]["type"] == "json_object"
    assert set(body["response_format"]["schema"]["properties"]) == {"term_en", "term_ar"}
    assert body["model"] == settings.fanar_model
