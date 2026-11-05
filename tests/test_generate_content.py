import importlib.util
import sys
from pathlib import Path

import pandas as pd

spec = importlib.util.spec_from_file_location("gen", Path(__file__).resolve().parent.parent / "jobs" / "generate_content.py")
gen = importlib.util.module_from_spec(spec)
sys.modules["gen"] = gen
spec.loader.exec_module(gen)


def bank():
    rows = [
        ("model-card", "model card", "بطاقة النموذج", ["gist"], False, False),
        ("language-model", "language model", "نموذج لغوي", ["gist"], False, False),
        ("neural-network", "neural network", "شبكة عصبية", ["gist"], False, False),
        ("bellman-operator", "Bellman operator", "مؤثر بيلمان", ["gist"], False, False),
        ("prompt", "Prompt", "أمر", ["darby"], False, True),
        ("drop-down-menu", "drop-down menu", "قائمة منسدلة", ["ms"], False, False),
    ]
    return pd.DataFrame(
        [{"id": i, "en": e, "ar_display": a, "ar_full": a, "source_names": s, "is_acronym": acr, "has_full_card": card} for i, e, a, s, acr, card in rows]
    )


VOCAB = {"model", "card", "language", "neural", "network", "drop", "down", "menu"}


def test_candidates_are_gist_everyday_terms_without_cards():
    c = gen.candidates(bank(), "a language model writes text", VOCAB)
    assert set(c.en) == {"model card", "language model", "neural network"}  # no Bellman, no MS, no existing card
    assert c.set_index("en").loc["language model", "in_lessons"]


def test_run_ranks_lessons_first_and_keeps_gist_arabic():
    cards, ratings, stats = gen.run(bank(), "a language model writes text", VOCAB, gen.Mock(), n=2)
    assert list(cards.term_en) == ["language model", "model card"]
    assert list(cards.term_msa) == ["نموذج لغوي", "بطاقة النموذج"]  # GIST human Arabic, never rewritten
    assert not cards.reviewed.any() and stats["cards"] == 2


def test_single_words_do_not_get_the_lessons_bonus():
    c = gen.candidates(bank(), "the model and the network", VOCAB | {"model"})
    assert not c.in_lessons.any()
