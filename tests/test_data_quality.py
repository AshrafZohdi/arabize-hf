"""Data quality gates (docs/DATA_PIPELINE.md). They run on the pipeline outputs when they exist:
build them with `python -m data.pipeline stage0 && python -m data.pipeline stage2`."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "interim" / "term_bank_clean.parquet"
FINAL = ROOT / "data" / "processed" / "term_bank.parquet"

pd = pytest.importorskip("pandas")


@pytest.fixture(scope="module")
def clean():
    if not CLEAN.exists():
        pytest.skip("stage 2 output not built")
    return pd.read_parquet(CLEAN)


def test_en_key_unique(clean):
    assert clean.en_key.is_unique


def test_ids_unique(clean):
    assert clean.id.is_unique


def test_every_row_has_a_source(clean):
    assert (clean.sources.map(len) > 0).all()


def test_no_empty_terms(clean):
    assert (clean.en.str.strip() != "").all()
    assert (clean.ar_display.str.strip() != "").all()


def test_arabic_is_normalised(clean):
    bad = clean.ar_display.str.contains("ـ|[ﭐ-﷿ﹰ-﻿]|[٠-٩۰-۹]", regex=True)
    assert not bad.any(), clean[bad][["en", "ar_display"]].head().to_dict("records")


def test_our_reviewed_choices_win(clean):
    by_key = clean.set_index("en_key")
    assert by_key.loc["prompt", "ar_display"] == "أمر"
    assert by_key.loc["prompt", "ar_origin"] == "darby_editor"
    assert by_key.loc["AI", "ar_display"] == "الذكاء الاصطناعي"


def test_acronyms_and_untranslated_are_queued_for_stage3(clean):
    assert clean[clean.is_acronym].stage3_reason.notna().all()
    from data.text import is_latin_only

    latin = clean[clean.ar_display.map(is_latin_only)]
    assert latin.stage3_reason.notna().all()


def test_everyday_ms_words_are_not_highlighted(clean):
    by_key = clean.set_index("en_key")
    for word in ("send", "client", "check", "more"):
        if word in by_key.index:
            assert not by_key.loc[word, "highlight"], word
    assert by_key.loc["model", "highlight"]


@pytest.fixture(scope="module")
def final():
    if not FINAL.exists():
        pytest.skip("final term bank not built yet (after stage 3)")
    return pd.read_parquet(FINAL)


def test_final_no_latin_only_arabic(final):
    from data.text import is_latin_only

    assert not final.ar_display.map(is_latin_only).any()


def test_final_every_acronym_has_expansion(final):
    assert final[final.is_acronym].en_expanded.notna().all()


def test_final_en_key_unique_and_sourced(final):
    assert final.en_key.is_unique and (final.sources.map(len) > 0).all()
