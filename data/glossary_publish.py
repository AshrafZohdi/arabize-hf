"""Publish `nuvais/darby-ai-glossary-ar-en`: Darby's full learning cards (our 40 plus 100 written by Fanar 2).

    python -m data.glossary_publish [--push]

The Space loads `data/glossary.json` from this dataset at startup, with content/ as the fallback.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
GLOSSARY_REPO = "nuvais/darby-ai-glossary-ar-en"
STAGING_REPO = "nuvais/darby-term-bank-staging"
OUT = ROOT / "data" / "glossary_public"
TEXT_FIELDS = [
    "term_en", "term_msa", "term_gulf", "def_en", "def_ar", "def_gulf", "analogy_en", "analogy_ar",
    "mistake_en", "mistake_ar", "example_en", "example_ar", "example_gulf",
]

CARD = """---
license: apache-2.0
language:
- ar
- en
pretty_name: Darby AI glossary (Arabic, Gulf Arabic, English)
size_categories:
- n<1K
task_categories:
- translation
- text-generation
tags:
- arabic
- gulf-arabic
- glossary
- qatar
- ai-literacy
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train.parquet
---

# Darby AI glossary: learning cards in Arabic, Gulf Arabic and English

<div dir="rtl" lang="ar">

بطاقات تعليمية لمصطلحات الذكاء الاصطناعي في الشغل: المصطلح بالإنجليزي، والمصطلح العربي الفصيح، وكيف يقوله الزملاء بالخليجي، وتعريف بالفصحى والخليجي والإنجليزي، وتشبيه، وغلطة شائعة، وأمثلة من بيئة عمل في الدوحة.

- {n_ours} بطاقة من دربي (اختيار المصطلح العربي مستند إلى اليونسكو وMBZUAI ومايكروسوفت وغوغل، والنص كُتب بمساعدة الذكاء الاصطناعي ولم يُراجع لغويًا بعد).
- {n_fanar} بطاقة كتبها نموذج «فنار 2» القطري حول الترجمة البشرية للمصطلح من GIST، ولم تُراجع بعد.

</div>

## What this is

{n} learning cards for the English vocabulary of AI at work, for Arabic-speaking professionals in Qatar. Each card has the English term, the standard Arabic term, how Gulf colleagues say it, definitions in English, simple Modern Standard Arabic and Gulf Arabic, an analogy, a common mistake, examples set in a Doha workplace, and related terms. Built for Darby (دربي) at the Qai x Hugging Face Hackathon 01 in Doha (November 2026).

| Origin | Cards | How it was made |
|---|---|---|
| `darby` | {n_ours} | Written for the earlier Arabize app. Arabic term choices cite UNESCO, MBZUAI, Microsoft Learn and Google's ML glossary (see `sources`); card text drafted with AI, not yet language-reviewed |
| `fanar_generated` | {n_fanar} | Chosen from GIST (`Jerry999/multilingual-terminology`, Apache 2.0) by Fanar 2's ratings for office relevance and usefulness with AI tools, then written by `QCRI/Fanar-2-27B-Instruct` (bf16, vLLM, HF Job on 1x A100) around GIST's human Arabic, which is kept as `term_msa` unchanged |

**No card has had a language review yet** (`reviewed` is false everywhere). A Gulf Arabic speaker on the team spot-checks the cards; corrections will be released as new revisions.

## Fields

`id`, `origin`, `domain` (`ai` or `software`), `term_en`, `term_msa`, `term_gulf`, `def_en`, `def_ar`, `def_gulf`, `analogy_en`, `analogy_ar`, `mistake_en`, `mistake_ar`, `example_en`, `example_ar`, `example_gulf`, `related` (English terms), `msa_source`, `reviewed`, `sources` (JSON: citations for our own terms), `extra` (JSON: technical notes, formula or code where a card has them). The same records are in `data/glossary.json`.

## Related

- Term bank with about 24,000 terms: [`nuvais/darby-term-bank`](https://huggingface.co/datasets/nuvais/darby-term-bank)
- Lessons: [`nuvais/darby-lessons`](https://huggingface.co/datasets/nuvais/darby-lessons)
- App and code: [Darby Space](https://huggingface.co/spaces/FayezAlkh12/darby), [GitHub](https://github.com/AshrafZohdi/arabize-hf)

## Licence and credit

Apache 2.0. GIST Arabic terms: Jiarui Liu et al., *Towards Global AI Inclusivity: A Large-Scale Multilingual Terminology Dataset (GIST)*, [arXiv 2412.18367](https://arxiv.org/abs/2412.18367). Fanar 2 by QCRI, Apache 2.0.
"""


def _ours() -> list[dict]:
    from server.glossary import slug

    out = []
    for name, domain in (("glossary.json", "ai"), ("terms-computing.json", "software")):
        for e in json.loads((ROOT / "content" / name).read_text(encoding="utf-8")):
            extra = {k: e[k] for k in ("technical_en", "technical_ar", "formula", "code", "other_forms_ar") if e.get(k)}
            out.append(
                {
                    "id": slug(e["term_en"]), "origin": "darby", "domain": domain, **{f: e.get(f) or "" for f in TEXT_FIELDS},
                    "related": list(e.get("related") or []), "msa_source": "Darby (sources cited)", "reviewed": False,
                    "sources": json.dumps(e.get("sources") or [], ensure_ascii=False), "extra": json.dumps(extra, ensure_ascii=False),
                }
            )
    return out


def _fanar(generated: pd.DataFrame, taken: set[str]) -> list[dict]:
    out = []
    for r in generated.to_dict("records"):
        if r["id"] in taken:
            continue
        out.append(
            {
                "id": r["id"], "origin": "fanar_generated", "domain": "ai", **{f: r.get(f) or "" for f in TEXT_FIELDS},
                "related": [str(x) for x in r.get("related", [])], "msa_source": r["msa_source"], "reviewed": False,
                "sources": "[]", "extra": json.dumps({"at_work": int(r["at_work"]), "for_ai_use": int(r["for_ai_use"])}),
            }
        )
    return out


def build() -> Path:
    from huggingface_hub import hf_hub_download

    generated = pd.read_parquet(hf_hub_download(STAGING_REPO, "generated/data/cards_generated.parquet", repo_type="dataset"))
    ours = _ours()
    cards = ours + _fanar(generated, {c["id"] for c in ours})
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "data").mkdir(parents=True)
    pd.DataFrame(cards).to_parquet(OUT / "data" / "train.parquet", index=False)
    (OUT / "data" / "glossary.json").write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")
    n_fanar = sum(c["origin"] == "fanar_generated" for c in cards)
    (OUT / "README.md").write_text(CARD.format(n=len(cards), n_ours=len(ours), n_fanar=n_fanar), encoding="utf-8")
    return OUT


if __name__ == "__main__":
    out = build()
    print(out, len(json.loads((out / "data" / "glossary.json").read_text(encoding="utf-8"))))
    if "--push" in sys.argv:
        from huggingface_hub import HfApi

        HfApi().create_repo(GLOSSARY_REPO, repo_type="dataset", exist_ok=True)
        HfApi().upload_folder(repo_id=GLOSSARY_REPO, repo_type="dataset", folder_path=str(out), commit_message="Darby AI glossary: 140 cards")
        print("pushed", GLOSSARY_REPO)
