from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from server.config import load_settings
from server.main import create_app


@pytest.fixture
def dist(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><title>Darby</title>")
    (tmp_path / "assets" / "app-abc123.js").write_text("console.log(1)")
    (tmp_path / "favicon.svg").write_text("<svg/>")
    return tmp_path


@pytest.fixture
def client(dist):
    settings = replace(load_settings(), web_dist=dist)
    return TestClient(create_app(settings))


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert set(body) >= {"version", "demo_mode", "llm", "voice_enabled"}
    assert body["llm"]["state"] in {"ready", "waking", "demo", "unconfigured", "unknown"}


def test_unknown_api_path_is_404_not_spa(client):
    assert client.get("/api/nope").status_code == 404


@pytest.mark.parametrize("path", ["/", "/glossary", "/tutor", "/lesson/3"])
def test_spa_routes_serve_index(client, path):
    r = client.get(path)
    assert r.status_code == 200
    assert "<title>Darby</title>" in r.text
    assert r.headers["cache-control"] == "no-cache"


def test_hashed_assets_are_cached(client):
    r = client.get("/assets/app-abc123.js")
    assert r.status_code == 200
    assert "immutable" in r.headers["cache-control"]


def test_path_traversal_does_not_leak_files(client):
    r = client.get("/%2e%2e/server/main.py")
    assert "create_app" not in r.text


def test_missing_build_is_503(tmp_path):
    settings = replace(load_settings(), web_dist=tmp_path / "missing")
    assert TestClient(create_app(settings)).get("/").status_code == 503


def test_assets_are_gzipped(dist):
    (dist / "assets" / "big.js").write_text("const x = 1;\n" * 500)
    c = TestClient(create_app(replace(load_settings(), web_dist=dist)))
    r = c.get("/assets/big.js", headers={"accept-encoding": "gzip"})
    assert r.headers.get("content-encoding") == "gzip"
