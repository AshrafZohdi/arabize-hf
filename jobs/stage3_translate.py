# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "vllm==0.33.0",
#   "sentence-transformers==6.2.0",
#   "huggingface_hub==2.4.0",
#   "pandas==3.1.1",
#   "pyarrow==26.0.1",
#   "pydantic==2.14.3",
# ]
# ///
"""Stage 3 of docs/DATA_PIPELINE.md: complete the translations, as an HF Job.

For every queued row of the clean term bank:
  1. expand acronyms to their full English form (deterministic candidates first, then Fanar);
  2. translate the full meaning into Arabic when the row has no Arabic meaning yet (never overwrites a human
     translation);
  3. back-translate Fanar's Arabic to English and score it against the English with multilingual-e5-small;
  4. flag rows for human review (several expansions, low similarity, rejected output).
Results and the review queue are pushed to the dataset repo from inside the Job.

    hf jobs uv run --flavor a100-large --timeout 45m --secrets HF_TOKEN jobs/stage3_translate.py \
        --repo nuvais/darby-term-bank --backend vllm

Local checks: --backend mock (no model) or --backend endpoint (our llama.cpp endpoint, a few rows).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, Field, ValidationError

FANAR = "QCRI/Fanar-2-27B-Instruct"
FANAR_REVISION = "074005040e9c3511b1c43b4298bef09908285534"
E5 = "intfloat/multilingual-e5-small"
SIMILARITY_THRESHOLD = 0.85
DOMAIN_TEXT = {"ai": "artificial intelligence and machine learning research", "software": "software, IT and Microsoft products"}


# --- output schemas -------------------------------------------------------------------------


class Expansion(BaseModel):
    is_name: bool = Field(description="True when the term is the name of a product, model or dataset rather than a short form")
    expansions: list[str] = Field(max_length=3, description="Plausible full English forms in this domain, most likely first")
    certain: bool = Field(description="True only when the first expansion is clearly the meaning in this domain")


class Translation(BaseModel):
    ar_full: str = Field(min_length=2, max_length=80, description="Arabic translation of the full meaning, at most 6 words")


class BackTranslation(BaseModel):
    en: str = Field(min_length=1, max_length=200)


# --- prompts ---------------------------------------------------------------------------------


def expansion_prompt(term: str, domain: str, context: list[str], candidates: list[str]) -> str:
    lines = [
        f"Term: {term}",
        f"Domain: {DOMAIN_TEXT.get(domain, domain)}",
        f"Other terms from the same glossary: {', '.join(context) or 'none'}",
    ]
    if candidates:
        lines.append(f"Long forms found in the glossary that may match: {', '.join(candidates)}")
    lines += [
        "Give the full English form of this term as used in this domain. If it is the name of a product, model or dataset, set is_name to true "
        "and describe it in a short English phrase instead (for example 'BERT-based French language model'). "
        "List every plausible full form if there is more than one, and set certain to false in that case. Never invent: if you do not know, "
        "set certain to false.",
        "Reply with JSON only.",
    ]
    return "\n".join(lines)


def translation_prompt(term: str, expanded: str, domain: str, examples: list[tuple[str, str]]) -> str:
    ex = "\n".join(f"- {e} = {a}" for e, a in examples)
    return "\n".join(
        [
            f"Translate this technical term into Arabic. Term: {term}. Full meaning: {expanded}. Domain: {DOMAIN_TEXT.get(domain, domain)}.",
            "Use established Arabic technical terminology, in the style of these glossary entries:",
            ex,
            "Translate the meaning, not the letters. Transliterate only established loanwords, and then add the meaning. "
            "Do not include the English in ar_full. Keep it short: a term of at most 6 words, not a sentence. "
            "For the name of a product, model or dataset, give a short Arabic description of what it is. Reply with JSON only.",
        ]
    )


def back_translation_prompt(ar: str) -> str:
    return f"Translate this Arabic technical term into English. Give only the English term.\nArabic: {ar}\nReply with JSON only."


SYSTEM = "You are a careful terminologist who translates English technical terms for Arabic-speaking professionals in Qatar."


# --- backends ---------------------------------------------------------------------------------


def strip_think(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S | re.I)
    if "</think>" in text.lower():
        text = text[text.lower().rindex("</think>") + 8 :]
    return text.strip()


def parse(text: str, schema: type[BaseModel]) -> BaseModel | None:
    text = strip_think(text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return schema.model_validate(json.loads(text[start : end + 1]))
    except (json.JSONDecodeError, ValidationError):
        return None


class Backend:
    name = "base"

    def run(self, prompts: list[str], schema: type[BaseModel], max_tokens: int) -> list[BaseModel | None]:
        raise NotImplementedError


class VllmBackend(Backend):
    name = "vllm"

    def __init__(self) -> None:
        # The uv Job image has no CUDA compiler, so nothing may be compiled at run time: PyTorch sampling instead
        # of FlashInfer's JIT kernels, the prebuilt FlashAttention backend, and eager mode (no torch.compile).
        # First run failed with "Could not find nvcc" (job 6aecdfb5c78863f9c6338f17).
        os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")
        os.environ.setdefault("VLLM_ATTENTION_BACKEND", "FLASH_ATTN")
        import vllm
        from vllm import LLM

        self.version = vllm.__version__
        self.llm = LLM(
            model=FANAR, revision=FANAR_REVISION, dtype="bfloat16", max_model_len=4096, gpu_memory_utilization=0.85, seed=0, enforce_eager=True
        )

    def _params(self, schema: type[BaseModel], max_tokens: int):
        from vllm import SamplingParams

        try:  # vLLM 0.11+
            from vllm.sampling_params import StructuredOutputsParams

            return SamplingParams(temperature=0, max_tokens=max_tokens, structured_outputs=StructuredOutputsParams(json=schema.model_json_schema()))
        except ImportError:
            from vllm.sampling_params import GuidedDecodingParams

            return SamplingParams(temperature=0, max_tokens=max_tokens, guided_decoding=GuidedDecodingParams(json=schema.model_json_schema()))

    def run(self, prompts, schema, max_tokens):
        convs = [[{"role": "system", "content": SYSTEM}, {"role": "user", "content": p}] for p in prompts]
        outs = self.llm.chat(convs, self._params(schema, max_tokens), chat_template_kwargs={"no_thinking": True}, use_tqdm=False)
        return [parse(o.outputs[0].text, schema) for o in outs]


class EndpointBackend(Backend):
    """Our llama.cpp endpoint (Q5_K_M), for a cheap look at the prompts on a few rows."""

    name = "endpoint"

    def __init__(self, url: str) -> None:
        from huggingface_hub import InferenceClient

        self.version = "llama.cpp endpoint"
        self.client = InferenceClient(base_url=url, timeout=120)

    def run(self, prompts, schema, max_tokens):
        out = []
        for p in prompts:
            r = self.client.chat_completion(
                messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": p}],
                max_tokens=max_tokens,
                temperature=0,
                response_format={"type": "json_object", "schema": schema.model_json_schema()},
                extra_body={"chat_template_kwargs": {"no_thinking": True}},
            )
            out.append(parse(r.choices[0].message.content or "", schema))
        return out


class MockBackend(Backend):
    """Deterministic answers for tests: no model."""

    name = "mock"
    version = "mock"

    def run(self, prompts, schema, max_tokens):
        out = []
        for p in prompts:
            term = re.search(r"Term: ([^\n.]+)", p)
            t = term.group(1) if term else "x"
            if schema is Expansion:
                cand = re.search(r"may match: ([^,\n]+)", p)
                out.append(Expansion(is_name=False, expansions=[cand.group(1) if cand else f"{t} expanded"], certain=not t.startswith("GCC")))
            elif schema is Translation:
                meaning = re.search(r"Full meaning: (.+?)\. Domain", p)
                out.append(None if t.startswith("BAD") else Translation(ar_full=f"ترجمة {meaning.group(1) if meaning else t}"))
            else:
                # Fanar's own Arabic comes back as its meaning; human Arabic comes back as something else.
                ar = re.search(r"Arabic: (.+)", p)
                text = ar.group(1) if ar else "x"
                out.append(BackTranslation(en=text.replace("ترجمة ", "") if text.startswith("ترجمة ") else "human arabic meaning"))
        return out


# --- deterministic helpers -----------------------------------------------------------------


def initials(phrase: str) -> str:
    return "".join(w[0] for w in re.findall(r"[A-Za-z][A-Za-z]*", phrase)).upper()


def candidates_from_bank(acronym: str, long_terms: dict[str, list[str]], curated: dict[str, str], domain: str) -> list[str]:
    """Long forms in the same domain whose initials spell the acronym (API -> application programming interface)."""
    core = re.sub(r"s$", "", re.sub(r"[^A-Za-z]", "", acronym)).upper()
    found = [curated[acronym]] if acronym in curated else []
    for t in long_terms.get(f"{domain}:{core}", []):
        if t not in found:
            found.append(t)
    return found[:3]


def key_of(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", s.lower().replace("-", " ")).strip()


def is_latin_only(s: str) -> bool:
    return bool(re.search(r"[A-Za-z]", s)) and not re.search(r"[؀-ۿ]", s)


def needs_arabic(ar_display: str, en: str) -> bool:
    return is_latin_only(ar_display) or ar_display.strip().lower() == en.strip().lower()


@dataclass
class Row:
    id: str
    en: str
    domain: str
    ar_display: str
    is_acronym: bool
    reason: str


def run_stage3(bank: pd.DataFrame, backend: Backend, embed, curated: dict[str, str], limit: int | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    t0 = time.time()
    queue = bank[bank.stage3_reason.notna()].copy()
    if limit:
        queue = queue.head(limit)
    long_terms: dict[str, list[str]] = {}
    for en, dom in zip(bank[~bank.is_acronym].en, bank[~bank.is_acronym].domain):
        if 2 <= len(en.split()) <= 6:
            long_terms.setdefault(f"{dom}:{initials(en)}", []).append(en)
    # Corroboration only counts within the same domain: CLS is "Common Language Specification" in the software
    # glossary, but in an AI research list it is the classification token.
    bank_keys = {(d, key_of(e)) for d, e in zip(bank.domain, bank.en)}
    word_index: dict[str, list[str]] = {}
    for e in bank.en:
        for w in set(re.findall(r"[A-Za-z0-9]+", e.lower())):
            word_index.setdefault(w, []).append(e)
    examples = list(bank[(bank.ar_origin == "darby_editor") | (bank.ar_origin == "human_gist")].head(12)[["en", "ar_display"]].itertuples(index=False, name=None))

    rows = [Row(r.id, r.en, r.domain, r.ar_display, bool(r.is_acronym), r.stage3_reason) for r in queue.itertuples()]
    res: dict[str, dict[str, Any]] = {r.id: {"id": r.id, "en": r.en, "issues": []} for r in rows}

    # 1. expansions (acronyms) and short descriptions (untranslated names), with context from the bank
    acr = [r for r in rows if r.is_acronym]
    cands = {r.id: candidates_from_bank(r.en, long_terms, curated, r.domain) for r in rows}
    ctx = {r.id: [t for t in word_index.get(r.en.lower(), []) if t != r.en][:6] for r in rows}
    outs = backend.run([expansion_prompt(r.en, r.domain, ctx[r.id], cands[r.id]) for r in rows], Expansion, 200)
    for r, o in zip(rows, outs):
        d = res[r.id]
        if o is None or not o.expansions:
            d["issues"].append("expansion: no valid output")
            continue
        d["is_name"] = o.is_name
        d["expansion_options"] = o.expansions
        if not r.is_acronym:
            d["en_description"] = o.expansions[0]
            # A description of a name (model, dataset, product) cannot be checked automatically.
            d["issues"].append("description of a name written by Fanar: check")
            continue
        d["en_expanded"] = o.expansions[0]
        if not o.certain or len(o.expansions) > 1:
            d["issues"].append("expansion: several or uncertain options")
        if o.expansions[0].strip().lower() == r.en.lower():
            d["issues"].append("expansion: same as the acronym")
        # Independent check 1: the expansion is itself a term somewhere in the bank, or came from it.
        d["corroborated"] = (r.domain, key_of(o.expansions[0])) in bank_keys or o.expansions[0] in cands[r.id]

    # 2. translations, only where the row has no Arabic meaning yet
    tr = [r for r in rows if needs_arabic(r.ar_display, r.en)]
    meaning = {r.id: res[r.id].get("en_expanded") or res[r.id].get("en_description") or r.en for r in rows}
    outs = backend.run([translation_prompt(r.en, meaning[r.id], r.domain, examples) for r in tr], Translation, 120)
    for r, o in zip(tr, outs):
        d = res[r.id]
        if o is None:
            d["issues"].append("translation: no valid output")
            continue
        ar = o.ar_full.strip()
        if not ar or is_latin_only(ar) or ar.lower() == r.en.lower():
            d["issues"].append("translation: rejected (empty, Latin only or same as input)")
            continue
        d["ar_full"] = ar
        d["ar_origin"] = "fanar_generated"

    # 3. back-translation check on everything Fanar translated
    done = [r for r in tr if "ar_full" in res[r.id]]
    outs = backend.run([back_translation_prompt(res[r.id]["ar_full"]) for r in done], BackTranslation, 60)
    pairs = []
    for r, o in zip(done, outs):
        if o is None:
            res[r.id]["issues"].append("back-translation: no valid output")
            continue
        res[r.id]["back_translation"] = o.en
        pairs.append((r.id, meaning[r.id], o.en))
    if pairs:
        sims = embed([p[1] for p in pairs], [p[2] for p in pairs])
        for (rid, _, _), s in zip(pairs, sims):
            res[rid]["similarity"] = round(float(s), 4)
            if s < SIMILARITY_THRESHOLD:
                res[rid]["issues"].append(f"back-translation similarity {s:.2f} below {SIMILARITY_THRESHOLD}")

    # 4. Independent check 2: where a human Arabic meaning exists, does it agree with the expansion?
    human = [r for r in acr if not needs_arabic(r.ar_display, r.en) and res[r.id].get("en_expanded")]
    plain = {r.id: re.sub(r"\s*\([^)]*\)", "", r.ar_display).strip() or r.ar_display for r in human}
    outs = backend.run([back_translation_prompt(plain[r.id]) for r in human], BackTranslation, 60)
    hpairs = [(r.id, res[r.id]["en_expanded"], o.en) for r, o in zip(human, outs) if o is not None]
    if hpairs:
        sims = embed([p[1] for p in hpairs], [p[2] for p in hpairs])
        for (rid, _, back), s in zip(hpairs, sims):
            res[rid]["human_ar_back_translation"] = back
            res[rid]["human_ar_agreement"] = round(float(s), 4)
            if s >= SIMILARITY_THRESHOLD:
                res[rid]["corroborated"] = True
            else:
                res[rid]["issues"].append(f"expansion disagrees with the human Arabic ({back}, {s:.2f})")
    for r in acr:
        d = res[r.id]
        if d.get("en_expanded") and not d.get("corroborated"):
            d["issues"].append("expansion unverified: not in any source and no human Arabic to compare")

    out = pd.DataFrame(list(res.values()))
    out["needs_review"] = out.issues.map(bool)
    sims = out.get("similarity", pd.Series(dtype=float)).dropna()
    stats = {
        "queued": len(rows),
        "acronyms": len(acr),
        "translated": len(done),
        "needs_review": int(out.needs_review.sum()),
        "similarity": {"count": int(len(sims)), **({k: round(float(v), 4) for k, v in sims.describe()[["mean", "min", "25%", "50%", "75%"]].items()} if len(sims) else {})},
        "seconds": round(time.time() - t0, 1),
    }
    return out, stats


def e5_embedder(device: str | None = None):
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(E5, device=device)

    def sim(a: list[str], b: list[str]) -> list[float]:
        ea = model.encode([f"query: {x}" for x in a], normalize_embeddings=True)
        eb = model.encode([f"query: {x}" for x in b], normalize_embeddings=True)
        return [float((x * y).sum()) for x, y in zip(ea, eb)]

    return sim


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="dataset repo holding interim/term_bank_clean.parquet")
    ap.add_argument("--backend", choices=["vllm", "endpoint", "mock"], default="vllm")
    ap.add_argument("--endpoint-url")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ids", help="comma-separated row ids to run (preview)")
    ap.add_argument("--out", default="stage3", help="folder in the repo for the results")
    ap.add_argument("--no-push", action="store_true")
    args = ap.parse_args()

    from huggingface_hub import HfApi, hf_hub_download

    t0 = time.time()
    bank = pd.read_parquet(hf_hub_download(args.repo, "interim/term_bank_clean.parquet", repo_type="dataset"))
    curated_path = hf_hub_download(args.repo, "curated/expansions.csv", repo_type="dataset")
    curated = dict(pd.read_csv(curated_path, dtype=str).fillna("").values.tolist())
    backend: Backend = VllmBackend() if args.backend == "vllm" else EndpointBackend(args.endpoint_url) if args.backend == "endpoint" else MockBackend()
    load_s = round(time.time() - t0, 1)
    embed = e5_embedder()
    if args.ids:
        keep = set(args.ids.split(","))
        bank = bank.assign(stage3_reason=bank.stage3_reason.where(bank.id.isin(keep)))
    out, stats = run_stage3(bank, backend, embed, curated, args.limit)
    stats.update({"backend": backend.name, "backend_version": getattr(backend, "version", None), "model": FANAR, "model_revision": FANAR_REVISION, "embedder": E5, "load_seconds": load_s, "total_seconds": round(time.time() - t0, 1)})
    print(json.dumps(stats, indent=1))

    folder = Path("stage3_out")
    folder.mkdir(exist_ok=True)
    out.to_parquet(folder / "results.parquet", index=False)
    review = out[out.needs_review].merge(bank[["id", "ar_display", "domain"]], on="id", how="left")
    review.assign(issues=review.issues.map("; ".join), expansion_options=review.get("expansion_options", pd.Series(dtype=object)).map(lambda v: " | ".join(v) if isinstance(v, list) else ""))[
        [c for c in ["id", "en", "domain", "ar_display", "en_expanded", "en_description", "expansion_options", "ar_full", "back_translation", "similarity", "human_ar_back_translation", "human_ar_agreement", "issues"] if c in review.columns]
    ].to_csv(folder / "needs_review.csv", index=False)
    (folder / "run.json").write_text(json.dumps(stats, indent=1))
    if not args.no_push:
        HfApi().upload_folder(repo_id=args.repo, repo_type="dataset", folder_path=str(folder), path_in_repo=args.out, commit_message=f"stage 3 results ({backend.name})")
        print(f"pushed to {args.repo}/{args.out}")


if __name__ == "__main__":
    main()
