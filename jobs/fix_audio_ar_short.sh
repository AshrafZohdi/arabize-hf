#!/usr/bin/env bash
# Retry the weakest Arabic card words with vowel-marked spellings (VoxCPM2 reads tashkeel; mms-tts-ara could not).
# A file is replaced only when Whisper large-v3 hears the new take closer to the card word than the current one.
#   hf jobs run --flavor a10g-small --timeout 15m -s HF_TOKEN -v hf://buckets/FayezAlkh12/darby-media:/out \
#     ghcr.io/astral-sh/uv:python3.11-bookworm bash -c "$(cat jobs/fix_audio_ar_short.sh)"
set -euo pipefail
apt-get update -qq && apt-get install -y -qq ffmpeg libsndfile1 >/dev/null
mkdir -p /tmp/w && cat > /tmp/w/fix_ar.py <<'PY'
import json, re, numpy as np, soundfile as sf, torch, torchaudio
from transformers import pipeline
from voxcpm import VoxCPM
VARIANTS = {
    "prompt": ("أمر", ["أَمْر", "أَمْرٌ", "أَمر"]),
    "bit": ("بت", ["بِت", "بِتّ"]),
    "output": ("الناتج", ["النَّاتِج", "النّاتِج"]),
    "chatbot": ("بوت محادثة", ["بوت مُحادَثة", "بُوت مُحَادَثَة"]),
    "image-recognition": ("التعرف على الصور", ["التَّعَرُّف على الصُّوَر"]),
    "knowledge-base": ("قاعدة المعرفة", ["قاعِدة المَعرِفة", "قَاعِدَةُ المَعْرِفَة"]),
}
tts = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3", dtype=torch.float16, device=0)
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
def hear(x, sr):
    x16 = torchaudio.functional.resample(torch.from_numpy(np.asarray(x, dtype=np.float32)), sr, 16000).numpy()
    return asr({"raw": x16, "sampling_rate": 16000}, generate_kwargs={"language": "arabic", "task": "transcribe"})["text"].strip()
manifest = json.load(open("/out/audio/manifest-ar.json", encoding="utf-8"))
for i, (word, spellings) in VARIANTS.items():
    cur, sr = sf.read(f"/out/audio/ar/{i}.wav", dtype="float32")
    cur_heard = hear(cur, sr); best = (cer(norm(cur_heard), norm(word)), None, None, cur_heard)
    for sp in spellings:
        for _ in range(3):
            wav = tts.generate(text=sp, cfg_value=2.0, inference_timesteps=10)
            h = hear(wav, tts.tts_model.sample_rate); s = cer(norm(h), norm(word))
            if s < best[0]:
                best = (s, wav, sp, h)
            if s == 0:
                break
        if best[0] == 0:
            break
    if best[1] is not None:
        out = torchaudio.functional.resample(torch.from_numpy(np.asarray(best[1], dtype=np.float32)), tts.tts_model.sample_rate, 24000).numpy()
        sf.write(f"/out/audio/ar/{i}.wav", out, 24000, subtype="PCM_16")
        manifest["scores"][i] = {"voice": "voxcpm2", "cer": round(best[0], 3), "spelling": best[2]}
        if i in manifest["kept_mms"]:
            manifest["kept_mms"].remove(i)
    print(i, "| now", round(best[0], 3), "| spelling", best[2] or "(unchanged)", "| heard", best[3], flush=True)
json.dump(manifest, open("/out/audio/manifest-ar.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
PY
cd /tmp/w && uv run -q --python 3.11 --with voxcpm==2.0.3 --with soundfile --with accelerate python fix_ar.py
