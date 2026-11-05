import pandas as pd
import pytest

from data.pipeline import apply_overrides, display_form


def test_display_form():
    assert display_form("الممثل والناقد ذو الميزة", "A2C", "Advantage Actor-Critic") == "الممثل والناقد ذو الميزة (A2C: Advantage Actor-Critic)"
    assert display_form("دولار أمريكي", "USD", None) == "دولار أمريكي (USD)"
    assert display_form("القانون العام لحماية البيانات (GDPR)", "GDPR", "General Data Protection Regulation") == "القانون العام لحماية البيانات (GDPR)"


def test_overrides_win_and_mark_reviewed():
    bank = pd.DataFrame([{"id": "gcc", "ar_display": "x", "reviewed": False, "needs_review": True}, {"id": "a", "ar_display": "y", "reviewed": False, "needs_review": False}])
    ov = pd.DataFrame([{"id": "gcc", "field": "ar_display", "value": "مجلس التعاون الخليجي (GCC)", "reviewer": "team", "note": ""}, {"id": "a", "field": "drop", "value": "", "reviewer": "team", "note": ""}])
    out = apply_overrides(bank, ov).set_index("id")
    assert out.loc["gcc", "ar_display"] == "مجلس التعاون الخليجي (GCC)" and out.loc["gcc", "reviewed"] and not out.loc["gcc", "needs_review"]
    assert "a" not in out.index


def test_overrides_reject_unknown_fields_and_ids():
    bank = pd.DataFrame([{"id": "x", "ar_display": "y", "reviewed": False, "needs_review": False}])
    with pytest.raises(ValueError):
        apply_overrides(bank, pd.DataFrame([{"id": "x", "field": "en", "value": "z", "reviewer": "", "note": ""}]))
    with pytest.raises(ValueError):
        apply_overrides(bank, pd.DataFrame([{"id": "nope", "field": "ar_display", "value": "z", "reviewer": "", "note": ""}]))
