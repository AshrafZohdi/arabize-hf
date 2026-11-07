import json
from pathlib import Path

from server.about import ABOUT, AUDIENCE
from server.prompts.explain import build_explain_prompt
from server.prompts.prompt_lab import build_scoring_prompt
from server.prompts.tutor import build_tutor_system

ROOT = Path(__file__).parents[1]


def test_interface_shows_the_same_about_sentence():
    for lang in ("ar", "en"):
        strings = json.loads((ROOT / f"web/src/i18n/{lang}.json").read_text(encoding="utf-8"))
        assert strings["app.about"] == ABOUT[lang]


def test_every_prompt_names_the_same_audience():
    tutor = build_tutor_system(None, "gulf", [])
    assert ABOUT["en"] in tutor and ABOUT["ar"] in tutor and "what Darbi is" in tutor
    assert AUDIENCE in build_explain_prompt("text", "gulf", "work", [])[0]
    assert AUDIENCE in build_scoring_prompt("task", "prompt", "gulf")[0]


def test_old_audience_wording_is_gone_from_the_app():
    old = ("professionals in Qatar", "Arabic-speaking professionals")
    for path in [*ROOT.joinpath("server").rglob("*.py"), *ROOT.joinpath("web/src").rglob("*.ts*"), ROOT / "README.md"]:
        text = path.read_text(encoding="utf-8")
        assert not any(o in text for o in old), path
