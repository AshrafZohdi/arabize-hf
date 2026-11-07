"""Publish Darby's 7 lessons as `nuvais/darby-lessons`: python -m data.lessons [--push]

The Space loads lessons from this dataset at startup and falls back to content/ when the Hub is unreachable.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LESSONS_REPO = "nuvais/darby-lessons"
OUT = ROOT / "data" / "lessons_public"

CARD = """---
license: apache-2.0
language:
- ar
- en
pretty_name: Darby lessons (AI at work, Arabic, Gulf Arabic, English)
size_categories:
- n<1K
tags:
- arabic
- gulf-arabic
- education
- qatar
- ai-literacy
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train.parquet
---

# Darby lessons: AI at work, in Arabic, Gulf Arabic and English

<div dir="rtl" lang="ar">

سبعة دروس قصيرة (حوالي 10 دقائق لكل درس) تعلّم خريجي المدارس المستقلة في قطر استخدام الذكاء الاصطناعي في الشغل ومصطلحاته الإنجليزية، بثلاث صيغ: إنجليزي، وعربي مبسط، ولهجة خليجية. كل درس: مدخل، فكرة، مثال، مصطلحات، تمارين، مختبر أوامر، وخلاصة.

**تنبيه:** الدروس كُتبت بمساعدة الذكاء الاصطناعي في تطبيق «Arabize» السابق، ولم تمرّ بعد بالمراجعة التقنية واللغوية.

</div>

## What this is

{n} lessons from Darbi (دربي), the app that teaches graduates of Qatar's Mostaqila schools the vocabulary of AI at work. Built at the Qai x Hugging Face Hackathon 01 in Doha (November 2026). Every text field comes in `en`, `ar` (simple Modern Standard Arabic) and `gulf` (Gulf Arabic; falls back to `ar` when missing).

**Status: AI-drafted, not yet reviewed.** The lessons were drafted with AI for the earlier Arabize app and have not had the technical and Arabic language review that app required before publishing a lesson.

## Lessons

| # | Slug | English title | Gulf title |
|---|---|---|---|
{rows}

## Structure

`data/train.parquet` has one row per lesson: `slug`, `order`, `est_minutes`, `title_en`, `title_ar`, `title_gulf`, `block_types`, `blocks` (the full lesson as JSON). The original files are in `lessons/`.

Block types: `hook`, `concept`, `example`, `key_terms`, `exercise` (multiple choice, match, fill the gap), `prompt_lab` (a work task for writing a prompt, scored on goal, context, format and constraints), `recap`. Glossary terms in lesson text are marked `[[Prompt]]` or `[[Prompt|الأمر]]`.

## Licence

Apache 2.0.
"""


def build() -> Path:
    import pandas as pd

    files = sorted((ROOT / "content").glob("day-*.json"), key=lambda p: int(p.stem.split("-")[1]))
    lessons = [json.loads(p.read_text(encoding="utf-8")) for p in files]
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "data").mkdir(parents=True)
    (OUT / "lessons").mkdir()
    for p in files:
        shutil.copy(p, OUT / "lessons" / p.name)
    df = pd.DataFrame(
        {
            "slug": [d["slug"] for d in lessons],
            "order": [d["order"] for d in lessons],
            "est_minutes": [d["est_minutes"] for d in lessons],
            "title_en": [d["title"]["en"] for d in lessons],
            "title_ar": [d["title"]["ar"] for d in lessons],
            "title_gulf": [d["title"].get("gulf") or d["title"]["ar"] for d in lessons],
            "block_types": [[b["type"] for b in d["blocks"]] for d in lessons],
            "blocks": [json.dumps(d["blocks"], ensure_ascii=False) for d in lessons],
        }
    )
    df.to_parquet(OUT / "data" / "train.parquet", index=False)
    rows = "\n".join(f"| {d['order']} | {d['slug']} | {d['title']['en']} | {d['title'].get('gulf') or d['title']['ar']} |" for d in lessons)
    (OUT / "README.md").write_text(CARD.format(n=len(lessons), rows=rows), encoding="utf-8")
    return OUT


if __name__ == "__main__":
    out = build()
    print(out)
    if "--push" in sys.argv:
        from huggingface_hub import HfApi

        HfApi().create_repo(LESSONS_REPO, repo_type="dataset", exist_ok=True)
        HfApi().upload_folder(repo_id=LESSONS_REPO, repo_type="dataset", folder_path=str(out), commit_message="Darby lessons")
        print("pushed", LESSONS_REPO)
