import json
from dataclasses import replace

from fastapi.testclient import TestClient

from server.config import load_settings
from server.game import qatar_today
from server.main import create_app
from server.mcp_app import build_tools


def app():
    return create_app(replace(load_settings(), termbank_source="off"))


def test_schema_lists_the_three_tools():
    c = TestClient(app())
    names = [t["name"] for t in c.get("/mcp-tools/gradio_api/mcp/schema").json()]
    assert set(names) == {"lookup_term", "explain_text", "todays_code_clue"}


def test_tools():
    a = app()
    _, (lookup_term, explain_text, todays_code_clue) = build_tools(a)
    r = lookup_term("الهلوسة")
    assert r["results"][0]["en"] == "Hallucination" and r["results"][0]["card"]["term_ar"] == "الهلوسة"
    e = explain_text("Check the summary for hallucinations before you send it.")
    assert {"Summary", "Hallucination"} <= {t["en"] for t in e["terms"]}
    clue = todays_code_clue("en")
    answer = a.state.game.puzzle("en", qatar_today()).word
    assert answer not in json.dumps(clue).lower() and clue["length"] == len(answer)


def test_web_app_still_serves_its_routes(tmp_path):
    (tmp_path / "index.html").write_text("<title>Darby</title>")
    c = TestClient(create_app(replace(load_settings(), termbank_source="off", web_dist=tmp_path)))
    assert "Darby" in c.get("/glossary").text and c.get("/api/health").status_code == 200
