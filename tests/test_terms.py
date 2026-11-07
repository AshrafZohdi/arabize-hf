import pytest

from server.terms import Term, TermFinder, is_acronym, suffix_forms


def t(en, source="darby_glossary"):
    return Term(id=en.lower().replace(" ", "-"), en=en, ar="ع", source=source, has_card=True)


@pytest.fixture
def finder():
    return TermFinder([t("Large language model"), t("Model"), t("Prompt"), t("Hallucination"), t("Context"), t("IT"), t("AI"), t("API"), t("Query"), t("Fact-check"), t("Training data")])


def found(finder, text):
    return [(m.text, m.term.en) for m in finder.find(text)]


def test_reference_email(finder):
    text = "Before you send the summary to the client, check it for hallucinations. Give the model more context in your prompt and ask it to cite the source paragraph."
    assert found(finder, text) == [("hallucinations", "Hallucination"), ("model", "Model"), ("context", "Context"), ("prompt", "Prompt")]


def test_longest_multiword_match_wins(finder):
    assert found(finder, "Our large language models are slow") == [("large language models", "Large language model")]
    assert found(finder, "a language model") == [("model", "Model")]


def test_acronyms_are_case_sensitive(finder):
    assert found(finder, "Send it to IT today") == [("IT", "IT")]
    assert found(finder, "AI said; the ai") == [("AI", "AI")]


def test_suffix_forms_and_possessive(finder):
    assert found(finder, "Two APIs and three queries") == [("APIs", "API"), ("queries", "Query")]
    assert found(finder, "PROMPTS prompted") == [("PROMPTS", "Prompt"), ("prompted", "Prompt")]
    assert found(finder, "The API's limit") == [("API's", "API")]


def test_hyphen_and_space_forms(finder):
    assert found(finder, "Please fact-check this, then fact check that.") == [("fact-check", "Fact-check"), ("fact check", "Fact-check")]


def test_offsets_point_into_original_text(finder):
    text = "Use the Training Data."
    (m,) = finder.find(text)
    assert text[m.start : m.end] == "Training Data"


def test_no_partial_word_matches(finder):
    assert found(finder, "remodel contextual") == []


def test_first_source_wins_on_conflict():
    f = TermFinder([t("Prompt", "darby_glossary"), t("Prompt", "gist")])
    assert f.find("prompt")[0].term.source == "darby_glossary"


@pytest.mark.parametrize("w,expected", [("AI", True), ("LLM", True), ("GPT4", True), ("It", False), ("a", False), ("ABCDEFG", False)])
def test_is_acronym(w, expected):
    assert is_acronym(w) is expected


def test_suffix_forms():
    assert {"queries", "querys"} & suffix_forms("query") == {"queries", "querys"}
    assert "promptes" in suffix_forms("prompt")  # harmless over-generation, never matches real text wrongly


def test_abbreviation_matches_its_full_term(finder):
    rag = t("Retrieval-augmented generation")
    finder.add(rag, surface="RAG")
    assert found(finder, "We use RAG and two RAGs.") == [("RAG", "Retrieval-augmented generation"), ("RAGs", "Retrieval-augmented generation")]
    assert found(finder, "a rag on the desk") == []  # without any_case, abbreviations keep their case like other acronyms


def test_non_technical_list_is_loaded_and_keeps_real_terms():
    from pathlib import Path

    from server.termbank import non_technical

    dropped = non_technical(Path(__file__).parents[1] / "content")
    assert {"WTF…", "a man and his dog", "bald man with glasses", "man"} <= dropped
    assert not {"A record", "man-in-the-middle", "trojan horse", "MAN", "ghost record"} & dropped


def test_longer_abbreviations_match_in_any_case(finder):
    rag = t("Retrieval-augmented generation")
    finder.add(rag, surface="RAG", any_case=True)
    finder.add(t("Machine learning"), surface="ML", any_case=False)
    assert [m.text for m in finder.find("RAG, Rag and rag")] == ["RAG", "Rag", "rag"]
    assert found(finder, "ML but not ml") == [("ML", "Machine learning")]


def test_irregular_technical_plurals():
    from server.terms import TermFinder

    f = TermFinder([t("Analysis"), t("Index"), t("Matrix"), t("Criterion"), t("Curriculum"), t("Shelf"), t("Skill"), t("Library")])
    text = "Two analyses, three indices, the matrices, these criteria, new curricula, the shelves, more skills and libraries."
    assert [m.term.en for m in f.find(text)] == ["Analysis", "Index", "Matrix", "Criterion", "Curriculum", "Shelf", "Skill", "Library"]


def test_singular_forms_for_search():
    from server.terms import singular_forms

    assert "skill" in singular_forms("skills") and "query" in singular_forms("queries")
    assert "analysis" in singular_forms("analyses") and "index" in singular_forms("indices") and "criterion" in singular_forms("criteria")
    assert singular_forms("access") == {"acc", "accis"} or "acces" not in singular_forms("access")
