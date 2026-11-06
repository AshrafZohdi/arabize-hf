// Listen buttons. English: the pre-generated Kokoro recording when the term has one, otherwise Kokoro-82M running
// in this browser (kokoro-js, loaded only on first use). Arabic: the recording, otherwise the Space speaks it
// (mms-tts-ara). Voice is on only when the server says so.

let enabled: Promise<boolean> | null = null
export function voiceEnabled(): Promise<boolean> {
  enabled ??= fetch('/api/health')
    .then((r) => r.json())
    .then((h) => Boolean(h.voice_enabled))
    .catch(() => false)
  return enabled
}

let current: HTMLAudioElement | null = null
function playUrl(url: string): Promise<void> {
  current?.pause()
  const a = new Audio(url)
  current = a
  return new Promise((resolve, reject) => {
    a.onended = () => resolve()
    a.onerror = () => reject(new Error('audio failed'))
    a.play().catch(reject)
  })
}

/** A recording exists when the server redirects to the bucket. GET (FastAPI answers HEAD with 405) without following
 * the redirect, so nothing is downloaded twice. */
async function hasRecording(url: string): Promise<boolean> {
  try {
    const r = await fetch(url, { redirect: 'manual' })
    return r.type === 'opaqueredirect' || r.status === 302
  } catch {
    return false
  }
}

type Kokoro = { generate: (text: string, opts: { voice: string }) => Promise<{ toBlob: () => Blob }> }
let kokoro: Promise<Kokoro> | null = null
function loadKokoro(): Promise<Kokoro> {
  kokoro ??= import('kokoro-js').then(({ KokoroTTS }) =>
    // kokoro-js takes no revision, so the model follows main (1939ad2a when this was written).
    KokoroTTS.from_pretrained('onnx-community/Kokoro-82M-v1.0-ONNX', { dtype: 'q8', device: 'wasm' }) as unknown as Promise<Kokoro>,
  )
  return kokoro
}

export async function speak(lang: 'en' | 'ar', text: string, termId?: string | null): Promise<void> {
  if (termId) {
    const url = `/api/tts/term/${encodeURIComponent(termId)}?lang=${lang}`
    if (lang === 'ar' || (await hasRecording(url))) return playUrl(url)
  }
  if (lang === 'ar') return playUrl(`/api/tts?lang=ar&text=${encodeURIComponent(text)}`)
  const tts = await loadKokoro()
  const audio = await tts.generate(text, { voice: 'af_heart' })
  const url = URL.createObjectURL(audio.toBlob())
  try {
    await playUrl(url)
  } finally {
    URL.revokeObjectURL(url)
  }
}
