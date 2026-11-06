# /// script
# requires-python = ">=3.11"
# dependencies = ["onnxruntime==1.31.1", "numpy==2.4.6", "huggingface_hub==2.4.0"]
# ///
"""Arabic audio for every Darby glossary card, written straight into the mounted Storage Bucket. CPU Job:

    hf jobs uv run --flavor cpu-upgrade --timeout 20m -v hf://spaces/FayezAlkh12/darby:/code \
        -v hf://buckets/FayezAlkh12/darby-media:/out jobs/pregen_audio_ar.py

Uses server/voice/mms.py from the Space (the same code the app runs), so recordings and live speech match.
"""

import json
import sys
import time
from pathlib import Path

from huggingface_hub import hf_hub_download

sys.path.insert(0, "/code")
from server.voice.base import to_wav  # noqa: E402
from server.voice.mms import LICENCE, REPO, REVISION, MmsArabic  # noqa: E402

OUT = Path("/out/audio")
t0 = time.time()
cards = json.loads(Path(hf_hub_download("nuvais/darby-ai-glossary-ar-en", "data/glossary.json", repo_type="dataset")).read_text(encoding="utf-8"))
tts = MmsArabic(threads=8)
(OUT / "ar").mkdir(parents=True, exist_ok=True)
files, failed = {}, []
for c in cards:
    try:
        (OUT / "ar" / f"{c['id']}.wav").write_bytes(to_wav(*tts.synthesize(c["term_msa"])))
        files[f"ar/{c['id']}"] = f"ar/{c['id']}.wav"
    except Exception as e:
        failed.append((c["id"], type(e).__name__))
manifest = {"lang": "ar", "model": REPO, "revision": REVISION, "licence": LICENCE, "files": files, "failed": failed, "seconds": round(time.time() - t0, 1)}
(OUT / "manifest-ar.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in manifest.items() if k != "files"} | {"written": len(files)}, ensure_ascii=False))
