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

let recordingList: Promise<Record<string, string>> | null = null
/** Recording URLs by "en/<id>" and "ar/<id>", fetched once, so taps go straight to the bucket. */
function recordings(): Promise<Record<string, string>> {
  recordingList ??= fetch('/api/tts/recordings')
    .then((r) => (r.ok ? r.json() : {}))
    .catch(() => ({}))
  return recordingList
}

// Preloaded audio for the cards on screen, so a tap plays at once (kept small: a few cards at a time).
const preloaded = new Map<string, HTMLAudioElement>()
function audioFor(url: string): HTMLAudioElement {
  let a = preloaded.get(url)
  if (!a) {
    a = new Audio(url)
    a.preload = 'auto'
    preloaded.set(url, a)
    if (preloaded.size > 12) preloaded.delete(preloaded.keys().next().value!)
  }
  return a
}

async function termUrl(lang: 'en' | 'ar', termId: string): Promise<string | null> {
  const list = await recordings()
  // Arabic without a recording is spoken by the Space (and cached there); English without one is spoken in the browser.
  return list[`${lang}/${termId}`] ?? (lang === 'ar' ? `/api/tts/term/${encodeURIComponent(termId)}?lang=ar` : null)
}

/** Start loading a term's audio in both languages before the learner taps. */
export async function preloadTerm(termId: string): Promise<void> {
  if (!(await voiceEnabled())) return
  for (const lang of ['ar', 'en'] as const) {
    const url = await termUrl(lang, termId)
    if (url) audioFor(url)
  }
}

let current: HTMLAudioElement | null = null
function playUrl(url: string): Promise<void> {
  current?.pause()
  const a = audioFor(url)
  a.currentTime = 0
  current = a
  return new Promise((resolve, reject) => {
    a.onended = () => resolve()
    a.onerror = () => reject(new Error('audio failed'))
    a.play().catch(reject)
  })
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
    const url = await termUrl(lang, termId)
    if (url) return playUrl(url)
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
