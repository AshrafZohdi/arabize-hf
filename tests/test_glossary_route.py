from dataclasses import replace

import numpy as np
from fastapi.testclient import TestClient

from server.config import load_settings
from server.main import create_app
from server.termbank import TermBank


def row(i, en, ar, origin="human_gist", domain="ai", card=False):
    return {"id": i, "en": en, "en_key": en.lower(), "en_expanded": None, "is_acronym": False, "ar_display": ar, "ar_full": ar, "ar_key": ar,
            "ar_origin": origin, "reviewed": origin == "darby_editor", "needs_review": False, "domain": domain, "source_names": [], "has_full_card": card, "highlight": True}


def client(tmp_path, bank=None, embedder=None):
    app = create_app(replace(load_settings(), web_dist=tmp_path, termbank_source="off"))
    if bank is not None:
        app.state.termbank = bank
    app.state.embedder = embedder
    return TestClient(app)


def test_cards_in_each_language(tmp_path):
    c = client(tmp_path)
    gulf = c.get("/api/glossary/cards", params={"lang": "gulf"}).json()["cards"]
    en = c.get("/api/glossary/cards", params={"lang": "en"}).json()["cards"]
    assert len(gulf) == 40
    assert {c["domain"] for c in gulf} == {"ai", "software"}
    assert sum(c["domain"] == "ai" for c in gulf) == 28
    h_gulf = next(x for x in gulf if x["term_en"] == "Hallucination")
    h_en = next(x for x in en if x["term_en"] == "Hallucination")
    assert h_gulf["term_ar"] == "الهلوسة" and h_gulf["explanation"] != h_en["explanation"] and h_gulf["example"]


def test_search_both_languages_and_article(tmp_path):
    c = client(tmp_path)
    assert c.get("/api/glossary/search", params={"q": "الهلوسة"}).json()["results"][0]["en"] == "Hallucination"
    assert c.get("/api/glossary/search", params={"q": "هلوسة"}).json()["results"][0]["en"] == "Hallucination"  # without ال
    assert c.get("/api/glossary/search", params={"q": "prompt"}).json()["results"][0]["en"] == "Prompt"


def test_domain_filter_and_ranking(tmp_path):
    bank = TermBank.from_rows([row("prompt", "Prompt", "أمر", "darby_editor", card=True), row("prompt-tuning", "prompt tuning", "تعديل"), row("command-prompt", "command prompt", "موجه الأوامر", "human_ms", "software")])
    c = client(tmp_path, bank)
    res = c.get("/api/glossary/search", params={"q": "prompt"}).json()["results"]
    assert [r["en"] for r in res][:2] == ["Prompt", "prompt tuning"] and res[0]["source"] == "darby"
    sw = c.get("/api/glossary/search", params={"q": "prompt", "domain": "software"}).json()["results"]
    assert [r["en"] for r in sw] == ["command prompt"]


class FakeEmbedder:
    def encode(self, texts):
        return np.array([[0.0, 1.0]], dtype=np.float32)


def test_semantic_matches_are_labelled(tmp_path):
    bank = TermBank.from_rows([row("hallucination", "Hallucination", "الهلوسة", "darby_editor", card=True), row("bias", "Bias", "التحيز", "darby_editor", card=True)])
    # Vectors follow the bank's own row order; hallucination is the meaning match among the cards.
    bank.vectors = np.zeros((len(bank.rows), 2), dtype=np.float32)
    bank.enrich_cards(type("E", (), {"encode": lambda self, texts: np.array([[0.0, 1.0] if "Hallucination" in t else [1.0, 0.0] for t in texts], dtype=np.float32)})(), {"hallucination": "Hallucination", "bias": "Bias"})
    c = client(tmp_path, bank, FakeEmbedder())
    res = c.get("/api/glossary/search", params={"q": "made-up facts"}).json()
    assert res["semantic"] and res["results"][0]["en"] == "Hallucination" and res["results"][0]["match"] == "meaning"


def test_term_lookup(tmp_path):
    c = client(tmp_path)
    assert c.get("/api/glossary/term/hallucination").json()["full"]["term_ar"] == "الهلوسة"
    assert c.get("/api/glossary/term/nope").status_code == 404


def test_browse_pages_through_every_term(tmp_path):
    bank = TermBank.from_rows([row("b", "beta", "ب"), row("a", "Alpha", "أ"), row("c", "3D model", "ثلاثي", domain="software"), row("d", "-delta", "د")])
    c = client(tmp_path, bank)
    page = c.get("/api/glossary/browse", params={"limit": 2}).json()
    assert page["total"] == 4 and [r["en"] for r in page["results"]] == ["3D model", "Alpha"]
    assert [r["en"] for r in c.get("/api/glossary/browse", params={"offset": 2, "limit": 2}).json()["results"]] == ["beta", "-delta"]
    assert [r["en"] for r in c.get("/api/glossary/browse", params={"letter": "#"}).json()["results"]] == ["3D model"]
    assert c.get("/api/glossary/browse", params={"domain": "software"}).json()["total"] == 1
    assert c.get("/api/glossary/browse", params={"letter": "ab"}).status_code == 422


def test_hub_glossary_shape_works_with_cards(tmp_path, monkeypatch):
    import json

    from server import glossary as g

    rec = {"id": "chatbot", "origin": "fanar_generated", "domain": "ai", "term_en": "chatbot", "term_msa": "بوت محادثة", "term_gulf": "بوت",
           "def_en": "A program that chats.", "def_ar": "برنامج يحاور.", "def_gulf": "برنامج يسولف وياك.", "analogy_en": "a", "analogy_ar": "مثل",
           "mistake_en": "m", "mistake_ar": "خطأ", "example_en": "e", "example_ar": "مثال", "example_gulf": "مثال", "related": [], "reviewed": False}
    path = tmp_path / "glossary.json"
    path.write_text(json.dumps([rec], ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr("huggingface_hub.hf_hub_download", lambda *a, **k: str(path))
    gl = g.load_glossary_from_hub()
    card = gl.card("chatbot", "gulf")
    assert card["explanation"] == "برنامج يسولف وياك." and card["source"] == "fanar"
    assert gl.finder.find("Ask the chatbots")[0].term.id == "chatbot"


def test_search_suggests_the_nearest_card_for_a_typo(tmp_path):
    c = client(tmp_path)
    body = c.get("/api/glossary/search", params={"q": "halucination"}).json()
    assert body["suggestion"]["en"] == "Hallucination"
    assert c.get("/api/glossary/search", params={"q": "Hallucination"}).json()["suggestion"] is None


def test_search_finds_abbreviations_in_any_case(tmp_path):
    c = client(tmp_path)
    for q in ("llm", "Llm", "LLM"):
        assert c.get("/api/glossary/search", params={"q": q}).json()["results"][0]["en"] == "Large language model"


def test_search_finds_the_singular_of_a_plural(tmp_path):
    c = client(tmp_path)
    assert c.get("/api/glossary/search", params={"q": "prompts"}).json()["results"][0]["en"] == "Prompt"
    assert c.get("/api/glossary/search", params={"q": "skills"}).json()["results"][0]["en"] == "skill"
    assert c.get("/api/glossary/search", params={"q": "plugins"}).json()["results"][0]["en"] == "plug-in"  # plural of another spelling


def test_new_terms_and_mcp_are_highlighted(tmp_path):
    from fastapi.testclient import TestClient  # noqa: F401

    c = client(tmp_path)
    text = "Install the plugin, add two connectors and MCP servers, then give the AI agent new skills with tool calling."
    got = [(m["text"], m["en"]) for m in c.post("/api/terms", json={"text": text}).json()["matches"]]
    for pair in [("plugin", "plug-in"), ("connectors", "connector"), ("MCP", "Model Context Protocol"), ("AI agent", "AI agent"), ("skills", "skill"), ("tool calling", "tool calling")]:
        assert pair in got, (pair, got)
