#!/usr/bin/env bash
# Arabic voice comparison (GPU Job, A10G, 30 min): the same 12 Darbi card terms spoken by Chatterbox Multilingual (MIT)
# and VoxCPM2 (Apache 2.0), next to our current mms-tts-ara recordings. Whisper large-v3 transcribes every clip and
# the character error rate against the intended term is the score. Audio and scores go to the bucket at /out/audio-test.
#   hf jobs run --flavor a10g-small --timeout 30m -s HF_TOKEN -v hf://buckets/FayezAlkh12/darby-media:/out \
#     ghcr.io/astral-sh/uv:python3.11-bookworm bash -c "$(cat jobs/tts_bakeoff.sh)"
set -euo pipefail
# Script files must not share a name with the package they import (chatterbox.py shadowed chatterbox).
export TERMS='{"ai":"الذكاء الاصطناعي","large-language-model":"نموذج لغوي كبير","prompt":"أمر","hallucination":"الهلوسة","context":"السياق","output-format":"صيغة المخرجات","iteration":"تكرار التحسين","fact-check":"التحقق من المعلومات","personal-data":"البيانات الشخصية","confidentiality":"السرية","bias":"التحيز","chaining":"تسلسل الأوامر"}'
mkdir -p /tmp/w /out/audio-test
apt-get update -qq && apt-get install -y -qq git ffmpeg libsndfile1 >/dev/null

cat > /tmp/w/gen_chatterbox.py <<'PY'
import json, os, soundfile as sf
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
try:
    m = ChatterboxMultilingualTTS.from_pretrained(device="cuda", t3_model="v3")
except TypeError:
    m = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
os.makedirs("/out/audio-test/chatterbox", exist_ok=True)
for i, t in json.loads(os.environ["TERMS"]).items():
    wav = m.generate(t, language_id="ar")
    sf.write(f"/out/audio-test/chatterbox/{i}.wav", wav.squeeze().cpu().numpy(), m.sr)
    print("chatterbox", i, flush=True)
PY

cat > /tmp/w/gen_voxcpm.py <<'PY'
import json, os, soundfile as sf
from voxcpm import VoxCPM
m = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)
os.makedirs("/out/audio-test/voxcpm", exist_ok=True)
for i, t in json.loads(os.environ["TERMS"]).items():
    wav = m.generate(text=t, cfg_value=2.0, inference_timesteps=10)
    sf.write(f"/out/audio-test/voxcpm/{i}.wav", wav, m.tts_model.sample_rate)
    print("voxcpm", i, flush=True)
PY

cat > /tmp/w/score.py <<'PY'
import json, os, re, numpy as np, soundfile as sf, torch
from transformers import pipeline
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3", torch_dtype=torch.float16, device=0)
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
terms = json.loads(os.environ["TERMS"])
out = {}
for voice, folder in (("mms (current)", "/out/audio/ar"), ("chatterbox", "/out/audio-test/chatterbox"), ("voxcpm", "/out/audio-test/voxcpm")):
    rows = []
    for i, t in terms.items():
        path = f"{folder}/{i}.wav"
        if not os.path.exists(path):
            rows.append({"id": i, "term": t, "heard": None, "cer": 1.0}); continue
        x, sr = sf.read(path, dtype="float32")
        if x.ndim > 1: x = x.mean(axis=1)
        if sr != 16000:
            x = np.interp(np.linspace(0, len(x), int(len(x) * 16000 / sr), endpoint=False), np.arange(len(x)), x).astype(np.float32)
        heard = asr({"raw": x, "sampling_rate": 16000}, generate_kwargs={"language": "arabic", "task": "transcribe"})["text"].strip()
        rows.append({"id": i, "term": t, "heard": heard, "cer": round(cer(norm(heard), norm(t)), 3)})
    out[voice] = {"mean_cer": round(sum(r["cer"] for r in rows) / len(rows), 3), "exact": sum(r["cer"] == 0 for r in rows), "rows": rows}
    print(f"{voice:14} mean CER {out[voice]['mean_cer']:.3f}  exact {out[voice]['exact']}/{len(rows)}", flush=True)
    for r in rows: print(f"   {r['id']:22} {r['term']:24} heard: {r['heard']}  cer {r['cer']}", flush=True)
json.dump(out, open("/out/audio-test/scores.json", "w"), ensure_ascii=False, indent=1)
PY

cd /tmp/w
echo "== chatterbox"; uv run -q --python 3.11 --with chatterbox-tts==0.1.7 --with soundfile python gen_chatterbox.py || echo "chatterbox FAILED"
echo "== voxcpm";     uv run -q --python 3.11 --with voxcpm==2.0.3 --with soundfile python gen_voxcpm.py || echo "voxcpm FAILED"
echo "== score";      uv run -q --python 3.11 --with torch --with "transformers<5" --with soundfile --with numpy --with accelerate python score.py
