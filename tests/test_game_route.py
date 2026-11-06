import json
from dataclasses import replace

from fastapi.testclient import TestClient

from server.config import load_settings
from server.main import create_app


def client(tmp_path):
    return TestClient(create_app(replace(load_settings(), web_dist=tmp_path, termbank_source="off")))


def test_start_and_guess_never_leak_the_answer(tmp_path):
    c = client(tmp_path)
    app_game = c.app.state.game
    from server.game import qatar_today

    answer = app_game.puzzle("en", qatar_today()).word
    s = c.get("/api/daily-code", params={"lang": "en"}).json()
    assert answer not in json.dumps(s).lower()
    words = sorted(w for w in app_game.words("en") if len(w) == len(answer) and w != answer)[:5]
    tok = s["token"]
    for w in words:
        r = c.post("/api/daily-code/guess", json={"lang": "en", "token": tok, "guess": w}).json()
        tok = r["token"]
        assert "answer" not in r and answer not in json.dumps(r)
    r = c.post("/api/daily-code/guess", json={"lang": "en", "token": tok, "guess": answer}).json()
    assert r["won"] and r["answer"]["word"] == answer


def test_errors(tmp_path):
    c = client(tmp_path)
    s = c.get("/api/daily-code", params={"lang": "ar"}).json()
    assert c.post("/api/daily-code/guess", json={"lang": "ar", "token": "x.y", "guess": "كتاب"}).status_code == 400
    assert c.post("/api/daily-code/guess", json={"lang": "ar", "token": s["token"], "guess": "ب"}).json()["reason"] == "length"
