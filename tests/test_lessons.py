from dataclasses import replace

from fastapi.testclient import TestClient

from server.config import load_settings
from server.lessons import load_lessons
from server.main import create_app


def test_lessons_from_content(tmp_path):
    lessons, source = load_lessons(load_settings().content_dir, from_hub=False)
    assert source == "content" and [d["order"] for d in lessons] == list(range(1, 8))
    assert all({"en", "ar"} <= set(d["title"]) for d in lessons)


def test_health_reports_lessons(tmp_path):
    c = TestClient(create_app(replace(load_settings(), web_dist=tmp_path, termbank_source="off")))
    assert c.get("/api/health").json()["lessons"] == {"count": 7, "source": "content"}
