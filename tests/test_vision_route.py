import base64
import json
from dataclasses import replace

from fastapi.testclient import TestClient

from server.config import load_settings
from server.llm import LLM, Fixtures
from server.main import create_app
from tests.test_explain_route import fresh_limiter  # noqa: F401  (fixture reused)
from tests.test_llm import FakeClient

PNG = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 64).decode()


def make(tmp_path, fake=None, **overrides):
    base = {"web_dist": tmp_path, "image_enabled": True, "oryx_ivu_url": "https://ivu.example", "hf_token": "x", "termbank_source": "off"}
    settings = replace(load_settings(), **{**base, **overrides})
    app = create_app(settings)
    if app.state.vision is not None:
        app.state.vision = LLM(replace(settings, fanar_endpoint_url=settings.oryx_ivu_url), client=fake, fixtures=Fixtures(tmp_path / "none"))
    return TestClient(app), app


def test_reads_the_image_and_sends_it_as_image_url(tmp_path):
    fake = FakeClient(json.dumps({"text": "Please check the summary for hallucinations.", "description": "صورة لإيميل شغل"}, ensure_ascii=False))
    c, _ = make(tmp_path, fake)
    r = c.post("/api/read-image", json={"image": PNG, "lang": "gulf"})
    assert r.status_code == 200 and r.json()["text"].startswith("Please check") and r.json()["source"] == "fanar"
    content = fake.calls[0]["messages"][-1]["content"]
    assert content[0] == {"type": "image_url", "image_url": {"url": PNG}} and content[1]["type"] == "text"
    assert "Gulf Arabic" in fake.calls[0]["messages"][0]["content"]


def test_rejects_non_images_and_is_off_by_default(tmp_path):
    c, _ = make(tmp_path, FakeClient("{}"))
    assert c.post("/api/read-image", json={"image": "data:text/html;base64," + "A" * 40}).status_code == 422
    off, app = make(tmp_path, image_enabled=False)
    assert app.state.vision is None and off.post("/api/read-image", json={"image": PNG}).status_code == 404
    assert off.get("/api/health").json()["image"] == {"read": False, "read_state": None, "generate": False}
