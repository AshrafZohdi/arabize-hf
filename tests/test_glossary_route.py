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
