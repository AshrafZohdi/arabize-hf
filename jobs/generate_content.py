# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "vllm==0.33.0",
#   "huggingface_hub==2.4.0",
#   "pandas==3.1.1",
#   "pyarrow==26.0.1",
#   "pydantic==2.14.3",
# ]
# ///
"""Full Darby cards for about 100 office-relevant GIST terms, written by Fanar 2 (bf16, vLLM) in an HF Job.

1. Rate every candidate 1 to 5: would a non-technical office worker in Qatar meet this term at work?
   Terms that appear in our lessons are always kept.
2. Take the top N and write a full card around GIST's human Arabic (the MSA term is never invented):
   Gulf usage, definitions in English, MSA and Gulf, analogy, common mistake, examples, related terms.
3. Push the cards (all `reviewed: false`) and the ratings to the dataset repo from inside the Job.

    hf jobs uv run --flavor a100-large --timeout 30m --secrets HF_TOKEN jobs/generate_content.py \
        --staging nuvais/darby-term-bank-staging
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, Field, ValidationError

FANAR = "QCRI/Fanar-2-27B-Instruct"
FANAR_REVISION = "074005040e9c3511b1c43b4298bef09908285534"
SYSTEM = (
    "You write learning cards that teach Arabic-speaking professionals in Qatar the English vocabulary of AI at work. "
    "Be accurate and plain. Never invent facts, people or statistics."
)


class Rating(BaseModel):
    at_work: int = Field(ge=1, le=5, description="How often an office worker meets it")
    for_ai_use: int = Field(ge=1, le=5, description="How much it helps to know it when using AI tools at work")


class CardOut(BaseModel):
    term_gulf: str = Field(max_length=60, description="How Gulf colleagues say it in speech; may be the English word")
    def_en: str = Field(max_length=220)
    def_ar: str = Field(max_length=220, description="Simple Modern Standard Arabic")
    def_gulf: str = Field(max_length=220, description="Gulf Arabic dialect as spoken in Qatar")
    analogy_en: str = Field(max_length=200)
    analogy_ar: str = Field(max_length=200)
    mistake_en: str = Field(max_length=200)
    mistake_ar: str = Field(max_length=200)
    example_en: str = Field(max_length=200)
    example_ar: str = Field(max_length=200)
    example_gulf: str = Field(max_length=200)
    related: list[str] = Field(max_length=3)


def rating_prompt(term: str) -> str:
    return (
        f"Term: {term}\n"
        "Rate this English term for a non-technical office worker in Qatar (government, bank, school, company) who is learning to use AI tools. "
        "at_work: how often they meet it in work emails, reports, meetings or AI tools (1 = almost never, research only; 5 = very often). "
        "for_ai_use: how much knowing it helps them use AI tools well at work (1 = not at all; 5 = essential). "
        "Generic everyday words (state, key, normal) score low on for_ai_use. Reply with JSON only."
    )


def card_prompt(term: str, ar: str) -> str:
    return "\n".join(
        [
            f"English term: {term}",
            f"Standard Arabic term (human translation, use it exactly): {ar}",
            "Write a learning card. def_*: one or two short sentences. analogy: one sentence from everyday work or life in the Gulf. "
            "mistake: one common misunderstanding. example: one sentence from a Doha workplace that uses the term. "
            "Write the *_ar fields in simple Modern Standard Arabic and the *_en fields in plain English. "
            "Write def_gulf and example_gulf in Gulf Arabic as spoken in Qatar, not Modern Standard Arabic: use everyday Gulf words such as "
            "شنو، يعني، عشان، وايد، زين، يبي، مو، هالشي، اللي، الحين. Example of the tone: \"يعني الـ AI يألّف معلومة مو موجودة ويقولها بثقة.\" "
            "term_gulf is how Gulf colleagues actually say the term in speech (often the English word, for example برومبت). "
            "In Arabic text put the English term in brackets after the Arabic term the first time. "
            "The Arabic for prompt is أمر (plural أوامر). related: up to 3 related English terms. Reply with JSON only.",
        ]
    )


def parse(text: str, schema: type[BaseModel]) -> BaseModel | None:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S | re.I)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return schema.model_validate(json.loads(text[start : end + 1]))
    except (json.JSONDecodeError, ValidationError):
        return None


class Vllm:
    name = "vllm"

    def __init__(self) -> None:
        # No CUDA compiler in the uv image: no runtime kernel compilation (see jobs/stage3_translate.py).
        os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")
        os.environ.setdefault("VLLM_ATTENTION_BACKEND", "FLASH_ATTN")
        import vllm
        from vllm import LLM

        self.version = vllm.__version__
        self.llm = LLM(model=FANAR, revision=FANAR_REVISION, dtype="bfloat16", max_model_len=4096, gpu_memory_utilization=0.85, seed=0, enforce_eager=True)

    def run(self, prompts: list[str], schema: type[BaseModel], max_tokens: int, temperature: float = 0.0) -> list[BaseModel | None]:
        from vllm import SamplingParams
        from vllm.sampling_params import StructuredOutputsParams

        params = SamplingParams(temperature=temperature, max_tokens=max_tokens, structured_outputs=StructuredOutputsParams(json=schema.model_json_schema()))
        convs = [[{"role": "system", "content": SYSTEM}, {"role": "user", "content": p}] for p in prompts]
        outs = self.llm.chat(convs, params, chat_template_kwargs={"no_thinking": True}, use_tqdm=False)
        return [parse(o.outputs[0].text, schema) for o in outs]


class Mock:
    name = "mock"
    version = "mock"

    def run(self, prompts, schema, max_tokens, temperature=0.0):
        out = []
        for p in prompts:
            term = re.search(r"Term: (.+)|English term: (.+)", p)
            t = (term.group(1) or term.group(2)).strip() if term else "x"
            if schema is Rating:
                top = t in ("model card", "language model")
                out.append(Rating(at_work=5 if top else 3 if "network" in t else 1, for_ai_use=4 if top else 3 if "network" in t else 1))
            else:
                out.append(CardOut(term_gulf=t, def_en=f"{t} means", def_ar="تعريف", def_gulf="يعني", analogy_en="like", analogy_ar="مثل",
                                   mistake_en="m", mistake_ar="خطأ", example_en="e", example_ar="مثال", example_gulf="مثال", related=[]))
        return out


def candidates(bank: pd.DataFrame, lesson_text: str, vocab: set[str]) -> pd.DataFrame:
    """GIST terms of at most 3 words made only of everyday office or software words, without a Darby card yet."""
    gist = bank[bank.source_names.map(lambda s: list(s)[0] == "gist") & ~bank.is_acronym & ~bank.has_full_card]

    def ok(en: str) -> bool:
        ws = re.findall(r"[a-z]+", en.lower())
        return 1 <= len(ws) <= 3 and all(w in vocab for w in ws)

    c = gist[gist.en.map(ok)].copy()
    # Only multi-word terms count as "in the lessons": single words like state or key match ordinary prose.
    c["in_lessons"] = c.en.str.lower().map(lambda t: " " in t and re.search(rf"\b{re.escape(t)}\b", lesson_text) is not None)
    return c


def run(bank: pd.DataFrame, lesson_text: str, vocab: set[str], backend, n: int) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    t0 = time.time()
    cand = candidates(bank, lesson_text, vocab)
    ratings = backend.run([rating_prompt(t) for t in cand.en], Rating, 40)
    cand["at_work"] = [r.at_work if r else 0 for r in ratings]
    cand["for_ai_use"] = [r.for_ai_use if r else 0 for r in ratings]
    cand["score"] = cand.at_work + cand.for_ai_use
    # Ties: AI usefulness first, then shorter terms (easier to meet in office text). Never the alphabet.
    cand["n_words"] = cand.en.str.split().map(len)
    chosen = cand.sort_values(["in_lessons", "score", "for_ai_use", "n_words", "en"], ascending=[False, False, False, True, True]).head(n)
    outs = backend.run([card_prompt(t, a) for t, a in zip(chosen.en, chosen.ar_full.fillna(chosen.ar_display))], CardOut, 900, temperature=0.3)
    cards = []
    for (_, r), o in zip(chosen.iterrows(), outs):
        if o is None:
            continue
        cards.append(
            {
                "id": r["id"], "term_en": r["en"], "term_msa": r["ar_full"] or r["ar_display"], **o.model_dump(), "domain": "ai",
                "msa_source": "GIST human translation (Jerry999/multilingual-terminology)", "written_by": f"{FANAR} (bf16, vLLM)",
                "reviewed": False, "at_work": int(r["at_work"]), "for_ai_use": int(r["for_ai_use"]), "in_lessons": bool(r["in_lessons"]),
            }
        )
    stats = {"candidates": len(cand), "chosen": len(chosen), "cards": len(cards), "failed": len(chosen) - len(cards),
             "score_counts": cand.score.value_counts().sort_index().to_dict(), "seconds": round(time.time() - t0, 1)}
    return pd.DataFrame(cards), cand[["id", "en", "at_work", "for_ai_use", "score", "in_lessons"]].sort_values("score", ascending=False), stats


def main() -> None:
    from huggingface_hub import HfApi, hf_hub_download, snapshot_download

    ap = argparse.ArgumentParser()
    ap.add_argument("--staging", default="nuvais/darby-term-bank-staging")
    ap.add_argument("--out-repo", default="nuvais/darby-term-bank-staging", help="private: published with a card after a look")
    ap.add_argument("--space", default="FayezAlkh12/darby")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--backend", choices=["vllm", "mock"], default="vllm")
    ap.add_argument("--no-push", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    bank = pd.read_parquet(hf_hub_download(args.staging, "final/term_bank.parquet", repo_type="dataset"))
    vocab = set(json.loads(Path(hf_hub_download(args.staging, "final/card_vocab.json", repo_type="dataset")).read_text()))
    lessons = snapshot_download(args.space, repo_type="space", allow_patterns=["content/day-*.json"])
    lesson_text = " ".join(Path(p).read_text(encoding="utf-8") for p in sorted(Path(lessons, "content").glob("day-*.json"))).lower()
    backend = Vllm() if args.backend == "vllm" else Mock()
    load_s = round(time.time() - t0, 1)
    cards, ratings, stats = run(bank, lesson_text, vocab, backend, args.n)
    stats.update({"backend": backend.name, "backend_version": backend.version, "model": FANAR, "model_revision": FANAR_REVISION, "load_seconds": load_s, "total_seconds": round(time.time() - t0, 1)})
    print(json.dumps(stats, indent=1))
    out = Path("content_out")
    (out / "data").mkdir(parents=True, exist_ok=True)
    cards.to_parquet(out / "data" / "cards_generated.parquet", index=False)
    (out / "data" / "cards_generated.json").write_text(json.dumps(cards.to_dict("records"), ensure_ascii=False, indent=1), encoding="utf-8")
    ratings.to_csv(out / "ratings.csv", index=False)
    (out / "run.json").write_text(json.dumps(stats, indent=1))
    if not args.no_push:
        HfApi().upload_folder(repo_id=args.out_repo, repo_type="dataset", folder_path=str(out), path_in_repo="generated", commit_message="Fanar-written cards (not reviewed)")
        print("pushed", args.out_repo)


if __name__ == "__main__":
    main()
