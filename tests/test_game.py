import json
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from server.game import MAX_TRIES, Game, mark, normalize, qatar_today, word_forms

DAY = date(2026, 11, 6)


def glossary():
    entries = {
        "draft": {"term_en": "Draft", "term_msa": "مسودة", "def_ar": "أول نسخة من النص.", "def_en": "A first version."},
        "prompt": {"term_en": "Prompt", "term_msa": "أمر", "def_ar": "التعليمات للذكاء الاصطناعي.", "def_en": "The instruction you give."},
        "large-language-model": {"term_en": "Large language model", "term_msa": "نموذج لغوي كبير", "def_ar": "x", "def_en": "x"},
        "ai": {"term_en": "AI", "term_msa": "الذكاء الاصطناعي", "def_ar": "x", "def_en": "x"},
    }
    return SimpleNamespace(entries=entries)


@pytest.fixture
def game(tmp_path):
    (tmp_path / "words-en.json").write_text(json.dumps({"words": ["draft", "craft", "chart", "graft", "prompt", "dreams"]}))
    (tmp_path / "words-ar.json").write_text(json.dumps({"words": ["مسوده", "مدرسه", "كتاب"]}))
    return Game(glossary(), tmp_path, b"test-secret")


@pytest.mark.parametrize(
    "answer,guess,marks",
    [
        ("draft", "draft", ["hit"] * 5),
        ("draft", "craft", ["miss", "hit", "hit", "hit", "hit"]),
        ("draft", "chart", ["miss", "miss", "hit", "near", "hit"]),
        # Repeated letter: only one spare "a", so only the first extra "a" is near.
        ("draft", "aaaaa", ["miss", "miss", "hit", "miss", "miss"]),
        ("abbey", "babes", ["near", "near", "hit", "hit", "miss"]),
    ],
)
def test_mark(answer, guess, marks):
    assert mark(answer, guess) == marks


def test_normalize_and_forms():
    assert normalize("مُسوَّدة") == "مسوده" and normalize("إأآ") == "ااا" and normalize("Draft ") == "draft"
    assert "مسوده" in word_forms("والمسوده") and "كتاب" in word_forms("كتابات")


def test_puzzle_words_are_single_words_of_3_to_9_letters(game):
    assert game.count("en") == 2  # draft, prompt (AI too short, LLM has spaces)
    assert game.count("ar") == 2  # مسوده and امر (أمر normalised, 3 letters)


def test_word_of_the_day_walks_the_list(game):
    words = [game.puzzle("en", date(2026, 1, 1)).word, game.puzzle("en", date(2026, 1, 2)).word, game.puzzle("en", date(2026, 1, 3)).word]
    assert words[0] != words[1] and words[0] == words[2]


def test_qatar_date():
    assert qatar_today(datetime(2026, 11, 5, 22, 30, tzinfo=timezone.utc)) == date(2026, 11, 6)


def answer_for(game, lang="en"):
    return game.puzzle(lang, DAY).word


def test_start_never_contains_the_answer(game):
    s = game.start("en", DAY)
    assert answer_for(game) not in json.dumps(s).lower()
    assert s["length"] == len(answer_for(game)) and s["clue"]["term"]


def test_wrong_guesses_never_reveal_the_answer_until_six(game):
    answer = answer_for(game)
    wrong = next(w for w in ("craft", "chart", "graft") if len(w) == len(answer) and w != answer) if len(answer) == 5 else "dreams"
    tok = game.start("en", DAY)["token"]
    for i in range(MAX_TRIES):
        r = game.guess("en", DAY, tok, wrong)
        tok = r["token"]
        if i < MAX_TRIES - 1:
            assert "answer" not in r and answer not in json.dumps(r) and not r["finished"]
    assert r["finished"] and not r["won"] and r["answer"]["word"] == answer and r["answer"]["xp"] == 10
    assert game.guess("en", DAY, tok, wrong) == {"error": "finished"}


def test_win_pays_30(game):
    r = game.guess("en", DAY, game.start("en", DAY)["token"], answer_for(game).upper())
    assert r["won"] and r["finished"] and r["answer"]["xp"] == 30


def test_not_a_word_is_refused_at_no_cost(game):
    tok = game.start("en", DAY)["token"]
    bad = "zzzzz" if len(answer_for(game)) == 5 else "zzzzzz"
    assert game.guess("en", DAY, tok, bad) == {"error": "invalid", "reason": "not_a_word"}
    assert game.guess("en", DAY, tok, "ab") == {"error": "invalid", "reason": "length"}


def test_forged_or_stale_tokens_are_refused(game):
    tok = game.start("en", DAY)["token"]
    body, sig = tok.rsplit(".", 1)
    assert game.guess("en", DAY, body + ".0000", answer_for(game))["error"] == "bad_token"
    # A token claiming six used tries, without a valid signature, cannot unlock the answer.
    import base64

    fake = base64.urlsafe_b64encode(json.dumps({"l": "en", "d": DAY.isoformat(), "g": ["x"] * 6}).encode()).decode() + "." + sig
    assert game.guess("en", DAY, fake, "craft")["error"] == "bad_token"
    assert game.read_token(tok, "en", date(2026, 11, 7)) is None and game.read_token(tok, "ar", DAY) is None


def test_arabic_game(game):
    s = game.start("ar", DAY)
    p = game.puzzle("ar", DAY)
    assert s["clue"]["term"] in ("Draft", "Prompt") and s["length"] == len(p.word)
    spelled = {"مسوده": "مُسوَّدة", "امر": "أمر"}[p.word]  # written with diacritics and hamza, still matches
    r = game.guess("ar", DAY, s["token"], spelled)
    assert r["won"] and r["marks"] == ["hit"] * len(p.word)


def test_real_word_lists_load_as_words_not_characters():
    """content/words-*.json store one space-separated string: a set of characters would refuse every guess."""
    from server.config import load_settings
    from server.glossary import load_glossary

    settings = load_settings()
    g = Game(load_glossary(settings.content_dir), settings.content_dir, b"s")
    en, ar = g.words("en"), g.words("ar")
    assert len(en) > 100_000 and {"people", "colors", "prompt", "draft"} <= en
    assert len(ar) > 100_000 and "كتاب" in ar
    assert g.is_real_word("en", "people", "column") and not g.is_real_word("en", "qzxqzx", "column")
