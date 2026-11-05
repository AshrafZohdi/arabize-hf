import importlib.util
import sys
from pathlib import Path

import pandas as pd

spec = importlib.util.spec_from_file_location("stage3", Path(__file__).resolve().parent.parent / "jobs" / "stage3_translate.py")
stage3 = importlib.util.module_from_spec(spec)
sys.modules["stage3"] = stage3  # dataclasses look the module up by name
spec.loader.exec_module(stage3)


def bank():
    rows = [
        # id, en, domain, ar_display, is_acronym, stage3_reason, ar_origin
        ("api", "API", "software", "API", True, "acronym without expansion", "human_gist"),
        ("gdpr", "GDPR", "software", "القانون العام لحماية البيانات (GDPR)", True, "acronym without expansion", "human_ms"),
        ("gcc", "GCC", "software", "سحابة القطاع الحكومي", True, "acronym without expansion", "human_ms"),
        ("camembert", "CamemBERT", "ai", "CamemBERT", False, "untranslated", "human_gist"),
        ("bad", "BAD term", "ai", "BAD term", False, "untranslated", "human_gist"),
        ("application-programming-interface", "application programming interface", "software", "واجهة برمجة التطبيقات", False, None, "human_ms"),
        ("cls", "CLS", "ai", "CLS", True, "acronym without expansion", "human_gist"),
        ("common-language-specification", "Common Language Specification", "software", "مواصفات اللغة العامة", False, None, "human_ms"),
        ("prompt", "Prompt", "ai", "أمر", False, None, "darby_editor"),
    ]
    return pd.DataFrame(rows, columns=["id", "en", "domain", "ar_display", "is_acronym", "stage3_reason", "ar_origin"])


def fake_embed(a, b):
    return [1.0 if x.lower() == y.lower() else 0.5 for x, y in zip(a, b)]


def run():
    return stage3.run_stage3(bank(), stage3.MockBackend(), fake_embed, {"AI": "artificial intelligence"})


def test_only_queued_rows_are_processed():
    out, stats = run()
    assert set(out.id) == {"api", "gdpr", "gcc", "camembert", "bad", "cls"} and stats["queued"] == 6


def test_human_arabic_is_never_overwritten():
    out, _ = run()
    by = out.set_index("id")
    assert pd.isna(by.loc["gdpr"].get("ar_full")) and pd.isna(by.loc["gcc"].get("ar_full"))
    assert by.loc["api", "ar_full"] == "ترجمة application programming interface" and by.loc["api", "ar_origin"] == "fanar_generated"


def test_uncertain_expansion_and_rejected_output_go_to_review():
    out, stats = run()
    by = out.set_index("id")
    assert by.loc["gcc", "needs_review"] and "several or uncertain" in "; ".join(by.loc["gcc", "issues"])
    assert by.loc["bad", "needs_review"] and "translation: no valid output" in by.loc["bad", "issues"]
    assert stats["needs_review"] >= 2


def test_back_translation_similarity_is_scored():
    out, stats = run()
    by = out.set_index("id")
    assert by.loc["api", "similarity"] == 1.0
    assert stats["similarity"]["count"] == 3


def test_expansions_are_checked_against_the_bank_and_human_arabic():
    out, _ = run()
    by = out.set_index("id")
    # API's expansion is a term in the bank: corroborated, nothing to review.
    assert by.loc["api", "corroborated"] and not by.loc["api", "needs_review"]
    # GDPR: human Arabic exists, mock back-translation disagrees with the expansion, so it is flagged.
    assert any("disagrees with the human Arabic" in i for i in by.loc["gdpr", "issues"])
    # Untranslated names get a description, not an expansion.
    assert by.loc["camembert", "en_description"] == "CamemBERT expanded" and pd.isna(by.loc["camembert"].get("en_expanded"))


def test_deterministic_candidates_from_initials():
    long_terms = {"software:API": ["application programming interface"]}
    assert stage3.candidates_from_bank("APIs", long_terms, {}, "software") == ["application programming interface"]
    assert stage3.candidates_from_bank("APIs", long_terms, {}, "ai") == []
    assert stage3.candidates_from_bank("AI", {}, {"AI": "artificial intelligence"}, "ai") == ["artificial intelligence"]


def test_parse_strips_think_and_validates():
    assert stage3.parse('<think>x</think>{"ar_full": "أمر"}', stage3.Translation).ar_full == "أمر"
    assert stage3.parse('{"ar_full": ""}', stage3.Translation) is None


def test_corroboration_only_counts_in_the_same_domain():
    b = bank()
    out, _ = stage3.run_stage3(b, stage3.MockBackend(), fake_embed, {"CLS": "Common Language Specification"})
    by = out.set_index("id")
    # The curated table is a deliberate source, so it still corroborates; without it the software term must not.
    assert by.loc["cls", "corroborated"]
    out, _ = stage3.run_stage3(b, stage3.MockBackend(), fake_embed, {})
    by = out.set_index("id")
    assert not by.loc["cls", "corroborated"] and by.loc["cls", "needs_review"]


def test_name_descriptions_go_to_review():
    out, _ = run()
    assert out.set_index("id").loc["camembert", "needs_review"]
