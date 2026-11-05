# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "onnxruntime==1.31.1",
#   "tokenizers==0.23.3",
#   "numpy==2.4.6",
#   "huggingface_hub==2.4.0",
#   "pandas==3.1.1",
#   "pyarrow==26.0.1",
# ]
# ///
"""Search vectors for every term in the bank, with multilingual-e5-small (ONNX, CPU). Runs as an HF Job:

    hf jobs uv run --flavor cpu-upgrade --timeout 20m --secrets HF_TOKEN jobs/embed_bank.py --repo nuvais/darby-term-bank-staging

The embedding code is `server/embed.py`, fetched from the Space repo so the Space and this Job use the same code.
Each term is embedded as "English; Arabic; full form", so a search in either language finds it.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd
from huggingface_hub import HfApi, hf_hub_download, snapshot_download


def term_text(en: str, ar: str, expanded: str | None) -> str:
    parts = [en, ar] + ([expanded] if expanded and expanded.lower() != en.lower() else [])
    return "; ".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--space", default="FayezAlkh12/darby")
    ap.add_argument("--no-push", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    code = snapshot_download(args.space, repo_type="space", allow_patterns=["server/__init__.py", "server/embed.py"])
    sys.path.insert(0, code)
    from server.embed import E5, E5_REPO, E5_REVISION

    bank = pd.read_parquet(hf_hub_download(args.repo, "interim/term_bank_clean.parquet", repo_type="dataset"))
    try:  # use the stage 3 expansions when they exist
        res = pd.read_parquet(hf_hub_download(args.repo, "stage3/results.parquet", repo_type="dataset")).set_index("id")
        expanded = {i: e for i, e in res.get("en_expanded", pd.Series(dtype=str)).dropna().items()}
    except Exception:
        expanded = {}
    texts = [term_text(en, ar, expanded.get(i)) for i, en, ar in zip(bank.id, bank.en, bank.ar_display)]
    e5 = E5(threads=8)
    vecs = e5.encode(texts, batch_size=128)
    out = pd.DataFrame({"en_key": bank.en_key, "vector": list(vecs.astype("float32"))})
    Path("embed_out").mkdir(exist_ok=True)
    out.to_parquet("embed_out/e5_small.parquet", index=False)
    stats = {"terms": len(out), "dim": int(vecs.shape[1]), "model": E5_REPO, "revision": E5_REVISION, "seconds": round(time.time() - t0, 1), "with_expansion": len(expanded)}
    Path("embed_out/run.json").write_text(json.dumps(stats, indent=1))
    print(json.dumps(stats, indent=1))
    if not args.no_push:
        HfApi().upload_folder(repo_id=args.repo, repo_type="dataset", folder_path="embed_out", path_in_repo="embeddings", commit_message="e5-small search vectors")
        print("pushed")


if __name__ == "__main__":
    main()
