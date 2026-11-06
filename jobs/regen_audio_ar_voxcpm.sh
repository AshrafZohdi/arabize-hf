#!/usr/bin/env bash
# Re-record the Arabic word of every Darbi glossary card with openbmb/VoxCPM2 (Apache 2.0), replacing the
# mms-tts-ara recordings (D25: Whisper large-v3 heard 0/12 test words right from MMS, 9/12 from VoxCPM2).
#   hf jobs run --flavor a10g-small --timeout 45m -s HF_TOKEN -v hf://buckets/FayezAlkh12/darby-media:/out \
#     ghcr.io/astral-sh/uv:python3.11-bookworm bash -c "$(cat jobs/regen_audio_ar_voxcpm.sh)"
# The MMS files are copied to audio/ar-mms-backup first. Each word gets up to 3 VoxCPM2 takes; Whisper large-v3 picks
# the take closest to the intended word, and a word keeps its MMS file when that one scored better.
set -euo pipefail
apt-get update -qq && apt-get install -y -qq ffmpeg libsndfile1 >/dev/null
if [ ! -d /out/audio/ar-mms-backup ]; then
  mkdir -p /out/audio/ar-mms-backup && cp /out/audio/ar/*.wav /out/audio/ar-mms-backup/ && cp /out/audio/manifest-ar.json /out/audio/ar-mms-backup/manifest-ar.json
fi
mkdir -p /tmp/w && cat > /tmp/w/regen_ar.py <<'PY'
import json, re, time, numpy as np, soundfile as sf, torch, torchaudio
from huggingface_hub import HfApi, hf_hub_download
from transformers import pipeline
from voxcpm import VoxCPM

t0 = time.time()
cards = json.load(open(hf_hub_download("nuvais/darby-ai-glossary-ar-en", "data/glossary.json", repo_type="dataset"), encoding="utf-8"))
rev = HfApi().model_info("openbmb/VoxCPM2").sha
tts = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3", dtype=torch.float16, device=0)

def arabic_only(t):  # the same text the MMS recordings said: no brackets, no Latin letters or digits
    t = re.sub(r"\([^)]*\)", " ", t)
    return " ".join(re.sub(r"[A-Za-z0-9:]+", " ", t).split())
def norm(s):
    s = re.sub(r"[ً-ٰٟـ]", "", s)
    s = s.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه"}))
    return re.sub(r"[^ء-ي]", "", s)
def cer(a, b):
    d = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev, d[0] = d[0], i
        for j, cb in enumerate(b, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (ca != cb))
    return d[len(b)] / max(1, len(b))
def heard(x, sr):
    x16 = torchaudio.functional.resample(torch.from_numpy(x), sr, 16000).numpy()
    return asr({"raw": x16, "sampling_rate": 16000}, generate_kwargs={"language": "arabic", "task": "transcribe"})["text"].strip()

files, scores, kept_mms, failed = {}, {}, [], []
for c in cards:
    i, text = c["id"], arabic_only(c["term_msa"])
    if not text:
        failed.append(i); continue
    old, old_sr = sf.read(f"/out/audio/ar-mms-backup/{i}.wav", dtype="float32")
    old_cer = cer(norm(heard(old, old_sr)), norm(text))
    best = None
    for take in range(3):
        wav = np.asarray(tts.generate(text=text, cfg_value=2.0, inference_timesteps=10), dtype=np.float32)
        score = cer(norm(heard(wav, tts.tts_model.sample_rate)), norm(text))
        if best is None or score < best[0]:
            best = (score, wav)
        if score == 0:
            break
    if best[0] > old_cer:
        kept_mms.append(i)
        files[f"ar/{i}"] = f"ar/{i}.wav"
        scores[i] = {"voice": "mms", "cer": round(old_cer, 3)}
        continue
    out = torchaudio.functional.resample(torch.from_numpy(best[1]), tts.tts_model.sample_rate, 24000).numpy()
    sf.write(f"/out/audio/ar/{i}.wav", out, 24000, subtype="PCM_16")
    files[f"ar/{i}"] = f"ar/{i}.wav"
    scores[i] = {"voice": "voxcpm2", "cer": round(best[0], 3), "mms_cer": round(old_cer, 3)}
    print(i, text, "cer", round(best[0], 3), "was", round(old_cer, 3), flush=True)

manifest = {"lang": "ar", "model": "openbmb/VoxCPM2", "revision": rev, "licence": "Apache 2.0", "fallback_model": "Xenova/mms-tts-ara (CC BY-NC 4.0) for kept words",
            "files": files, "kept_mms": kept_mms, "failed": failed, "scores": scores, "seconds": round(time.time() - t0, 1)}
json.dump(manifest, open("/out/audio/manifest-ar.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
v = [s["cer"] for s in scores.values() if s["voice"] == "voxcpm2"]; m = [s["mms_cer"] for s in scores.values() if s["voice"] == "voxcpm2"]
print(json.dumps({"written": len(files), "voxcpm2": len(v), "kept_mms": len(kept_mms), "failed": failed,
                  "mean_cer_voxcpm2": round(sum(v) / max(1, len(v)), 3), "mean_cer_mms_same_words": round(sum(m) / max(1, len(m)), 3),
                  "exact_voxcpm2": sum(x == 0 for x in v), "exact_mms_same_words": sum(x == 0 for x in m)}, ensure_ascii=False), flush=True)
PY
cd /tmp/w && uv run -q --python 3.11 --with voxcpm==2.0.3 --with soundfile --with accelerate python regen_ar.py
