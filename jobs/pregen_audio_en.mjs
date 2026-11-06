// English audio for every Darby glossary card with Kokoro-82M (kokoro-js, the same engine the browser uses),
// written straight into the mounted Storage Bucket. CPU Job on the node image:
//
//   hf jobs run --flavor cpu-upgrade --timeout 20m -v hf://spaces/FayezAlkh12/darby:/code \
//     -v hf://buckets/FayezAlkh12/darby-media:/out node:22-slim \
//     bash -c "cd /tmp && npm i --no-audit --no-fund kokoro-js@1.2.1 && cp /code/jobs/pregen_audio_en.mjs . && node pregen_audio_en.mjs"
// (Node resolves packages next to the script, so it runs from /tmp where kokoro-js is installed.)
import { mkdirSync, writeFileSync } from 'node:fs'
import { KokoroTTS } from 'kokoro-js'

const MODEL = 'onnx-community/Kokoro-82M-v1.0-ONNX'
// kokoro-js takes no revision: the model follows main (1939ad2a8e416c0acfeecc08a694d14ef25f2231 when written).
const REVISION = 'main (not pinnable through kokoro-js)'
const VOICE = 'af_heart'
const t0 = Date.now()
const res = await fetch('https://huggingface.co/datasets/nuvais/darby-ai-glossary-ar-en/resolve/main/data/glossary.json')
const cards = await res.json()
const tts = await KokoroTTS.from_pretrained(MODEL, { dtype: 'q8', device: 'cpu' })
mkdirSync('/out/audio/en', { recursive: true })
const files = {}
const failed = []
for (const c of cards) {
  try {
    const audio = await tts.generate(c.term_en, { voice: VOICE })
    await audio.save(`/out/audio/en/${c.id}.wav`)
    files[`en/${c.id}`] = `en/${c.id}.wav`
  } catch (e) {
    failed.push([c.id, String(e?.name ?? e)])
  }
}
const manifest = { lang: 'en', model: MODEL, revision: REVISION, voice: VOICE, licence: 'Apache 2.0', files, failed, seconds: (Date.now() - t0) / 1000 }
writeFileSync('/out/audio/manifest-en.json', JSON.stringify(manifest, null, 1))
console.log(JSON.stringify({ written: Object.keys(files).length, failed, seconds: manifest.seconds }))
