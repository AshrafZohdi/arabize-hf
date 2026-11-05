import pandas as pd

from data.pipeline import build_clean, merge_stage3
from data.publish import apply_public, key_hash, public_frames


def rows():
    data = [
        ("darby", "darby_glossary", "g#0", "Prompt", "أمر"),
        ("gist", "gist", "gist#1", "CRF", "CRF"),
        ("gist", "gist", "gist#2", "prompt tuning", "تعديل التلميحات"),
        ("ms", "ms", "ms#1", "GCC", "سحابة القطاع الحكومي"),
        ("ms", "ms", "ms#2", "drop-down menu", "قائمة منسدلة"),
        ("ms", "ms", "ms#3", "CDA", "CDA"),
        ("ms", "ms", "ms#4", "prompt", "مطالبة"),
    ]
    return pd.DataFrame(data, columns=["source", "set", "row_id", "en", "ar"])


def results():
    return pd.DataFrame(
        [
            {"id": "crf", "en": "CRF", "en_expanded": "conditional random field", "ar_full": "مجال عشوائي مشروط", "needs_review": False, "issues": []},
            {"id": "gcc", "en": "GCC", "en_expanded": "Gulf Cooperation Council", "ar_full": None, "needs_review": True, "issues": ["expansion disagrees with the human Arabic"]},
            {"id": "cda", "en": "CDA", "en_expanded": "content data analysis", "ar_full": "تحليل بيانات المحتوى", "needs_review": True, "issues": ["expansion unverified"]},
        ]
    )


def overrides():
    return pd.DataFrame([{"id": "gcc", "field": "ar_display", "value": "سحابة المجتمع الحكومي (GCC: Government Community Cloud)", "reviewer": "team", "note": ""}])


def test_public_round_trip_equals_direct_merge():
    clean, _, _ = build_clean(rows())
    final, published, _ = merge_stage3(clean, results(), overrides())
    train, completions, _ = public_frames(final)
    rebuilt = apply_public(clean, train, completions, overrides())
    cols = ["id", "en", "en_expanded", "ar_display", "ar_origin", "reviewed", "needs_review"]
    a = published.sort_values("id")[cols].reset_index(drop=True).astype(str)
    b = rebuilt.sort_values("id")[cols].reset_index(drop=True).astype(str)
    assert a.equals(b), (a, b)


def test_public_files_hold_no_microsoft_text():
    clean, _, _ = build_clean(rows())
    final, _, _ = merge_stage3(clean, results(), overrides())
    train, completions, _ = public_frames(final)
    ms_terms = {"GCC", "drop-down menu", "CDA"}
    assert not ms_terms & set(train.en)
    # "prompt" is ours and also in MS; MS's wording (مطالبة) must not ride along in the variants.
    assert "مطالبة" not in train.set_index("id").loc["prompt", "ar_variants"]
    flat = completions.astype(str).to_string()
    assert not any(t in flat for t in ("GCC", "drop-down", "CDA", "سحابة القطاع الحكومي"))
    assert set(completions.key) <= {key_hash(k) for k in final.en_key}
    # Our generated translation for an MS acronym is published (it is our work), the MS Arabic is not.
    assert "تحليل بيانات المحتوى" in flat
