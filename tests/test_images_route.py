import json
from dataclasses import replace

import httpx
from fastapi.testclient import TestClient

from server.config import load_settings
from server.llm import LLM, Fixtures
from server.main import create_app
from tests.test_explain_route import fresh_limiter  # noqa: F401  (fixture reused)
from tests.test_llm import FakeClient

SCORE = {k: {"score": 3, "feedback": "x"} for k in ("goal", "context", "format", "constraints")} | {"summary": "x", "improved_prompt": "A bright office in Doha"}


def make(tmp_path, fake=None, **overrides):
    base = {"web_dist": tmp_path, "image_enabled": True, "oryx_ig_url": "https://ig.example", "fanar_endpoint_url": "https://f.example", "hf_token": "x", "termbank_source": "off"}
    settings = replace(load_settings(), **{**base, **overrides})
    app = create_app(settings)
    app.state.llm = LLM(settings, client=fake, fixtures=Fixtures(tmp_path / "none"))
    return TestClient(app)


def fake_post(monkeypatch, status=200, body=None, seen=None):
    async def post(self, url, **kw):
        if seen is not None:
            seen.append((url, kw["json"]))
        return httpx.Response(status, json=body if body is not None else {"image": "QUJD"})

    monkeypatch.setattr(httpx.AsyncClient, "post", post)


def test_image_lab_asks_for_an_english_improved_prompt(tmp_path):
    fake = FakeClient(json.dumps(SCORE))
    c = make(tmp_path, fake)
    r = c.post("/api/image-lab", json={"prompt": "صورة مكتب في الدوحة", "lang": "gulf"})
    assert r.status_code == 200 and r.json()["total"] == 12
    assert "Write improved_prompt in English" in fake.calls[0]["messages"][-1]["content"]
    assert c.get("/api/image-lab/task", params={"lang": "gulf"}).json()["task_en"].startswith("Write a prompt for an image")


def test_generate_checks_safety_then_draws(tmp_path, monkeypatch):
    seen = []
    fake_post(monkeypatch, seen=seen)
    c = make(tmp_path, FakeClient(json.dumps({"allowed": True})))
    r = c.post("/api/generate-image", json={"prompt": "A bright office in Doha"})
    assert r.status_code == 200 and r.json()["image"] == "data:image/jpeg;base64,QUJD"
    assert seen == [("https://ig.example", {"inputs": "A bright office in Doha", "parameters": {"width": 768, "height": 768, "steps": 4}})]


def test_unsafe_prompts_are_never_drawn(tmp_path, monkeypatch):
    seen = []
    fake_post(monkeypatch, seen=seen)
    c = make(tmp_path, FakeClient(json.dumps({"allowed": False, "reason": "ما يناسب الشغل"}, ensure_ascii=False)))
    r = c.post("/api/generate-image", json={"prompt": "something unsafe"})
    assert r.status_code == 422 and r.json()["reason"] == "ما يناسب الشغل" and seen == []


def test_waking_endpoint_and_switch(tmp_path, monkeypatch):
    fake_post(monkeypatch, status=503, body={"error": "loading"})
    c = make(tmp_path, FakeClient(json.dumps({"allowed": True})))
    assert c.post("/api/generate-image", json={"prompt": "A bright office"}).json() == {"error": "unavailable", "state": "waking"}
    off = make(tmp_path, image_enabled=False)
    assert off.post("/api/generate-image", json={"prompt": "A bright office"}).status_code == 404
    assert off.get("/api/image-lab/task").status_code == 404
