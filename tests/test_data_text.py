import pytest

from data.text import (
    ar_compare_key,
    acronym_kinds,
    ar_key,
    arabic_share,
    en_key,
    is_acronym_term,
    is_latin_only,
    keeps_acronym_only,
    normalise_ar,
    split_packed,
)


def test_arabic_share_and_latin_only():
    assert arabic_share("الهلوسة") == 1.0
    assert arabic_share("GPT") == 0.0
    assert 0 < arabic_share("نموذج GPT") < 1
    assert is_latin_only("Transformer") and not is_latin_only("محوّل Transformer")
    assert keeps_acronym_only("GPT-4") and not keeps_acronym_only("Attention")


def test_split_packed():
    assert split_packed("تسجيل الخروج؛ خروج") == ["تسجيل الخروج", "خروج"]
    assert split_packed("قائمة / لائحة") == ["قائمة", "لائحة"]
    assert split_packed("أمر أو موجه") == ["أمر", "موجه"]
    assert split_packed("شبكة عصبية") == ["شبكة عصبية"]


@pytest.mark.parametrize(
    "en,kinds",
    [
        ("A2C", {"all_caps", "digit_mix"}),
        ("GPT-4", {"all_caps", "digit_mix"}),
        ("A/B testing", {"all_caps", "slash"}),
        ("i.i.d. samples", {"dots"}),
        ("LLMs", {"acronym_plural"}),
        ("Focal Loss", set()),
        ("value function", set()),
    ],
)
def test_acronym_kinds(en, kinds):
    assert acronym_kinds(en) == kinds


@pytest.mark.parametrize("en", ["SAC", "A2C", "GPT-4", "LLMs", "F1", "A/B testing", "i.i.d.", "API", "BERT"])
def test_is_acronym_term(en):
    assert is_acronym_term(en)


@pytest.mark.parametrize("en", ["Euclidean space", "USB port", "Power BI Report Server", "Microsoft Teams for E3/E5", "CamemBERT", "softmax", "Focal Loss"])
def test_is_not_acronym_term(en):
    assert not is_acronym_term(en)


def test_normalise_ar():
    assert normalise_ar("الـــذكاء  الاصطناعي") == "الذكاء الاصطناعي"  # tatweel and spaces
    assert normalise_ar("ﻣﻠﻒ") == "ملف"  # presentation forms
    assert normalise_ar("نسخة ٣") == "نسخة 3"
    assert normalise_ar("<b>ملف</b>, مجلد") == "ملف، مجلد"
    assert normalise_ar("هل؟") == "هل؟" and normalise_ar("هل?") == "هل؟"


def test_ar_key():
    assert ar_key("إِدارة") == ar_key("ادارة") == "اداره"
    assert ar_key("مستوى") == "مستوي"


@pytest.mark.parametrize(
    "en,key",
    [
        ("Prompts", "prompt"),
        ("Large Language Models", "large language model"),
        ("LLMs", "LLM"),
        ("IT", "IT"),
        ("it", "it"),
        ("A/B testing", "a b testing"),
        ("queries", "query"),
        ("loss", "loss"),
        ("analysis", "analysis"),
        ("Fact-check", "fact check"),
    ],
)
def test_en_key(en, key):
    assert en_key(en) == key


def test_ar_compare_key_ignores_the_definite_article():
    assert ar_compare_key("المصدر") == ar_compare_key("مصدر")
    assert ar_compare_key("الذكاء الاصطناعي") == ar_compare_key("ذكاء اصطناعي")
    assert ar_compare_key("مطالبة") != ar_compare_key("أمر")
    assert ar_compare_key("الة") == "اله"  # short words keep their letters
