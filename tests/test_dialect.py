import json
from pathlib import Path

from server.dialect import gulf_marker_count, gulf_words

ROOT = Path(__file__).resolve().parent.parent


def test_gulf_answers_are_told_apart_from_standard_arabic():
    gulf = "يعني الـ AI يألّف معلومة مو موجودة ويقولها بثقة، عشان جذي لازم تتأكد."
    msa = "يعني ذلك أن النموذج يؤلف معلومة غير موجودة ويقولها بثقة، لذلك يجب أن تتأكد."
    assert gulf_marker_count(gulf) >= 4  # يعني، مو، عشان، جذي، لازم
    assert gulf_marker_count(msa) <= 1  # يعني is shared with Standard Arabic
    assert gulf_marker_count("Plain English text.") == 0


def test_attached_conjunctions_and_diacritics_still_count():
    assert gulf_marker_count("وعشان الوقت ضيّق، فلازم نبدأ الحِين") == 3


def test_prompt_words_come_from_the_content_file():
    words = gulf_words(limit=5).split("، ")
    assert len(words) == 5 and words[0] == "لازم"


def test_missing_file_falls_back_to_a_short_list(tmp_path):
    assert "وايد" in gulf_words(content_dir=tmp_path)
    assert gulf_marker_count("وايد زين", content_dir=tmp_path) == 2


def test_marker_file_names_its_source_and_has_no_duplicates():
    data = json.loads((ROOT / "content/gulf-markers.json").read_text(encoding="utf-8"))
    assert data["source"]["repo"] == "drelhaj/Arabic-Dialects" and len(data["source"]["revision"]) == 40
    rows = data["markers"] + data["darbi_additions"]["markers"]
    spellings = [w for r in rows for w in (r["word"], *r.get("also", []))]
    assert len(spellings) == len(set(spellings))
    assert all(r["msa"] and r["en"] for r in rows)
    assert all(isinstance(r["count"], int) and r["count"] > 0 for r in data["markers"])
