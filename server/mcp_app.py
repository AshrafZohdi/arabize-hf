"""Darbi as an MCP server (P1, docs/HF_PLAN.md #11): a small Gradio app mounted in FastAPI with mcp_server=True, so
any AI assistant can use Darbi's Arabic AI glossary. Each function's docstring and type hints become the tool's
description and schema. The answer to today's code is never exposed.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

MOUNT_PATH = "/mcp-tools"


def build_tools(app: FastAPI):
    import gradio as gr

    from server.game import qatar_today
    from server.routes.glossary import quick_card

    def lookup_term(term: str, lang: str = "gulf") -> dict[str, Any]:
        """Look up an English AI or software term (or its Arabic) in Darbi's term bank of about 24,000 terms.

        Args:
            term: The term to look up, in English or Arabic, for example "hallucination" or "الأوامر".
            lang: Language of the explanation on full cards: "en", "msa" (Modern Standard Arabic) or "gulf" (Gulf Arabic).

        Returns:
            The best matches. Each has the English term, the Arabic term, its source, whether a person reviewed it,
            and a full learning card (definition, analogy, example) when Darbi has one.
        """
        lang = lang if lang in ("en", "msa", "gulf") else "gulf"
        tb, g = app.state.termbank, app.state.glossary
        hits = tb.lexical(term, limit=5)
        out = []
        for _, i in hits[:5]:
            r = tb.rows[i]
            out.append(quick_card(r) | {"card": g.card(r["id"], lang)})
        return {"query": term, "results": out, "terms_in_bank": len(tb.rows)}

    def explain_text(text: str, lang: str = "gulf") -> dict[str, Any]:
        """Find the AI and software terms in an English work text and give their Arabic, with Darbi's cards.

        No AI model is called: matching is deterministic against Darbi's term bank, so this is fast and free.

        Args:
            text: An English work text such as an email or report paragraph (up to 2,000 characters).
            lang: Language of the explanations: "en", "msa" or "gulf".

        Returns:
            Every matched term with its position in the text, its Arabic, and a full card when Darbi has one.
        """
        lang = lang if lang in ("en", "msa", "gulf") else "gulf"
        text = text[:2000]
        g = app.state.glossary
        matches = []
        for m in app.state.termbank.finder.find(text):
            matches.append({"text": m.text, "start": m.start, "end": m.end, "en": m.term.en, "ar": m.term.ar, "card": g.card(m.term.id, lang)})
        return {"terms": matches, "count": len(matches)}

    def todays_code_clue(lang: str = "en") -> dict[str, Any]:
        """Today's Darbi daily code (شيفرة اليوم): the clue and the word length, never the answer.

        Args:
            lang: "en" to guess the English term (the clue is in Arabic) or "ar" to guess the Arabic term (the clue is in English).

        Returns:
            The date (Qatar time), the word length, the number of tries and the clue.
        """
        lang = lang if lang in ("en", "ar") else "en"
        s = app.state.game.start(lang, qatar_today())
        return {k: s[k] for k in ("date", "lang", "length", "max_tries", "clue")}

    with gr.Blocks(title="Darbi tools") as demo:
        gr.Markdown("# Darbi (دربي) tools\nAI and software terms in Arabic and English, as MCP tools. The app is at the Space root.")
        with gr.Tab("lookup_term"):
            t1, l1 = gr.Textbox(label="term"), gr.Dropdown(["gulf", "msa", "en"], value="gulf", label="lang")
            o1 = gr.JSON()
            gr.Button("Look up").click(lookup_term, [t1, l1], o1, api_name="lookup_term")
        with gr.Tab("explain_text"):
            t2, l2 = gr.Textbox(label="text", lines=4), gr.Dropdown(["gulf", "msa", "en"], value="gulf", label="lang")
            o2 = gr.JSON()
            gr.Button("Find terms").click(explain_text, [t2, l2], o2, api_name="explain_text")
        with gr.Tab("todays_code_clue"):
            l3 = gr.Dropdown(["en", "ar"], value="en", label="lang")
            o3 = gr.JSON()
            gr.Button("Get clue").click(todays_code_clue, [l3], o3, api_name="todays_code_clue")
    return demo, (lookup_term, explain_text, todays_code_clue)


def mount(app: FastAPI) -> FastAPI:
    import gradio as gr

    demo, _ = build_tools(app)
    return gr.mount_gradio_app(app, demo, path=MOUNT_PATH, mcp_server=True)
